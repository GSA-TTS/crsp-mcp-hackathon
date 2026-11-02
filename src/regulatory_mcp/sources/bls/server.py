"""Conventional BLS series retrieval tool."""

from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from regulatory_mcp.evidence import StoreError
from regulatory_mcp.sources.bls.client import BLS
from regulatory_mcp.sources.http import SourceError


def create_bls_server(adapter: BLS) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("BLS public time series", mask_error_details=True)

    @server.tool
    async def get_series(series_id: str, latest: bool = False) -> dict[str, Any]:
        """Retrieve the past three years or latest observation for one BLS series."""
        try:
            return await adapter.series(series_id, latest)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def get_popular_series(survey: str | None = None) -> dict[str, Any]:
        """Discover popular series IDs, optionally within a two-letter BLS survey."""
        try:
            return await adapter.popular(survey)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def get_surveys(survey: str | None = None) -> dict[str, Any]:
        """List surveys or inspect one survey's metadata and calculation capabilities."""
        try:
            return await adapter.surveys(survey)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    return server
