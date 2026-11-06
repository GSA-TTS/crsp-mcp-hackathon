"""Bound S3 storage with conditional writes and no ambient credential discovery."""

import json
import re
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ConfigDict, Field, SecretStr, ValidationError

from regulatory_mcp.evidence.backend import StoreError


class S3Credentials(BaseModel):
    """Required cloud.gov S3 binding fields; other broker fields are ignored."""

    model_config = ConfigDict(hide_input_in_errors=True)
    bucket: str = Field(pattern=r"^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$")
    region: str = Field(pattern=r"^us-gov-(?:west|east)-1$")
    access_key_id: SecretStr = Field(min_length=1)
    secret_access_key: SecretStr = Field(min_length=1)


def binding_credentials(raw: str, service_name: str) -> S3Credentials:
    """Select exactly one named service, never print VCAP_SERVICES on failure."""
    try:
        services = json.loads(raw)
        if not isinstance(services, dict):
            raise ValueError
        matches = []
        for entries in services.values():
            if not isinstance(entries, list):
                raise ValueError
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ValueError
                if entry.get("name") == service_name:
                    matches.append(entry)
        if len(matches) != 1:
            raise ValueError
        return S3Credentials.model_validate(matches[0].get("credentials"))
    except ValueError, ValidationError:
        raise StoreError("STORAGE_CONFIGURATION: expected one valid named S3 binding") from None


def create_s3_backend(raw: str, service_name: str, max_bytes: int) -> S3ByteStore:
    credentials = binding_credentials(raw, service_name)
    # An isolated session with explicit credentials avoids metadata-service lookups.
    client = boto3.session.Session().client(
        "s3",
        region_name=credentials.region,
        endpoint_url=f"https://s3.{credentials.region}.amazonaws.com",
        aws_access_key_id=credentials.access_key_id.get_secret_value(),
        aws_secret_access_key=credentials.secret_access_key.get_secret_value(),
        config=Config(
            connect_timeout=5,
            read_timeout=10,
            retries={"mode": "standard", "total_max_attempts": 2},
            proxies={},
            s3={"addressing_style": "virtual"},
        ),
    )
    return S3ByteStore(client, credentials.bucket, max_bytes)


class S3ByteStore:
    """Private objects under a fixed prefix; existing data is never overwritten."""

    def __init__(self, client: Any, bucket: str, max_bytes: int):
        self.client, self.bucket, self.max_bytes = client, bucket, max_bytes

    @staticmethod
    def _key(name: str) -> str:
        if re.fullmatch(r"(?:[0-9a-f]{64}\.blob|[0-9a-f-]{36}\.json)", name) is None:
            raise StoreError("INVALID_REFERENCE: expected a generated object name")
        return "evidence/v1/" + name

    def read(self, name: str) -> bytes:
        key = self._key(name)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"]
            try:
                if response["ContentLength"] > self.max_bytes:
                    raise StoreError("STORAGE_REJECTED: stored object exceeds size limit")
                data = body.read(self.max_bytes + 1)
                if not isinstance(data, bytes) or len(data) > self.max_bytes:
                    raise StoreError("STORAGE_REJECTED: stored object exceeds size limit")
                return data
            finally:
                body.close()
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                raise StoreError("MISSING_OR_UNSAFE_REFERENCE: cannot read stored object") from None
            raise StoreError("STORAGE_FAILURE: object could not be read") from None
        except BotoCoreError, OSError:
            raise StoreError("STORAGE_FAILURE: object could not be read") from None

    def write(self, name: str, data: bytes) -> None:
        key = self._key(name)
        if len(data) > self.max_bytes:
            raise StoreError("STORAGE_REJECTED: object exceeds size limit")
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                IfNoneMatch="*",
                ServerSideEncryption="AES256",
                ContentType=(
                    "application/json" if name.endswith(".json") else "application/octet-stream"
                ),
            )
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code")
            if code in {"PreconditionFailed", "412"}:
                if self.read(name) != data:
                    raise StoreError("IMMUTABLE_CONFLICT: stored object differs") from None
                return
            # A concurrent-delete/conditional-request 409 is explicit, not an overwrite retry.
            raise StoreError("STORAGE_FAILURE: conditional object create failed") from None
        except BotoCoreError, OSError:
            raise StoreError("STORAGE_FAILURE: object could not be persisted") from None
