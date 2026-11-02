"""Source contract/error fixtures plus actual gateway dispatch; no network needed."""

import asyncio
import json
from uuid import UUID

import httpx2 as httpx
import pytest
from fastmcp import Client
from pydantic import SecretStr

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.http import PublicHTTP, SourceError, retry_delay
from regulatory_mcp.sources.reginfo.client import Reginfo, parse
from regulatory_mcp.sources.reginfo.server import create_reginfo_server
from regulatory_mcp.sources.regulations.client import Regulations
from regulatory_mcp.sources.regulations.server import create_regulations_server


class FixtureHTTP:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    async def get(self, url, *, key=None):
        self.requests.append((url, key))
        value = self.responses.pop(0)
        return value if isinstance(value, bytes) else json.dumps(value).encode()


def resource(kind="documents", record_id="FDA-TEST-0001", **attributes):
    return {"id": record_id, "type": kind, "attributes": attributes}


def test_regulations_auth_id_translation_and_attachments(tmp_path):
    async def run():
        http = FixtureHTTP(
            {"data": resource(objectId="internal-object")},
            {
                "data": [
                    resource(
                        "comments",
                        "COMMENT-1",
                        comment="fixture",
                        firstName="omit",
                        withdrawn=False,
                    )
                ],
                "meta": {"totalElements": 1, "hasNextPage": False},
            },
            {"data": resource(), "included": [resource("attachments", "ATTACH-1", fileFormats=[])]},
        )
        settings = Settings(regulations_gov_api_key=SecretStr("fixture-value"))
        adapter = Regulations(settings, EvidenceStore(tmp_path), http)
        async with Client(create_regulations_server(adapter)) as client:
            result = await client.call_tool("search_comments", {"document_id": "FDA-TEST-0001"})
            attrs = result.data["items"][0]["attributes"]
            assert attrs["withdrawn"] is False and "firstName" not in attrs
            assert "commentOnId%5D=internal-object" in http.requests[1][0]
            result = await client.call_tool(
                "get_document", {"document_id": "FDA-TEST-0001", "include_attachments": True}
            )
            assert result.data["attachments"][0]["id"] == "ATTACH-1"
        assert "include=attachments" in http.requests[2][0]
        assert all(
            key == "fixture-value" and "fixture-value" not in url for url, key in http.requests
        )

    asyncio.run(run())


def test_missing_credentials_never_requests(tmp_path):
    async def run():
        http = FixtureHTTP()
        adapter = Regulations(Settings(), EvidenceStore(tmp_path), http)
        with pytest.raises(SourceError, match="MISSING_CREDENTIALS"):
            await adapter.detail("dockets", "FDA-TEST")
        assert not http.requests

    asyncio.run(run())


@pytest.mark.parametrize(
    "payload",
    [
        b"not json",
        [],
        {"data": []},
        {"data": [], "meta": {"totalElements": "1", "hasNextPage": False}},
    ],
)
def test_invalid_search_shapes_fail(tmp_path, payload):
    async def run():
        adapter = Regulations(
            Settings(regulations_gov_api_key=SecretStr("fixture-value")),
            EvidenceStore(tmp_path),
            FixtureHTTP(payload),
        )
        with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
            await adapter.search("documents", {}, 1, 5)

    asyncio.run(run())


def test_window_limit_and_deduplication(tmp_path):
    async def run():
        payload = {
            "data": [resource(), resource()],
            "meta": {"totalElements": 6000, "hasNextPage": True},
        }
        adapter = Regulations(
            Settings(regulations_gov_api_key=SecretStr("fixture-value")),
            EvidenceStore(tmp_path),
            FixtureHTTP(payload),
        )
        result = await adapter.search("documents", {}, 20, 250)
        assert result["retrieved_count"] == 1
        assert result["next_page"] is None and result["retrieval_status"] == "partial"
        with pytest.raises(SourceError, match="INVALID_INPUT"):
            await adapter.search("documents", {}, 21, 250)
        with pytest.raises(SourceError, match="INVALID_INPUT"):
            await adapter.detail("documents", "../invalid")

    asyncio.run(run())


