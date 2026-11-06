"""Fixture source metadata through actual collection/download/evidence MCP dispatch."""

import asyncio
from uuid import UUID

import pytest
from fastmcp import Client
from pydantic import SecretStr
from test_sources import FixtureHTTP, resource

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.evidence.server import create_evidence_server
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.http import SourceError
from regulatory_mcp.sources.regulations.client import Regulations
from regulatory_mcp.sources.regulations.collection import download_url
from regulatory_mcp.sources.regulations.server import create_regulations_server


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_source_file_to_evidence(mode, tmp_path):
    async def run():
        document_id = "FDA-TEST-0001"
        url = f"https://downloads.regulations.gov/{document_id}/content.csv"
        metadata = {
            "data": resource(
                record_id=document_id,
                title="Fixture",
                fileFormats=[{"fileUrl": url, "format": "csv", "size": 13}],
            )
        }
        http = FixtureHTTP(metadata, metadata, b"cost\n1000\n")
        store = EvidenceStore(tmp_path)
        adapter = Regulations(
            Settings(regulations_gov_api_key=SecretStr("fixture-value")), store, http
        )
        gateway = await create_gateway(
            {
                "regulations": create_regulations_server(adapter),
                "documents": create_evidence_server(store),
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

            listing = await call("regulations_list_document_files", {"document_id": document_id})
            assert listing["items"][0]["record_id"] == document_id
            result = await call(
                "regulations_retrieve_document_file",
                {"document_id": document_id, "record_id": document_id, "format_name": "csv"},
            )
            artifact = result["artifact"]
            assert artifact["origin"] == "retrieved" and artifact["source_url"] == url
            preview = await call(
                "documents_extract_tables", {"artifact_id": artifact["artifact_id"]}
            )
            assert preview["rows"][0]["cells"] == ["1000"]
            assert http.requests[-1] == (url, None)
            assert (
                store.artifact(UUID(result["metadata_artifact_id"])).source_system
                == "regulations.gov"
            )

    asyncio.run(run())


def test_docket_manifest_preserves_partial_coverage(tmp_path):
    async def run():
        from regulatory_mcp.sources.regulations.collection import Collection

        http = FixtureHTTP(
            {"data": resource("dockets", "FDA-TEST", title="Test docket", rin="0910-TEST")},
            {
                "data": [
                    resource(
                        record_id="FDA-TEST-0001", title="Proposed analysis", documentType="Other"
                    )
                ],
                "meta": {"totalElements": 30, "hasNextPage": True},
            },
        )
        store = EvidenceStore(tmp_path)
        adapter = Regulations(
            Settings(regulations_gov_api_key=SecretStr("fixture-value")), store, http
        )
        result = await Collection(adapter).collect("FDA-TEST", "impact", 1, 5)
        assert result["retrieval_status"] == "partial" and result["next_page"] == 2
        assert result["documents"][0]["documentType"] == "Other"
        assert (
            store.artifact(UUID(result["collection_artifact_id"])).source_system
            == "rule-collection"
        )

    asyncio.run(run())


@pytest.mark.parametrize(
    "url",
    [
        "http://downloads.regulations.gov/FDA-TEST/content.pdf",
        "https://example.com/FDA-TEST/content.pdf",
        "https://downloads.regulations.gov/OTHER/content.pdf",
        "https://downloads.regulations.gov/FDA-TEST/%2e%2e/content.pdf",
        "https://downloads.regulations.gov/FDA-TEST/content.pdf?key=x",
        "https://user@downloads.regulations.gov/FDA-TEST/content.pdf",
    ],
)
def test_download_location_rejected(url):
    with pytest.raises(SourceError, match="DESTINATION_REJECTED"):
        download_url(url, "FDA-TEST", "pdf")
