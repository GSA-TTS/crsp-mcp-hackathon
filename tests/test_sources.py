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
from regulatory_mcp.sources.http import DOWNLOAD_USER_AGENT, PublicHTTP, SourceError, retry_delay
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
        with pytest.raises(SourceError, match="credentials"):
            await adapter.get("https://api.regulations.gov", census_key="fixture-value")
        with pytest.raises(SourceError, match="API key must not be passed in the URL"):
            await adapter.get(
                "https://api.census.gov/data?key=fixture-value", census_key="fixture-value"
            )

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


def test_download_user_agent_is_host_scoped_and_credentials_stay_on_api(monkeypatch):
    async def run():
        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, content=b"fixture")

        real_client = httpx.AsyncClient

        def client(**kwargs):
            assert kwargs["follow_redirects"] is False
            return real_client(**kwargs, transport=httpx.MockTransport(respond))

        async def public_address(*args, **kwargs):
            return [(2, 1, 6, "", ("8.8.8.8", 443))]

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", public_address)
        monkeypatch.setattr("regulatory_mcp.sources.http.httpx.AsyncClient", client)
        adapter = PublicHTTP(Settings(source_request_interval_seconds=0.1))
        await adapter.get("https://api.regulations.gov/v4/documents", key="fixture-value")
        download = "https://downloads.regulations.gov/FDA-TEST-0001/content.pdf"
        assert await adapter.get(download) == b"fixture"
        await adapter.get("https://www.federalregister.gov/api/v1/documents.json")
        for credential in ({"key": "fixture-value"}, {"census_key": "fixture-value"}):
            with pytest.raises(SourceError, match="credentials cannot cross origins"):
                await adapter.get(download, **credential)
        assert len(requests) == 3
        assert requests[0].headers["X-Api-Key"] == "fixture-value"
        assert requests[0].headers["User-Agent"] == "regulatory-mcp/0.1"
        assert requests[1].headers["User-Agent"] == DOWNLOAD_USER_AGENT
        assert "regulatory-mcp/0.1" in DOWNLOAD_USER_AGENT
        assert DOWNLOAD_USER_AGENT.startswith("Mozilla/5.0")
        assert requests[2].headers["User-Agent"] == "regulatory-mcp/0.1"
        for request in requests[1:]:
            assert "X-Api-Key" not in request.headers
            assert "Authorization" not in request.headers
            assert "Cookie" not in request.headers
            assert "fixture-value" not in str(request.url)

    asyncio.run(run())


@pytest.mark.parametrize(
    ("origin", "location", "marker", "code"),
    [
        (
            "api.census.gov",
            "https://api.census.gov/data/missing_key.html",
            "1",
            "MISSING_CREDENTIALS",
        ),
        ("api.census.gov", "/data/missing_key.html", "1", "MISSING_CREDENTIALS"),
        ("api.census.gov", "https://example.com/missing_key.html", "1", "UPSTREAM_HTTP_ERROR"),
        ("api.census.gov", "/data/missing_key.html", "0", "UPSTREAM_HTTP_ERROR"),
        ("api.bls.gov", "https://api.census.gov/data/missing_key.html", "1", "UPSTREAM_HTTP_ERROR"),
    ],
)
def test_census_missing_key_redirect_is_classified_without_exposing_headers(
    origin, location, marker, code
):
    async def run():
        response = httpx.Response(
            302,
            headers={
                "Location": location,
                "X-DataWebAPI-KeyError": marker,
                "Set-Cookie": "private",
            },
            request=httpx.Request("GET", f"https://{origin}/data/2023/cbp?get=ESTAB&for=us:1"),
        )
        with pytest.raises(SourceError, match=code) as error:
            await PublicHTTP(Settings())._response(response, 0)
        assert "private" not in str(error.value) and "https://" not in str(error.value)
        if code == "MISSING_CREDENTIALS":
            with pytest.raises(SourceError, match="AUTHENTICATION_FAILED") as key_err:
                await PublicHTTP(Settings())._response(response, 0, had_census_key=True)
            assert "private" not in str(key_err.value) and "https://" not in str(key_err.value)

    asyncio.run(run())


def test_transport_uses_only_explicit_proxy_without_local_target_dns(monkeypatch):
    async def run():
        requested = {}

        async def target_dns_must_not_run(*args, **kwargs):
            raise AssertionError("proxy mode must not resolve the target locally")

        class Stream:
            async def __aenter__(self):
                return httpx.Response(200, content=b"fixture")

            async def __aexit__(self, *args):
                return False

        class Client:
            def __init__(self, **kwargs):
                requested.update(kwargs)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def stream(self, method, url, *, headers):
                requested.update(method=method, url=url, headers=headers)
                return Stream()

        monkeypatch.setattr(asyncio.get_running_loop(), "getaddrinfo", target_dns_must_not_run)
        monkeypatch.setattr("regulatory_mcp.sources.http.httpx.AsyncClient", Client)
        settings = Settings(
            https_proxy=SecretStr("http://proxy.internal:8080"),
            source_request_interval_seconds=0.1,
        )
        assert await PublicHTTP(settings).get("https://api.bls.gov/test") == b"fixture"
        assert requested["proxy"] == "http://proxy.internal:8080"
        assert requested["trust_env"] is False
        assert requested["follow_redirects"] is False
        assert requested["url"] == "https://api.bls.gov/test"

    asyncio.run(run())
