"""Validate the owner-supplied document contract; retain full source JSON."""

import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.sources.federal_register.search import decode_search, search_summary
from regulatory_mcp.sources.http import PublicHTTP, SourceError

BASE = "https://www.federalregister.gov/api/v1/documents"


def document_number(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,39}", value) is None:
        raise SourceError("INVALID_INPUT: invalid Federal Register document number")
    return value


class SupportingDocument(BaseModel):
    model_config = ConfigDict(extra="ignore")
    document_id: str = Field(min_length=1, max_length=150)
    title: str = Field(max_length=2000)


class DocketInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")
    docket_id: str | None = None
    regulation_id_number: str | None = None
    checked_regulationsdotgov_at: str | None = None
    supporting_documents_count: StrictInt | None = Field(default=None, ge=0)
    supporting_documents: list[SupportingDocument] = Field(default_factory=list)


class Document(BaseModel):
    model_config = ConfigDict(extra="ignore")
    document_number: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=2000)
    type: str = Field(min_length=1, max_length=100)
    publication_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    action: str | None = None
    citation: str | None = None
    effective_on: str | None = None
    dates: str | None = None
    docket_ids: list[str] = Field(default_factory=list)
    regulation_id_numbers: list[str] = Field(default_factory=list)
    cfr_references: list[dict[str, Any]] = Field(default_factory=list)
    correction_of: Any = None
    corrections: list[Any] = Field(default_factory=list)
    html_url: str | None = None
    pdf_url: str | None = None
    raw_text_url: str | None = None
    full_text_xml_url: str | None = None
    regulations_dot_gov_info: DocketInfo | None = None


def decode(raw: bytes, expected: str) -> Document:
    try:
        record = Document.model_validate_json(raw)
    except ValidationError:
        raise SourceError("SCHEMA_MISMATCH: invalid Federal Register document") from None
    if record.document_number != expected:
        raise SourceError("SCHEMA_MISMATCH: document number differs from requested record")
    return record


def summarize(record: Document, artifact_id: UUID, origin: str) -> dict[str, Any]:
    data = record.model_dump(exclude={"regulations_dot_gov_info"})
    info = record.regulations_dot_gov_info
    data["regulations_dot_gov_info"] = (
        info.model_dump(exclude={"supporting_documents"}) if info else None
    )
    result = {
        "artifact_id": str(artifact_id),
        "origin": origin,
        "record": data,
        "embedded_supporting_count": len(info.supporting_documents) if info else 0,
        "warnings": [
            "Source-reported relationships, not independently verified version lineage.",
            "Embedded supporting documents may be partial and historical; "
            "inspect retained list separately.",
            "Linked URLs are metadata only; this tool does not retrieve their content.",
        ],
    }
    if len(json.dumps(result).encode()) > 20000:
        raise SourceError("BUDGET_EXHAUSTED: document summary exceeds output budget")
    return result


class FederalRegister:
    def __init__(self, store: EvidenceStore, http: PublicHTTP):
        self.store, self.http = store, http

    async def search_documents(self, query: str, page: int, page_size: int) -> dict[str, Any]:
        max_pages = min(20, self.store.settings.max_pages)
        if not query.strip() or len(query) > 500 or not 1 <= page <= max_pages:
            raise SourceError("INVALID_INPUT: nonempty search term and bounded page required")
        if not 1 <= page_size <= 5:
            raise SourceError("INVALID_INPUT: search page size must be 1–5")
        # Reconstruct the next request from typed inputs; never follow next_page_url.
        url = f"{BASE}.json?" + urlencode(
            {
                "conditions[term]": query,
                "per_page": page_size,
                "page": page,
            }
        )
        started_at = datetime.now(UTC).isoformat()
        raw = await self.http.get(url)
        result = decode_search(raw, page, page_size)
        artifact = await asyncio.to_thread(
            self.store.retain,
            raw,
            source_system="federalregister.gov",
            source_url=url,
            origin="retrieved",
            media_type="application/json",
            title=f"Federal Register keyword search: {query}",
        )
        summary = {
            **search_summary(result, query, page, page_size, max_pages),
            "artifact_id": str(artifact.artifact_id),
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
        }
        if len(json.dumps(summary).encode()) > 20000:
            raise SourceError("BUDGET_EXHAUSTED: search summary too large; reduce page size")
        return summary

    async def get_document(self, number: str) -> dict[str, Any]:
        url = f"{BASE}/{document_number(number)}.json"
        raw = await self.http.get(url)
        record = decode(raw, number)
        artifact = await asyncio.to_thread(
            self.store.retain,
            raw,
            source_system="federalregister.gov",
            source_url=url,
            source_record_id=number,
            origin="retrieved",
            media_type="application/json",
            title=record.title,
            publication_date=record.publication_date,
        )
        return summarize(record, artifact.artifact_id, artifact.origin)

    def import_document(self, number: str, content_json: str) -> dict[str, Any]:
        document_number(number)
        raw = content_json.encode()
        if len(raw) > min(1_000_000, self.store.settings.max_download_bytes):
            raise SourceError("BUDGET_EXHAUSTED: imported JSON exceeds byte limit")
        record = decode(raw, number)
        artifact = self.store.retain(
            raw,
            source_system="federalregister.gov",
            source_record_id=number,
            origin="user_supplied",
            media_type="application/json",
            title=record.title,
            publication_date=record.publication_date,
        )
        return summarize(record, artifact.artifact_id, artifact.origin)

    def supporting_documents(self, artifact_id: UUID, offset: int, limit: int) -> dict[str, Any]:
        artifact = self.store.artifact(artifact_id)
        if artifact.source_system != "federalregister.gov" or not artifact.source_record_id:
            raise SourceError("INVALID_REFERENCE: expected Federal Register document artifact")
        record = decode(self.store.read_bytes(artifact.sha256), artifact.source_record_id)
        info = record.regulations_dot_gov_info
        items = info.supporting_documents if info else []
        count = info.supporting_documents_count if info else None
        end = min(offset + limit, len(items))
        return {
            "artifact_id": str(artifact_id),
            "document_number": record.document_number,
            "items": [item.model_dump() for item in items[offset:end]],
            "embedded_count": len(items),
            "reported_total": count,
            "checked_regulationsdotgov_at": info.checked_regulationsdotgov_at if info else None,
            "next_offset": end if end < len(items) else None,
            "retrieval_status": "partial"
            if offset or end < len(items) or (count is not None and count > len(items))
            else "unknown",
            "warnings": [
                "End of embedded list is not end of docket; "
                "use Regulations.gov for current coverage."
            ],
        }
