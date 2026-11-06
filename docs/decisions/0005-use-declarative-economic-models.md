---
title: "Use bounded declarative economic models"
description: "Persist claims, assumptions and typed arithmetic graphs for reproducible review."
status: proposed
tier: 2
last_updated: "2026-11-06"
date: "2026-11-06"
decision_makers: ["Project owner"]
category: architecture
nist_controls: ["SI-10", "SA-11", "AU-3"]
impact_level: not-assessed
ato_relevance: no
risk_treatment: mitigate
related_files: ["../ANALYSIS.md", "../IMPLEMENTATION_PIPELINE.md"]
---

# Use bounded declarative economic models

## Context and Decision Drivers

Phase 3 scope was approved by the owner: reconstruct economic arguments against
the original 2016 FDA analysis. Existing calculations retain evidence, but cannot
represent reusable formula graphs or the claims and assumptions driving them.
Reviewers need missing inputs to remain visible and results to be reproducible.
This is a public-source prototype with no asserted FIPS impact level or ATO.

## Considered Options

1. Existing six calculators only: zero new operations, but no reusable model graph.
2. Typed arithmetic graph: five operations, at most 100 parameters and 100 formulas,
   no new dependencies; named edges, unit dimensions and immutable model records.
3. Uploaded code/workbooks: broader expressiveness, but introduces an execution
   subsystem and formula/macro interpretation outside this milestone.

## Decision Outcome

Implement option 2 under the existing analysis namespace, contracts package and
byte-store abstraction. Add immutable model records and embed the exact model
and all intermediate values into existing calculation manifests. Operations are
add, subtract, multiply, divide and bounded integer power; no expression parser
or caller code is executed. Unit vectors are checked statically across the graph.
One declared dollar year and real/nominal basis apply to the entire model.

Numeric evidence must be reviewed before a run is retained. Missing values can
be saved but not evaluated. Claims retain supporting and conflicting evidence;
assessment labels are analyst assertions, not automated findings of validity.

## Consequences

No new services or dependencies; local and hosted stores share validation.
New public contracts and seven MCP tools require both-mode integration tests.
Bounds and explicit decimal precision make evaluation auditable. Unit dimensions
do not validate population comparability, causal transferability, implicit scales,
or timing; these require analyst review. Monetary inputs must be normalized to
the declared year/basis before entry. Fractional powers, simulations and scenario
overrides are outside this bounded first model evaluator; Phase 4 remains tracked.

## Verification and Rollback

Test independent small models, invalid dependency/unit graphs, missing inputs,
numeric edge cases, immutable persistence, evidence review and reconciliation.
Register tools on the analysis child shared by both transports. FDA model fidelity
requires the final RIA and confirmed input evidence. Roll back registration and
code while preserving stored records. Human code/ADR review remains pending.

## Run response sizing amendment

The 97-formula FDA candidate exposed a gateway output-budget failure after run
persistence. Owner approved compact evaluation/comparison summaries and paginated
inspection. Summaries expose outputs, IDs and provenance metadata; new read tools
retrieve summaries or at most 4000 ASCII characters of deterministic JSON per
page. Concatenation and SHA-256 verification recover the complete manifest.
This avoids raising shared limits or dropping provenance. Clients must reassemble
pages before parsing JSON. Existing small calculator responses remain compatible.
