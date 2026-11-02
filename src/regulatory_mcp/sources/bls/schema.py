"""Validate both response envelopes shown in the supplied BLS v2 signatures."""

import re
from typing import Any

from regulatory_mcp.sources.http import SourceError


def series_identifier(value: str) -> str:
    # 100 is a local resource bound, not a claimed BLS maximum.
    if re.fullmatch(r"[A-Z0-9_#-]{1,100}", value) is None:
        raise SourceError(
            "INVALID_INPUT: expected uppercase letters, digits, underscore, dash or hash"
        )
    return value


def survey_identifier(value: str) -> str:
    if re.fullmatch(r"[A-Z]{2}", value) is None:
        raise SourceError("INVALID_INPUT: expected a two-letter uppercase survey abbreviation")
    return value


def result_items(payload: Any, field: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict) or not isinstance(payload.get("status"), str):
        raise SourceError("SCHEMA_MISMATCH: expected BLS status")
    if payload["status"] != "REQUEST_SUCCEEDED":
        raise SourceError("UPSTREAM_REJECTED: BLS did not report request success")
    messages = payload.get("message", [])
    if not isinstance(messages, list) or any(not isinstance(x, str) for x in messages):
        raise SourceError("SCHEMA_MISMATCH: invalid BLS messages")
    envelope = payload.get("Results")
    groups = [envelope] if isinstance(envelope, dict) else envelope
    if not isinstance(groups, list) or not groups:
        raise SourceError("SCHEMA_MISMATCH: missing BLS Results envelope")
    items = []
    for group in groups:
        if not isinstance(group, dict) or not isinstance(group.get(field), list):
            raise SourceError("SCHEMA_MISMATCH: missing BLS result list")
        for item in group[field]:
            if not isinstance(item, dict):
                raise SourceError("SCHEMA_MISMATCH: invalid BLS result item")
            items.append(item)
    if len(items) > 1000:
        raise SourceError("BUDGET_EXHAUSTED: too many BLS results")
    return items


def observations(series: dict[str, Any], latest: bool) -> list[dict[str, Any]]:
    data = series.get("data")
    if not isinstance(data, list) or len(data) > (1 if latest else 1000):
        raise SourceError("SCHEMA_MISMATCH: invalid or excessive observation list")
    seen = set()
    for item in data:
        if not isinstance(item, dict) or any(
            not isinstance(item.get(key), str) for key in ("year", "period", "periodName", "value")
        ):
            raise SourceError("SCHEMA_MISMATCH: invalid BLS observation")
        key = (item["year"], item["period"])
        if key in seen or re.fullmatch(r"[0-9]{4}", key[0]) is None:
            raise SourceError("SCHEMA_MISMATCH: duplicate period or invalid year")
        seen.add(key)
        for field in ("footnotes", "aspects"):
            if field in item and (
                not isinstance(item[field], list)
                or any(not isinstance(entry, dict) for entry in item[field])
            ):
                raise SourceError("SCHEMA_MISMATCH: invalid BLS observation annotations")
    return list(data)
