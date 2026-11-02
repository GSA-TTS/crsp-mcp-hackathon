"""Bounded calculation requests with explicit units and modeling assumptions."""

from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from regulatory_mcp.contracts import CalculationInput
from regulatory_mcp.contracts.models import Contract, Nonempty

Number = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=30, decimal_places=15)]
Rate = Annotated[Number, Field(gt=-1, le=10)]
Time = Annotated[Number, Field(ge=-1000, le=1000)]
Amount = Annotated[CalculationInput, Field()]


class Request(Contract):
    assumption_rationale: Nonempty


class Flow(Contract):
    amount: Amount
    time: Time


class DiscountRequest(Request):
    flows: tuple[Flow, ...] = Field(min_length=1, max_length=1000)
    rate: Rate
    valuation_time: Time = Decimal(0)
    cash_flow_basis: Literal["real", "nominal"]
    rate_basis: Literal["real", "nominal"]

    @model_validator(mode="after")
    def matching_bases(self) -> Self:
        if self.cash_flow_basis != self.rate_basis:
            raise ValueError("Cash flows and discount rate must share a real/nominal basis")
        return self


class AnnualizeRequest(Request):
    present_value: Amount
    rate: Rate
    valuation_time: Time = Decimal(0)
    payment_times: tuple[Time, ...] = Field(min_length=1, max_length=1000)
    monetary_basis: Literal["real", "nominal"]

    @model_validator(mode="after")
    def distinct_payments(self) -> Self:
        if len(set(self.payment_times)) != len(self.payment_times):
            raise ValueError("Payment times must be distinct")
        return self


class BreakEvenRequest(Request):
    cost: Amount
    quantity: Amount


class CostReceiptsRequest(Request):
    cost: Amount
    receipts: Amount
    period: Nonempty


class ReconcileRequest(Request):
    calculated: Amount
    reported: Amount
    absolute_tolerance: Annotated[Number, Field(ge=0)] = Decimal(0)
    relative_tolerance: Annotated[Number, Field(ge=0, le=1)] = Decimal(0)
    rounding_increment: Annotated[Number, Field(gt=0)] | None = None


class ScenariosRequest(Request):
    discount: DiscountRequest
    rates: tuple[Rate, ...] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def bounded_grid(self) -> Self:
        if len(set(self.rates)) != len(self.rates):
            raise ValueError("Scenario rates must be unique")
        if len(self.rates) * len(self.discount.flows) > 10_000:
            raise ValueError("Scenario grid exceeds 10000 flow evaluations")
        return self
