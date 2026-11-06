"""Search envelope from owner response; reduced records are labeled fixture data."""

import asyncio
import json
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

import pytest
from fastmcp import Client
from test_federal_register import RECORD
from test_sources import FixtureHTTP

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.federal_register.client import FederalRegister
from regulatory_mcp.sources.federal_register.search import decode_search
from regulatory_mcp.sources.federal_register.server import create_federal_register_server
from regulatory_mcp.sources.http import SourceError


def search_payload():
    # Order and identities from the owner response; titles shortened for the fixture.
    pairs = [
        ("2022-20975", "Healthy definition", "Proposed Rule", "2022-09-29"),
        ("2020-01165", "Small Entity Compliance Guide", "Rule", "2020-02-04"),
        ("2018-27431", "Technical Amendments", "Rule", "2018-12-21"),
        ("2018-09476", "Extension of Compliance Dates", "Rule", "2018-05-04"),
        ("2018-27283", "National Bioengineered Food Disclosure Standard", "Rule", "2018-12-21"),
    ]
    return {
        "count": 20,
        "total_pages": 4,
        "next_page_url": "https://www.federalregister.gov/api/v1/documents?page=2",
        "results": [
            {"document_number": n, "title": title, "type": kind, "publication_date": date}
            for n, title, kind, date in pairs
        ],
    }


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_search_then_detail_and_exact_bytes(tmp_path, mode):
    async def run():
        payload = search_payload()
        raw = json.dumps(payload).encode()
        detail = {**RECORD, **payload["results"][3]}
        http = FixtureHTTP(raw, detail)
        store = EvidenceStore(tmp_path)
        gateway = await create_gateway(
            {"federal_register": create_federal_register_server(FederalRegister(store, http))},
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

            result = await call(
                "federal_register_search_documents", {"search_term": "FDA-2012-N-1210"}
            )
            assert result["reported_total"] == 20 and result["next_page"] == 2
            assert result["retrieval_status"] == "partial"
            assert result["items"][-1]["document_number"] == "2018-27283"
            assert result["query_scope"]["match_type"] == "keyword"
            artifact = store.artifact(UUID(result["artifact_id"]))
            assert store.read_bytes(artifact.sha256) == raw
            assert parse_qs(urlsplit(http.requests[0][0]).query) == {
                "conditions[term]": ["FDA-2012-N-1210"],
                "per_page": ["5"],
                "page": ["1"],
            }
            selected = await call(
                "federal_register_get_document",
                {"document_number": result["items"][3]["document_number"]},
            )
            assert selected["record"]["document_number"] == "2018-09476"

    asyncio.run(run())


def test_local_limit_and_untrusted_continuation(tmp_path):
    async def run():
        payload = search_payload()
        payload["next_page_url"] = "https://example.invalid/do-not-follow"
        http = FixtureHTTP(payload)
        adapter = FederalRegister(EvidenceStore(tmp_path, Settings(max_pages=1)), http)
        result = await adapter.search_documents("FDA-2012-N-1210", 1, 5)
        assert result["next_page"] is None and result["retrieval_status"] == "partial"
        assert len(http.requests) == 1
        with pytest.raises(SourceError, match="INVALID_INPUT"):
            await adapter.search_documents("FDA-2012-N-1210", 2, 5)

    asyncio.run(run())


@pytest.mark.parametrize("count,pages", [(0, 0), (5, 1)])
def test_final_or_empty_page_does_not_claim_exhaustiveness(tmp_path, count, pages):
    async def run():
        payload = search_payload()
        payload.update(count=count, total_pages=pages, next_page_url=None)
        payload["results"] = payload["results"][:count]
        adapter = FederalRegister(EvidenceStore(tmp_path), FixtureHTTP(payload))
        result = await adapter.search_documents("fixture", 1, 5)
        assert result["retrieval_status"] == "unknown" and result["next_page"] is None

    asyncio.run(run())


@pytest.mark.parametrize(
    "change",
    [
        {"count": "20"},
        {"total_pages": -1},
        {"results": [{}]},
        {"count": 1},
        {"next_page_url": None},
    ],
)
def test_bad_search_schema(change):
    payload = {**search_payload(), **change}
    with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
        decode_search(json.dumps(payload).encode(), 1, 5)
