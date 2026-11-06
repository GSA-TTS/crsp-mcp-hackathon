"""Local stdio entry point; exposes implemented capabilities only."""

import asyncio
import logging
from pathlib import Path

from regulatory_mcp.application import create_application
from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore


async def main() -> None:
    settings = Settings()
    store = EvidenceStore(Path.cwd(), settings)
    gateway = await create_application(settings, store)
    await gateway.run_async(transport="stdio", show_banner=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