OIRA = (
    b'<OIRA_DATA RUNDATE="2026-10-30"><REGACT><RIN>0000-AA00</RIN><TITLE>Fixture</TITLE>'
    b"<DATE_RECEIVED>2026-10-01</DATE_RECEIVED></REGACT></OIRA_DATA>"
)
AGENDA = (
    b"<REGINFO_RIN_DATA><RIN_INFO><RIN>0000-AA00</RIN><RULE_TITLE>Fixture</RULE_TITLE>"
    b"<AGENCY><CODE>0000</CODE></AGENCY></RIN_INFO></REGINFO_RIN_DATA>"
)
PRA = (
    b"<InformationCollectionRequestList><InformationCollectionRequest>"
    b"<ICRReferenceNumber>202610-0000-001</ICRReferenceNumber><Title>Fixture</Title>"
    b"<RequestBurden><TotalRequestHour>0</TotalRequestHour></RequestBurden>"
    b"</InformationCollectionRequest></InformationCollectionRequestList>"
)


@pytest.mark.parametrize(
    ("report", "xml", "kind"),
    [
        ("oira_pending", OIRA, "oira_review"),
        ("agenda_202510", AGENDA, "agenda_entry"),
        ("pra_pending", PRA, "pra_request"),
    ],
)
def test_reginfo_snapshot_provenance_and_code_mode_wiring(tmp_path, report, xml, kind):
    async def run():
        store = EvidenceStore(tmp_path)
        adapter = Reginfo(store, FixtureHTTP(xml))
        gateway = await create_gateway(
            {"reginfo": create_reginfo_server(adapter)}, Settings(gateway_mode="codemode")
        )
        async with Client(gateway) as client:
            code = f'''snapshot = await call_tool("reginfo_fetch_report", {{"report": "{report}"}})
return await call_tool("reginfo_inspect_report", {{"artifact_id": snapshot["artifact_id"]}})'''
            result = (await client.call_tool("execute", {"code": code})).data
        assert result["items"][0]["record_type"] == kind
        artifact = store.artifact(UUID(result["artifact_id"]))
        assert store.read_bytes(artifact.sha256) == xml
        assert result["retrieval_status"] == "complete"

    asyncio.run(run())


@pytest.mark.parametrize(
    "xml",
    [
        b"<broken",
        b"<wrong/>",
        b'<!DOCTYPE x [<!ENTITY e "expanded">]><OIRA_DATA>&e;</OIRA_DATA>',
        b"<OIRA_DATA><unexpected/></OIRA_DATA>",
    ],
)
def test_xml_fails_closed(xml):
    with pytest.raises(SourceError, match="SCHEMA_MISMATCH"):
        parse(xml, "oira_pending")


def test_transport_status_and_size_handling():
    async def run():
        adapter = PublicHTTP(Settings(max_download_bytes=3, max_retries=1))
        assert await adapter._response(httpx.Response(200, content=b"abc"), 0) == b"abc"
        for response in [
            httpx.Response(200, content=b"abcd"),
            httpx.Response(302),
            httpx.Response(403),
        ]:
            with pytest.raises(SourceError):
                await adapter._response(response, 0)
        assert await adapter._response(httpx.Response(429, headers={"Retry-After": "2"}), 0) == 2
        with pytest.raises(SourceError, match="RATE_LIMITED"):
            await adapter._response(httpx.Response(429), 1)
        for url in [
            "http://www.reginfo.gov",
            "https://example.com",
            "https://www.reginfo.gov@127.0.0.1",
        ]:
            with pytest.raises(SourceError, match="DESTINATION_REJECTED"):
                await adapter.get(url)
        with pytest.raises(SourceError, match="credentials"):
            await adapter.get("https://www.reginfo.gov", key="fixture-value")

    asyncio.run(run())
    with pytest.raises(SourceError, match="RATE_LIMITED"):
        retry_delay("1000", 0)


def test_transport_rejects_private_dns_before_http(monkeypatch):
    async def run():
        async def private_address(*args, **kwargs):
            return [(2, 1, 6, "", ("127.0.0.1", 443))]

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", private_address)
        with pytest.raises(SourceError, match="nonpublic address"):
            await PublicHTTP(Settings()).get("https://www.reginfo.gov/public/do/PRAXML")

    asyncio.run(run())
