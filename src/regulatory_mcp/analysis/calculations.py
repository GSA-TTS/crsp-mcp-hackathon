"""Decimal arithmetic; strings retain precision in JSON and stored run manifests."""

from collections.abc import Callable
from decimal import ROUND_HALF_UP, Decimal, DecimalException, localcontext
from typing import Any

from regulatory_mcp.analysis.requests import (
    AnnualizeRequest,
    BreakEvenRequest,
    CostReceiptsRequest,
    DiscountRequest,
    ReconcileRequest,
    ScenariosRequest,
)
from regulatory_mcp.contracts import CalculationInput


class AnalysisError(ValueError):
    """Safe domain error to expose through MCP."""


def number(item: CalculationInput) -> Decimal:
    if isinstance(item.value, bool) or not isinstance(item.value, (str, int, float)):
        raise AnalysisError("INVALID_INPUT: expected a finite numeric scalar")
    try:
        value = Decimal(str(item.value))
    except DecimalException as exc:
        raise AnalysisError("INVALID_INPUT: invalid numeric value") from exc
    if not value.is_finite() or (value and not -100 <= value.adjusted() <= 100):
        raise AnalysisError("INVALID_INPUT: nonfinite value or magnitude outside supported range")
    if len(value.as_tuple().digits) > 50:
        raise AnalysisError("INVALID_INPUT: values support at most 50 significant digits")
    return value


def matching(items: list[CalculationInput], *, entity: bool = False) -> None:
    first = items[0]
    for item in items[1:]:
        if (item.unit, item.dollar_year) != (first.unit, first.dollar_year):
            raise AnalysisError("INCOMPATIBLE_UNITS: normalize units and dollar years explicitly")
        if entity and item.entity_definition != first.entity_definition:
            raise AnalysisError("INCOMPATIBLE_ENTITIES: entity definitions must match")


def monetary(item: CalculationInput) -> None:
    # Canonical units avoid silently interpreting 'millions' or alternate currencies.
    if item.unit != "USD" or item.dollar_year is None:
        raise AnalysisError("INCOMPATIBLE_UNITS: monetary inputs require USD and a dollar year")


def pv(request: DiscountRequest, rate: Decimal | None = None) -> Decimal:
    amounts = [flow.amount for flow in request.flows]
    matching(amounts, entity=True)
    monetary(amounts[0])
    effective_rate = request.rate if rate is None else rate
    return sum(
        (
            number(flow.amount) / (1 + effective_rate) ** (flow.time - request.valuation_time)
            for flow in request.flows
        ),
        Decimal(0),
    )


def discount(request: DiscountRequest) -> tuple[dict[str, Any], dict[str, str], str]:
    return {"present_value": str(pv(request))}, {"present_value": "USD"}, "sum(C[t]/(1+r)^(t-v))"


def annualize(request: AnnualizeRequest) -> tuple[dict[str, Any], dict[str, str], str]:
    monetary(request.present_value)
    factor = sum(
        ((1 + request.rate) ** -(t - request.valuation_time) for t in request.payment_times),
        Decimal(0),
    )
    result = number(request.present_value) / factor
    return {"payment": str(result)}, {"payment": "USD/payment"}, "PV/sum((1+r)^(-(t-v)))"


def break_even(request: BreakEvenRequest) -> tuple[dict[str, Any], dict[str, str], str]:
    monetary(request.cost)
    denominator = number(request.quantity)
    if (
        denominator <= 0
        or request.quantity.dollar_year is not None
        or request.quantity.unit == "USD"
    ):
        raise AnalysisError("INVALID_DENOMINATOR: quantity must be positive and nonmonetary")
    result = number(request.cost) / denominator
    return (
        {"break_even": str(result)},
        {"break_even": f"USD/({request.quantity.unit})"},
        "cost/quantity",
    )


def cost_receipts(request: CostReceiptsRequest) -> tuple[dict[str, Any], dict[str, str], str]:
    matching([request.cost, request.receipts], entity=True)
    monetary(request.cost)
    denominator = number(request.receipts)
    if denominator <= 0:
        raise AnalysisError("INVALID_DENOMINATOR: receipts must be positive")
    value = number(request.cost) / denominator
    return (
        {"ratio": str(value), "percent": str(value * 100)},
        {"ratio": "dimensionless", "percent": "percent"},
        "cost/receipts; percent=100*ratio",
    )


def reconcile(request: ReconcileRequest) -> tuple[dict[str, Any], dict[str, str], str]:
    matching([request.calculated, request.reported], entity=True)
    actual, reported = number(request.calculated), number(request.reported)
    difference = actual - reported
    tolerance = max(request.absolute_tolerance, abs(reported) * request.relative_tolerance)
    rounding_match = None
    if request.rounding_increment is not None:
        step = request.rounding_increment
        if reported / step != (reported / step).to_integral_value():
            raise AnalysisError("INVALID_INPUT: reported value is not on the rounding increment")
        rounding_match = (actual / step).quantize(
            Decimal(1), rounding=ROUND_HALF_UP
        ) * step == reported
    outputs = {
        "difference": str(difference),
        "absolute_difference": str(abs(difference)),
        "relative_difference": str(abs(difference) / abs(reported)) if reported else None,
        "within_tolerance": abs(difference) <= tolerance,
        "rounding_match": rounding_match,
    }
    units = {
        "difference": request.calculated.unit,
        "absolute_difference": request.calculated.unit,
        "relative_difference": "dimensionless",
        "within_tolerance": "boolean",
        "rounding_match": "boolean or null",
    }
    return (
        outputs,
        units,
        "delta=calculated-reported; max(abs_tol,abs(reported)*rel_tol); half-up rounding",
    )


def scenarios(request: ScenariosRequest) -> tuple[dict[str, Any], dict[str, str], str]:
    rows = [
        {"rate": str(rate), "present_value": str(pv(request.discount, rate))}
        for rate in request.rates
    ]
    return (
        {"scenarios": rows},
        {"scenarios": "rate: fraction; present_value: USD"},
        "PV for each stated rate",
    )


def calculate(operation: str, request: Any) -> tuple[dict[str, Any], dict[str, str], str]:
    functions: dict[str, Callable[[Any], tuple[dict[str, Any], dict[str, str], str]]] = {
        "discount_cost_stream": discount,
        "annualize_present_value": annualize,
        "calculate_break_even": break_even,
        "calculate_cost_to_receipts": cost_receipts,
        "reconcile_reported_values": reconcile,
        "run_parameter_scenarios": scenarios,
    }
    try:
        with localcontext() as context:
            context.prec = 40
            context.Emax, context.Emin = 10000, -10000
            return functions[operation](request)
    except DecimalException as exc:
        raise AnalysisError("NUMERIC_RANGE: calculation exceeds supported decimal range") from exc
