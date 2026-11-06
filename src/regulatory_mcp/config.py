"""Validated local-runtime configuration shared by future adapters."""

from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Read process environment only; constructing settings performs no I/O.

    Adapters must enforce these budgets and validate each outbound destination.
    An empty credential is allowed until a Regulations.gov operation needs it.
    """

    model_config = SettingsConfigDict(
        env_prefix="REGULATORY_MCP_", frozen=True, extra="forbid", hide_input_in_errors=True
    )

    regulations_gov_api_key: SecretStr | None = Field(
        default=None, validation_alias="REGULATIONS_GOV_API_KEY"
    )
    census_api_key: SecretStr | None = Field(default=None, validation_alias="CENSUS_API_KEY")
    artifact_dir: Path = Path("artifacts")
    gateway_mode: Literal["conventional", "codemode"] = "conventional"
    allowed_hosts: tuple[str, ...] = (
        "api.regulations.gov",
        "www.reginfo.gov",
        "api.census.gov",
        "api.bls.gov",
    )
    https_proxy: SecretStr | None = None
    source_request_interval_seconds: float = Field(default=4, ge=0.1, le=60, allow_inf_nan=False)
    request_timeout_seconds: float = Field(default=30, gt=0, le=300, allow_inf_nan=False)
    max_retries: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=20, ge=1, le=100)
    max_download_bytes: int = Field(default=25_000_000, ge=1, le=100_000_000)
    max_tool_calls: int = Field(default=20, ge=1, le=100)
    max_concurrency: int = Field(default=4, ge=1, le=16)
    execution_timeout_seconds: float = Field(default=120, gt=0, le=600, allow_inf_nan=False)
    max_output_bytes: int = Field(default=100_000, ge=1, le=1_000_000)

    @field_validator("artifact_dir")
    @classmethod
    def relative_artifact_directory(cls, value: Path) -> Path:
        """Require a project-relative path; storage must also check resolved paths."""
        if value.is_absolute() or ".." in value.parts or value == Path("."):
            raise ValueError("artifact_dir must be a non-root project-relative directory")
        return value

    @field_validator("allowed_hosts")
    @classmethod
    def explicit_hostnames(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Accept explicit DNS names, never URL patterns or wildcard destinations."""
        import re

        pattern = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
        for host in value:
            labels = host.split(".")
            if (
                len(host) > 253
                or len(labels) < 2
                or labels[-1].isdigit()
                or any(re.fullmatch(pattern, label) is None for label in labels)
            ):
                raise ValueError("allowed_hosts must contain explicit lowercase DNS hostnames")
        return value

    @field_validator("https_proxy")
    @classmethod
    def explicit_https_proxy(cls, value: SecretStr | None) -> SecretStr | None:
        """Accept one explicit proxy endpoint without trusting ambient proxy variables."""
        if value is None:
            return None
        parsed = urlsplit(value.get_secret_value())
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("https_proxy must be an explicit HTTP(S) proxy origin")
        try:
            if parsed.port is not None and not 1 <= parsed.port <= 65535:
                raise ValueError("https_proxy port is outside the valid range")
        except ValueError as exc:
            raise ValueError("https_proxy must contain a valid port") from exc
        return value
