"""Real ASGI/MCP HTTP lifecycle and bearer checks; no external network needed."""

import asyncio
import secrets

import httpx2 as httpx
import pytest
from pydantic import ValidationError

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.hosted_config import HostedSettings
from regulatory_mcp.http_server import create_http_app


def hosted(**overrides):
    values = {
        "bearer_token": secrets.token_urlsafe(32),
        "public_url": "https://mcp.example.gov",
        "storage_backend": "local",
    }
    return HostedSettings(**(values | overrides))


@pytest.mark.parametrize(
    "overrides",
    [
        {"bearer_token": "short"},
        {"bearer_token": " " * 40},
        {"public_url": "http://mcp.example.gov"},
        {"public_url": f"https://user:{secrets.token_hex(8)}@mcp.example.gov"},
        {"public_url": "https://mcp.example.gov/mcp"},
        {"public_url": "https://mcp.example.gov:99999"},
        {"bind_host": "0.0.0.0"},  # noqa: S104 -- verifies public binding rejection
        {"PORT": 0},
        {"bind_host": "example.com"},
    ],
)
def test_invalid_hosted_settings(overrides):
    with pytest.raises(ValidationError):
        hosted(**overrides)


def test_required_auth_and_masking(monkeypatch):
    monkeypatch.delenv("REGULATORY_MCP_BEARER_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        HostedSettings(public_url="https://mcp.example.gov")
    settings = hosted()
    assert settings.bearer_token.get_secret_value() not in repr(settings)


async def rpc(client, method, params=None, request_id=1):
    response = await client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        },
    )
    assert response.status_code == 200, response.text
    assert "mcp-session-id" not in response.headers
    return response.json()


async def authenticate(client, settings):
    assert (await client.get("/health")).status_code == 200
    assert (await client.post("/mcp", json={})).status_code == 401
    client.headers["Authorization"] = "Bearer incorrect"
    assert (await client.post("/mcp", json={})).status_code == 401
    client.headers["Authorization"] = "Bearer " + settings.bearer_token.get_secret_value()
    result = await rpc(
        client,
        "initialize",
        {
            "protocolVersion": "2025-11-25",
            "capabilities": {},
            "clientInfo": {"name": "http-test", "version": "1"},
        },
    )
    assert "serverInfo" in result["result"]
    client.headers["MCP-Protocol-Version"] = result["result"]["protocolVersion"]


def test_http_auth_catalog_calculation_and_reopen(tmp_path):
    async def run():
        settings = hosted()
        store = EvidenceStore(tmp_path)
        app = await create_http_app(Settings(), settings, store)
        headers = {"Accept": "application/json, text/event-stream"}
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url=settings.public_url,
                headers=headers,
            ) as client:
                await authenticate(client, settings)
                catalog = await rpc(client, "tools/list")
                names = {item["name"] for item in catalog["result"]["tools"]}
                assert {"analysis_calculate_break_even", "documents_get_run", "catalog"} <= names
                calculation = await rpc(
                    client,
                    "tools/call",
                    {
                        "name": "analysis_calculate_break_even",
                        "arguments": {"request": request()},
                    },
                )
                assert not calculation["result"].get("isError"), calculation
                data = calculation["result"]["structuredContent"]
                assert data["outputs"]["break_even"] == "10"
        # A new app/store has no transport session or in-memory persistence state.
        app = await create_http_app(Settings(), settings, EvidenceStore(tmp_path))
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url=settings.public_url,
                headers=dict(client.headers),
            ) as reopened:
                result = await rpc(
                    reopened,
                    "tools/call",
                    {
                        "name": "documents_get_run",
                        "arguments": {"run_id": data["run_id"]},
                    },
                )
                assert result["result"]["structuredContent"]["outputs"] == data["outputs"]
                assert (
                    await reopened.post(
                        "/mcp", headers={"Origin": "https://other.example"}, json={}
                    )
                ).status_code in {400, 403, 421}

    asyncio.run(run())


def request():
    def value(name, amount, unit):
        return {
            "name": name,
            "value": amount,
            "unit": unit,
            "dollar_year": 2025 if unit == "USD" else None,
            "entity_definition": "synthetic scenario",
            "basis": "assumption",
            "assumption_rationale": "synthetic HTTP test",
        }

    return {
        "assumption_rationale": "synthetic HTTP test",
        "cost": value("cost", "1000", "USD"),
        "quantity": value("quantity", "100", "units"),
    }
