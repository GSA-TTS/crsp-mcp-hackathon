"""Evidence integrity and reference tests on a real local filesystem."""

import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastmcp import Client
from pydantic import ValidationError

from regulatory_mcp.config import Settings
from regulatory_mcp.contracts import (
    CalculationInput,
    CalculationRun,
    Evidence,
    Locator,
    SearchPage,
    ToolResponse,
)
from regulatory_mcp.evidence import EvidenceStore, StoreError
from regulatory_mcp.evidence.server import create_evidence_server
from regulatory_mcp.gateway import create_gateway


def retain(store, data=b"Cost: 42"):
    return store.retain(
        data, source_system="test fixture", origin="user_supplied", media_type="text/plain"
    )


def passage(artifact, review_state="reviewed"):
    return Evidence(
        artifact_id=artifact.artifact_id,
        locator=Locator(kind="text", start=0, end=8),
        content="Cost: 42",
        extraction_method="manual",
        extraction_version="1",
        review_state=review_state,
    )


def calculation(evidence_id):
    return CalculationRun(
        tool="fixture",
        tool_version="1",
        code_revision="fixture-revision",
        inputs=(
            CalculationInput(
                name="cost",
                value=42,
                unit="USD",
                dollar_year=2023,
                entity_definition="one item",
                basis="reported",
                evidence_refs=(evidence_id,),
            ),
        ),
        parameters={},
        formulas=("cost",),
        timing_convention="instantaneous",
        outputs={"cost": 42},
        output_units={"cost": "USD"},
        verification_level="published_table",
        created_at=datetime.now(UTC),
    )


def test_versioning_and_persistent_run_resolution(tmp_path):
    store = EvidenceStore(tmp_path)
    first = retain(store)
    changed = retain(store, b"Cost: 43")
    assert changed.sha256 != first.sha256
    assert changed.artifact_id != first.artifact_id
    evidence = passage(first)
    store.save_evidence(evidence)
    run = calculation(evidence.evidence_id)
    store.save_run(run)
    reopened = EvidenceStore(tmp_path)
    assert reopened.run(run.run_id) == run
    assert reopened.artifact(first.artifact_id) == first
    assert reopened.read_bytes(first.sha256) == b"Cost: 42"
    with pytest.raises(StoreError, match="IMMUTABLE_CONFLICT"):
        store.save_evidence(evidence.model_copy(update={"content": "changed"}))


def test_broken_and_ambiguous_references_fail(tmp_path):
    store = EvidenceStore(tmp_path)
    with pytest.raises(StoreError, match="REFERENCE"):
        store.save_run(calculation(uuid4()))
    evidence = passage(retain(store), review_state="ambiguous")
    store.save_evidence(evidence)
    with pytest.raises(StoreError, match="needs review"):
        store.save_run(calculation(evidence.evidence_id))


def test_persistence_revalidates_unchecked_model_copies(tmp_path):
    store = EvidenceStore(tmp_path)
    evidence = passage(retain(store))
    invalid = evidence.model_copy(update={"extraction_version": ""})
    with pytest.raises(ValidationError):
        store.save_evidence(invalid)
    assert not (tmp_path / "artifacts" / f"{invalid.evidence_id}.json").exists()


def test_tampered_blob_fails_before_calculation(tmp_path):
    store = EvidenceStore(tmp_path)
    artifact = retain(store)
    evidence = passage(artifact)
    store.save_evidence(evidence)
    (tmp_path / "artifacts" / f"{artifact.sha256}.blob").write_bytes(b"tampered")
    with pytest.raises(StoreError, match="INTEGRITY_FAILURE"):
        store.save_run(calculation(evidence.evidence_id))


def test_symlinks_and_unsafe_references_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / "artifacts").symlink_to(outside, target_is_directory=True)
    with pytest.raises(StoreError, match="STORAGE_REJECTED"):
        retain(EvidenceStore(project))
    assert list(outside.iterdir()) == []
    with pytest.raises(StoreError, match="INVALID_REFERENCE"):
        EvidenceStore(tmp_path).read_bytes("../outside")


def test_size_limit_and_blob_symlink(tmp_path):
    store = EvidenceStore(tmp_path, Settings(max_download_bytes=2))
    with pytest.raises(StoreError, match="size limit"):
        retain(store)
    store = EvidenceStore(tmp_path)
    artifact = retain(store)
    # A separate generated digest points to a symlink; never follow it.
    fake_digest = "0" * 64
    (tmp_path / "artifacts" / f"{fake_digest}.blob").symlink_to(
        tmp_path / "artifacts" / f"{artifact.sha256}.blob"
    )
    with pytest.raises(StoreError, match="UNSAFE_REFERENCE"):
        store.read_bytes(fake_digest)


def test_missing_null_false_and_contract_errors():
    response = ToolResponse[dict](status="ok", data={"null": None, "false": False})
    data = ToolResponse[dict].model_validate_json(response.model_dump_json()).data
    assert "missing" not in data
    assert data["null"] is None and data["false"] is False
    with pytest.raises(ValidationError):
        ToolResponse(status="error", data={})
    with pytest.raises(ValidationError):
        CalculationInput(name="x", value=1, unit="USD", entity_definition="item", basis="reported")
    with pytest.raises(ValidationError):
        Locator(kind="text", start=9, end=2)
    with pytest.raises(ValidationError):
        SearchPage(
            items=(),
            retrieved_count=0,
            retrieval_status="complete",
            query_scope="fixture",
            started_at=datetime.now(UTC),
            finished_at=datetime.now(UTC),
            snapshot_consistency="fixture",
            next_cursor="more",
        )


def test_evidence_tools_are_wired_into_gateway(tmp_path):
    async def run():
        store = EvidenceStore(tmp_path)
        artifact = retain(store)
        child = create_evidence_server(store)
        gateway = await create_gateway({"documents": child})
        async with Client(gateway) as client:
            names = {tool.name for tool in await client.list_tools()}
            assert names >= {
                "documents_get_artifact",
                "documents_get_evidence",
                "documents_get_run",
            }
            result = await client.call_tool(
                "documents_get_artifact", {"artifact_id": str(artifact.artifact_id)}
            )
            assert result.structured_content["sha256"] == artifact.sha256

    asyncio.run(run())
