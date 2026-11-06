"""SDK contract tests with Stubber; no claim of live S3 service validation."""

import io
import json
import secrets
from uuid import uuid4

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import ANY, Stubber

from regulatory_mcp.evidence import EvidenceStore, StoreError
from regulatory_mcp.evidence.s3 import S3ByteStore, binding_credentials, create_s3_backend


@pytest.fixture
def s3():
    client = boto3.client(
        "s3",
        region_name="us-gov-west-1",
        aws_access_key_id="fixture",
        aws_secret_access_key=secrets.token_hex(16),
    )
    with Stubber(client) as stub:
        yield S3ByteStore(client, "fixture-bucket", 10000), stub
        stub.assert_no_pending_responses()


def put_params(name, data):
    return {
        "Bucket": "fixture-bucket",
        "Key": "evidence/v1/" + name,
        "Body": data,
        "IfNoneMatch": "*",
        "ServerSideEncryption": "AES256",
        "ContentType": "application/json" if name.endswith(".json") else "application/octet-stream",
    }


def queue_read(stub, name, data):
    body = StreamingBody(io.BytesIO(data), len(data))
    stub.add_response(
        "get_object",
        {"Body": body, "ContentLength": len(data)},
        {"Bucket": "fixture-bucket", "Key": "evidence/v1/" + name},
    )
    return body


def test_conditional_create_idempotence_and_conflict(s3):
    backend, stub = s3
    name, data = "a" * 64 + ".blob", b"example"
    stub.add_response("put_object", {}, put_params(name, data))
    backend.write(name, data)
    stub.add_client_error(
        "put_object",
        "PreconditionFailed",
        http_status_code=412,
        expected_params=put_params(name, data),
    )
    queue_read(stub, name, data)
    backend.write(name, data)
    stub.add_client_error(
        "put_object",
        "PreconditionFailed",
        http_status_code=412,
        expected_params=put_params(name, b"changed"),
    )
    queue_read(stub, name, data)
    with pytest.raises(StoreError, match="IMMUTABLE_CONFLICT"):
        backend.write(name, b"changed")


def test_reads_bounded_closed_and_errors_masked(s3):
    backend, stub = s3
    name = "b" * 64 + ".blob"
    body = queue_read(stub, name, b"x" * 10001)
    with pytest.raises(StoreError, match="size limit"):
        backend.read(name)
    assert body._raw_stream.closed
    stub.add_client_error("get_object", "NoSuchKey", http_status_code=404)
    with pytest.raises(StoreError, match="MISSING_OR_UNSAFE_REFERENCE"):
        backend.read(name)
    stub.add_client_error("get_object", "AccessDenied", service_message="sensitive detail")
    with pytest.raises(StoreError, match="STORAGE_FAILURE") as error:
        backend.read(name)
    assert "sensitive" not in str(error.value)
    with pytest.raises(StoreError, match="INVALID_REFERENCE"):
        backend.read("../escape")
    with pytest.raises(StoreError, match="size limit"):
        backend.write(name, b"x" * 10001)


def test_conflicting_conditional_request_fails_without_overwrite(s3):
    backend, stub = s3
    stub.add_client_error("put_object", "ConditionalRequestConflict", http_status_code=409)
    with pytest.raises(StoreError, match="conditional object create"):
        backend.write("c" * 64 + ".blob", b"example")


def test_reopened_store_and_digest_validation(tmp_path, s3):
    import hashlib

    from regulatory_mcp.contracts import Artifact

    backend, stub = s3
    data = b"retained bytes"
    digest = hashlib.sha256(data).hexdigest()
    artifact = Artifact(
        artifact_id=uuid4(),
        source_system="fixture",
        origin="user_supplied",
        retrieved_at="2026-11-05T00:00:00Z",
        sha256=digest,
        storage_ref=digest,
        byte_length=len(data),
        media_type="text/plain",
    )
    queue_read(stub, f"{artifact.artifact_id}.json", artifact.model_dump_json().encode())
    queue_read(stub, digest + ".blob", data)
    store = EvidenceStore(tmp_path, backend=backend)
    assert store.artifact(artifact.artifact_id) == artifact
    queue_read(stub, digest + ".blob", b"changed")
    with pytest.raises(StoreError, match="INTEGRITY_FAILURE"):
        store.read_bytes(digest)
    assert not (tmp_path / "artifacts").exists()


