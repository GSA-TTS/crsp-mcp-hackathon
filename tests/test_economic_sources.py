"""Synthetic economic contracts and real cross-child MCP orchestration."""

import asyncio
import json
from uuid import UUID

import pytest
from fastmcp import Client
from pydantic import SecretStr

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
        self.census_keys = []

    async def get(self, url, *, census_key=None):
        self.urls.append(url)
        self.census_keys.append(census_key)
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


def test_census_table_with_key_preserves_clean_provenance(tmp_path):
    async def run():
        http = HTTP(METADATA, [["EMP", "us"], ["100", "1"]])
        settings = Settings(census_api_key=SecretStr("fixture-key"))
        adapter = Census(EvidenceStore(tmp_path), http, settings)
        result = await adapter.fetch_table("2022/cbp", ["EMP"], "us:1", {})
        assert http.census_keys[-1] == "fixture-key"
        assert "key=" not in http.urls[-1]
        assert "key" not in result["query"]
        artifact = EvidenceStore(tmp_path).artifact(UUID(result["artifact_id"]))
        assert "key=" not in str(artifact.source_url)

    asyncio.run(run())


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_census_large_metadata_and_advertised_flags_through_gateway(tmp_path, mode):
    """Synthetic reproduction of hosted metadata overflow and missing attribute lookup."""

    async def run():
        metadata = {
            "variables": {
                "NAICS2022": {
                    "label": "Industry of establishments",
                    "values": {"item": {str(i): "Establishment industry" for i in range(6000)}},
                },
                "ESTAB": {
                    "label": "Number of establishments",
                    "attributes": "ESTAB_F",
                    "predicateType": "int",
                },
            }
        }
        rows = [["ESTAB", "ESTAB_F", "NAICS2022", "us"], [None, "D", "00", "1"]]
        store = EvidenceStore(tmp_path)
        http = HTTP(metadata, metadata, rows)
        gateway = await create_gateway(
            {"census": create_census_server(Census(store, http))}, Settings(gateway_mode=mode)
        )
        async with Client(gateway) as client:

            async def call(name, args):
                if mode == "codemode":
                    code = f"return await call_tool({name!r}, {args!r})"
                    return (await client.call_tool("execute", {"code": code})).data
                return (await client.call_tool(name, args)).data

            found = await call(
                "census_get_variables", {"dataset": "2023/cbp", "query": "ESTAB", "limit": 10}
            )
            assert {item["name"] for item in found["items"]} >= {"ESTAB", "ESTAB_F"}
            assert "values" in found["items"][0]["omitted_fields"]
            source = store.artifact(UUID(found["artifact_id"]))
            assert json.loads(store.read_bytes(source.sha256)) == metadata
            fetched = await call(
                "census_fetch_table",
                {"dataset": "2023/cbp", "variables": ["ESTAB", "ESTAB_F", "NAICS2022"]},
            )
            assert fetched["variable_metadata"]["ESTAB_F"]["attribute_of"] == "ESTAB"
            assert "values" in fetched["variable_metadata"]["NAICS2022"]["omitted_fields"]
            page = await call("census_inspect_table", {"artifact_id": fetched["artifact_id"]})
            assert page["items"] == [{"ESTAB": None, "ESTAB_F": "D", "NAICS2022": "00", "us": "1"}]
            assert len(http.urls) == 3

    asyncio.run(run())


@pytest.mark.parametrize("attributes", [123, ["ESTAB_F"], "../bad", "ESTAB_F,,OTHER"])
def test_census_malformed_attributes_fail_before_table_request(tmp_path, attributes):
    async def run():
        http = HTTP({"variables": {"ESTAB": {"attributes": attributes}}})
        adapter = Census(EvidenceStore(tmp_path), http)
        with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
            await adapter.fetch_table("2023/cbp", ["ESTAB"], "us:1", {})
        assert len(http.urls) == 1

    asyncio.run(run())


def test_census_metadata_summary_budget_and_raw_retention(tmp_path):
    async def run():
        metadata = {
            "variables": {
                f"VAR{i}": {"label": "x" * 10000, "concept": "y" * 10000} for i in range(100)
            }
        }
        store = EvidenceStore(tmp_path)
        gateway = await create_gateway(
            {"census": create_census_server(Census(store, HTTP(metadata)))}, Settings()
        )
        async with Client(gateway) as client:
            result = (
                await client.call_tool(
                    "census_get_variables", {"dataset": "2023/cbp", "limit": 100}
                )
            ).data
        assert 0 < len(result["items"]) < result["matched_count"] == 100
        assert result["retrieval_status"] == "partial"
        assert result["items"][0]["truncated_fields"] == ["label", "concept"]
        artifact = store.artifact(UUID(result["artifact_id"]))
        assert json.loads(store.read_bytes(artifact.sha256)) == metadata

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
