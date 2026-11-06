"""Document lookup, keyword search, and bounded supporting-document inspection."""

import asyncio
from typing import Annotated, Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from regulatory_mcp.evidence import StoreError
from regulatory_mcp.sources.federal_register.client import FederalRegister
from regulatory_mcp.sources.http import SourceError


def create_federal_register_server(adapter: FederalRegister) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("Federal Register documents", mask_error_details=True)

    @server.tool
    async def search_documents(
        search_term: Annotated[str, Field(min_length=1, max_length=500)],
        page: Annotated[int, Field(ge=1, le=20)] = 1,
        page_size: Annotated[int, Field(ge=1, le=5)] = 5,
    ) -> dict[str, Any]:
        """Search keyword mentions, not exact docket membership; return one bounded page."""
        try:
            return await adapter.search_documents(search_term, page, page_size)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def get_document(document_number: str) -> dict[str, Any]:
        """Retrieve a Federal Register record with RIN, docket and CFR metadata."""
        try:
            return await adapter.get_document(document_number)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def import_document_json(
        document_number: str,
        content_json: Annotated[str, Field(min_length=1, max_length=1_000_000)],
    ) -> dict[str, Any]:
        """Retain caller-provided Federal Register JSON as user-supplied, not live retrieval."""
        try:
            return await asyncio.to_thread(adapter.import_document, document_number, content_json)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def inspect_supporting_documents(
        artifact_id: UUID,
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=5)] = 5,
    ) -> dict[str, Any]:
        """Page embedded document IDs; preserve reported totals and historical lookup date."""
        try:
            return await asyncio.to_thread(adapter.supporting_documents, artifact_id, offset, limit)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    return server
