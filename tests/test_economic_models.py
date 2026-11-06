"""Independent formula cases, persistence validation and real gateway dispatch."""

import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastmcp import Client
from pydantic import ValidationError

from regulatory_mcp.analysis.calculations import AnalysisError
from regulatory_mcp.analysis.model_engine import evaluate, evaluate_saved
from regulatory_mcp.analysis.model_server import ModelComparison, compare_output, inspect_model
from regulatory_mcp.application import create_application
from regulatory_mcp.config import Settings
from regulatory_mcp.contracts import (
    CalculationInput,
    EconomicModel,
    Evidence,
    Locator,
    ModelDefinition,
)
from regulatory_mcp.evidence import EvidenceStore, StoreError

USD = [{"symbol": "USD", "exponent": 1}]


def parameter(name, value, unit=(), **overrides):
    return dict(
        name=name,
        value=value,
        unit=unit,
        entity_definition="Synthetic population",
        basis="assumption",
        rationale="Synthetic example",
        **overrides,
    )


def definition():
    return dict(
        title="Synthetic benefits transfer",
        baseline="No action",
        alternative="Illustrative labeling intervention",
        affected_population="Synthetic population",
        monetary_basis="real",
        dollar_year=2014,
        timing_convention="PV at year zero",
        parameters=[
            parameter("reference_benefits", "1000", USD),
            parameter("scale", "0.2"),
            parameter("cost", "150", USD),
        ],
        # Deliberately out of order to test dependency ordering.
        formulas=[
            dict(
                name="net",
                operation="subtract",
                operands=["benefits", "cost"],
                unit=USD,
                rationale="Benefits less resource costs",
            ),
            dict(
                name="benefits",
                operation="multiply",
                operands=["reference_benefits", "scale"],
                unit=USD,
                rationale="Illustrative transfer assumption",
            ),
        ],
        outputs=["benefits", "net"],
        claims=[
            dict(
                name="transfer",
                statement="Earlier benefits transfer proportionally",
                depends_on=["scale"],
                assessment="unassessed",
            )
        ],
    )


def model(data=None):
    return EconomicModel(**(data or definition()), created_at=datetime.now(UTC))


def test_independent_scaling_and_intermediates():
    result = evaluate(model())
    assert Decimal(result["benefits"]) == 200
    assert Decimal(result["net"]) == 50
    assert Decimal(result["reference_benefits"]) == 1000


@pytest.mark.parametrize(
    "invalid", ["duplicate", "cycle", "unknown", "unit", "claim", "output", "arity", "nan"]
)
def test_invalid_definitions(invalid):
    data = definition()
    if invalid == "duplicate":
        data["parameters"].append(data["parameters"][0])
    elif invalid == "cycle":
        data["formulas"][1]["operands"][0] = "net"
    elif invalid == "unknown":
        data["formulas"][1]["operands"][0] = "absent"
    elif invalid == "unit":
        data["parameters"][2]["unit"] = []
    elif invalid == "claim":
        data["claims"][0]["depends_on"] = ["unknown"]
    elif invalid == "output":
        data["outputs"] = ["net", "net"]
    elif invalid == "arity":
        data["formulas"][0]["operands"] = ["cost"]
    else:
        data["parameters"][0]["value"] = "NaN"
    with pytest.raises(ValidationError):
        model(data)


def test_missing_input_inspection_and_no_successful_run(tmp_path):
    data = definition()
    data["parameters"][1].update(value=None, basis="missing", rationale="Need study transfer rate")
    stored = model(data)
    store = EvidenceStore(tmp_path)
    store.save_model(stored)
    readiness = inspect_model(store, stored.model_id)
    assert readiness["missing_parameters"] == ["scale"]
    assert readiness["claims_without_support"] == ["transfer"]
    assert readiness["ready_for_evaluation"] is False
    with pytest.raises(AnalysisError, match="MISSING_INPUTS: scale"):
        evaluate_saved(store, stored.model_id)


def test_division_power_units_and_invalid_arithmetic():
    data = definition()
    data["formulas"] = [
        dict(
            name="ratio",
            operation="divide",
            operands=["reference_benefits", "cost"],
            unit=[],
            rationale="Cost coverage ratio",
        ),
        dict(
            name="squared",
            operation="integer_power",
            operands=["ratio"],
            exponent=2,
            unit=[],
            rationale="Synthetic square",
        ),
    ]
    data["outputs"] = ["ratio", "squared"]
    data["parameters"][0]["value"] = "300"
    assert Decimal(evaluate(model(data))["squared"]) == 4
    data["parameters"][2]["value"] = "0"
    with pytest.raises(AnalysisError, match="INVALID_ARITHMETIC"):
        evaluate(model(data))


def reviewed_source(store, state="reviewed"):
    artifact = store.retain(
        b"150", source_system="synthetic-test", origin="user_supplied", media_type="text/plain"
    )
    evidence = Evidence(
        artifact_id=artifact.artifact_id,
        locator=Locator(kind="text", start=0, end=3),
        content="150",
        extraction_method="synthetic",
        extraction_version="1",
        review_state=state,
    )
    store.save_evidence(evidence)
    return evidence


