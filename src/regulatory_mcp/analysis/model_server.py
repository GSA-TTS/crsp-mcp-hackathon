"""Register persisted model tools on the existing analysis child server."""

import asyncio
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

from regulatory_mcp.analysis.calculations import AnalysisError, calculate
from regulatory_mcp.analysis.model_engine import evaluate_saved, fingerprint
from regulatory_mcp.analysis.requests import Number, ReconcileRequest
from regulatory_mcp.analysis.run_views import manifest_page, model_run, summary
from regulatory_mcp.contracts import (
    CalculationInput,
    CalculationRun,
    EconomicModel,
    ModelDefinition,
)
from regulatory_mcp.contracts.economic_model import ModelFormula, ModelParameter
from regulatory_mcp.contracts.models import Contract
from regulatory_mcp.evidence import EvidenceStore, StoreError


class ModelComparison(Contract):
    run_id: UUID
    output_name: str = Field(min_length=1, max_length=64)
    reported: CalculationInput
    absolute_tolerance: Number = Field(default=Decimal(0), ge=0)
    relative_tolerance: Number = Field(default=Decimal(0), ge=0, le=1)
    rounding_increment: Number | None = Field(default=None, gt=0)


def inspect_model(store: EvidenceStore, model_id: UUID) -> dict[str, Any]:
    model = store.model(model_id)
    missing = [p.name for p in model.parameters if p.basis == "missing"]
    unreviewed = sorted(
        {
            str(ref)
            for p in model.parameters
            for ref in p.evidence_refs
            if store.evidence(ref).review_state != "reviewed"
        }
    )
    return {
        "model_id": str(model_id),
        "missing_parameters": missing,
        "assumptions": [
            p.model_dump(mode="json") for p in model.parameters if p.basis == "assumption"
        ],
        "unreviewed_parameter_evidence": unreviewed,
        "claims_without_support": [c.name for c in model.claims if not c.supporting_evidence],
        "claims": [c.model_dump(mode="json") for c in model.claims],
        "ready_for_evaluation": not missing and not unreviewed,
        "warnings": [
            "Readiness checks input availability and review only; arithmetic may fail. "
            "Claims and causal transferability remain analyst judgments."
        ],
    }


def compare_output(store: EvidenceStore, request: ModelComparison) -> CalculationRun:
    source = store.run(request.run_id)
    if source.tool != "evaluate_model" or request.output_name not in source.outputs:
        raise AnalysisError("INVALID_REFERENCE: expected an output of a saved model evaluation")
    model = EconomicModel.model_validate(source.parameters["model"])
    nodes: dict[str, ModelParameter | ModelFormula] = {p.name: p for p in model.parameters}
    nodes.update({p.name: p for p in model.formulas})
    node = nodes[request.output_name]
    calculated = CalculationInput(
        name="model_output",
        value=source.outputs[request.output_name],
        unit=source.output_units[request.output_name],
        dollar_year=model.dollar_year if any(p.symbol == "USD" for p in node.unit) else None,
        entity_definition=model.affected_population,
        basis="assumption",
        assumption_rationale="Value from saved model run; analyst must confirm comparison scope.",
    )
    comparison = ReconcileRequest(
        calculated=calculated,
        reported=request.reported,
        absolute_tolerance=request.absolute_tolerance,
        relative_tolerance=request.relative_tolerance,
        rounding_increment=request.rounding_increment,
        assumption_rationale="Analyst-selected published comparison and tolerances.",
    )
    outputs, units, formula = calculate("reconcile_reported_values", comparison)
    run = CalculationRun(
        tool="reconcile_model_output",
        tool_version="1.0",
        code_revision=fingerprint(),
        inputs=(
            *source.inputs,
            request.reported.model_copy(update={"name": "comparison:reported"}),
        ),
        parameters={
            "source_run": source.model_dump(mode="json"),
            "comparison": request.model_dump(mode="json"),
        },
        formulas=(formula,),
        timing_convention=source.timing_convention,
        outputs=outputs,
        output_units=units,
        created_at=datetime.now(UTC),
        verification_level="model_reconstruction",
        warnings=source.warnings,
    )
    store.save_run(run)
    return run


def register_model_tools(server: FastMCP[Any], store: EvidenceStore) -> None:
    async def call[T](function: Callable[..., T], *args: Any) -> T:
        try:
            return await asyncio.to_thread(function, *args)
        except (AnalysisError, StoreError) as exc:
            raise ToolError(str(exc)) from exc

    @server.tool
    async def create_model(definition: ModelDefinition) -> EconomicModel:
        """Save a new immutable model; sourced parameters may await evidence review."""
        model = EconomicModel(**definition.model_dump(), created_at=datetime.now(UTC))
        await call(store.save_model, model)
        return model

    @server.tool
    async def get_model(model_id: UUID) -> EconomicModel:
        """Retrieve a model and verify all parameter and claim evidence references."""
        return await call(store.model, model_id)

    @server.tool
    async def inspect_model_readiness(model_id: UUID) -> dict[str, Any]:
        """Report missing parameters, assumptions, unreviewed evidence and unsupported claims."""
        return await call(inspect_model, store, model_id)

    @server.tool
    async def evaluate_model(model_id: UUID) -> dict[str, Any]:
        """Save evaluation; return a summary. Page the manifest with inspect_model_run."""
        return summary(await call(evaluate_saved, store, model_id))

    @server.tool
    async def reconcile_model_output(request: ModelComparison) -> dict[str, Any]:
        """Save comparison; return a summary. Full provenance remains in the paged manifest."""
        return summary(await call(compare_output, store, request))

    @server.tool
    async def get_model_run(run_id: UUID) -> dict[str, Any]:
        """Retrieve a compact model-run summary and validate its numeric evidence references."""
        return summary(await call(model_run, store, run_id))

    @server.tool
    async def inspect_model_run(
        run_id: UUID,
        offset: Annotated[int, Field(ge=0)] = 0,
        limit: Annotated[int, Field(ge=1, le=4000)] = 4000,
    ) -> dict[str, Any]:
        """Read a bounded JSON text page of the complete saved model-run manifest."""
        return await call(manifest_page, store, run_id, offset, limit)
