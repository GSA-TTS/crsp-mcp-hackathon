"""Conventional Census discovery, metadata, and retained table tools."""

from collections.abc import Awaitable
from typing import Annotated, Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from regulatory_mcp.evidence import StoreError
from regulatory_mcp.sources.census.client import Census
from regulatory_mcp.sources.http import SourceError


async def guarded(call: Awaitable[dict[str, Any]]) -> dict[str, Any]:
    try:
        return await call
    except (SourceError, StoreError) as exc:
        raise ToolError(str(exc)) from exc


def create_census_server(adapter: Census) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("Census public data", mask_error_details=True)

    @server.tool
    async def discover_datasets(query: str = "", limit: int = 20) -> dict[str, Any]:
        """Find actual catalog entries; SUSB availability is not assumed."""
        return await guarded(adapter.discover(query, limit))

    @server.tool
    async def get_variables(dataset: str, query: str = "", limit: int = 50) -> dict[str, Any]:
        """Inspect variable definitions, labels, and available annotations."""
        return await guarded(adapter.variables(dataset, query, limit))

    @server.tool
    async def fetch_table(
        dataset: str,
        variables: list[str],
        geography: str = "us:1",
        predicates: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Retain a metadata-validated national/state table with explicit query and vintage."""
        return await guarded(adapter.fetch_table(dataset, variables, geography, predicates or {}))

    @server.tool
    async def inspect_table(
        artifact_id: UUID,
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=100)] = 25,
    ) -> dict[str, Any]:
        """Page through raw table values without converting suppression markers to numbers."""
        try:
            return adapter.inspect(artifact_id, offset, limit)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    return server
