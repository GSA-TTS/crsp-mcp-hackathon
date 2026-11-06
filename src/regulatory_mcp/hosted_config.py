"""Fail-closed settings for the shared, authenticated HTTP deployment."""

from typing import Literal, Self
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Required by the CF router; selected only with authenticated HTTP and durable storage.
PUBLIC_BIND = "0.0.0.0"  # noqa: S104  # nosec B104


class HostedSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="REGULATORY_MCP_", extra="forbid", frozen=True, hide_input_in_errors=True
    )

    bearer_token: SecretStr
    public_url: str
    storage_backend: Literal["local", "s3"] = "s3"
    s3_service_name: str = Field(default="regulatory-mcp-evidence", min_length=1, max_length=100)
    bind_host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535, validation_alias="PORT")

    @field_validator("bind_host")
    @classmethod
    def explicit_bind(cls, value: str) -> str:
        if value not in {"127.0.0.1", PUBLIC_BIND}:
            raise ValueError("bind_host must be loopback or the platform's all-interface address")
        return value

    @field_validator("bearer_token")
    @classmethod
    def strong_token(cls, value: SecretStr) -> SecretStr:
        token = value.get_secret_value()
        if not 32 <= len(token) <= 512 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError("bearer_token must be 32–512 non-whitespace ASCII characters")
        return value

    @field_validator("public_url")
    @classmethod
    def public_origin(cls, value: str) -> str:
        parsed = urlsplit(value)
        try:
            port = parsed.port
        except ValueError:
            raise ValueError("public_url must be a valid origin") from None
        if (
            not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
            or (port is not None and not 1 <= port <= 65535)
        ):
            raise ValueError("public_url must be an origin without credentials, path or query")
        if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname == "127.0.0.1"
        ):
            raise ValueError("public_url requires HTTPS except for loopback testing")
        return value.rstrip("/")

    @model_validator(mode="after")
    def durable_public_deployment(self) -> Self:
        if self.bind_host != "127.0.0.1" and (
            self.storage_backend != "s3" or not self.public_url.startswith("https://")
        ):
            raise ValueError("public binding requires HTTPS public_url and S3 storage")
        return self
