---
title: "Regulatory Analysis MCP Project Plan"
description: "Scope, source readiness, milestones, and acceptance criteria for the regulatory analysis suite."
status: draft
tier: 1
last_updated: "2026-10-30"
related_files: ["README.md", "docs/SPECIFICATION.md", "docs/IMPLEMENTATION_PIPELINE.md"]
---

# Project plan

## Purpose

Help analysts follow a federal rulemaking from regulatory agenda and docket records to supporting evidence, reproducible economic calculations, and an evidence-linked review memo or draft public comment.

The initial product is a local, read-only research and analysis suite. Proposed interfaces and acceptance tests are specified in the [technical specification](docs/SPECIFICATION.md); implementation tasks are tracked in the [pipeline](docs/IMPLEMENTATION_PIPELINE.md).

## Scope and architecture

### Project identity and implementation baseline

Project: Regulatory Analysis MCP Suite (`regulatory-mcp`). Initial stack: Python 3.14, FastMCP 4.1.4, pydantic-settings 2.16.2, Hatchling packaging, and uv locking. Storage is planned as project-local artifacts; no database is selected. Hosting is local stdio. CI configuration is not part of the foundation authorization.

Compliance/data scope: the owner authorized a local public-source prototype on 2026-10-30. FIPS impact level and ATO relevance remain undetermined. Public-source inputs can contain personal information. See [development instructions](docs/DEVELOPMENT.md) for the implemented foundation and [AD-001](docs/adr/0001-local-fastmcp-gateway.md) for the proposed architecture.

Use modular FastMCP child servers mounted into one namespaced gateway. Apply CodeMode at the gateway for discovery and bounded tool orchestration. Keep conventional tool access available for evaluation and individual children independently usable.

| Namespace | Responsibility |
|---|---|
| `regulations` | Regulations.gov dockets, documents, and comments |
| `reginfo` | Public regulatory agenda, OIRA review, and PRA information where verified |
| `documents` | Retained source artifacts, passages, tables, and references |
| `analysis` | Deterministic calculations and explicitly parameterized scenarios |
| `census` | Business counts, size classes, and receipts |
| `bls` | Wage and price-series inputs |
| `research` | Supporting studies and bibliographic evidence |

These are proposed modules, not claims of working integrations. ROCIS.gov access is not assumed: the public Reginfo interfaces and any ROCIS-specific capability must be distinguished and verified in WP-05. A public record does not imply access to an internal application or its API.

Initial exclusions: comment submission, production deployment, proprietary-data acquisition, and automated conclusions that an agency has complied with legal requirements.

## Source readiness

The evidence available for this draft is the user-provided planning handoff and pasted Regulations.gov documentation. Source files, live API responses, and the original FDA RIA have not been retained in this repository.

| Source | Available basis | Implementation gate | Owner task |
|---|---|---|---|
| FastMCP | Handoff describes `mount()` and gateway CodeMode | Pin a compatible release; demonstrate combined discovery and execution | WP-01, WP-02 |
| Regulations.gov | Supplied v4 overview and examples | Obtain OpenAPI schemas, verify attachment fields, filters, and GET limits | WP-04 |
| Reginfo / ROCIS | Handoff reports prior public XML investigation | Recover exact public URLs, schemas, coverage, and sample snapshots | WP-05 |
| FDA RIA | Handoff provides selected tables and reported figures | Confirm docket, document identity, publication version, and original table locators | WP-06 |
| FDA cost models | References 26 and 28 named in handoff | Retrieve reports and identify missing reconstruction parameters | WP-08 |
| Census SUSB / SBA | Candidate business-size sources | Verify vintages, receipts availability, definitions, and relevant size standards | WP-09 |
| BLS / other price sources | Candidate wage and inflation inputs | Identify the actual series used to express costs in 2023 dollars | WP-09 |
| Research literature | RIA references are starting points | Resolve studies, access conditions, and transferability assumptions | WP-10 |
| Nielsen IQ Label Insight / Circana | Proprietary inputs reported in handoff | Independent validation requires lawful access or explicitly non-equivalent public substitutes | WP-08 |

