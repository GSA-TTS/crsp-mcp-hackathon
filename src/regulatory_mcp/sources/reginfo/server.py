"""Public snapshot retrieval and bounded inspection tools."""

import asyncio
from typing import Annotated, Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from regulatory_mcp.evidence import StoreError
from regulatory_mcp.sources.http import SourceError
from regulatory_mcp.sources.reginfo.client import Reginfo, Report


def create_reginfo_server(adapter: Reginfo) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("Reginfo public reports", mask_error_details=True)

    @server.tool
    async def fetch_report(report: Report = "oira_pending") -> dict[str, Any]:
        """Retain an OIRA, agenda-202510, or pending-PRA public XML snapshot."""
        try:
            return await adapter.fetch(report)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def inspect_report(
        artifact_id: UUID,
        query: Annotated[str, Field(max_length=500)] = "",
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=50)] = 10,
    ) -> dict[str, Any]:
        """Search retained snapshot fields, preserving record type and source locators."""
        try:
            return await asyncio.to_thread(adapter.inspect, artifact_id, query, offset, limit)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    return server
