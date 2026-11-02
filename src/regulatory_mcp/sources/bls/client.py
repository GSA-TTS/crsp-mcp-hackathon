"""Preserve BLS periods, raw values, footnotes, and available series metadata."""

from typing import Any
from urllib.parse import quote, urlencode

from regulatory_mcp.sources.bls.schema import (
    observations,
    result_items,
    series_identifier,
    survey_identifier,
)
from regulatory_mcp.sources.economic import EconomicSource
from regulatory_mcp.sources.http import SourceError


class BLS(EconomicSource):
    async def series(self, series_id: str, latest: bool = False) -> dict[str, Any]:
        encoded_id = quote(series_identifier(series_id), safe="")
        url = f"https://api.bls.gov/publicAPI/v2/timeseries/data/{encoded_id}"
        if latest:
            url += "?latest=true"
        payload, artifact = await self.fetch(url, "bls.gov")
        series = result_items(payload, "series")
        if (
            len(series) != 1
            or not isinstance(series[0], dict)
            or series[0].get("seriesID") != series_id
        ):
            raise SourceError("SCHEMA_MISMATCH: unexpected BLS series identity")
        data = observations(series[0], latest)
        catalog = series[0].get("catalog")
        if catalog is not None and not isinstance(catalog, dict):
            raise SourceError("SCHEMA_MISMATCH: invalid BLS catalog")
        if catalog and catalog.get("series_id", series_id) != series_id:
            raise SourceError("SCHEMA_MISMATCH: catalog series identity mismatch")
        seasonality = catalog.get("seasonality") if catalog else None
        if seasonality is not None and not isinstance(seasonality, str):
            raise SourceError("SCHEMA_MISMATCH: invalid BLS seasonality")
        return {
            "series_id": series_id,
            "observations": data,
            "catalog": catalog,
            "artifact_id": str(artifact.artifact_id),
            "retrieved_at": artifact.retrieved_at.isoformat(),
            "source_messages": payload.get("message", []),
            "retrieval_status": "unknown",
            "scope": "Latest observation"
            if latest
            else "Past three years (BLS default GET window)",
            "units": None,
            "seasonal_adjustment": seasonality,
            "warnings": [
                "Requested-window observations only; not full series history. "
                "Units are not inferred from the series ID or measure description. "
                "Raw values, annual-average periods and footnotes are not transformed."
            ],
        }

    async def popular(self, survey: str | None = None) -> dict[str, Any]:
        url = "https://api.bls.gov/publicAPI/v2/timeseries/popular"
        if survey is not None:
            url += "?" + urlencode({"survey": survey_identifier(survey)})
        payload, artifact = await self.fetch(url, "bls.gov")
        items = result_items(payload, "series")
        ids = [item.get("seriesID") for item in items]
        for value in ids:
            if not isinstance(value, str):
                raise SourceError("SCHEMA_MISMATCH: invalid popular series ID")
            series_identifier(value)
        if len(set(ids)) != len(ids):
            raise SourceError("SCHEMA_MISMATCH: duplicate popular series ID")
        return {
            "items": items,
            "artifact_id": str(artifact.artifact_id),
            "survey": survey,
            "scope": "Source-provided popular series; not all available series",
            "source_messages": payload.get("message", []),
            "retrieval_status": "unknown",
        }

    async def surveys(self, survey: str | None = None) -> dict[str, Any]:
        url = "https://api.bls.gov/publicAPI/v2/surveys"
        if survey is not None:
            url += "/" + survey_identifier(survey)
        payload, artifact = await self.fetch(url, "bls.gov")
        items = result_items(payload, "survey")
        seen = set()
        for item in items:
            abbreviation = item.get("survey_abbreviation")
            if not isinstance(abbreviation, str) or not isinstance(item.get("survey_name"), str):
                raise SourceError("SCHEMA_MISMATCH: invalid survey metadata")
            survey_identifier(abbreviation)
            if abbreviation in seen or (survey is not None and abbreviation != survey):
                raise SourceError("SCHEMA_MISMATCH: unexpected or duplicate survey")
            seen.add(abbreviation)
        if survey is not None and len(items) != 1:
            raise SourceError("SCHEMA_MISMATCH: expected requested survey")
        return {
            "items": items,
            "artifact_id": str(artifact.artifact_id),
            "scope": "Survey metadata supplied by BLS",
            "retrieval_status": "unknown",
            "source_messages": payload.get("message", []),
        }