## Three levels of verification

1. **Published-table reproduction:** check arithmetic, schedules, ratios, and reported rounding using agency inputs.
2. **Model reconstruction:** implement documented formulas and uncertainty assumptions, identifying omitted inputs and tolerances.
3. **Independent input validation:** compare underlying inputs with independently obtained evidence, preserving coverage and definition differences.

Every finding identifies its level. A suitable qualification is: “Reproduced using agency-reported inputs; underlying product counts not independently verified.”

## Initial FDA demonstration

Treat `FDA-2024-N-2910` as a candidate docket from the handoff until its identity and relationship to the target RIA are verified.

1. Retrieve docket details and available RIN values.
2. Find the rule and supporting analysis; request attachment metadata explicitly.
3. Retain the original RIA with hash, retrieval timestamp, and source identifiers.
4. Extract selected tables and assumptions with page/table locators and reviewed transcription.
5. Reproduce annualized costs, break-even values, and selected ratios.
6. Reconstruct cost components where published inputs permit it.
7. Produce an evidence-linked memo separating reconciled results, unresolved inputs, and methodological questions.

### Preliminary calculation baseline

These checks were recomputed with Python 3 during planning from the handoff's rounded values. All cost figures below are millions of dollars. They are not original-document verification.

| Component | Year 3 | Year 4 | PV at time 0, end-year timing | Ten-year annualized cost at 2% |
|---|---:|---:|---:|---:|
| Relabeling | 693 | 318 | 946.812223 | 105.405317 |
| Reformulation | 1,138 | 1,050 | 2,042.400514 | 227.373358 |
| Combined | 1,831 | 1,368 | 2,989.212737 | 332.778675 |

Reported annualized figures of 105, 227, and 333 reconcile at whole-million precision. Their rounded components need not sum to the rounded combined value.

Discounting the combined stream with exponents two and three instead yields 3,048.996992, consistent with the reported PV of 3,049. Moving the valuation date and annuity timing consistently preserves annualized cost; WP-06 must establish the RIA's intended convention.

Other baseline checks:

- `2,187 / 322,326 × 100 = 0.678506%`; compare with the reported narrative's 0.5% after checking definitions and transcription.
- `$333 million / 184.6 billion encounters = $0.0018039003` per encounter.
- `$333 million / $1,086 billion × 100 = 0.030663%`.
- Three- and four-year relabeling costs require their respective coordination assumptions; splitting one total 52%/48% is insufficient.

## Milestones and release criteria

| Milestone | Deliverable | Work packages |
|---|---|---|
| M1: Foundation | Reproducible setup, gateway proof, evidence contracts | WP-01–WP-03 |
| M2: Evidence path | Verified source adapters and retained FDA artifacts | WP-04–WP-06 |
| M3: Reproduction | Tested deterministic calculations and FDA reconciliation | WP-07 |
| M4: Reconstruction | Cost-model scenarios and targeted external evidence | WP-08–WP-10 |
| M5: Demonstration | Cited report, independent review, live end-to-end transcript | WP-11–WP-12 |

A successful first demonstration requires M1–M3 plus the applicable reporting and review gates in M5. M4 findings may remain explicitly blocked; the report must not imply model reconstruction or independent validation was completed.

Acceptance requires cross-child CodeMode execution, traceable numerical inputs, explicit partial-result semantics, independently derived numerical tests, and a live source-to-report run. Mocked tests alone cannot establish source availability or end-to-end readiness.

## Working mode

This is a scoped documentation deliverable authorized by the user's request to continue the four-file handoff. Implementation, source access, and architectural acceptance are tracked separately. The pipeline is the repository's initial durable work ledger; each blocked task has a trigger for resumption. AI-assisted changes require human review before production use.
