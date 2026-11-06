"""Common JSON retention and validation for economic-source reads."""

import asyncio
import json
from typing import Any

from regulatory_mcp.contracts import Artifact
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.sources.http import PublicHTTP, SourceError


class EconomicSource:
    def __init__(self, store: EvidenceStore, http: PublicHTTP):
        self.store, self.http = store, http

    async def fetch(
        self, url: str, source: str, *, census_key: str | None = None
    ) -> tuple[Any, Artifact]:
        raw = await self.http.get(url, census_key=census_key)
        artifact = await asyncio.to_thread(
            self.store.retain,
            raw,
            source_system=source,
            source_url=url,
            origin="retrieved",
            media_type="application/json",
        )
        try:
            return json.loads(raw), artifact
        except (ValueError, UnicodeError) as exc:
            raise SourceError("SCHEMA_MISMATCH: economic source did not return JSON") from exc
