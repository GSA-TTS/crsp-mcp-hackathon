"""Independent small cases, handoff-derived FDA checks, and persistent MCP wiring."""

import asyncio
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastmcp import Client
from pydantic import ValidationError

from regulatory_mcp.analysis.calculations import AnalysisError, calculate
from regulatory_mcp.analysis.requests import (
    AnnualizeRequest,
    BreakEvenRequest,
    CostReceiptsRequest,
    DiscountRequest,
    Flow,
    ReconcileRequest,
    ScenariosRequest,
)
from regulatory_mcp.analysis.server import create_analysis_server
from regulatory_mcp.config import Settings
from regulatory_mcp.contracts import CalculationInput
from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.evidence.server import create_evidence_server
from regulatory_mcp.gateway import create_gateway

RATIONALE = "Synthetic fixture or handoff-derived calculation; original source not verified."


def amount(value, name="amount", **overrides):
    args = dict(
        name=name,
        value=value,
        unit="USD",
        dollar_year=2023,
        entity_definition="fixture scope",
        basis="assumption",
        assumption_rationale=RATIONALE,
    )
    args.update(overrides)
    return CalculationInput(**args)


def stream(values=((1, 110),), rate="0.1", **overrides):
    args = dict(
        flows=tuple(Flow(time=t, amount=amount(v)) for t, v in values),
        rate=rate,
        cash_flow_basis="real",
        rate_basis="real",
        assumption_rationale=RATIONALE,
    )
    args.update(overrides)
    return DiscountRequest(**args)


def test_independent_single_payment_zero_rate_and_negative_savings():
    assert Decimal(calculate("discount_cost_stream", stream())[0]["present_value"]) == 100
    assert (
        Decimal(calculate("discount_cost_stream", stream(((1, -110),)))[0]["present_value"]) == -100
    )
    request = AnnualizeRequest(
        present_value=amount(90),
        rate=0,
        payment_times=(1, 2, 3),
        monetary_basis="real",
        assumption_rationale=RATIONALE,
    )
    assert Decimal(calculate("annualize_present_value", request)[0]["payment"]) == 30


def test_timing_shift_preserves_equivalent_payment():
    for valuation in [0, 1]:
        request = stream(valuation_time=valuation)
        value = calculate("discount_cost_stream", request)[0]["present_value"]
        annual = AnnualizeRequest(
            present_value=amount(value),
            rate="0.1",
            valuation_time=valuation,
            payment_times=(1,),
            monetary_basis="real",
            assumption_rationale=RATIONALE,
        )
        assert Decimal(calculate("annualize_present_value", annual)[0]["payment"]) == 110


@pytest.mark.parametrize(
    ("flows", "expected"),
    [
        (((3, 693e6), (4, 318e6)), 105405317),
        (((3, 1138e6), (4, 1050e6)), 227373358),
        (((3, 1831e6), (4, 1368e6)), 332778675),
    ],
)
def test_handoff_fda_annualization(flows, expected):
    value = calculate("discount_cost_stream", stream(flows, "0.02"))[0]["present_value"]
    annual = AnnualizeRequest(
        present_value=amount(value),
        rate="0.02",
        payment_times=tuple(range(1, 11)),
        monetary_basis="real",
        assumption_rationale=RATIONALE,
    )
    assert float(calculate("annualize_present_value", annual)[0]["payment"]) == pytest.approx(
        expected, abs=1
    )


def test_break_even_receipts_and_rounding():
    request = BreakEvenRequest(
        cost=amount(333000000),
        quantity=amount(184600000000, unit="encounters", dollar_year=None),
        assumption_rationale=RATIONALE,
    )
    assert float(calculate("calculate_break_even", request)[0]["break_even"]) == pytest.approx(
        0.001803900325
    )
    ratio = CostReceiptsRequest(
        cost=amount(3), receipts=amount(100), period="one year", assumption_rationale=RATIONALE
    )
    assert Decimal(calculate("calculate_cost_to_receipts", ratio)[0]["percent"]) == 3
    for value, match in [("2.4999", False), ("2.5", True), ("3.5", False)]:
        compare = ReconcileRequest(
            calculated=amount(value),
            reported=amount(3),
            rounding_increment=1,
            assumption_rationale=RATIONALE,
        )
        assert calculate("reconcile_reported_values", compare)[0]["rounding_match"] is match
    zero = ReconcileRequest(
        calculated=amount(0), reported=amount(0), assumption_rationale=RATIONALE
    )
    assert calculate("reconcile_reported_values", zero)[0]["relative_difference"] is None


def test_grid_and_validation():
    grid = ScenariosRequest(
        discount=stream(((1, 110),)), rates=(0, "0.1"), assumption_rationale=RATIONALE
    )
    rows = calculate("run_parameter_scenarios", grid)[0]["scenarios"]
    assert [Decimal(row["present_value"]) for row in rows] == [110, 100]
    for kwargs in [{"rate": -1}, {"rate": "NaN"}, {"rate_basis": "nominal"}, {"flows": ()}]:
        with pytest.raises(ValidationError):
            stream(**kwargs)
    for bad in [True, "NaN", "1e999", [], "invalid"]:
        with pytest.raises(AnalysisError):
            calculate("discount_cost_stream", stream(((1, bad),)))
    with pytest.raises(AnalysisError, match="INCOMPATIBLE_UNITS"):
        calculate(
            "discount_cost_stream",
            stream(flows=(Flow(time=1, amount=amount(1, unit="million USD")),)),
        )
    with pytest.raises(AnalysisError, match="DENOMINATOR"):
        calculate(
            "calculate_cost_to_receipts",
            CostReceiptsRequest(
                cost=amount(1), receipts=amount(0), period="year", assumption_rationale=RATIONALE
            ),
        )


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_saved_calculation_resolves_across_children(tmp_path, mode):
    async def run():
        store = EvidenceStore(tmp_path)
        gateway = await create_gateway(
            {"analysis": create_analysis_server(store), "documents": create_evidence_server(store)},
            Settings(gateway_mode=mode),
        )
        async with Client(gateway) as client:
            request = stream().model_dump(mode="json")
            if mode == "codemode":
                code = (
                    'run = await call_tool("analysis_discount_cost_stream", {"request": '
                    + repr(request)
                    + "})\n"
                    'return await call_tool("documents_get_run", {"run_id": run["run_id"]})'
                )
                result = await client.call_tool("execute", {"code": code})
            else:
                result = await client.call_tool(
                    "analysis_discount_cost_stream", {"request": request}
                )
            data = result.structured_content
            assert Decimal(data["outputs"]["present_value"]) == 100
            assert store.run(UUID(data["run_id"])).code_revision.startswith("sha256:")

    asyncio.run(run())


def test_missing_evidence_prevents_saved_run(tmp_path):
    async def run():
        item = amount(110, basis="reported", assumption_rationale=None, evidence_refs=(uuid4(),))
        request = stream(flows=(Flow(time=1, amount=item),))
        async with Client(create_analysis_server(EvidenceStore(tmp_path))) as client:
            result = await client.call_tool(
                "discount_cost_stream",
                {"request": request.model_dump(mode="json")},
                raise_on_error=False,
            )
            assert result.is_error
        assert not list((tmp_path / "artifacts").glob("*.json"))

    asyncio.run(run())
