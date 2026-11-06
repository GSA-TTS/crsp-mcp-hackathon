"""Fixed-origin, bounded HTTPS retrieval shared by public-source adapters."""

import asyncio
import ipaddress
import logging
import socket
import ssl
import time
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from urllib.parse import SplitResult, urlsplit

import httpx2 as httpx

from regulatory_mcp.config import Settings

logger = logging.getLogger(__name__)
ORIGINS = {"api.regulations.gov", "www.reginfo.gov", "api.census.gov", "api.bls.gov"}


class SourceError(ValueError):
    """Safe source error; never carries response bodies or credentials."""


def census_key_required(response: httpx.Response) -> bool:
    """Recognize the observed Census error without following or exposing its redirect."""
    if response.status_code != 302 or response.headers.get("X-DataWebAPI-KeyError") != "1":
        return False
    try:
        origin = response.request.url
    except RuntimeError:
        return False
    return (
        origin.scheme == "https"
        and origin.host == "api.census.gov"
        and response.headers.get("Location")
        in {"/data/missing_key.html", "https://api.census.gov/data/missing_key.html"}
    )


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

    def _validate_destination(self, url: str) -> SplitResult:
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
        return parsed

    async def _validate_public_dns(self, hostname: str | None) -> None:
        if self.settings.https_proxy is not None:
            return
        try:
            async with asyncio.timeout(self.settings.request_timeout_seconds):
                addresses = await asyncio.get_running_loop().getaddrinfo(
                    hostname, 443, type=socket.SOCK_STREAM
                )
            if not addresses or any(
                not ipaddress.ip_address(address[4][0]).is_global for address in addresses
            ):
                raise SourceError("DESTINATION_REJECTED: source resolves to a nonpublic address")
        except (OSError, TimeoutError) as exc:
            raise SourceError("SOURCE_UNAVAILABLE: DNS lookup failed") from exc

    async def get(
        self, url: str, *, key: str | None = None, census_key: str | None = None
    ) -> bytes:
        parsed = self._validate_destination(url)
        if key is not None and parsed.hostname != "api.regulations.gov":
            raise SourceError("DESTINATION_REJECTED: credentials cannot cross origins")
        if census_key is not None:
            if parsed.hostname != "api.census.gov":
                raise SourceError("DESTINATION_REJECTED: credentials cannot cross origins")
            if "key=" in parsed.query:
                raise SourceError("INVALID_INPUT: API key must not be passed in the URL")
            separator = "&" if parsed.query else "?"
            request_url = f"{url}{separator}key={census_key}"
        else:
            request_url = url
        await self._validate_public_dns(parsed.hostname)
        proxy = self.settings.https_proxy
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
            proxy=proxy.get_secret_value() if proxy is not None else None,
            trust_env=False,
            follow_redirects=False,
            timeout=self.settings.request_timeout_seconds,
        ) as client:
            return await self._request(client, request_url, headers, census_key is not None)

    async def _request(
        self,
        client: httpx.AsyncClient,
        request_url: str,
        headers: dict[str, str],
        had_census_key: bool,
    ) -> bytes:
        hostname = urlsplit(request_url).hostname
        for attempt in range(self.settings.max_retries + 1):
            await self._pace()
            try:
                async with asyncio.timeout(self.settings.request_timeout_seconds):
                    async with client.stream("GET", request_url, headers=headers) as response:
                        data = await self._response(
                            response, attempt, had_census_key=had_census_key
                        )
                if isinstance(data, bytes):
                    return data
                delay = data
            except httpx.TransportError, TimeoutError:
                if attempt == self.settings.max_retries:
                    raise SourceError("SOURCE_UNAVAILABLE: request failed or timed out") from None
                delay = float(2**attempt)
            logger.warning("source_retry host=%s attempt=%s", hostname, attempt + 1)
            await asyncio.sleep(delay)
        raise SourceError("SOURCE_UNAVAILABLE: retry budget exhausted")

    async def _response(
        self, response: httpx.Response, attempt: int, *, had_census_key: bool = False
    ) -> bytes | float:
        status = response.status_code
        if census_key_required(response):
            if had_census_key:
                raise SourceError("AUTHENTICATION_FAILED: Census rejected the supplied API key")
            raise SourceError("MISSING_CREDENTIALS: Census requires an API key for this query")
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
