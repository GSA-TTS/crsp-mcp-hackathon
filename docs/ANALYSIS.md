---
title: "Deterministic Analysis Tools"
description: "Calculation request formats, units, timing, and evidence-linked run manifests."
status: draft
tier: 2
last_updated: "2026-11-06"
related_files: ["DEVELOPMENT.md", "IMPLEMENTATION_PIPELINE.md"]
---

# Deterministic analysis

The gateway registers six calculation tools and seven model tools in the `analysis` namespace. Each calculation tool takes a typed `request`, validates units and assumptions, calculates using a 40-digit Decimal context, and saves a `CalculationRun`. Numerical results are decimal strings, preserving precision across JSON and CodeMode calls. Calculator inputs support up to 50 significant digits, with nonzero magnitudes between 1e-100 and below 1e101.

| Tool | Request | Output |
|---|---|---|
| `analysis_discount_cost_stream` | Dated flows, rate, valuation time, real/nominal bases | USD present value |
| `analysis_annualize_present_value` | USD present value, rate, explicit payment times | USD per equal payment |
| `analysis_calculate_break_even` | USD cost and positive nonmonetary quantity | USD per quantity unit |
| `analysis_calculate_cost_to_receipts` | Matched USD costs/receipts and stated period | Ratio and percent |
| `analysis_reconcile_reported_values` | Matched values, tolerances, optional rounding increment | Differences, tolerance and rounding checks |
| `analysis_run_parameter_scenarios` | Discount request and explicit rate grid | Present value at each rate |

## Input and evidence rules

Amounts use `CalculationInput`: name, numeric value, unit, entity definition, basis, and evidence references or an assumption rationale. Monetary inputs must be canonical `USD` and specify `dollar_year`; convert millions to dollars explicitly. Matching calculations reject different units, dollar years, or required entity definitions rather than silently normalizing them.

Every request also includes `assumption_rationale`, explaining its rates, timing, tolerances, and scope. These parameters are retained as an explicit assumption input. Numerical evidence references must resolve to reviewed evidence and intact artifacts before the run is saved. Synthetic or handoff-derived values must use `basis: assumption` with an honest rationale until source evidence is available.

Run manifests record the formula, parameters, outputs and units, UTC creation time, tool version, and a SHA-256 fingerprint of the installed analysis source files. Original caller input names are preserved in parameters; stored input roles are prefixed to make repeated flow names unambiguous. Retrieve the manifest with `documents_get_run(run_id)`.

Runs are labeled `model_reconstruction` with an explicit warning that deterministic arithmetic is not independent validation or original-document verification. This label identifies execution of the supplied model, not confirmation that an agency model was reconstructed faithfully. Source-grounded FDA reproduction remains gated on WP-06.

## Discounting example

Call `analysis_discount_cost_stream` with:

```json
{
  "request": {
    "flows": [{
      "amount": {
        "name": "year_one_cost",
        "value": "110",
        "unit": "USD",
        "dollar_year": 2023,
        "entity_definition": "one synthetic project",
        "basis": "assumption",
        "assumption_rationale": "Synthetic arithmetic demonstration"
      },
      "time": "1"
    }],
    "rate": "0.1",
    "valuation_time": "0",
    "cash_flow_basis": "real",
    "rate_basis": "real",
    "assumption_rationale": "Ten percent real rate; end-year cost valued at time zero"
  }
}
```

The saved run returns `outputs.present_value = "100"`. Negative flows are supported as explicitly supplied savings/benefits.

## Timing and bounds

Discounting uses `sum(C[t]/(1+r)^(t-v))`. Annualization uses `PV/sum((1+r)^(-(t-v)))` over the requested payment times. Times are relative years on the same origin; each must be between -1000 and 1000. For ordinary ten-year end-year annualization, pass payment times 1 through 10. Equal periodic spacing is the caller's responsibility; arbitrary distinct dates calculate equal payments at those dates, not necessarily annual payments.

Rates are fractions greater than -1 and at most 10. Real and nominal discounting bases must match. At zero rate, annualization divides PV by the number of payments. There can be at most 1000 flows or payments. Scenario grids have at most 100 distinct rates and 10000 flow/rate evaluations. Simulation and stochastic assumptions belong to WP-08.

Reconciliation uses the larger of absolute tolerance and absolute reported value times relative tolerance. Relative difference is null for a zero reported value. Rounding uses the declared increment and decimal half-up convention, including ties away from zero; it is reported separately from tolerance agreement. Published rounding conventions must be verified before using that comparison to judge an agency result.

Cost-to-receipts requires identical entity definitions and a stated period; the period is a caller assertion, not independently verified. A sector-average ratio does not describe the distribution of small-firm burdens. Break-even similarly depends on the stated scope and units of its quantity denominator.

## Declarative economic models

Models make the path from evidence and assumptions to conclusions explicit.
See [ADR-0005](decisions/0005-use-declarative-economic-models.md).

