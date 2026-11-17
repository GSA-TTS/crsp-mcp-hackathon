---
title: "EVAL-04: Independent Reviewer Analysis"
description: "Evaluate robust, independent review of a commenter's analysis and supporting comment draft."
status: draft
tier: 2
last_updated: "2026-11-09"
related_files: ["README.md", "../PROJECT_PLAN.md", "../docs/SPECIFICATION.md"]
---

# EVAL-04: Independent reviewer analysis

## Objective

Measure whether a reviewer can use MCP evidence and analysis tools to critically assess a commenter's reasoning and supporting draft, identify substantiated strengths and defects, and return transparent, actionable findings. The review must not simply endorse, rewrite, or score the argument based on whether the reviewer agrees with its policy conclusion.

## Case design

Each case supplies a rule record, a commenter's analysis and draft, referenced source artifacts or evidence locators, relevant calculations/data where available, and a gold review key. Seed cases with known issues: a correct argument, a missing citation, a source that does not support its attributed claim, a unit/date mismatch, an omitted counterargument, an unsupported causal inference, and an honestly qualified uncertainty. Include clean cases to detect false-positive criticism.

The gold key should identify material claims, evidence support level, calculation conventions and expected values/tolerances where applicable, missing issues, acceptable reviewer interpretations, and severity rationale. Use independently derived expected results rather than outputs copied from the implementation under test.

## Procedure

1. Give the reviewer the same bounded package a human reviewer would receive; do not reveal seeded defects or expected findings.
2. Run through registered MCP tools in the intended mode and capture source/evidence lookups and calculations.
3. Require a finding list with severity, affected claim/passage, evidence locator, explanation, confidence/uncertainty, and a concrete correction or follow-up.
4. Compare findings against the gold key, check citation resolution and calculations independently, and assess unsupported accusations as false positives.

## Rubric (0–4 each)

| Dimension | What to assess |
|---|---|
| Claim and citation verification | Material assertions are traced to the cited source and accurately classified as supported, contradicted, not found, or unverifiable. |
| Analytical / quantitative rigor | Units, denominators, dates, timing, assumptions, formulas, precision, and reproducibility are checked where relevant; errors are independently reproducible. |
| Completeness and prioritization | Material strengths, weaknesses, omissions, counterarguments, and limitations are considered; findings are prioritized by consequence. |
| Independence and fairness | Critiques reasoning and evidence rather than viewpoint; recognizes supported claims and avoids inventing defects or applying asymmetric standards. |
| Actionability and traceability | Each material finding identifies the affected passage, evidence, rationale, confidence, and a practical correction or validation step. |
| Uncertainty and scope | Distinguishes disproven claims from unverified claims and identifies inaccessible/partial sources; avoids legal or agency-compliance conclusions outside scope. |

## Critical failures

- Misses a seeded material factual contradiction, invalid calculation, or fabricated citation while asserting that review is complete.
- Invents a source, evidence locator, numerical result, or defect.
- Treats inability to access a source as proof that the commenter's claim is false, or represents partial evidence as exhaustive.
- Recommends or performs submission, or asserts a legal determination beyond the evaluation's scope.

## Result

Apply the common threshold in [the suite protocol](README.md). In addition to rubric scores, report seeded-defect detection and false-positive counts by severity, with precision/recall only where the gold key is adjudicated and complete. Human review remains necessary for disputed interpretations; record disagreements rather than silently forcing a single automated answer.
