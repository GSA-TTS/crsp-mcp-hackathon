"""Shared test fixtures and environment isolation."""

import os

import pytest


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent ambient shell settings from leaking into tests."""
    for name in list(os.environ):
        if (
            name.startswith("REGULATORY_MCP_")
            or name == "REGULATIONS_GOV_API_KEY"
            or name == "CENSUS_API_KEY"
        ):
            monkeypatch.delenv(name, raising=False)
