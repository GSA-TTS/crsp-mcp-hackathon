"""Local stdio entry point; exposes implemented capabilities only."""

import asyncio
import logging
from pathlib import Path

from regulatory_mcp.analysis.server import create_analysis_server
from regulatory_mcp.config import Settings
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.evidence.server import create_evidence_server
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.bls.client import BLS
from regulatory_mcp.sources.bls.server import create_bls_server
from regulatory_mcp.sources.census.client import Census
from regulatory_mcp.sources.census.server import create_census_server
from regulatory_mcp.sources.http import PublicHTTP
from regulatory_mcp.sources.reginfo.client import Reginfo
from regulatory_mcp.sources.reginfo.server import create_reginfo_server
from regulatory_mcp.sources.regulations.client import Regulations
from regulatory_mcp.sources.regulations.server import create_regulations_server


async def main() -> None:
    settings = Settings()
    store = EvidenceStore(Path.cwd(), settings)
    http = PublicHTTP(settings)
    gateway = await create_gateway(
        {
            "documents": create_evidence_server(store),
            "analysis": create_analysis_server(store),
            "census": create_census_server(Census(store, http)),
            "bls": create_bls_server(BLS(store, http)),
            "reginfo": create_reginfo_server(Reginfo(store, http)),
            "regulations": create_regulations_server(Regulations(settings, store, http)),
        },
        settings,
    )
    await gateway.run_async(transport="stdio", show_banner=False)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
