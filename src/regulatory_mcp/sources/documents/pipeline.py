"""Ingestion, bounded extraction, and immutable reviewer attestations."""

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID, uuid4

from regulatory_mcp.contracts import Evidence, Locator
from regulatory_mcp.evidence import EvidenceStore, StoreError
from regulatory_mcp.sources.documents.parsing import MAX_UPLOAD_BYTES, parse, table_candidates


class Documents:
    def __init__(self, store: EvidenceStore):
        self.store = store

    def ingest(self, content_base64: str, media_type: str, title: str) -> dict[str, Any]:
        try:
            data = base64.b64decode(content_base64, validate=True)
        except ValueError, binascii.Error:
            raise StoreError("INVALID_INPUT: invalid base64 upload") from None
        if not data or len(data) > min(MAX_UPLOAD_BYTES, self.store.settings.max_download_bytes):
            raise StoreError("INVALID_INPUT: upload exceeds document or configured byte limit")
        artifact = self.store.retain(
            data,
            source_system="user-upload",
            origin="user_supplied",
            media_type=media_type,
            title=title,
        )
        try:
            parsed = parse(data, media_type)
        except StoreError as exc:
            raise StoreError(f"{exc}; retained artifact_id={artifact.artifact_id}") from None
        return {
            "artifact": artifact.model_dump(mode="json"),
            "kind": parsed["kind"],
            "count": len(parsed.get("pages", parsed.get("rows", []))),
            "warnings": ["User-supplied bytes; no independent source retrieval or review."],
        }

    def load(self, artifact_id: UUID) -> dict[str, Any]:
        artifact = self.store.artifact(artifact_id)
        return parse(self.store.read_bytes(artifact.sha256), artifact.media_type)

    def page(self, artifact_id: UUID, page_index: int, offset: int, limit: int) -> dict[str, Any]:
        parsed = self.load(artifact_id)
        text = pdf_page(parsed, page_index)
        if offset > len(text):
            raise StoreError("INVALID_INPUT: offset exceeds page text")
        return {
            "artifact_id": str(artifact_id),
            "page_index": page_index,
            "text": text[offset : offset + limit],
            "start": offset,
            "next_offset": offset + limit if offset + limit < len(text) else None,
            "page_count": len(parsed["pages"]),
            "extraction_version": parsed["version"],
            "warnings": ["No extractable text; OCR is unavailable."] if not text.strip() else [],
        }

    def search(
        self, artifact_id: UUID, query: str, start_page: int, page_count: int
    ) -> dict[str, Any]:
        parsed = self.load(artifact_id)
        pdf_page(parsed, start_page)
        pages = parsed["pages"]
        end = min(len(pages), start_page + page_count)
        matches = []
        for index in range(start_page, end):
            text = pages[index]
            # One bounded excerpt per matching page. Exact offsets use original text.
            import re

            match = re.search(re.escape(query), text, flags=re.IGNORECASE)
            if match:
                start = max(0, match.start() - 150)
                matches.append(
                    {"page_index": index, "start": start, "text": text[start : start + 600]}
                )
        return {
            "artifact_id": str(artifact_id),
            "items": matches,
            "next_page": end if end < len(pages) else None,
            "scope": {"start_page": start_page, "end_page_exclusive": end},
            "warnings": ["First match per page only; searches extracted text, not images."],
        }

    def table(self, artifact_id: UUID, page_index: int, offset: int, limit: int) -> dict[str, Any]:
        parsed = self.load(artifact_id)
        if parsed["kind"] == "pdf":
            text = pdf_page(parsed, page_index)
            count = len(text.splitlines())
            rows = table_candidates(text, offset, limit)
            extra = {
                "page_index": page_index,
                "warnings": [
                    "Layout candidates, not verified columns; inspect headers, units and footnotes."
                ],
            }
        else:
            count = len(parsed["rows"])
            rows = [
                {"row_index": i, "cells": row}
                for i, row in enumerate(parsed["rows"][offset : offset + limit], start=offset)
            ]
            extra = {
                "header": parsed["header"],
                "warnings": ["All CSV cells are preserved as strings."],
            }
        result = {
            "artifact_id": str(artifact_id),
            "rows": rows,
            "total_rows": count,
            "next_offset": offset + limit if offset + limit < count else None,
            **extra,
        }
        if len(json.dumps(result).encode()) > 20_000:
            raise StoreError("BUDGET_EXHAUSTED: table preview too large; request fewer rows")
        return result

    def create_evidence(self, artifact_id: UUID, locator: Locator) -> Evidence:
        parsed = self.load(artifact_id)
        if parsed["kind"] == "pdf":
            text = pdf_page(parsed, locator.page_index)
            if locator.kind != "pdf" or locator.start is None or locator.end is None:
                raise StoreError("INVALID_INPUT: PDF selection needs page index and text span")
            if not 0 <= locator.start < locator.end <= len(text):
                raise StoreError("INVALID_INPUT: PDF span outside extracted page")
            content = text[locator.start : locator.end]
        else:
            if locator.kind != "table" or locator.row is None or locator.column is None:
                raise StoreError("INVALID_INPUT: CSV selection needs table label, row and column")
            if not locator.row.isdecimal() or locator.column not in parsed["header"]:
                raise StoreError("INVALID_INPUT: unknown CSV row or column")
            row = int(locator.row)
            if row >= len(parsed["rows"]):
                raise StoreError("INVALID_INPUT: CSV row outside table")
            content = parsed["rows"][row][parsed["header"].index(locator.column)]
        if len(content) > 8000:
            raise StoreError("BUDGET_EXHAUSTED: evidence selection exceeds 8000 characters")
        record = Evidence(
            artifact_id=artifact_id,
            locator=locator,
            content=content,
            extraction_method="source-selection",
            extraction_version=parsed["version"],
        )
        self.store.save_evidence(record)
        return record

    def review(
        self, evidence_id: UUID, state: Literal["reviewed", "ambiguous"], note: str, confirmed: bool
    ) -> Evidence:
        if not confirmed:
            raise StoreError("INVALID_INPUT: explicit reviewer confirmation required")
        old = self.store.evidence(evidence_id)
        event = json.dumps(
            {
                "previous_evidence_id": str(evidence_id),
                "review_note": note,
                "reviewed_at": datetime.now(UTC).isoformat(),
                "attribution": "caller attestation; shared workspace",
            }
        )
        new = old.model_copy(
            update={
                "evidence_id": uuid4(),
                "review_state": state,
                "transformations": (*old.transformations, event),
            }
        )
        self.store.save_evidence(new)
        return new


def pdf_page(parsed: dict[str, Any], page_index: int | None) -> str:
    if parsed["kind"] != "pdf" or page_index is None or not 0 <= page_index < len(parsed["pages"]):
        raise StoreError("INVALID_INPUT: expected an existing zero-based PDF page")
    return str(parsed["pages"][page_index])
