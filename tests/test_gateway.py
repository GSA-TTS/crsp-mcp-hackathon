"""Use real FastMCP clients and Monty, with small deterministic child tools."""

import asyncio
import sys
from contextlib import asynccontextmanager

import pytest
from fastmcp import Client, FastMCP
from fastmcp.client.transports import StdioTransport

from regulatory_mcp.config import Settings
from regulatory_mcp.gateway import create_gateway


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_stdio_entry_point(mode, tmp_path):
    async def run():
        transport = StdioTransport(
            command=sys.executable,
            args=["-m", "regulatory_mcp"],
            env={"REGULATORY_MCP_GATEWAY_MODE": mode},
            cwd=str(tmp_path),
            keep_alive=False,
        )
        async with Client(transport) as client:
            names = {tool.name for tool in await client.list_tools()}
            if mode == "codemode":
                assert "execute" in names
                result = await client.call_tool(
                    "execute", {"code": 'return await call_tool("catalog", {})'}
                )
                assert "documents_get_artifact" in str(result.structured_content)
            else:
                assert "documents_get_artifact" in names
                assert "analysis_discount_cost_stream" in names
                assert {"census_discover_datasets", "census_fetch_table", "bls_get_series"} <= names
                assert {
                    "reginfo_fetch_report",
                    "reginfo_inspect_report",
                    "regulations_get_document",
                    "regulations_search_comments",
                } <= names
        assert not (tmp_path / "artifacts").exists()

    asyncio.run(run())


def children():
    source = FastMCP("source", mask_error_details=True)
    math = FastMCP("math", mask_error_details=True)

    @source.tool
    async def value() -> dict[str, int]:
        return {"value": 21}

    @math.tool
    async def double(value: int) -> dict[str, int]:
        return {"value": value * 2}

    return {"source": source, "math": math}


def test_discovery_and_cross_child_chain_matches_conventional():
    async def run():
        conventional = await create_gateway(children(), Settings())
        async with Client(conventional) as client:
            names = {t.name for t in await client.list_tools()}
            assert names == {"source_value", "math_double", "catalog"}
            value = (await client.call_tool("source_value", {})).data
            expected = (await client.call_tool("math_double", value)).data
        gateway = await create_gateway(children(), Settings(gateway_mode="codemode"))
        async with Client(gateway) as client:
            code = """
catalog = await call_tool("catalog", {})
names = [tool["name"] for tool in catalog["result"]]
value = await call_tool("source_value", {})
answer = await call_tool("math_double", {"value": value["value"]})
return {"names": names, "answer": answer}
"""
            result = (await client.call_tool("execute", {"code": code})).data
            assert result["answer"] == expected == {"value": 42}
            assert set(result["names"]) == {"source_value", "math_double"}

    asyncio.run(run())


def test_collision_detected_across_namespace_boundaries():
    async def run():
        first = FastMCP("first", mask_error_details=True)
        second = FastMCP("second", mask_error_details=True)
        first.tool(lambda: 1, name="b_c")
        second.tool(lambda: 2, name="c")
        with pytest.raises(ValueError, match="collision"):
            await create_gateway({"a": first, "a_b": second})

    asyncio.run(run())


@pytest.mark.parametrize(
    "code",
    [
        'return open("/etc/passwd").read()',
        "import os\nreturn os.environ",
        "import socket\nreturn socket.socket()",
        'return await call_tool("missing", {})',
        "while True:\n    pass",
    ],
)
def test_sandbox_rejects_unavailable_capabilities_and_bounds_cpu(code):
    async def run():
        settings = Settings(gateway_mode="codemode", execution_timeout_seconds=0.2)
        async with Client(await create_gateway(children(), settings)) as client:
            result = await client.call_tool("execute", {"code": code}, raise_on_error=False)
            assert result.is_error

    asyncio.run(run())


def test_tool_count_and_output_limits():
    async def run():
        settings = Settings(gateway_mode="codemode", max_tool_calls=1)
        async with Client(await create_gateway(children(), settings)) as client:
            result = await client.call_tool(
                "execute",
                {
                    "code": """
await call_tool("source_value", {})
return await call_tool("source_value", {})
"""
                },
                raise_on_error=False,
            )
            assert result.is_error
        settings = Settings(max_output_bytes=20)
        gateway = await create_gateway(children(), settings)
        result = await gateway.call_tool("source_value", {})
        assert result.is_error

    asyncio.run(run())


def test_lifespan_deadline_and_concurrency():
    async def run():
        events = []
        active = 0
        peak = 0

        @asynccontextmanager
        async def lifespan(server):
            events.append("start")
            yield {}
            events.append("stop")

        child = FastMCP("slow", lifespan=lifespan, mask_error_details=True)

        @child.tool
        async def wait(seconds: float) -> dict[str, bool]:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            try:
                await asyncio.sleep(seconds)
                return {"done": True}
            finally:
                active -= 1

        settings = Settings(max_concurrency=1, execution_timeout_seconds=0.2)
        async with Client(await create_gateway({"slow": child}, settings)) as client:
            await asyncio.gather(
                *(client.call_tool("slow_wait", {"seconds": 0.01}) for _ in range(3))
            )
            result = await client.call_tool("slow_wait", {"seconds": 1}, raise_on_error=False)
            assert result.is_error
            assert active == 0
        assert peak == 1
        assert events == ["start", "stop"]

    asyncio.run(run())
