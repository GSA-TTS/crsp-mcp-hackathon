"""Use published catalog paths and variable metadata rather than guessed datasets."""

import json
import re
from typing import Any
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.sources.economic import EconomicSource
from regulatory_mcp.sources.http import PublicHTTP, SourceError

BASE = "https://api.census.gov/data"
VARIABLE_NAME = r"[A-Za-z][A-Za-z0-9_]{0,99}"
SUMMARY_FIELDS = (
    "label",
    "concept",
    "predicateType",
    "group",
    "required",
    "limit",
    "attributes",
    "attribute_of",
)


def metadata_summary(value: dict[str, Any]) -> dict[str, Any]:
    """Bound presentation only; full source definitions remain in the retained artifact."""
    result: dict[str, Any] = {}
    omitted, truncated = [], []
    for key in SUMMARY_FIELDS:
        if key not in value:
            continue
        item = value[key]
        if isinstance(item, str) and len(item) > 256:
            item = item[:256]
            truncated.append(key)
        if not isinstance(item, str | int | float | bool | type(None)):
            omitted.append(key)
        elif len(json.dumps({**result, key: item}).encode()) > 800:
            omitted.append(key)
        else:
            result[key] = item
    omitted.extend(key for key in ("values", "validValues") if key in value)
    if omitted:
        result["omitted_fields"] = omitted
    if truncated:
        result["truncated_fields"] = truncated
    return result


def dataset_path(value: str) -> str:
    if re.fullmatch(r"[0-9]{4}/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", value) is None:
        raise SourceError("INVALID_INPUT: expected a year-qualified Census dataset path")
    return value


def validate_variables(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("variables"), dict):
        raise SourceError("SCHEMA_MISMATCH: expected Census variable metadata")
    if any(not isinstance(value, dict) for value in payload["variables"].values()):
        raise SourceError("SCHEMA_MISMATCH: invalid variable description")
    variables = dict(payload["variables"])
    for name, definition in payload["variables"].items():
        if re.fullmatch(VARIABLE_NAME, name) is None:
            raise SourceError("SCHEMA_MISMATCH: invalid Census variable name")
        attributes = definition.get("attributes", "")
        if not isinstance(attributes, str):
            raise SourceError("SCHEMA_MISMATCH: invalid Census attribute list")
        if not attributes:
            continue
        for attribute in attributes.split(","):
            attribute = attribute.strip()
            if re.fullmatch(VARIABLE_NAME, attribute) is None:
                raise SourceError("SCHEMA_MISMATCH: invalid Census attribute name")
            # An advertised attribute is selectable even without a top-level definition.
            # Do not infer its type or flag meaning from the parent measure.
            variables.setdefault(attribute, {"attribute_of": name})
    return variables


