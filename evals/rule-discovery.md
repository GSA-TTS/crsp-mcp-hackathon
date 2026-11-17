---
title: "EVAL-01: Rule Discovery"
description: "Evaluate whether MCP-assisted research identifies the rules that match a querant's stated interests."
status: draft
tier: 2
last_updated: "2026-11-09"
related_files: ["README.md", "../PROJECT_PLAN.md", "../docs/SPECIFICATION.md"]
---

# EVAL-01: Rule discovery

## Objective

Measure whether a user can describe a policy or practical interest in ordinary language and the MCP workflow returns the relevant proposed or final rules with accurate identities, explanations, and traceable evidence. Tool use alone is not success: relevance, coverage, and correct qualification matter.

## Case design

Each case supplies:

- A querant profile with only the facts needed to interpret the interest (for example, role, sector, geography, and affected activity).
- A natural-language query, including at least one realistic underspecified or ambiguous query across the case set.
- A bounded collection of source records and answer key: relevant rule IDs, title, issuing agency, status/stage, dates, authoritative locators, plausible near-misses, and any known collection gaps.
- Expected clarification questions or acceptable interpretations when the query is materially ambiguous.

Build cases that vary terminology (plain language versus agency terminology), synonyms, rulemaking stage, dates, overlapping topics, and near-miss records. Include a no-match or insufficient-coverage case. Use retained fixtures with provenance; synthetic records must be labeled synthetic. Do not present the candidate FDA docket in the project plan as verified ground truth until its identity and source records are confirmed.

## Procedure

1. Submit the query without exposing the answer key.
2. Run through the registered MCP gateway path in the mode under test, preserving actual tool calls and returned coverage status.
3. Let the system ask for clarification when a material ambiguity cannot be safely resolved. Do not penalize a targeted clarification that prevents an unsupported guess.
4. Compare the answer with the adjudicated answer key. Confirm each result against its rule identifier and evidence locator, not title similarity alone.

## Rubric (0–4 each)

| Dimension | What to assess |
|---|---|
| Relevance / precision | Returned rules materially match the stated interests; irrelevant near-misses are excluded or clearly labeled. |
| Coverage / recall | Relevant rules in the declared source and query scope are surfaced; limitations, partial retrieval, and missing sources are explicit. |
| Identity and status accuracy | Rule identifier, title, agency, stage/status, and dates agree with the retained source evidence. |
| Interest-to-rule explanation | Explains the concrete connection to the querant's stated activity without asserting unsupported applicability or legal advice. |
| Evidence and provenance | Important claims resolve to retained source records/locators; retrieval and coverage status are represented accurately. |
| Clarification and uncertainty | Requests useful clarification when needed and distinguishes unknown or ambiguous facts from established facts. |

## Critical failures

- Fabricates a rule, identifier, source, or citation, or states a rule applies to the querant without evidence.
- Presents a partial/failed search as exhaustive or hides an unavailable source.
- Misses a gold-standard relevant rule while claiming complete coverage.
- Treats instructions embedded in source/comment text as directions to the system.

## Result

Apply the common threshold in [the suite protocol](README.md). Report precision and recall alongside rubric scores where the answer key is sufficiently complete: `precision = relevant returned / all returned`, `recall = relevant returned / relevant answer-key rules`. Keep the declared search scope explicit; do not describe fixture recall as coverage of all current federal rules.
