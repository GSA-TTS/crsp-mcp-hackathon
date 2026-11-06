"""Six conventional read tools; no submissions or binary downloads."""

from typing import Annotated, Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from regulatory_mcp.evidence import StoreError
from regulatory_mcp.sources.http import SourceError
from regulatory_mcp.sources.regulations.client import Regulations, identifier
from regulatory_mcp.sources.regulations.collection import Collection

Term = Annotated[str, Field(max_length=500)]
Page = Annotated[int, Field(ge=1, le=20)]
Size = Annotated[int, Field(ge=5, le=250)]


def create_regulations_server(adapter: Regulations) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("Regulations.gov", mask_error_details=True)
    collection = Collection(adapter)

    @server.tool
    async def list_document_files(document_id: str) -> dict[str, Any]:
        """List primary and attachment file metadata for a public document ID."""
        try:
            return await collection.list_files(document_id)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def retrieve_document_file(
        document_id: str,
        record_id: str,
        format_name: str = "pdf",
    ) -> dict[str, Any]:
        """Retrieve a metadata-selected PDF/CSV into the document evidence store."""
        try:
            return await collection.retrieve(document_id, record_id, format_name)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def collect_docket_page(
        docket_id: str,
        search_term: Term = "",
        page: Page = 1,
        page_size: Annotated[int, Field(ge=5, le=25)] = 10,
    ) -> dict[str, Any]:
        """Retain a bounded docket/document manifest; no exhaustive collection claim."""
        try:
            return await collection.collect(docket_id, search_term, page, page_size)
        except (SourceError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    async def detail(kind: Any, record_id: str, attachments: bool = False) -> dict[str, Any]:
        try:
            return await adapter.detail(kind, record_id, attachments)
        except SourceError as exc:
            raise ToolError(str(exc)) from exc

    async def search(kind: Any, filters: dict[str, str], page: int, size: int) -> dict[str, Any]:
        try:
            return await adapter.search(kind, filters, page, size)
        except SourceError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def get_docket(docket_id: str) -> dict[str, Any]:
        """Get docket details, including available RIN values."""
        return await detail("dockets", docket_id)

    @server.tool
    async def get_document(document_id: str, include_attachments: bool = False) -> dict[str, Any]:
        """Get a document and optional attachment metadata."""
        return await detail("documents", document_id, include_attachments)

    @server.tool
    async def get_comment(comment_id: str, include_attachments: bool = False) -> dict[str, Any]:
        """Read a public comment; omit optional submitter identity fields."""
        return await detail("comments", comment_id, include_attachments)

    @server.tool
    async def search_dockets(
        search_term: Term = "", page: Page = 1, page_size: Size = 25
    ) -> dict[str, Any]:
        """Read one bounded docket-search page; coverage is not exhaustive."""
        return await search("dockets", {"searchTerm": search_term}, page, page_size)

    @server.tool
    async def search_documents(
        docket_id: str, search_term: Term = "", page: Page = 1, page_size: Size = 25
    ) -> dict[str, Any]:
        """Find documents within a docket, with optional keyword search."""
        return await search(
            "documents",
            {"docketId": identifier(docket_id), "searchTerm": search_term},
            page,
            page_size,
        )

    @server.tool
    async def search_comments(
        document_id: str, search_term: Term = "", page: Page = 1, page_size: Size = 25
    ) -> dict[str, Any]:
        """Resolve a public document ID to objectId, then search one comment page."""
        document = await detail("documents", document_id)
        object_id = document["record"]["attributes"].get("objectId")
        if not isinstance(object_id, str) or not object_id:
            raise ToolError("SCHEMA_MISMATCH: document has no objectId")
        result = await search(
            "comments", {"commentOnId": object_id, "searchTerm": search_term}, page, page_size
        )
        result["document_artifact_id"] = document["artifact_id"]
        return result

    return server
