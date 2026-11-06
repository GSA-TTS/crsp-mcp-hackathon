"""Deployment contract checks; actual CF staging remains a live operator gate."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_is_single_process_durable_and_secret_free():
    manifest = yaml.safe_load((ROOT / "manifest.yml").read_text())
    (app,) = manifest["applications"]
    assert app["instances"] == 1
    assert app["command"] == "python -m regulatory_mcp.http_server"
    assert app["path"] == "dist/cloudgov"
    assert app["services"] == ["regulatory-mcp-evidence"]
    assert app["health-check-http-endpoint"] == "/health"
    assert app["env"]["REGULATORY_MCP_STORAGE_BACKEND"] == "s3"
    assert "REGULATORY_MCP_BEARER_TOKEN" not in app["env"]
    assert "REGULATIONS_GOV_API_KEY" not in app["env"]
