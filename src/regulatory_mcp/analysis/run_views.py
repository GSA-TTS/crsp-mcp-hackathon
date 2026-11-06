"""Small run summaries and lossless, bounded manifest pages for MCP clients."""

import hashlib
import json
from typing import Any
from uuid import UUID

from regulatory_mcp.contracts import CalculationRun
from regulatory_mcp.evidence import EvidenceStore, StoreError


def model_run(store: EvidenceStore, run_id: UUID) -> CalculationRun:
    run = store.run(run_id)
    if run.tool not in {"evaluate_model", "reconcile_model_output"}:
        raise StoreError("INVALID_REFERENCE: expected a model evaluation or comparison run")
    return run


def summary(run: CalculationRun) -> dict[str, Any]:
    return {
        "run_id": str(run.run_id),
        "tool": run.tool,
        "tool_version": run.tool_version,
        "code_revision": run.code_revision,
        "created_at": run.created_at.isoformat(),
        "outputs": run.outputs,
        "output_units": run.output_units,
        "verification_level": run.verification_level,
        "warnings": [item.model_dump(mode="json") for item in run.warnings],
        "manifest_tool": "analysis_inspect_model_run",
        "manifest_included": False,
    }


def manifest_page(store: EvidenceStore, run_id: UUID, offset: int, limit: int) -> dict[str, Any]:
    if offset < 0 or not 1 <= limit <= 4000:
        raise StoreError("INVALID_INPUT: offset must be nonnegative and limit 1–4000")
    run = model_run(store, run_id)
    # ASCII serialization bounds wire size even for non-ASCII analyst text.
    text = json.dumps(
        run.model_dump(mode="json"), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    if offset > len(text):
        raise StoreError("INVALID_INPUT: offset exceeds manifest length")
    end = min(offset + limit, len(text))
    return {
        "run_id": str(run_id),
        "format": "json",
        "encoding": "ascii",
        "offset": offset,
        "next_offset": end if end < len(text) else None,
        "total_characters": len(text),
        "text": text[offset:end],
        "sha256": hashlib.sha256(text.encode("ascii")).hexdigest(),
        "instructions": "Concatenate text pages by offset, verify SHA-256, then parse JSON. "
        "Individual pages may split JSON tokens or escape sequences.",
    }
