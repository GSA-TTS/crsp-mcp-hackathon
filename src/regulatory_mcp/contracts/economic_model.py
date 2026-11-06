"""Bounded declarative economic models; units and dependencies are explicit."""

from decimal import Decimal
from typing import Annotated, Literal, Self
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from regulatory_mcp.contracts.models import Contract, Timestamp

Label = Annotated[str, Field(min_length=1, max_length=2000)]
Name = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")]
Number = Annotated[Decimal, Field(allow_inf_nan=False, max_digits=30, decimal_places=15)]


class Dimension(Contract):
    """A base unit; use USD for dollars, and an empty unit tuple for ratios."""

    symbol: Annotated[str, Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,31}$")]
    exponent: int = Field(ge=-16, le=16, strict=True)

    @model_validator(mode="after")
    def nonzero(self) -> Self:
        if self.exponent == 0:
            raise ValueError("Omit zero-exponent dimensions")
        return self


Unit = Annotated[tuple[Dimension, ...], Field(max_length=8)]


def dimensions(unit: Unit) -> dict[str, int]:
    result = {part.symbol: part.exponent for part in unit}
    if len(result) != len(unit):
        raise ValueError("Duplicate unit dimensions")
    return result


class ModelParameter(Contract):
    name: Name
    value: Number | None = None
    unit: Unit = ()
    entity_definition: Label
    basis: Literal["reported", "derived", "assumption", "missing"]
    evidence_refs: tuple[UUID, ...] = Field(default=(), max_length=20)
    rationale: Label | None = None

    @model_validator(mode="after")
    def attributable(self) -> Self:
        dimensions(self.unit)
        if self.basis == "missing":
            if self.value is not None or not self.rationale:
                raise ValueError("Missing parameters require null value and an explanation")
        elif self.value is None:
            raise ValueError("Known parameters require a value")
        if self.basis == "assumption" and not self.rationale:
            raise ValueError("Assumptions require a rationale")
        if self.basis in ("reported", "derived") and not self.evidence_refs:
            raise ValueError("Sourced parameters require evidence references")
        return self


class ModelFormula(Contract):
    name: Name
    operation: Literal["add", "subtract", "multiply", "divide", "integer_power"]
    operands: tuple[Name, ...] = Field(min_length=1, max_length=2)
    exponent: int | None = Field(default=None, ge=-20, le=20, strict=True)
    unit: Unit = ()
    rationale: Label

    @model_validator(mode="after")
    def arity(self) -> Self:
        dimensions(self.unit)
        if self.operation == "integer_power":
            if len(self.operands) != 1 or self.exponent is None:
                raise ValueError("Integer power requires one operand and an exponent")
        elif len(self.operands) != 2 or self.exponent is not None:
            raise ValueError("Binary operations require two operands and no exponent")
        return self


class EconomicClaim(Contract):
    name: Name
    statement: Label
    supporting_evidence: tuple[UUID, ...] = Field(default=(), max_length=20)
    conflicting_evidence: tuple[UUID, ...] = Field(default=(), max_length=20)
    depends_on: tuple[Name, ...] = Field(default=(), max_length=50)
    assessment: Literal["unassessed", "supported", "contested", "insufficient"] = "unassessed"
    assessment_rationale: Label | None = None

    @model_validator(mode="after")
    def explain_assessment(self) -> Self:
        if self.assessment != "unassessed" and not self.assessment_rationale:
            raise ValueError("Analyst assessments require a rationale")
        return self


def formula_order(
    parameters: tuple[ModelParameter, ...], formulas: tuple[ModelFormula, ...]
) -> list[ModelFormula]:
    available = {item.name for item in parameters}
    remaining = list(formulas)
    ordered = []
    while remaining:
        ready = [item for item in remaining if set(item.operands) <= available]
        if not ready:
            raise ValueError("Unresolved or circular formula dependencies")
        for item in ready:
            available.add(item.name)
            ordered.append(item)
            remaining.remove(item)
    return ordered


def formula_dimensions(formula: ModelFormula, units: dict[str, dict[str, int]]) -> dict[str, int]:
    left = units[formula.operands[0]]
    if formula.operation == "integer_power":
        if formula.exponent is None:
            raise ValueError("Integer power requires an exponent")
        result = {key: value * formula.exponent for key, value in left.items()}
    else:
        right = units[formula.operands[1]]
        if formula.operation in ("add", "subtract"):
            if left != right:
                raise ValueError("Addition/subtraction require identical units")
            return left
        sign = -1 if formula.operation == "divide" else 1
        result = dict(left)
        for key, value in right.items():
            result[key] = result.get(key, 0) + sign * value
    return {key: value for key, value in result.items() if value}


class ModelDefinition(Contract):
    title: Label
    baseline: Label
    alternative: Label
    affected_population: Label
    monetary_basis: Literal["real", "nominal"]
    dollar_year: int = Field(ge=1900, le=2200, strict=True)
    timing_convention: Label
    parameters: tuple[ModelParameter, ...] = Field(min_length=1, max_length=100)
    formulas: tuple[ModelFormula, ...] = Field(min_length=1, max_length=100)
    outputs: tuple[Name, ...] = Field(min_length=1, max_length=20)
    claims: tuple[EconomicClaim, ...] = Field(default=(), max_length=50)

    @model_validator(mode="after")
    def valid_graph(self) -> Self:
        names = [item.name for item in self.parameters] + [item.name for item in self.formulas]
        if len(set(names)) != len(names):
            raise ValueError("Parameter and formula names must be unique")
        if len(set(self.outputs)) != len(self.outputs) or not set(self.outputs) <= set(names):
            raise ValueError("Outputs must be unique references to model nodes")
        claim_names = [claim.name for claim in self.claims]
        if len(set(claim_names)) != len(claim_names):
            raise ValueError("Claim names must be unique")
        for claim in self.claims:
            if not set(claim.depends_on) <= set(names):
                raise ValueError("Claim dependencies must reference model nodes")
        units = {item.name: dimensions(item.unit) for item in self.parameters}
        for formula in formula_order(self.parameters, self.formulas):
            expected = formula_dimensions(formula, units)
            if expected != dimensions(formula.unit):
                raise ValueError("Declared formula units do not match derived dimensions")
            units[formula.name] = expected
        return self


class EconomicModel(ModelDefinition):
    model_id: UUID = Field(default_factory=uuid4)
    created_at: Timestamp
