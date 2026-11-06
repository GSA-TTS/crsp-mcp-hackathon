"""Configuration boundary tests; no external sources or credentials required."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from regulatory_mcp.config import Settings


def test_defaults_do_not_create_artifact_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings()
    assert settings.gateway_mode == "conventional"
    assert settings.artifact_dir == Path("artifacts")
    assert settings.regulations_gov_api_key is None
    assert settings.census_api_key is None
    assert not settings.artifact_dir.exists()


def test_environment_overrides_and_secret_redaction(monkeypatch: pytest.MonkeyPatch):
    sentinel = "fixture-value"  # Not an API credential.
    monkeypatch.setenv("REGULATIONS_GOV_API_KEY", sentinel)
    monkeypatch.setenv("CENSUS_API_KEY", sentinel)
    monkeypatch.setenv("REGULATORY_MCP_MAX_TOOL_CALLS", "3")
    monkeypatch.setenv("REGULATORY_MCP_ALLOWED_HOSTS", '["api.regulations.gov","www.reginfo.gov"]')
    monkeypatch.setenv("REGULATORY_MCP_HTTPS_PROXY", "http://proxy.internal:8080")
    settings = Settings()
    assert settings.max_tool_calls == 3
    assert settings.allowed_hosts == ("api.regulations.gov", "www.reginfo.gov")
    assert settings.https_proxy is not None
    assert "proxy.internal" not in repr(settings)
    assert "proxy.internal" not in settings.model_dump_json()
    assert settings.regulations_gov_api_key is not None
    assert settings.regulations_gov_api_key.get_secret_value() == sentinel
    assert sentinel not in repr(settings)
    assert sentinel not in settings.model_dump_json()
    assert settings.census_api_key is not None
    assert settings.census_api_key.get_secret_value() == sentinel


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("GATEWAY_MODE", "remote"),
        ("MAX_RETRIES", "-1"),
        ("MAX_PAGES", "0"),
        ("MAX_DOWNLOAD_BYTES", "100000001"),
        ("MAX_TOOL_CALLS", "0"),
        ("MAX_CONCURRENCY", "17"),
        ("MAX_OUTPUT_BYTES", "0"),
        ("REQUEST_TIMEOUT_SECONDS", "nan"),
        ("EXECUTION_TIMEOUT_SECONDS", "inf"),
        ("ARTIFACT_DIR", "../outside"),
        ("ARTIFACT_DIR", "/outside/artifacts"),
        ("ARTIFACT_DIR", "."),
        ("ALLOWED_HOSTS", '["*.gov"]'),
        ("ALLOWED_HOSTS", '["https://api.regulations.gov"]'),
        ("ALLOWED_HOSTS", '["127.0.0.1"]'),
        ("ALLOWED_HOSTS", '["localhost"]'),
        ("HTTPS_PROXY", "socks5://proxy.internal:1080"),
        ("HTTPS_PROXY", "http://proxy.internal/path"),
        ("HTTPS_PROXY", "http://proxy.internal:70000"),
    ],
)
def test_invalid_environment_fails_closed(name: str, value: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(f"REGULATORY_MCP_{name}", value)
    with pytest.raises(ValidationError):
        Settings()


def test_empty_allowlist_can_disable_outbound_access(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REGULATORY_MCP_ALLOWED_HOSTS", "[]")
    assert Settings().allowed_hosts == ()
