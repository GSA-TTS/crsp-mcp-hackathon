"""Register calculations and persist every successful result with its input lineage."""

import asyncio
import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from regulatory_mcp.analysis.calculations import AnalysisError, calculate
from regulatory_mcp.analysis.requests import (
    AnnualizeRequest,
    BreakEvenRequest,
    CostReceiptsRequest,
    DiscountRequest,
    ReconcileRequest,
    Request,
    ScenariosRequest,
)
from regulatory_mcp.contracts import CalculationInput, CalculationRun, WarningDetail
from regulatory_mcp.evidence import EvidenceStore, StoreError


def code_fingerprint() -> str:
    """Fingerprint actual installed calculation code, including uncommitted edits."""
    digest = hashlib.sha256()
    for name in ("requests.py", "calculations.py", "server.py"):
        digest.update(name.encode())
        digest.update(Path(__file__).with_name(name).read_bytes())
    return "sha256:" + digest.hexdigest()


def inputs(request: Request) -> tuple[CalculationInput, ...]:
    if isinstance(request, ScenariosRequest):
        amounts = [flow.amount for flow in request.discount.flows]
    elif isinstance(request, DiscountRequest):
        amounts = [flow.amount for flow in request.flows]
    elif isinstance(request, AnnualizeRequest):
        amounts = [request.present_value]
    elif isinstance(request, BreakEvenRequest):
        amounts = [request.cost, request.quantity]
    elif isinstance(request, CostReceiptsRequest):
        amounts = [request.cost, request.receipts]
    elif isinstance(request, ReconcileRequest):
        amounts = [request.calculated, request.reported]
    else:
        raise AnalysisError("UNSUPPORTED_CAPABILITY: unknown calculation request")
    # Role names avoid duplicate caller-supplied names while preserving them in parameters.
    values = [
        item.model_copy(update={"name": f"input_{i}:{item.name}"}) for i, item in enumerate(amounts)
    ]
    values.append(
        CalculationInput(
            name="model_assumptions",
            value=request.model_dump(mode="json"),
            unit="model parameters",
            entity_definition="Timing, rates, comparison tolerances and input definitions",
            basis="assumption",
            assumption_rationale=request.assumption_rationale,
        )
    )
    return tuple(values)


def create_analysis_server(store: EvidenceStore) -> FastMCP[Any]:
    server: FastMCP[Any] = FastMCP("Deterministic economic analysis", mask_error_details=True)

    async def execute(operation: str, request: Request) -> CalculationRun:
        try:
            output, units, formula = calculate(operation, request)
            run = CalculationRun(
                tool=operation,
                tool_version="1.0",
                code_revision=code_fingerprint(),
                inputs=inputs(request),
                parameters=request.model_dump(mode="json"),
                formulas=(formula,),
                timing_convention="Explicit relative years/payment times in parameters",
                outputs=output,
                output_units=units,
                created_at=datetime.now(UTC),
                verification_level="model_reconstruction",
                warnings=(
                    WarningDetail(
                        code="INPUTS_NOT_INDEPENDENTLY_VALIDATED",
                        message="Deterministic arithmetic using supplied inputs and assumptions; "
                        "not independent input validation or original-document verification.",
                    ),
                ),
            )
            await asyncio.to_thread(store.save_run, run)
            return run
        except (AnalysisError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def discount_cost_stream(request: DiscountRequest) -> CalculationRun:
        """Discount USD flows at explicit relative-year times to a stated valuation time."""
        return await execute("discount_cost_stream", request)

    @server.tool
    async def annualize_present_value(request: AnnualizeRequest) -> CalculationRun:
        """Compute equal payments at explicit times, including zero-rate cases."""
        return await execute("annualize_present_value", request)

    @server.tool
    async def calculate_break_even(request: BreakEvenRequest) -> CalculationRun:
        """Divide USD cost by positive nonmonetary quantity; returns USD per quantity unit."""
        return await execute("calculate_break_even", request)

    @server.tool
    async def calculate_cost_to_receipts(request: CostReceiptsRequest) -> CalculationRun:
        """Compare same-entity, same-dollar-year costs and receipts for a stated period."""
        return await execute("calculate_cost_to_receipts", request)

    @server.tool
    async def reconcile_reported_values(request: ReconcileRequest) -> CalculationRun:
        """Compare matched units using explicit tolerances and optional half-up rounding."""
        return await execute("reconcile_reported_values", request)

    @server.tool
    async def run_parameter_scenarios(request: ScenariosRequest) -> CalculationRun:
        """Evaluate a bounded deterministic discount-rate grid; no Monte Carlo simulation."""
        return await execute("run_parameter_scenarios", request)

    return server
