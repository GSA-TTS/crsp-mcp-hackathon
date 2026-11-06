"""Single-process HTTP entry point; platform TLS terminates at the cloud.gov router."""

import asyncio
import logging
import os
from pathlib import Path
from urllib.parse import urlsplit

from fastmcp.server.http import StarletteWithLifespan
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse
from uvicorn import Config, Server

from regulatory_mcp.application import create_application
from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore, StoreError
from regulatory_mcp.evidence.s3 import create_s3_backend
from regulatory_mcp.gateway.auth import SharedTokenVerifier
from regulatory_mcp.hosted_config import HostedSettings


async def create_http_app(
    settings: Settings, hosted: HostedSettings, store: EvidenceStore
) -> StarletteWithLifespan:
    gateway = await create_application(
        settings, store, SharedTokenVerifier(hosted.bearer_token, hosted.public_url)
    )

    @gateway.custom_route("/health", methods=["GET"])
    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    return gateway.http_app(
        path="/mcp",
        transport="streamable-http",
        stateless_http=True,
        json_response=True,
        host_origin_protection=True,
        allowed_hosts=[urlsplit(hosted.public_url).netloc, "localhost", "127.0.0.1"],
        allowed_origins=[hosted.public_url],
    )


async def main() -> None:
    settings, hosted = Settings(), HostedSettings()
    backend = None
    if hosted.storage_backend == "s3":
        backend = create_s3_backend(
            os.environ.get("VCAP_SERVICES", "{}"),
            hosted.s3_service_name,
            settings.max_download_bytes,
        )
    store = EvidenceStore(Path.cwd(), settings, backend=backend)
    app = await create_http_app(settings, hosted, store)
    await Server(
        Config(
            app,
            host=hosted.bind_host,
            port=hosted.port,
            workers=1,
            access_log=False,
            proxy_headers=False,
            server_header=False,
            limit_concurrency=32,
            timeout_keep_alive=5,
        )
    ).serve()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except ValidationError, StoreError:
        logging.error("HOSTED_CONFIGURATION: invalid HTTP settings or storage binding")
        raise SystemExit(1) from None
