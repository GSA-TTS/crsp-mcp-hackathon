"""Content-addressed bytes and immutable JSON records over a byte-store boundary."""

import hashlib
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from regulatory_mcp.config import Settings
from regulatory_mcp.contracts import Artifact, CalculationRun, EconomicModel, Evidence
from regulatory_mcp.evidence.backend import ByteStore
from regulatory_mcp.evidence.backend import StoreError as StoreError
from regulatory_mcp.evidence.local import LocalByteStore


class EvidenceStore:
    """Generated object names; shared validation for local and remote storage."""

    def __init__(
        self,
        project_root: Path,
        settings: Settings | None = None,
        *,
        backend: ByteStore | None = None,
    ):
        self.settings = settings or Settings()
        self.backend = (
            backend if backend is not None else LocalByteStore(project_root, self.settings)
        )

    def _read(self, name: str) -> bytes:
        return self.backend.read(name)

    def _write(self, name: str, data: bytes) -> None:
        self.backend.write(name, data)

    def _save(self, record: BaseModel, identifier: UUID) -> None:
        # Revalidate at the persistence boundary: model_copy can bypass validators.
        validated = type(record).model_validate_json(record.model_dump_json())
        self._write(f"{identifier}.json", validated.model_dump_json().encode())

    def _load[T: BaseModel](self, identifier: UUID, model: type[T]) -> T:
        # Validate before constructing a filename, including calls from untyped consumers.
        identifier = UUID(str(identifier))
        try:
            return model.model_validate_json(self._read(f"{identifier}.json"))
        except StoreError:
            raise
        except ValueError as exc:
            raise StoreError("INVALID_RECORD: stored manifest failed validation") from exc

    def retain(self, data: bytes, **metadata: Any) -> Artifact:
        """Keep bytes and a provenance record; changed bytes get a new digest/version."""
        digest = hashlib.sha256(data).hexdigest()
        record = Artifact(
            sha256=digest,
            storage_ref=digest,
            byte_length=len(data),
            retrieved_at=datetime.now(UTC),
            **metadata,
        )
        self._write(f"{digest}.blob", data)
        self._save(record, record.artifact_id)
        return record

    def artifact(self, identifier: UUID) -> Artifact:
        record = self._load(identifier, Artifact)
        if record.artifact_id != identifier:
            raise StoreError("INVALID_RECORD: artifact identity mismatch")
        data = self._read(f"{record.storage_ref}.blob")
        if len(data) != record.byte_length or hashlib.sha256(data).hexdigest() != record.sha256:
            raise StoreError("INTEGRITY_FAILURE: artifact bytes do not match manifest")
        return record

    def read_bytes(self, digest: str) -> bytes:
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise StoreError("INVALID_REFERENCE: expected a content digest")
        data = self._read(f"{digest}.blob")
        if hashlib.sha256(data).hexdigest() != digest:
            raise StoreError("INTEGRITY_FAILURE: content digest mismatch")
        return data

    def save_evidence(self, record: Evidence) -> None:
        self.artifact(record.artifact_id)
        self._save(record, record.evidence_id)

    def evidence(self, identifier: UUID) -> Evidence:
        record = self._load(identifier, Evidence)
        if record.evidence_id != identifier:
            raise StoreError("INVALID_RECORD: evidence identity mismatch")
        self.artifact(record.artifact_id)
        return record

    def _validate_run(self, record: CalculationRun) -> None:
        for item in record.inputs:
            for reference in item.evidence_refs:
                if self.evidence(reference).review_state != "reviewed":
                    raise StoreError("INSUFFICIENT_EVIDENCE: calculation evidence needs review")

    def _validate_model(self, record: EconomicModel) -> None:
        references = {ref for item in record.parameters for ref in item.evidence_refs}
        for claim in record.claims:
            references.update(claim.supporting_evidence)
            references.update(claim.conflicting_evidence)
        for reference in references:
            self.evidence(reference)

    def save_model(self, record: EconomicModel) -> None:
        record = EconomicModel.model_validate_json(record.model_dump_json())
        self._validate_model(record)
        self._save(record, record.model_id)

    def model(self, identifier: UUID) -> EconomicModel:
        record = self._load(identifier, EconomicModel)
        if record.model_id != identifier:
            raise StoreError("INVALID_RECORD: model identity mismatch")
        self._validate_model(record)
        return record

    def save_run(self, record: CalculationRun) -> None:
        self._validate_run(record)
        self._save(record, record.run_id)

    def run(self, identifier: UUID) -> CalculationRun:
        record = self._load(identifier, CalculationRun)
        if record.run_id != identifier:
            raise StoreError("INVALID_RECORD: run identity mismatch")
        self._validate_run(record)
        return record
