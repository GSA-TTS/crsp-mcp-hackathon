"""Bounded keyword-search contracts from the owner-supplied API response."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictInt, ValidationError

from regulatory_mcp.sources.http import SourceError


class SearchRecord(BaseModel):
    model_config = ConfigDict(extra="ignore")
    document_number: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,39}$")
    title: str = Field(min_length=1, max_length=2000)
    type: str = Field(min_length=1, max_length=100)
    publication_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    html_url: str | None = None
    pdf_url: str | None = None


class SearchResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    count: StrictInt = Field(ge=0)
    total_pages: StrictInt = Field(ge=0)
    next_page_url: str | None = None
    results: list[SearchRecord]


def decode_search(raw: bytes, page: int, page_size: int) -> SearchResponse:
    try:
        result = SearchResponse.model_validate_json(raw)
    except ValidationError:
        raise SourceError("SCHEMA_MISMATCH: invalid Federal Register search response") from None
    if len(result.results) > page_size or result.count < len(result.results):
        raise SourceError("SCHEMA_MISMATCH: inconsistent Federal Register search counts")
    if result.next_page_url and page >= result.total_pages:
        raise SourceError("SCHEMA_MISMATCH: continuation beyond reported final page")
    if result.total_pages > page and not result.next_page_url:
        raise SourceError("SCHEMA_MISMATCH: missing search continuation")
    return result


def search_summary(
    result: SearchResponse, query: str, page: int, page_size: int, max_pages: int
) -> dict[str, Any]:
    more = page < result.total_pages
    warnings = [
        "Keyword matches may only mention a docket; results are not verified docket members "
        "or a proposed/final version chain.",
        "One mutable search page, not an exhaustive or transactional snapshot. "
        "Upstream relevance order is preserved, not chronological order.",
        "Full response including agency metadata and excerpts is retained in artifact_id; "
        "result links are metadata, not downloaded content.",
    ]
    if more and page >= max_pages:
        warnings.append("Local page limit reached; additional results remain upstream.")
    return {
        "items": [record.model_dump() for record in result.results],
        "retrieved_count": len(result.results),
        "reported_total": result.count,
        "total_pages": result.total_pages,
        "next_page": page + 1 if more and page < max_pages else None,
        "retrieval_status": "partial" if more or page > 1 else "unknown",
        "query_scope": {
            "search_term": query,
            "page": page,
            "page_size": page_size,
            "match_type": "keyword",
        },
        "warnings": warnings,
    }
