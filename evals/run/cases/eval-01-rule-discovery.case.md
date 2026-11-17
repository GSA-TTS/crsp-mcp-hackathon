---
title: "EVAL-01 case RD-01: packaged-food regulatory affairs querant"
description: "Frozen natural-language rule-discovery case for run RUN-2026-11-17-A."
status: draft
tier: 2
last_updated: "2026-11-17"
related_files: ["../../rule-discovery.md", "../keys/eval-01-rule-discovery.key.md"]
---

# EVAL-01 case RD-01

**Case ID:** `RD-01`
**Spec:** [`../../rule-discovery.md`](../../rule-discovery.md)
**Source mode:** live public sources (Federal Register API, Regulations.gov API, Reginfo public XML). No fixtures.

## Querant profile (synthetic, no real person)

| Field | Value |
| --- | --- |
| Role | Regulatory affairs lead |
| Organization type | Mid-size packaged-food manufacturer, roughly $40 million annual food sales |
| Sector | Packaged food manufacturing (shelf-stable sauces and snacks) |
| Geography | United States, single manufacturing site |
| Affected activity | Designing and printing retail food package labels; deciding whether to reformulate products |
| Practical interest | "Do I have to change my package artwork, and by when?" |

## Queries submitted (verbatim)

| Query ID | Type | Text |
| --- | --- | --- |
| `Q1` | plain language | new rules about what must be printed on the front of food packages |
| `Q2` | agency terminology | front-of-package nutrition labeling |
| `Q3` | underspecified / ambiguous | food label changes |
| `Q4` | out-of-scope (no federal match expected) | municipal sugary drink warning sign |
| `Q5` | near-miss heavy | front-of-package nutrition labels school cafeteria meals |
| `Q6` | docket-oriented | front-of-package nutrition information (Regulations.gov docket search) |
| `Q7` | nonsense control | zzzqqxnonexistentterm12345 |

`Q3` is the required underspecified query. `Q4` and `Q7` are the required
no-match / insufficient-coverage cases. `Q5` deliberately mixes the target
vocabulary with an adjacent program (menu and vending labeling) that has its own
real rules, to test whether near-misses displace the gold record.

## Declared search scope

One bounded page per query, `page_size` 5 for Federal Register and 5 for the
Regulations.gov docket search. Recall below is recall against the case answer key
only. It is **not** coverage of all current federal rules.

## Execution constraints

- The answer key in `../keys/` was not shown to the retrieval step.
- Clarification questions were permitted without penalty; none were required because
  the querant profile already named sector, size, and activity.
- All tool responses retained as artifacts; identifiers listed in
  `../transcripts/eval-01.transcript.md`.
