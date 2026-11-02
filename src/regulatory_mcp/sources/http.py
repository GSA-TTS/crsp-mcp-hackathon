"""Fixed-origin, bounded HTTPS retrieval shared by public-source adapters."""

import asyncio
import ipaddress
import logging
import socket
import ssl
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit

import httpx2 as httpx

from regulatory_mcp.config import Settings

logger = logging.getLogger(__name__)
ORIGINS = {"api.regulations.gov", "www.reginfo.gov", "api.census.gov", "api.bls.gov"}


class SourceError(ValueError):
    """Safe source error; never carries response bodies or credentials."""


def retry_delay(value: str | None, attempt: int) -> float:
    if value is None:
        return float(2**attempt)
    try:
        seconds = float(value)
    except ValueError:
        try:
            seconds = (parsedate_to_datetime(value) - datetime.now(UTC)).total_seconds()
        except ValueError, TypeError, OverflowError:
            return float(2**attempt)
    if not 0 <= seconds <= 60:
        raise SourceError("RATE_LIMITED: retry delay exceeds automatic retry budget")
    return seconds


class PublicHTTP:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.lock = asyncio.Lock()
        self.last_request = 0.0

    async def _pace(self) -> None:
        async with self.lock:
            wait = self.settings.source_request_interval_seconds - (
                time.monotonic() - self.last_request
            )
            if wait > 0:
                await asyncio.sleep(wait)
            self.last_request = time.monotonic()

    async def get(self, url: str, *, key: str | None = None) -> bytes:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname not in ORIGINS
            or parsed.hostname not in self.settings.allowed_hosts
            or parsed.port not in (None, 443)
            or parsed.username
            or parsed.password
        ):
            raise SourceError("DESTINATION_REJECTED: source origin is not allowed")
        if key is not None and parsed.hostname != "api.regulations.gov":
            raise SourceError("DESTINATION_REJECTED: credentials cannot cross origins")
        try:
            async with asyncio.timeout(self.settings.request_timeout_seconds):
                addresses = await asyncio.get_running_loop().getaddrinfo(
                    parsed.hostname, 443, type=socket.SOCK_STREAM
                )
            if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
                raise SourceError("DESTINATION_REJECTED: source resolves to a nonpublic address")
        except (OSError, TimeoutError) as exc:
            raise SourceError("SOURCE_UNAVAILABLE: DNS lookup failed") from exc
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        headers = {
            "Accept": "application/json, application/xml, text/xml",
            "User-Agent": "regulatory-mcp/0.1",
        }
        if key is not None:
            headers["X-Api-Key"] = key
        async with httpx.AsyncClient(
            verify=context,
            trust_env=False,
            follow_redirects=False,
            timeout=self.settings.request_timeout_seconds,
        ) as client:
            for attempt in range(self.settings.max_retries + 1):
                await self._pace()
                try:
                    async with asyncio.timeout(self.settings.request_timeout_seconds):
                        async with client.stream("GET", url, headers=headers) as response:
                            data = await self._response(response, attempt)
                    if isinstance(data, bytes):
                        return data
                    delay = data
                except httpx.TransportError, TimeoutError:
                    if attempt == self.settings.max_retries:
                        raise SourceError(
                            "SOURCE_UNAVAILABLE: request failed or timed out"
                        ) from None
                    delay = float(2**attempt)
                logger.warning("source_retry host=%s attempt=%s", parsed.hostname, attempt + 1)
                await asyncio.sleep(delay)
        raise SourceError("SOURCE_UNAVAILABLE: retry budget exhausted")

    async def _response(self, response: httpx.Response, attempt: int) -> bytes | float:
        status = response.status_code
        if status in (429, 502, 503, 504):
            if attempt == self.settings.max_retries:
                code = "RATE_LIMITED" if status == 429 else "SOURCE_UNAVAILABLE"
                raise SourceError(f"{code}: retry budget exhausted")
            return retry_delay(response.headers.get("Retry-After"), attempt)
        if status in (401, 403):
            raise SourceError("AUTHENTICATION_FAILED: source rejected access")
        if status != 200:
            raise SourceError(f"UPSTREAM_HTTP_ERROR: status {status}")
        result = bytearray()
        async for chunk in response.aiter_bytes():
            result.extend(chunk)
            if len(result) > self.settings.max_download_bytes:
                raise SourceError("BUDGET_EXHAUSTED: source response exceeds byte limit")
        return bytes(result)
