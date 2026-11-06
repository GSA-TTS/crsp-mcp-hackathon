"""Owner-response-derived contract subset; not a captured complete API response."""

import asyncio
import copy
import json
from uuid import UUID

import pytest
from fastmcp import Client
from pydantic import SecretStr
from test_sources import FixtureHTTP, resource

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.federal_register.client import FederalRegister
from regulatory_mcp.sources.federal_register.server import create_federal_register_server
from regulatory_mcp.sources.http import SourceError
from regulatory_mcp.sources.regulations.client import Regulations
from regulatory_mcp.sources.regulations.server import create_regulations_server

# Reduced transcription of fields supplied by the owner on 2026-11-06.
# The two supporting entries are a subset of ten embedded entries, not the full source.
RECORD = {
    "document_number": "2016-11867",
    "title": "Food Labeling: Revision of the Nutrition and Supplement Facts Labels",
    "type": "Rule",
    "action": "Final rule.",
    "publication_date": "2016-05-27",
    "citation": "81 FR 33742",
    "effective_on": "2016-07-26",
    "docket_ids": ["Docket No. FDA-2012-N-1210"],
    "regulation_id_numbers": ["0910-AF22"],
    "cfr_references": [{"chapter": None, "citation_url": None, "part": 101, "title": 21}],
    "correction_of": None,
    "corrections": [],
    "regulations_dot_gov_info": {
        "docket_id": "FDA-2012-N-1210",
        "regulation_id_number": "0910-AF22",
        "checked_regulationsdotgov_at": "2016-06-16T06:00:14Z",
        "supporting_documents_count": 435,
        "supporting_documents": [
            {
                "title": "Reference 214-Dorup-1993-Correlation between magnesium and p "
                "re Food Labeling: Revision of the Nutrition and Supplement Facts Labels",
                "document_id": "FDA-2012-N-1210-1207",
            },
            {
                "title": "Reference 222-USDA_Labeling re Food Labeling: Revision of the "
                "Nutrition and Supplement Facts Labels",
                "document_id": "FDA-2012-N-1210-1199",
            },
        ],
    },
}


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_fr_to_regulations_cross_source_chain(tmp_path, mode):
    async def run():
        store = EvidenceStore(tmp_path)
        raw = json.dumps(RECORD).encode()
        fr_http = FixtureHTTP(raw)
        regulations_http = FixtureHTTP({"data": resource(record_id="FDA-2012-N-1210-1207")})
        gateway = await create_gateway(
            {
                "federal_register": create_federal_register_server(FederalRegister(store, fr_http)),
                "regulations": create_regulations_server(
                    Regulations(
                        Settings(regulations_gov_api_key=SecretStr("fixture-value")),
                        store,
                        regulations_http,
                    )
                ),
            },
            Settings(gateway_mode=mode),
        )
        async with Client(gateway) as client:

            async def call(name, args):
                if mode == "codemode":
                    return (
                        await client.call_tool(
                            "execute", {"code": f"return await call_tool({name!r}, {args!r})"}
                        )
                    ).data
                return (await client.call_tool(name, args)).structured_content

            result = await call("federal_register_get_document", {"document_number": "2016-11867"})
            assert result["record"]["regulation_id_numbers"] == ["0910-AF22"]
            assert result["record"]["docket_ids"] == RECORD["docket_ids"]
            artifact = store.artifact(UUID(result["artifact_id"]))
            assert store.read_bytes(artifact.sha256) == raw and artifact.origin == "retrieved"
            refs = await call(
                "federal_register_inspect_supporting_documents",
                {"artifact_id": result["artifact_id"], "limit": 1},
            )
            assert refs["reported_total"] == 435 and refs["next_offset"] == 1
            detail = await call(
                "regulations_get_document", {"document_id": refs["items"][0]["document_id"]}
            )
            assert detail["record"]["id"] == "FDA-2012-N-1210-1207"
            tail = await call(
                "federal_register_inspect_supporting_documents",
                {"artifact_id": result["artifact_id"], "offset": 1},
            )
            assert tail["next_offset"] is None and tail["retrieval_status"] == "partial"

    asyncio.run(run())


def test_import_retains_user_supplied_origin(tmp_path):
    store = EvidenceStore(tmp_path)
    adapter = FederalRegister(store, FixtureHTTP())
    result = adapter.import_document("2016-11867", json.dumps(RECORD))
    artifact = store.artifact(UUID(result["artifact_id"]))
    assert artifact.origin == "user_supplied" and artifact.source_url is None
    assert result["record"]["correction_of"] is None
    assert result["record"]["corrections"] == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("document_number", "WRONG"),
        ("title", None),
        ("regulations_dot_gov_info", {"supporting_documents_count": "435"}),
    ],
)
def test_malformed_records_fail(tmp_path, field, value):
    data = copy.deepcopy(RECORD)
    data[field] = value
    with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
        FederalRegister(EvidenceStore(tmp_path), FixtureHTTP()).import_document(
            "2016-11867", json.dumps(data)
        )


def test_invalid_number_never_fetches(tmp_path):
    async def run():
        http = FixtureHTTP()
        with pytest.raises(SourceError, match="INVALID_INPUT"):
            await FederalRegister(EvidenceStore(tmp_path), http).get_document("../wrong")
        assert http.requests == []

    asyncio.run(run())