class Census(EconomicSource):
    def __init__(self, store: EvidenceStore, http: PublicHTTP, settings: Settings | None = None):
        super().__init__(store, http)
        self.settings = settings

    async def discover(self, query: str, limit: int = 20) -> dict[str, Any]:
        if len(query) > 200 or not 1 <= limit <= 100:
            raise SourceError("INVALID_INPUT: query length at most 200 and limit 1–100")
        payload, artifact = await self.fetch(BASE + ".json", "census.gov")
        if not isinstance(payload, dict) or not isinstance(payload.get("dataset"), list):
            raise SourceError("SCHEMA_MISMATCH: expected Census dataset catalog")
        matches: list[dict[str, Any]] = []
        for entry in payload["dataset"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("title"), str):
                raise SourceError("SCHEMA_MISMATCH: invalid catalog entry")
            if query.casefold() not in str(entry).casefold():
                continue
            matches.append(
                {
                    k: entry[k]
                    for k in (
                        "title",
                        "description",
                        "c_vintage",
                        "c_dataset",
                        "distribution",
                        "c_variablesLink",
                        "c_geographyLink",
                    )
                    if k in entry
                }
            )
        return {
            "items": matches[:limit],
            "matched_count": len(matches),
            "artifact_id": str(artifact.artifact_id),
            "retrieval_status": "partial" if len(matches) > limit else "complete",
            "scope": "Matching entries in downloaded catalog; not evidence of SUSB availability.",
        }

    async def variables(self, dataset: str, query: str = "", limit: int = 50) -> dict[str, Any]:
        if len(query) > 200 or not 1 <= limit <= 100:
            raise SourceError("INVALID_INPUT: metadata query or limit outside bounds")
        url = f"{BASE}/{dataset_path(dataset)}/variables.json"
        payload, artifact = await self.fetch(url, "census.gov")
        variables = validate_variables(payload)
        matches: list[dict[str, Any]] = []
        matched_count = size = 0
        for key, value in variables.items():
            if query.casefold() not in (key + str(value)).casefold():
                continue
            matched_count += 1
            item = {"name": key, **metadata_summary(value)}
            item_size = len(json.dumps(item).encode())
            if len(matches) < limit and size + item_size <= 16000:
                matches.append(item)
                size += item_size
        return {
            "items": matches,
            "matched_count": matched_count,
            "dataset": dataset,
            "artifact_id": str(artifact.artifact_id),
            "retrieval_status": "partial" if len(matches) < matched_count else "complete",
            "warnings": [
                "Compact definitions; nested values are omitted and long text may be shortened. "
                "Full metadata is retained in artifact_id. Narrow query for omitted matches."
            ],
        }

    async def fetch_table(
        self, dataset: str, variables: list[str], geography: str, predicates: dict[str, str]
    ) -> dict[str, Any]:
        dataset_path(dataset)
        if not 1 <= len(variables) <= 40 or len(set(variables)) != len(variables):
            raise SourceError("INVALID_INPUT: select 1–40 distinct variables")
        if len(predicates) > 10 or len(geography) > 100:
            raise SourceError("INVALID_INPUT: too many predicates or excessive geography length")
        if re.fullmatch(r"(?:us:1|state:(?:\*|[0-9]{2}))", geography) is None:
            raise SourceError("INVALID_INPUT: supported geography is us:1 or state:NN or state:*")
        payload, metadata = await self.fetch(f"{BASE}/{dataset}/variables.json", "census.gov")
        descriptions = validate_variables(payload)
        for name in [*variables, *predicates]:
            if re.fullmatch(VARIABLE_NAME, name) is None or name not in descriptions:
                raise SourceError("INVALID_INPUT: variable absent from dataset metadata")
        if any(key.lower() in {"get", "for", "in", "key", "time"} for key in predicates):
            raise SourceError("INVALID_INPUT: reserved query parameter")
        if any(not value or len(value) > 100 for value in predicates.values()):
            raise SourceError("INVALID_INPUT: predicate values must be 1–100 characters")
        params = {"get": ",".join(variables), "for": geography, **predicates}
        key = (
            self.settings.census_api_key.get_secret_value()
            if self.settings and self.settings.census_api_key
            else None
        )
        payload, artifact = await self.fetch(
            f"{BASE}/{dataset}?{urlencode(params)}", "census.gov", census_key=key
        )
        rows = table(payload)
        if not set(variables) <= set(rows[0]):
            raise SourceError("SCHEMA_MISMATCH: response omitted requested columns")
        return {
            "artifact_id": str(artifact.artifact_id),
            "metadata_artifact_id": str(metadata.artifact_id),
            "dataset": dataset,
            "vintage": dataset.split("/")[0],
            "row_count": len(rows) - 1,
            "columns": rows[0],
            "query": params,
            "variable_metadata": {key: metadata_summary(descriptions[key]) for key in variables},
            "warnings": [
                "Values and suppression/annotation fields are preserved as returned. "
                "Select relevant flags and size/industry labels explicitly; "
                "dataset definitions determine firms versus establishments.",
                "Variable metadata is compact; full definitions are retained "
                "in metadata_artifact_id.",
            ],
        }

    def inspect(self, artifact_id: UUID, offset: int = 0, limit: int = 25) -> dict[str, Any]:
        if offset < 0 or not 1 <= limit <= 100:
            raise SourceError("INVALID_INPUT: nonnegative offset and limit 1–100 required")
        artifact = self.store.artifact(artifact_id)
        if artifact.source_system != "census.gov" or artifact.source_url is None:
            raise SourceError("INVALID_REFERENCE: expected Census table artifact")
        if not urlsplit(str(artifact.source_url)).query:
            raise SourceError("INVALID_REFERENCE: expected query response, not metadata")
        try:
            rows = table(json.loads(self.store.read_bytes(artifact.sha256)))
        except (ValueError, UnicodeError) as exc:
            raise SourceError("SCHEMA_MISMATCH: invalid retained table") from exc
        selected = rows[1:][offset : offset + limit]
        return {
            "artifact_id": str(artifact_id),
            "items": [dict(zip(rows[0], row, strict=True)) for row in selected],
            "row_count": len(rows) - 1,
            "next_offset": offset + limit if offset + limit < len(rows) - 1 else None,
            "retrieval_status": "partial" if offset or limit < len(rows) - 1 else "complete",
        }


def table(payload: Any) -> list[list[Any]]:
    if not isinstance(payload, list) or not payload or not isinstance(payload[0], list):
        raise SourceError("SCHEMA_MISMATCH: expected Census header and rows")
    header = payload[0]
    if not header or any(not isinstance(x, str) for x in header) or len(set(header)) != len(header):
        raise SourceError("SCHEMA_MISMATCH: invalid table header")
    if any(
        not isinstance(row, list)
        or len(row) != len(header)
        or any(value is not None and not isinstance(value, str) for value in row)
        for row in payload[1:]
    ):
        raise SourceError("SCHEMA_MISMATCH: malformed Census row")
    return list(payload)
