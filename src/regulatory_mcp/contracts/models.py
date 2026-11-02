"""Schema v1: source identity, evidence, calculations, and retrieval semantics."""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    JsonValue,
    model_validator,
)


def utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


Timestamp = Annotated[AwareDatetime, AfterValidator(utc)]
Nonempty = Annotated[str, Field(min_length=1)]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
VerificationLevel = Literal["published_table", "model_reconstruction", "independent_validation"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    schema_version: Literal["1.0"] = "1.0"


class WarningDetail(Contract):
    code: Nonempty
    message: Nonempty


class ToolErrorDetail(WarningDetail):
    retryable: bool = False
    retry_after_seconds: float | None = Field(default=None, ge=0)


class ToolResponse[T](Contract):
    request_id: UUID = Field(default_factory=uuid4)
    status: Literal["ok", "partial", "error"]
    data: T | None = None
    evidence_refs: tuple[UUID, ...] = ()
    warnings: tuple[WarningDetail, ...] = ()
    error: ToolErrorDetail | None = None

    @model_validator(mode="after")
    def consistent_status(self) -> Self:
        if self.status == "error":
            if self.error is None or self.data is not None:
                raise ValueError("Error responses require an error and null data")
        elif self.error is not None or self.data is None:
            raise ValueError("Successful responses require data and no error")
        if self.status == "partial" and not self.warnings:
            raise ValueError("Partial responses require an explanation")
        return self


class SearchPage[T](Contract):
    items: tuple[T, ...]
    next_cursor: str | None = None
    retrieved_count: int = Field(ge=0)
    reported_total: int | None = Field(default=None, ge=0)
    retrieval_status: Literal["complete", "partial", "unknown"]
    query_scope: Nonempty
    page_count: int = Field(default=1, ge=0)
    request_count: int = Field(default=1, ge=0)
    started_at: Timestamp
    finished_at: Timestamp
    snapshot_consistency: Nonempty
    warnings: tuple[WarningDetail, ...] = ()

    @model_validator(mode="after")
    def consistent_coverage(self) -> Self:
        if self.finished_at < self.started_at or self.retrieved_count < len(self.items):
            raise ValueError("Invalid observation interval or retrieved count")
        if self.retrieval_status == "complete" and self.next_cursor is not None:
            raise ValueError("Complete retrieval cannot have a next cursor")
        if self.retrieval_status == "partial" and not self.warnings:
            raise ValueError("Partial retrieval requires a warning")
        return self


class Artifact(Contract):
    artifact_id: UUID = Field(default_factory=uuid4)
    source_system: Nonempty
    source_url: HttpUrl | None = None
    source_record_id: str | None = None
    origin: Literal["retrieved", "user_supplied"]
    retrieved_at: Timestamp
    sha256: Digest
    media_type: Nonempty
    byte_length: int = Field(ge=0)
    storage_ref: Digest
    title: str | None = None
    publication_date: str | None = None
    upstream_modified_at: Timestamp | None = None
    dataset_vintage: str | None = None
    access_terms: str | None = None

    @model_validator(mode="after")
    def source_identity(self) -> Self:
        if self.origin == "retrieved" and self.source_url is None:
            raise ValueError("Retrieved artifacts require a source URL")
        if self.sha256 != self.storage_ref:
            raise ValueError("Storage reference must equal the content digest")
        return self


class Locator(Contract):
    kind: Literal["pdf", "text", "table", "dataset"]
    page_index: int | None = Field(default=None, ge=0)
    printed_page_label: str | None = None
    section: str | None = None
    table_label: str | None = None
    row: str | None = None
    column: str | None = None
    start: int | None = Field(default=None, ge=0)
    end: int | None = Field(default=None, ge=0)
    query: str | None = None

    @model_validator(mode="after")
    def meaningful_locator(self) -> Self:
        if self.kind == "pdf" and self.page_index is None:
            raise ValueError("PDF evidence requires a zero-based page index")
        if self.kind == "table" and not self.table_label:
            raise ValueError("Table evidence requires a table label")
        if self.kind == "dataset" and not self.query:
            raise ValueError("Dataset evidence requires a query")
        if self.kind == "text" and (self.start is None or self.end is None):
            raise ValueError("Text evidence requires a half-open character span")
        if (self.start is None) != (self.end is None):
            raise ValueError("Text span requires both endpoints")
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise ValueError("Text span must be nonempty and ordered")
        return self


class Evidence(Contract):
    evidence_id: UUID = Field(default_factory=uuid4)
    artifact_id: UUID
    locator: Locator
    content: JsonValue
    extraction_method: Nonempty
    extraction_version: Nonempty
    transformations: tuple[str, ...] = ()
    review_state: Literal["unreviewed", "reviewed", "ambiguous"] = "unreviewed"


class CalculationInput(Contract):
    name: Nonempty
    value: JsonValue
    unit: Nonempty
    dollar_year: int | None = Field(default=None, ge=1900, le=2200)
    entity_definition: Nonempty
    basis: Literal["reported", "derived", "assumption", "independently_validated"]
    evidence_refs: tuple[UUID, ...] = ()
    assumption_rationale: Nonempty | None = None

    @model_validator(mode="after")
    def attributable_input(self) -> Self:
        if self.basis == "assumption":
            if self.assumption_rationale is None:
                raise ValueError("Assumptions require a rationale")
        elif not self.evidence_refs or self.assumption_rationale is not None:
            raise ValueError("Non-assumptions require evidence, not an assumption rationale")
        return self


class CalculationRun(Contract):
    run_id: UUID = Field(default_factory=uuid4)
    tool: Nonempty
    tool_version: Nonempty
    code_revision: Nonempty
    inputs: tuple[CalculationInput, ...] = Field(min_length=1)
    parameters: dict[str, JsonValue]
    formulas: tuple[Nonempty, ...] = Field(min_length=1)
    timing_convention: Nonempty
    transformations: tuple[str, ...] = ()
    outputs: dict[str, JsonValue]
    output_units: dict[str, Nonempty]
    warnings: tuple[WarningDetail, ...] = ()
    verification_level: VerificationLevel
    created_at: Timestamp

    @model_validator(mode="after")
    def output_units_and_names(self) -> Self:
        if not self.outputs or self.outputs.keys() != self.output_units.keys():
            raise ValueError("Every output requires exactly one unit")
        names = [item.name for item in self.inputs]
        if len(set(names)) != len(names):
            raise ValueError("Input names must be unique")
        return self
