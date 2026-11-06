"""Deterministic model evaluation with bounded Decimal arithmetic and full lineage."""

import hashlib
from datetime import UTC, datetime
from decimal import Decimal, DecimalException, Underflow, localcontext
from pathlib import Path
from uuid import UUID

from regulatory_mcp.analysis.calculations import AnalysisError
from regulatory_mcp.contracts import CalculationInput, CalculationRun, EconomicModel, WarningDetail
from regulatory_mcp.contracts.economic_model import (
    ModelFormula,
    ModelParameter,
    Unit,
    formula_order,
)
from regulatory_mcp.evidence import EvidenceStore


def unit_label(unit: Unit) -> str:
    return (
        " * ".join(
            part.symbol if part.exponent == 1 else f"{part.symbol}^{part.exponent}"
            for part in sorted(unit, key=lambda p: p.symbol)
        )
        or "1"
    )


def apply(formula: ModelFormula, values: dict[str, Decimal]) -> Decimal:
    left = values[formula.operands[0]]
    if formula.operation == "integer_power":
        if formula.exponent is None:
            raise AnalysisError("INVALID_MODEL: integer power requires an exponent")
        return left**formula.exponent
    right = values[formula.operands[1]]
    if formula.operation == "add":
        return left + right
    if formula.operation == "subtract":
        return left - right
    if formula.operation == "multiply":
        return left * right
    return left / right


def evaluate(model: EconomicModel) -> dict[str, str]:
    missing = [item.name for item in model.parameters if item.value is None]
    if missing:
        raise AnalysisError("MISSING_INPUTS: " + ", ".join(missing))
    values = {item.name: item.value for item in model.parameters if item.value is not None}
    try:
        with localcontext() as context:
            context.prec = 40
            context.Emax = 100
            context.Emin = -100
            for formula in formula_order(model.parameters, model.formulas):
                value = apply(formula, values)
                if not value.is_finite() or (value and not -100 <= value.adjusted() <= 100):
                    raise AnalysisError("NUMERIC_RANGE: model result exceeds arithmetic bounds")
                if context.flags[Underflow]:
                    raise AnalysisError("NUMERIC_RANGE: model result underflow")
                values[formula.name] = value
    except DecimalException:
        raise AnalysisError(
            "INVALID_ARITHMETIC: undefined or out-of-range model operation"
        ) from None
    return {name: str(value) for name, value in values.items()}


def model_inputs(model: EconomicModel) -> tuple[CalculationInput, ...]:
    result = []
    for item in model.parameters:
        if item.basis == "missing":
            raise AnalysisError("MISSING_INPUTS: " + item.name)
        result.append(
            CalculationInput(
                name=item.name,
                value=str(item.value),
                unit=unit_label(item.unit),
                dollar_year=model.dollar_year
                if any(p.symbol == "USD" for p in item.unit)
                else None,
                entity_definition=item.entity_definition,
                basis=item.basis,
                evidence_refs=item.evidence_refs,
                assumption_rationale=item.rationale if item.basis == "assumption" else None,
            )
        )
    return tuple(result)


def fingerprint() -> str:
    from regulatory_mcp.contracts import economic_model

    digest = hashlib.sha256()
    for path in (
        Path(economic_model.__file__),
        Path(__file__),
        Path(__file__).with_name("model_server.py"),
        Path(__file__).with_name("run_views.py"),
        Path(__file__).with_name("calculations.py"),
        Path(__file__).with_name("requests.py"),
    ):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()


def evaluate_saved(store: EvidenceStore, model_id: UUID) -> CalculationRun:
    model = store.model(model_id)
    values = evaluate(model)
    nodes: dict[str, ModelParameter | ModelFormula] = {item.name: item for item in model.parameters}
    nodes.update({item.name: item for item in model.formulas})
    run = CalculationRun(
        tool="evaluate_model",
        tool_version="1.0",
        code_revision=fingerprint(),
        inputs=model_inputs(model),
        parameters={
            "model": model.model_dump(mode="json"),
            "intermediate_values": values,
            "decimal_precision": 40,
        },
        formulas=tuple(
            f"{f.name} = {f.operation}({', '.join(f.operands)})"
            + (f" exponent={f.exponent}" if f.exponent is not None else "")
            for f in formula_order(model.parameters, model.formulas)
        ),
        timing_convention=model.timing_convention,
        outputs={name: values[name] for name in model.outputs},
        output_units={name: unit_label(nodes[name].unit) for name in model.outputs},
        verification_level="model_reconstruction",
        created_at=datetime.now(UTC),
        warnings=(
            WarningDetail(
                code="MODEL_NOT_INDEPENDENTLY_VALIDATED",
                message="Arithmetic under analyst-supplied model and assumptions; "
                "claim assessments and causal validity are not independently verified.",
            ),
        ),
    )
    store.save_run(run)
    return run
