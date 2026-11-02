"""Assemble static child catalogs before publishing the gateway."""

import re
from collections.abc import Mapping
from typing import Any

from fastmcp import FastMCP
from fastmcp.experimental.transforms.code_mode import CodeMode, MontySandboxProvider

from regulatory_mcp.config import Settings
from regulatory_mcp.gateway.limits import Limits


async def create_gateway(
    children: Mapping[str, FastMCP[Any]], settings: Settings | None = None
) -> FastMCP[Any]:
    """Mount children and reject exposed-name collisions before returning.

    Children must have static registration after assembly. Lifespans are owned
    by FastMCP mounting. The catalog tool enables discovery inside CodeMode.
    """
    settings = settings or Settings()
    gateway: FastMCP[Any] = FastMCP("Regulatory analysis", mask_error_details=True)
    names = {"catalog", "execute", "search", "get_schema", "list_tools", "tags"}
    for namespace, child in children.items():
        # FastMCP 4.1.4 exposes this constructor setting only on the private attribute.
        if not child._mask_error_details:
            raise ValueError("Mounted children must enable mask_error_details")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", namespace):
            raise ValueError("Namespaces must be lowercase identifiers")
        # Probe actual names through FastMCP rather than duplicating its separator rules.
        probe: FastMCP[Any] = FastMCP("namespace probe")
        probe.mount(child, namespace=namespace)
        for tool in await probe.list_tools():
            if tool.name in names:
                raise ValueError(f"Exposed tool name collision: {tool.name}")
            names.add(tool.name)
        gateway.mount(child, namespace=namespace)
    catalog = [
        {"name": tool.name, "description": tool.description, "parameters": tool.parameters}
        for tool in await gateway.list_tools()
    ]

    @gateway.tool(name="catalog")
    async def catalog_tools() -> list[dict[str, Any]]:
        """List mounted backend tool names and parameter schemas for orchestration."""
        return catalog

    gateway.add_middleware(Limits(settings))
    if settings.gateway_mode == "codemode":
        gateway.add_transform(
            CodeMode(
                sandbox_provider=MontySandboxProvider(
                    limits={
                        "max_feed_duration_secs": settings.execution_timeout_seconds,
                        "max_memory": 100_000_000,
                    }
                ),
                max_tool_calls=settings.max_tool_calls,
            )
        )
    return gateway