def test_retain_and_run_use_s3_for_both_records_and_blobs(tmp_path, s3):
    import hashlib
    from datetime import UTC, datetime

    from regulatory_mcp.contracts import CalculationInput, CalculationRun

    backend, stub = s3
    data = b"public fixture"
    digest = hashlib.sha256(data).hexdigest()
    stub.add_response("put_object", {}, put_params(digest + ".blob", data))
    record_params = put_params(str(uuid4()) + ".json", b"unused")
    record_params.update(Key=ANY, Body=ANY)
    stub.add_response("put_object", {}, record_params)
    store = EvidenceStore(tmp_path, backend=backend)
    artifact = store.retain(
        data, source_system="fixture", origin="user_supplied", media_type="text/plain"
    )
    run = CalculationRun(
        tool="fixture",
        tool_version="1",
        code_revision="test",
        inputs=(
            CalculationInput(
                name="x",
                value=1,
                unit="units",
                entity_definition="test",
                basis="assumption",
                assumption_rationale="synthetic fixture",
            ),
        ),
        parameters={},
        formulas=("x",),
        timing_convention="none",
        outputs={"x": 1},
        output_units={"x": "units"},
        verification_level="model_reconstruction",
        created_at=datetime.now(UTC),
    )
    stub.add_response(
        "put_object",
        {},
        put_params(
            str(run.run_id) + ".json",
            run.model_dump_json().encode(),
        ),
    )
    store.save_run(run)
    queue_read(stub, str(run.run_id) + ".json", run.model_dump_json().encode())
    reopened = EvidenceStore(tmp_path, backend=S3ByteStore(backend.client, backend.bucket, 10000))
    assert reopened.run(run.run_id) == run
    queue_read(stub, str(artifact.artifact_id) + ".json", artifact.model_dump_json().encode())
    queue_read(stub, digest + ".blob", data)
    assert reopened.artifact(artifact.artifact_id) == artifact
    assert not (tmp_path / "artifacts").exists()


def binding():
    return {
        "s3": [
            {
                "name": "evidence",
                "credentials": {
                    "bucket": "fixture-bucket",
                    "region": "us-gov-west-1",
                    "access_key_id": "fixture",
                    "secret_access_key": secrets.token_hex(16),
                },
            }
        ]
    }


def test_binding_selection_masks_secrets_and_uses_explicit_client(monkeypatch):
    raw = json.dumps(binding())
    credentials = binding_credentials(raw, "evidence")
    assert "fixture" not in repr(credentials.secret_access_key)
    monkeypatch.setenv("AWS_ENDPOINT_URL", "http://127.0.0.1:1")
    backend = create_s3_backend(raw, "evidence", 100)
    assert backend.client.meta.endpoint_url == "https://s3.us-gov-west-1.amazonaws.com"
    assert backend.client.meta.config.proxies == {}
    assert backend.client.meta.config.retries["total_max_attempts"] == 2


@pytest.mark.parametrize("raw", ["broken", "[]", "{}", '{"s3": {}}'])
def test_malformed_bindings_fail_closed(raw):
    with pytest.raises(StoreError, match="STORAGE_CONFIGURATION"):
        binding_credentials(raw, "evidence")


def test_duplicate_missing_and_invalid_credentials_rejected():
    values = binding()
    values["s3"].append(values["s3"][0])
    with pytest.raises(StoreError):
        binding_credentials(json.dumps(values), "evidence")
    with pytest.raises(StoreError):
        binding_credentials(json.dumps(binding()), "missing")
    values = binding()
    values["s3"][0]["credentials"]["region"] = "http://example.com"
    with pytest.raises(StoreError):
        binding_credentials(json.dumps(values), "evidence")
