"""Bounded docket manifests and downloads selected from fresh source metadata."""

import asyncio
import json
from typing import Any
from urllib.parse import unquote, urlsplit

from regulatory_mcp.sources.documents.parsing import MAX_UPLOAD_BYTES, parse
from regulatory_mcp.sources.http import SourceError
from regulatory_mcp.sources.regulations.client import Regulations, identifier

MEDIA_TYPES = {"pdf": "application/pdf", "csv": "text/csv"}


def download_url(value: Any, document_id: str, format_name: str) -> str:
    if not isinstance(value, str):
        raise SourceError("SCHEMA_MISMATCH: file URL missing")
    try:
        url = urlsplit(value)
        path = unquote(url.path)
        valid = (
            url.scheme == "https"
            and url.hostname == "downloads.regulations.gov"
            and url.port in (None, 443)
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
            and path.startswith(f"/{document_id}/")
            and path.endswith(f".{format_name}")
            and ".." not in path.split("/")
            and "\\" not in path
        )
    except ValueError:
        valid = False
    if not valid:
        raise SourceError("DESTINATION_REJECTED: unsupported document download location")
    return value


def files(detail: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for record in [detail["record"], *detail["attachments"]]:
        formats = record["attributes"].get("fileFormats") or []
        if not isinstance(formats, list):
            raise SourceError("SCHEMA_MISMATCH: invalid file format list")
        for item in formats:
            if not isinstance(item, dict):
                raise SourceError("SCHEMA_MISMATCH: invalid file format")
            result.append(
                {
                    "file_index": len(result),
                    "record_id": record["id"],
                    "format": item.get("format"),
                    "url": item.get("fileUrl"),
                    "reported_bytes": item.get("size"),
                    "supported": item.get("format") in MEDIA_TYPES,
                }
            )
    return result


class Collection:
    def __init__(self, adapter: Regulations):
        self.adapter = adapter

    async def list_files(self, document_id: str) -> dict[str, Any]:
        detail = await self.adapter.detail("documents", identifier(document_id), True)
        return {
            "document_id": document_id,
            "metadata_artifact_id": detail["artifact_id"],
            "items": files(detail),
            "warnings": [
                "Metadata only; file ordering can change. Retrieve by record ID and format."
            ],
        }

    async def retrieve(self, document_id: str, record_id: str, format_name: str) -> dict[str, Any]:
        detail = await self.adapter.detail("documents", identifier(document_id), True)
        identifier(record_id)
        if format_name not in MEDIA_TYPES:
            raise SourceError("UNSUPPORTED_CAPABILITY: only PDF and CSV retrieval is supported")
        selected = [
            f for f in files(detail) if f["record_id"] == record_id and f["format"] == format_name
        ]
        if len(selected) != 1:
            raise SourceError("INVALID_REFERENCE: expected one matching source file")
        selected_file = selected[0]
        url = download_url(selected_file["url"], document_id, format_name)
        size = selected_file["reported_bytes"]
        if isinstance(size, int) and size > MAX_UPLOAD_BYTES:
            raise SourceError("BUDGET_EXHAUSTED: reported file exceeds document parser limit")
        # No API credential is forwarded to the download host.
        raw = await self.adapter.http.get(url)
        artifact = await asyncio.to_thread(
            self.adapter.store.retain,
            raw,
            source_system="regulations.gov",
            source_url=url,
            source_record_id=record_id,
            origin="retrieved",
            media_type=MEDIA_TYPES[format_name],
            title=detail["record"]["attributes"].get("title"),
        )
        from regulatory_mcp.evidence import StoreError

        try:
            parsed = await asyncio.to_thread(parse, raw, MEDIA_TYPES[format_name])
        except StoreError as exc:
            raise StoreError(f"{exc}; retained artifact_id={artifact.artifact_id}") from None
        return {
            "artifact": artifact.model_dump(mode="json"),
            "metadata_artifact_id": detail["artifact_id"],
            "document_id": document_id,
            "count": len(parsed.get("pages", parsed.get("rows", []))),
            "warnings": ["Source bytes retrieved; extracted content still requires review."],
        }

    async def collect(
        self, docket_id: str, query: str, page: int, page_size: int
    ) -> dict[str, Any]:
        docket = await self.adapter.detail("dockets", identifier(docket_id))
        search = await self.adapter.search(
            "documents", {"docketId": docket_id, "searchTerm": query}, page, page_size
        )
        records = []
        for item in search["items"]:
            attrs = item["attributes"]
            records.append(
                {
                    "document_id": item["id"],
                    **{
                        k: attrs.get(k)
                        for k in (
                            "title",
                            "documentType",
                            "subtype",
                            "postedDate",
                            "lastModifiedDate",
                            "frDocNum",
                        )
                    },
                }
            )
        manifest = {
            "docket_id": docket_id,
            "docket_artifact_id": docket["artifact_id"],
            "search_artifact_id": search["artifact_id"],
            "documents": records,
            "docket_attributes": {
                k: docket["record"]["attributes"].get(k) for k in ("title", "rin", "agencyId")
            },
            "query_scope": search["query_scope"],
            "next_page": search["next_page"],
            "reported_total": search["reported_total"],
            "retrieval_status": search["retrieval_status"],
            "warnings": [
                *search["warnings"],
                "Document types/dates are source metadata, not verified proposed/final lineage. "
                "Files not downloaded.",
            ],
        }
        artifact = await asyncio.to_thread(
            self.adapter.store.retain,
            json.dumps(manifest).encode(),
            source_system="rule-collection",
            origin="user_supplied",
            media_type="application/json",
            title=f"Collection: {docket_id}",
        )
        return {"collection_artifact_id": str(artifact.artifact_id), **manifest}
