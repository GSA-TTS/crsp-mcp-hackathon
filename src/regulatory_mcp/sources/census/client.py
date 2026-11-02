"""Use published catalog paths and variable metadata rather than guessed datasets."""

import re
from typing import Any
from urllib.parse import urlencode, urlsplit
from uuid import UUID

from regulatory_mcp.sources.economic import EconomicSource
from regulatory_mcp.sources.http import SourceError

BASE = "https://api.census.gov/data"


def dataset_path(value: str) -> str:
    if re.fullmatch(r"[0-9]{4}/[a-zA-Z0-9_-]+(?:/[a-zA-Z0-9_-]+)*", value) is None:
        raise SourceError("INVALID_INPUT: expected a year-qualified Census dataset path")
    return value


def validate_variables(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("variables"), dict):
        raise SourceError("SCHEMA_MISMATCH: expected Census variable metadata")
    if any(not isinstance(value, dict) for value in payload["variables"].values()):
        raise SourceError("SCHEMA_MISMATCH: invalid variable description")
    return dict(payload["variables"])


class Census(EconomicSource):
    async def discover(self, query: str, limit: int = 20) -> dict[str, Any]:
        if len(query) > 200 or not 1 <= limit <= 100:
            raise SourceError("INVALID_INPUT: query length at most 200 and limit 1–100")
        payload, artifact = await self.fetch(BASE + ".json", "census.gov")
        if not isinstance(payload, dict) or not isinstance(payload.get("dataset"), list):
            raise SourceError("SCHEMA_MISMATCH: expected Census dataset catalog")
        matches = []
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
        matches = [
            {"name": key, **value}
            for key, value in variables.items()
            if query.casefold() in (key + str(value)).casefold()
        ]
        return {
            "items": matches[:limit],
            "matched_count": len(matches),
            "dataset": dataset,
            "artifact_id": str(artifact.artifact_id),
            "retrieval_status": "partial" if len(matches) > limit else "complete",
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
            if (
                re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", name) is None
                or name not in descriptions
            ):
                raise SourceError("INVALID_INPUT: variable absent from dataset metadata")
        if any(key.lower() in {"get", "for", "in", "key", "time"} for key in predicates):
            raise SourceError("INVALID_INPUT: reserved query parameter")
        if any(not value or len(value) > 100 for value in predicates.values()):
            raise SourceError("INVALID_INPUT: predicate values must be 1–100 characters")
        params = {"get": ",".join(variables), "for": geography, **predicates}
        payload, artifact = await self.fetch(f"{BASE}/{dataset}?{urlencode(params)}", "census.gov")
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
            "variable_metadata": {key: descriptions[key] for key in variables},
            "warnings": [
                "Values and suppression/annotation fields are preserved as returned. "
                "Select relevant flags and size/industry labels explicitly; "
                "dataset definitions determine firms versus establishments."
            ],
        }

    def inspect(self, artifact_id: UUID, offset: int = 0, limit: int = 25) -> dict[str, Any]:
        import json

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
