---
title: "Deterministic Analysis Tools"
description: "Calculation request formats, units, timing, and evidence-linked run manifests."
status: draft
tier: 2
last_updated: "2026-10-30"
related_files: ["DEVELOPMENT.md", "IMPLEMENTATION_PIPELINE.md"]
---

# Deterministic analysis

The gateway registers six tools in the `analysis` namespace. Each takes a typed `request`, validates units and assumptions, calculates using a 40-digit Decimal context, and saves a `CalculationRun`. Numerical results are decimal strings, preserving precision across JSON and CodeMode calls. Inputs support up to 50 significant digits, with nonzero magnitudes between 1e-100 and below 1e101.

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
