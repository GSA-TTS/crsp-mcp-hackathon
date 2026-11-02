"""Regression fixtures based on user-supplied BLS v2 documentation (2020-10-05)."""

import asyncio
from urllib.parse import urlsplit

import pytest
from fastmcp import Client
from test_economic_sources import HTTP, bls_payload

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.bls.client import BLS
from regulatory_mcp.sources.bls.server import create_bls_server
from regulatory_mcp.sources.http import SourceError


@pytest.mark.parametrize("series_id", ["OEUN000000056--5747213213", "AB_12#34", "CUUR0000SA0"])
@pytest.mark.parametrize("list_envelope", [True, False])
def test_documented_ids_envelopes_and_latest(tmp_path, series_id, list_envelope):
    async def run():
        payload = bls_payload()
        item = payload["Results"]["series"][0]
        item["seriesID"] = series_id
        item["catalog"] = {
            "series_id": series_id,
            "seasonality": "Not Seasonally Adjusted",
            "measure_data_type": "Average Hourly Wage",
        }
        item["data"][0]["aspects"] = [{"name": "Relative Standard Error", "value": "1.9"}]
        if list_envelope:
            payload["Results"] = [payload["Results"]]
        http = HTTP(payload)
        result = await BLS(EvidenceStore(tmp_path), http).series(series_id, latest=True)
        assert urlsplit(http.urls[0]).fragment == ""
        assert http.urls[0].endswith("?latest=true")
        if "#" in series_id:
            assert "%23" in http.urls[0]
        assert result["seasonal_adjustment"] == "Not Seasonally Adjusted"
        assert result["units"] is None
        assert result["observations"][0]["aspects"][0]["value"] == "1.9"

    asyncio.run(run())


@pytest.mark.parametrize("identifier", ["lowercase", "AB/../CD", "ABC?x=1", "", "A" * 101])
def test_invalid_ids_fail_before_http(tmp_path, identifier):
    async def run():
        http = HTTP()
        with pytest.raises(SourceError, match="INVALID_INPUT"):
            await BLS(EvidenceStore(tmp_path), http).series(identifier)
        assert not http.urls

    asyncio.run(run())


@pytest.mark.parametrize("results", [[], None, [None], [{"series": {}}], [{"series": [None]}]])
def test_malformed_envelopes(tmp_path, results):
    async def run():
        payload = bls_payload()
        payload["Results"] = results
        with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
            await BLS(EvidenceStore(tmp_path), HTTP(payload)).series("CUUR0000SA0")

    asyncio.run(run())


def test_discovery_to_latest_via_codemode(tmp_path):
    async def run():
        survey = {
            "survey_abbreviation": "TU",
            "survey_name": "American Time Use",
            "hasAnnualAverages": "false",
        }
        http = HTTP(
            {"status": "REQUEST_SUCCEEDED", "Results": {"survey": [survey]}},
            {"status": "REQUEST_SUCCEEDED", "Results": [{"series": [{"seriesID": "CUUR0000SA0"}]}]},
            bls_payload(),
        )
        adapter = BLS(EvidenceStore(tmp_path), http)
        gateway = await create_gateway(
            {"bls": create_bls_server(adapter)}, Settings(gateway_mode="codemode")
        )
        async with Client(gateway) as client:
            result = await client.call_tool(
                "execute",
                {
                    "code": """
surveys = await call_tool("bls_get_surveys", {"survey": "TU"})
popular = await call_tool("bls_get_popular_series", {})
series_id = popular["items"][0]["seriesID"]
data = await call_tool("bls_get_series", {"series_id": series_id, "latest": True})
return {"surveys": surveys, "data": data}
"""
                },
            )
        assert result.data["surveys"]["items"][0]["hasAnnualAverages"] == "false"
        assert result.data["data"]["scope"] == "Latest observation"
        assert http.urls[0].endswith("/surveys/TU")
        assert http.urls[1].endswith("/timeseries/popular")

    asyncio.run(run())