| Tool | Input | Result |
|---|---|---|
| `analysis_create_model` | `definition` | New immutable model ID and full validated definition |
| `analysis_get_model` | `model_id` | Definition with evidence references checked |
| `analysis_inspect_model_readiness` | `model_id` | Missing parameters, assumptions, unreviewed numerical evidence, claims and support gaps |
| `analysis_evaluate_model` | `model_id` | Compact outputs/ID summary; full model and intermediate values saved |
| `analysis_reconcile_model_output` | `request` | Compact comparison summary; source run, tolerances and evidence saved |
| `analysis_get_model_run` | `run_id` | Compact summary with evidence references validated |
| `analysis_inspect_model_run` | `run_id`, `offset`, `limit` | Lossless JSON text page of the full manifest; default/max 4000 characters |

Every definition declares title, no-action baseline, one alternative, affected
population, monetary basis (`real` or `nominal`), dollar year and timing convention.
Represent another alternative with a new model record. Parameters have `name`,
decimal `value`, `unit`, `entity_definition`, `basis`, evidence and/or rationale.
Basis is `reported`, `derived`, `assumption`, or `missing`. Missing parameters
must have a null value and rationale; they block evaluation even when unused.
Reported/derived values require evidence; assumptions require a rationale.
Evidence review confirms a selection, not automatic verification of its numeric
interpretation. Sourced values must be normalized explicitly by the analyst.

Units are dimension vectors: `[{"symbol":"USD","exponent":1}]` for dollars,
`[]` for a dimensionless ratio. Use USD, not millions of USD; all currency values
share the model's dollar year/basis. Addition/subtraction require equal vectors;
multiplication/division combine exponents. Integer power scales exponents.
Canonical output labels omit exponent 1 (`USD`), enabling existing calculators.
Different populations or timing can still share dimensions; their comparability
is an analyst responsibility, not something unit checking establishes.

Formulas contain a name, operation, operand names, expected unit and rationale.
Operations `add`, `subtract`, `multiply`, `divide` take two operands;
`integer_power` takes one operand and an integer `exponent` from -20 to 20.
Input order is irrelevant; cycles, unknown references and duplicate names fail.
At most 100 parameters, 100 formulas, 20 outputs and 50 claims are accepted.
Numeric parameters allow 30 digits, at most 15 decimal places; evaluation uses
40-digit Decimal arithmetic and bounded exponents. Undefined operations and
out-of-range results fail without saving a successful run.

Claims include a statement, supporting/conflicting evidence IDs, node dependencies,
and an analyst assessment with rationale. They can remain unassessed or unsupported;
that is reported by inspection rather than converted into a credibility score.
Claim evidence must exist, but only parameter evidence requires review to calculate.

### Minimal model example

Pass this as `definition` to `analysis_create_model`:

```json
{
  "title": "Synthetic proportional benefit model",
  "baseline": "No intervention",
  "alternative": "Illustrative intervention",
  "affected_population": "Synthetic population",
  "monetary_basis": "real",
  "dollar_year": 2014,
  "timing_convention": "Present values at year zero",
  "parameters": [
    {"name":"reference_benefits","value":"1000","unit":[{"symbol":"USD","exponent":1}],"entity_definition":"Synthetic population","basis":"assumption","rationale":"Synthetic illustration, not FDA data"},
    {"name":"scale","value":"0.2","unit":[],"entity_definition":"Transfer fraction","basis":"assumption","rationale":"Synthetic illustration"}
  ],
  "formulas": [
    {"name":"benefits","operation":"multiply","operands":["reference_benefits","scale"],"unit":[{"symbol":"USD","exponent":1}],"rationale":"Illustrative linear transfer"}
  ],
  "outputs": ["benefits"],
  "claims": []
}
```

Evaluate the returned `model_id`: the result is 200 USD, not an FDA estimate.
Retrieve its summary with `analysis_get_model_run`. To compare, pass `run_id`, `output_name`,
a `reported` CalculationInput, and explicit absolute/relative tolerances or a
rounding increment to `analysis_reconcile_model_output` under `request`.
The reported entity must match `affected_population`; units and dollar year must
match the selected output. The comparison retains the entire source run and
reported evidence. Reconciliation does not confer human approval or establish
that the model faithfully reconstructs the agency analysis.

Model evaluation and comparison return compact summaries with `manifest_included:
false` and `manifest_tool: analysis_inspect_model_run`. Large manifests can exceed
the legacy `documents_get_run` response budget. To retrieve them, request manifest
pages starting at offset 0, follow `next_offset` until null, concatenate `text`
in order, verify SHA-256 over ASCII bytes, then parse JSON. Individual pages may
split tokens/escape sequences and are not independently parseable JSON documents.
`total_characters` and the stable hash identify the full serialized manifest.
All intermediates, evidence references and nested comparison source runs remain
in immutable storage. Pagination bounds response size without raising gateway
limits. Model definitions/readiness still use their original response shapes.