def test_evidence_references_and_review_enforced(tmp_path):
    store = EvidenceStore(tmp_path)
    evidence = reviewed_source(store, "unreviewed")
    data = definition()
    data["parameters"][2].update(
        basis="reported", rationale=None, evidence_refs=[evidence.evidence_id]
    )
    stored = model(data)
    store.save_model(stored)
    assert not inspect_model(store, stored.model_id)["ready_for_evaluation"]
    with pytest.raises(StoreError, match="needs review"):
        evaluate_saved(store, stored.model_id)
    data["claims"][0]["supporting_evidence"] = [uuid4()]
    with pytest.raises(StoreError):
        store.save_model(model(data))


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_model_gateway_roundtrip_and_reconciliation(tmp_path, mode):
    async def run():
        store = EvidenceStore(tmp_path)
        evidence = reviewed_source(store)
        data = definition()
        data["parameters"][2].update(
            basis="reported", rationale=None, evidence_refs=[str(evidence.evidence_id)]
        )
        app = await create_application(Settings(gateway_mode=mode), store)
        async with Client(app) as client:

            async def call(name, args):
                if mode == "codemode":
                    result = await client.call_tool(
                        "execute", {"code": f"return await call_tool({name!r}, {args!r})"}
                    )
                else:
                    result = await client.call_tool(name, args)
                return result.structured_content

            saved = await call("analysis_create_model", {"definition": data})
            got = await call("analysis_get_model", {"model_id": saved["model_id"]})
            assert got == saved
            ready = await call("analysis_inspect_model_readiness", {"model_id": saved["model_id"]})
            assert ready["ready_for_evaluation"]
            result = await call("analysis_evaluate_model", {"model_id": saved["model_id"]})
            retrieved = await call("documents_get_run", {"run_id": result["run_id"]})
            assert Decimal(retrieved["outputs"]["net"]) == 50
            assert retrieved["parameters"]["model"]["model_id"] == saved["model_id"]
            assert Decimal(retrieved["parameters"]["intermediate_values"]["benefits"]) == 200
            comparison = await call(
                "analysis_reconcile_model_output",
                {
                    "request": dict(
                        run_id=result["run_id"],
                        output_name="net",
                        reported=dict(
                            name="published",
                            value="50",
                            unit="USD",
                            dollar_year=2014,
                            entity_definition="Synthetic population",
                            basis="assumption",
                            assumption_rationale="Synthetic expected result",
                        ),
                    )
                },
            )
            assert comparison["outputs"]["within_tolerance"] is True
            assert (
                store.run(UUID(comparison["run_id"])).parameters["source_run"]["run_id"]
                == result["run_id"]
            )

    asyncio.run(run())


def test_reconciliation_rejects_mismatched_scope_and_units(tmp_path):
    store = EvidenceStore(tmp_path)
    saved = model()
    store.save_model(saved)
    run = evaluate_saved(store, saved.model_id)
    for overrides in (
        {"dollar_year": 2025},
        {"unit": "million USD"},
        {"entity_definition": "Other population"},
    ):
        fields = dict(
            name="reported",
            value="50",
            unit="USD",
            dollar_year=2014,
            entity_definition="Synthetic population",
            basis="assumption",
            assumption_rationale="Test",
        )
        fields.update(overrides)
        with pytest.raises(AnalysisError):
            compare_output(
                store,
                ModelComparison(
                    run_id=run.run_id, output_name="net", reported=CalculationInput(**fields)
                ),
            )


def test_model_immutability_and_corruption(tmp_path):
    store = EvidenceStore(tmp_path)
    saved = model()
    store.save_model(saved)
    changed = saved.model_copy(update={"baseline": "Changed"})
    with pytest.raises(StoreError):
        store.save_model(changed)
    assert store.model(saved.model_id).baseline == "No action"
    invalid = json.loads(saved.model_dump_json())
    invalid["outputs"] = ["absent"]
    with pytest.raises(ValidationError):
        ModelDefinition.model_validate(
            {k: v for k, v in invalid.items() if k not in ("model_id", "created_at")}
        )


@pytest.mark.parametrize("value,exponent", [("10000000000", 20), ("0.000000000001", 20), ("0", -1)])
def test_numeric_limits(value, exponent):
    data = definition()
    data["parameters"][1]["value"] = value
    data["formulas"] = [
        dict(
            name="power",
            operation="integer_power",
            operands=["scale"],
            exponent=exponent,
            unit=[],
            rationale="Bound test",
        )
    ]
    data["outputs"] = ["power"]
    with pytest.raises(AnalysisError):
        evaluate(model(data))


def test_addition_and_negative_power():
    data = definition()
    data["formulas"] = [
        dict(
            name="sum",
            operation="add",
            operands=["cost", "reference_benefits"],
            unit=USD,
            rationale="Synthetic sum",
        ),
        dict(
            name="inverse",
            operation="integer_power",
            operands=["scale"],
            exponent=-1,
            unit=[],
            rationale="Synthetic reciprocal",
        ),
    ]
    data["outputs"] = ["sum", "inverse"]
    result = evaluate(model(data))
    assert Decimal(result["sum"]) == 1150
    assert Decimal(result["inverse"]) == 5
