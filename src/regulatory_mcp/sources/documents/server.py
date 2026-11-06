"""Register document ingestion and review tools alongside evidence retrieval."""

import asyncio
from collections.abc import Callable
from typing import Annotated, Any, Literal
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from regulatory_mcp.contracts import Evidence, Locator
from regulatory_mcp.evidence import StoreError
from regulatory_mcp.sources.documents.pipeline import Documents

Short = Annotated[str, Field(min_length=1, max_length=500)]
Index = Annotated[int, Field(ge=0)]
Rows = Annotated[int, Field(ge=1, le=20)]


async def guarded[T](function: Callable[..., T], *args: Any) -> T:
    try:
        return await asyncio.to_thread(function, *args)
    except StoreError as exc:
        raise ToolError(str(exc)) from exc


def register_document_tools(server: FastMCP[Any], adapter: Documents) -> None:
    """Cohesive registration; individual handlers delegate bounded blocking work."""

    @server.tool
    async def ingest_upload(
        content_base64: Annotated[str, Field(min_length=1, max_length=6_666_668)],
        media_type: Literal["application/pdf", "text/csv"],
        title: Short,
    ) -> dict[str, Any]:
        """Retain user-supplied PDF/UTF-8 CSV bytes (5 MB max); never read server paths."""
        return await guarded(adapter.ingest, content_base64, media_type, title)

    @server.tool
    async def read_page(
        artifact_id: UUID,
        page_index: Index,
        offset: Index = 0,
        limit: Annotated[int, Field(ge=1, le=8000)] = 4000,
    ) -> dict[str, Any]:
        """Read a PDF text slice with zero-based page and exact extracted-text offsets."""
        return await guarded(adapter.page, artifact_id, page_index, offset, limit)

    @server.tool
    async def search_passages(
        artifact_id: UUID,
        query: Short,
        start_page: Index = 0,
        page_count: Rows = 10,
    ) -> dict[str, Any]:
        """Search a bounded PDF page range; return first matching excerpt per page."""
        return await guarded(adapter.search, artifact_id, query, start_page, page_count)

    @server.tool
    async def extract_tables(
        artifact_id: UUID,
        page_index: Index = 0,
        offset: Index = 0,
        limit: Rows = 10,
    ) -> dict[str, Any]:
        """Preview CSV rows or PDF layout candidates; PDF columns require confirmation."""
        return await guarded(adapter.table, artifact_id, page_index, offset, limit)

    @server.tool
    async def create_evidence(artifact_id: UUID, locator: Locator) -> Evidence:
        """Select exact PDF text or a CSV cell; content comes from source, not caller text."""
        return await guarded(adapter.create_evidence, artifact_id, locator)

    @server.tool
    async def record_review(
        evidence_id: UUID,
        state: Literal["reviewed", "ambiguous"],
        note: Short,
        confirmed: bool = False,
    ) -> Evidence:
        """Create an immutable caller-attested review copy; never infer human approval."""
        return await guarded(adapter.review, evidence_id, state, note, confirmed)
