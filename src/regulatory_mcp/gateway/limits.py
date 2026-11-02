"""Enforce deadlines, bounded responses, and concurrent backend calls."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.middleware.middleware import CallNext
from fastmcp.tools import ToolResult

from regulatory_mcp.config import Settings

logger = logging.getLogger(__name__)


class Limits(Middleware):
    """Apply to the gateway; execute itself must not hold a backend permit."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.permits = asyncio.Semaphore(settings.max_concurrency)
        self.executions = asyncio.Semaphore(settings.max_concurrency)

    async def on_call_tool(
        self, context: MiddlewareContext[Any], call_next: CallNext[Any, ToolResult]
    ) -> ToolResult:
        request_id = str(uuid4())
        status = "error"
        try:
            async with asyncio.timeout(self.settings.execution_timeout_seconds):
                if context.message.name == "execute":
                    async with self.executions:
                        result = await call_next(context)
                else:
                    async with self.permits:
                        result = await call_next(context)
            size = len(result.model_dump_json().encode())
            if size > self.settings.max_output_bytes:
                raise ToolError("BUDGET_EXHAUSTED: output byte limit exceeded")
            status = "error" if result.is_error else "ok"
            return result
        except TimeoutError:
            return ToolResult(
                content="BUDGET_EXHAUSTED: execution deadline exceeded", is_error=True
            )
        except ToolError as exc:
            return ToolResult(content=str(exc), is_error=True)
        finally:
            logger.info(
                "tool_call timestamp=%s request_id=%s tool=%s status=%s",
                datetime.now(UTC).isoformat(),
                request_id,
                context.message.name,
                status,
            )
