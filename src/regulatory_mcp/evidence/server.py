"""Read-only MCP access to retained evidence and calculation manifests."""

import asyncio
from typing import Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from regulatory_mcp.contracts import Artifact, CalculationRun, Evidence
from regulatory_mcp.evidence.store import EvidenceStore, StoreError
from regulatory_mcp.sources.documents.pipeline import Documents
from regulatory_mcp.sources.documents.server import register_document_tools


def create_evidence_server(store: EvidenceStore) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("Retained evidence", mask_error_details=True)

    @server.tool
    async def get_artifact(artifact_id: UUID) -> Artifact:
        """Inspect provenance and verify the bytes of a retained artifact."""
        try:
            return await asyncio.to_thread(store.artifact, artifact_id)
        except StoreError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def get_evidence(evidence_id: UUID) -> Evidence:
        """Retrieve a passage or table locator and verify its source artifact."""
        try:
            return await asyncio.to_thread(store.evidence, evidence_id)
        except StoreError as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def get_run(run_id: UUID) -> CalculationRun:
        """Retrieve a calculation manifest and validate its evidence references."""
        try:
            return await asyncio.to_thread(store.run, run_id)
        except StoreError as exc:
            raise ToolError(str(exc)) from exc

    register_document_tools(server, Documents(store))
    return server
