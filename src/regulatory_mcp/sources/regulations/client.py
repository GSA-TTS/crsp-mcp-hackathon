"""Validated JSON:API records; bounded page reads with explicit coverage."""

import json
import re
from datetime import UTC, datetime
from typing import Any, Literal
from urllib.parse import urlencode

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.sources.http import PublicHTTP, SourceError

Kind = Literal["documents", "comments", "dockets"]
BASE = "https://api.regulations.gov/v4"
COMMENT_FIELDS = {
    "agencyId",
    "comment",
    "commentOnId",
    "docketId",
    "documentId",
    "documentType",
    "postedDate",
    "receiveDate",
    "restrictReason",
    "restrictReasonType",
    "reasonWithdrawn",
    "title",
    "trackingNbr",
    "withdrawn",
    "lastModifiedDate",
    "objectId",
    "numItemsReceived",
}


class Resource(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str = Field(min_length=1)
    type: str = Field(min_length=1)
    attributes: dict[str, JsonValue]


def identifier(value: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,149}", value) is None:
        raise SourceError("INVALID_INPUT: expected a public record identifier")
    return value


def resource(value: Any, kind: str) -> dict[str, Any]:
    try:
        item = Resource.model_validate(value)
    except ValidationError as exc:
        raise SourceError("SCHEMA_MISMATCH: invalid resource") from exc
    if item.type != kind:
        raise SourceError("SCHEMA_MISMATCH: unexpected resource type")
    result = item.model_dump(exclude_unset=True)
    if kind == "comments":
        result["attributes"] = {k: v for k, v in item.attributes.items() if k in COMMENT_FIELDS}
    return result


class Regulations:
    def __init__(self, settings: Settings, store: EvidenceStore, http: PublicHTTP):
        self.settings, self.store, self.http = settings, store, http

    async def _fetch(self, path: str, params: dict[str, str]) -> tuple[dict[str, Any], str]:
        key = self.settings.regulations_gov_api_key
        if key is None or not key.get_secret_value().strip():
            raise SourceError("MISSING_CREDENTIALS: set REGULATIONS_GOV_API_KEY")
        url = f"{BASE}/{path}" + ("?" + urlencode(params) if params else "")
        raw = await self.http.get(url, key=key.get_secret_value())
        try:
            payload = json.loads(raw)
        except (ValueError, UnicodeError) as exc:
            raise SourceError("SCHEMA_MISMATCH: expected JSON") from exc
        if not isinstance(payload, dict):
            raise SourceError("SCHEMA_MISMATCH: expected an object")
        artifact = self.store.retain(
            raw,
            source_system="regulations.gov",
            source_url=url,
            origin="retrieved",
            media_type="application/json",
        )
        return payload, str(artifact.artifact_id)

    async def detail(self, kind: Kind, record_id: str, attachments: bool = False) -> dict[str, Any]:
        payload, artifact = await self._fetch(
            f"{kind}/{identifier(record_id)}", {"include": "attachments"} if attachments else {}
        )
        data = resource(payload.get("data", payload), kind)
        if data["id"] != record_id:
            raise SourceError("SCHEMA_MISMATCH: returned ID differs from requested ID")
        included = payload.get("included", [])
        if not isinstance(included, list):
            raise SourceError("SCHEMA_MISMATCH: invalid included attachments")
        return {
            "record": data,
            "attachments": [resource(x, "attachments") for x in included] if attachments else [],
            "artifact_id": artifact,
            "warnings": ["Submitter identity fields omitted; free text can contain personal data."]
            if kind == "comments"
            else [],
        }

    async def search(
        self, kind: Kind, filters: dict[str, str], page: int, size: int
    ) -> dict[str, Any]:
        if not 1 <= page <= min(20, self.settings.max_pages) or not 5 <= size <= 250:
            raise SourceError("INVALID_INPUT: page must be 1–20 and size 5–250 within local limits")
        start = datetime.now(UTC)
        params = {f"filter[{k}]": v for k, v in filters.items() if v}
        params.update(
            {
                "page[number]": str(page),
                "page[size]": str(size),
                "sort": "lastModifiedDate," + ("docketId" if kind == "dockets" else "documentId"),
            }
        )
        payload, artifact = await self._fetch(kind, params)
        if not isinstance(payload.get("data"), list) or not isinstance(payload.get("meta"), dict):
            raise SourceError("SCHEMA_MISMATCH: missing search data or metadata")
        items = [resource(x, kind) for x in payload["data"]]
        meta = payload["meta"]
        total, more = meta.get("totalElements"), meta.get("hasNextPage")
        if type(total) is not int or total < 0 or type(more) is not bool:
            raise SourceError("SCHEMA_MISMATCH: invalid search totals or paging flag")
        unique = {x["id"]: x for x in items}
        # Even a final page does not establish complete coverage of a mutable source.
        return {
            "items": list(unique.values()),
            "retrieved_count": len(unique),
            "reported_total": total,
            "retrieval_status": "partial" if more or page > 1 else "unknown",
            "next_page": page + 1 if more and page < min(20, self.settings.max_pages) else None,
            "query_scope": {"kind": kind, "filters": filters, "page": page, "size": size},
            "started_at": start.isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "artifact_id": artifact,
            "warnings": [
                "Single bounded page; no exhaustive or transactional snapshot guarantee.",
                *(
                    ["Paging window exhausted; bulk timestamp continuation is not implemented."]
                    if more and page >= min(20, self.settings.max_pages)
                    else []
                ),
                *(["Duplicate IDs removed within this page."] if len(unique) != len(items) else []),
            ],
        }
