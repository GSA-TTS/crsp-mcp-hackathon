"""Synthetic economic contracts and real cross-child MCP orchestration."""

import asyncio
import json
from uuid import UUID

import pytest
from fastmcp import Client

from regulatory_mcp.analysis.server import create_analysis_server
from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.bls.client import BLS
from regulatory_mcp.sources.bls.server import create_bls_server
from regulatory_mcp.sources.census.client import Census, table
from regulatory_mcp.sources.census.server import create_census_server
from regulatory_mcp.sources.http import SourceError


class HTTP:
    def __init__(self, *payloads):
        self.payloads = list(payloads)
        self.urls = []

    async def get(self, url):
        self.urls.append(url)
        return json.dumps(self.payloads.pop(0)).encode()


METADATA = {
    "variables": {
        "EMP": {"label": "Employees"},
        "EMP_F": {"label": "Flag"},
        "NAICS2017": {"label": "Industry"},
        "EMPSZES": {"label": "Size"},
    }
}


def bls_payload():
    return {
        "status": "REQUEST_SUCCEEDED",
        "message": [],
        "Results": {
            "series": [
                {
                    "seriesID": "CUUR0000SA0",
                    "data": [
                        {
                            "year": "2023",
                            "period": "M13",
                            "periodName": "Annual",
                            "value": "300.0",
                            "footnotes": [{"code": "P", "text": "Preliminary"}],
                        }
                    ],
                }
            ]
        },
    }


def test_census_discovery_and_metadata(tmp_path):
    async def run():
        adapter = Census(
            EvidenceStore(tmp_path),
            HTTP(
                {
                    "dataset": [
                        {
                            "title": "County Business Patterns",
                            "c_vintage": 2022,
                            "c_dataset": ["cbp"],
                        }
                    ]
                },
                METADATA,
            ),
        )
        result = await adapter.discover("SUSB")
        assert result["items"] == []
        result = await adapter.variables("2022/cbp", "employees")
        assert result["items"][0]["name"] == "EMP"

    asyncio.run(run())


def test_census_retained_table_flags_and_queries(tmp_path):
    async def run():
        http = HTTP(METADATA, [["EMP", "EMP_F", "us"], [None, "D", "1"], ["100", None, "1"]])
        adapter = Census(EvidenceStore(tmp_path), http)
        result = await adapter.fetch_table("2022/cbp", ["EMP", "EMP_F"], "us:1", {"EMPSZES": "001"})
        assert result["vintage"] == "2022" and result["row_count"] == 2
        assert "EMPSZES=001" in http.urls[-1] and "key=" not in http.urls[-1]
        page = adapter.inspect(UUID(result["artifact_id"]), limit=1)
        assert page["items"][0] == {"EMP": None, "EMP_F": "D", "us": "1"}
        assert page["next_offset"] == 1
        assert adapter.inspect(UUID(result["artifact_id"]), offset=1)["items"][0]["EMP"] == "100"

    asyncio.run(run())


@pytest.mark.parametrize("payload", [[], {}, [["x", "x"]], [["x"], [1]], [["x"], []]])
def test_census_bad_table(payload):
    with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
        table(payload)


def test_unknown_variable_and_unsafe_dataset(tmp_path):
    async def run():
        http = HTTP(METADATA)
        adapter = Census(EvidenceStore(tmp_path), http)
        with pytest.raises(SourceError, match="INVALID_INPUT"):
            await adapter.fetch_table("2022/../cbp", ["EMP"], "us:1", {})
        assert not http.urls
        with pytest.raises(SourceError, match="absent"):
            await adapter.fetch_table("2022/cbp", ["INVENTED"], "us:1", {})
        assert len(http.urls) == 1

    asyncio.run(run())


def test_bls_preserves_periods_footnotes_and_unknown_units(tmp_path):
    async def run():
        adapter = BLS(EvidenceStore(tmp_path), HTTP(bls_payload()))
        result = await adapter.series("CUUR0000SA0")
        assert result["observations"][0]["period"] == "M13"
        assert result["observations"][0]["footnotes"][0]["code"] == "P"
        assert result["units"] is None and result["seasonal_adjustment"] is None
        assert result["retrieval_status"] == "unknown"

    asyncio.run(run())


@pytest.mark.parametrize("case", ["status", "identity", "duplicate", "shape"])
def test_bls_rejects_bad_response(tmp_path, case):
    async def run():
        payload = bls_payload()
        series = payload["Results"]["series"][0]
        if case == "status":
            payload["status"] = "REQUEST_FAILED"
        elif case == "identity":
            series["seriesID"] = "WRONG"
        elif case == "duplicate":
            series["data"] *= 2
        else:
            series["data"][0]["year"] = 2023
        with pytest.raises(SourceError):
            await BLS(EvidenceStore(tmp_path), HTTP(payload)).series("CUUR0000SA0")

    asyncio.run(run())


def test_source_to_analysis_via_code_mode(tmp_path):
    async def run():
        store = EvidenceStore(tmp_path)
        gateway = await create_gateway(
            {
                "bls": create_bls_server(BLS(store, HTTP(bls_payload()))),
                "census": create_census_server(Census(store, HTTP())),
                "analysis": create_analysis_server(store),
            },
            Settings(gateway_mode="codemode"),
        )
        code = """
source = await call_tool("bls_get_series", {"series_id": "CUUR0000SA0"})
value = source["observations"][0]["value"]
item = {"name": "fixture_index", "value": value, "unit": "index points",
        "entity_definition": "Synthetic BLS-shaped fixture",
        "basis": "assumption",
        "assumption_rationale": "Fixture only; source artifact " + source["artifact_id"]}
reported = dict(item)
reported["value"] = "300"
run = await call_tool("analysis_reconcile_reported_values", {"request": {
    "calculated": item, "reported": reported,
    "assumption_rationale": "Synthetic wiring; units asserted for fixture only"}})
return {"artifact_id": source["artifact_id"], "run_id": run["run_id"], "outputs": run["outputs"]}
"""
        async with Client(gateway) as client:
            result = (await client.call_tool("execute", {"code": code})).structured_content
        assert result["outputs"]["within_tolerance"] is True
        assert store.artifact(UUID(result["artifact_id"])).source_system == "bls.gov"
        assert result["artifact_id"] in store.run(UUID(result["run_id"])).model_dump_json()

    asyncio.run(run())
