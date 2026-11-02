---
title: "Regulatory Analysis MCP Implementation Pipeline"
description: "Durable work ledger, dependencies, agent handoffs, and verification gates."
status: draft
tier: 2
last_updated: "2026-10-30"
related_files: ["../README.md", "../PROJECT_PLAN.md", "SPECIFICATION.md"]
---

# Implementation pipeline

## Work ledger and execution rules

This file is the initial repository-local change-tracking record. Each WP entry is a distinct tracked item, including dependency-blocked work. Maintain status, owner, blocking dependency, and acceptance evidence here until external issues are created; then add issue links without losing the task identifiers.

Statuses: `ready`, `blocked`, `in_progress`, `in_review`, `done`. Ready means ready for scoping and assignment, not authorization to install dependencies or change infrastructure. WP-01 through WP-03 were implemented by the OpenCode AI agent under the owner's approval; other implementation owners are unassigned.

Implementation file paths below are proposed bounded scopes to confirm during WP-01. Shared contracts belong to WP-03; consumers must coordinate changes through that owner. Before editing, inspect current repository instructions and user changes, identify exact files and checks, and obtain the applicable approval. Implement each accepted package through a reviewable pull request.

The [specification](SPECIFICATION.md) defines acceptance criteria AC-01 through AC-09. The [project plan](../PROJECT_PLAN.md) defines milestones and source readiness.

| ID | Task | Status | Depends on / unblocking trigger | Acceptance |
|---|---|---|---|---|
| WP-01 | Project foundation and architectural record | in_review | Local checks pass; human review pending | Setup and verification entry points |
| WP-02 | FastMCP gateway proof | in_review | Runtime tests pass; human review pending | AC-01 |
| WP-03 | Evidence and result contracts | in_review | Persistence/reference tests pass; human review pending | AC-02 |
| WP-04 | Regulations.gov read adapter | blocked | WP-03 and verified OpenAPI/access | AC-03 |
| WP-05 | Reginfo public-source adapter | blocked | WP-03 and recovered source contracts | AC-02, AC-03 |
| WP-06 | Document pipeline and FDA source fixture | blocked | WP-03, WP-04, confirmed FDA artifact | AC-04 |
| WP-07 | Deterministic analysis and FDA reproduction | blocked | Numerical implementation passes; source-grounded FDA acceptance needs WP-06 | AC-05 |
| WP-08 | Cost-model reconstruction | blocked | WP-06, WP-07, cost-model reports | AC-07 |
| WP-09 | Economic-source adapters | blocked | WP-03, WP-06 identify required datasets | AC-06 |
| WP-10 | Research and reference resolution | blocked | WP-03, WP-06 identify relevant references | AC-02, AC-06 |
| WP-11 | Analysis skills and report bundle | blocked | WP-02, WP-06, WP-07 | AC-08 |
| WP-12 | Independent review and live demonstration | blocked | WP-11 and applicable source packages pass | AC-09 |

## WP-01 — Project foundation and architectural record

**Owner:** OpenCode AI agent (implementation), project owner (review pending). **Status:** in_review.

Implemented: Python 3.14/FastMCP 4.1.4 package, exact direct dependencies and `uv.lock`, validated settings, `make setup`, `make check`, project instructions, development documentation, and proposed AD-001. Local verification passed; see [WP-01 transcript](verification/WP-01.md). Gateway execution and source access are subsequent packages, not foundation claims.

Scope: package metadata and lockfile, local developer commands, project instructions, decision records, and corresponding README updates. Select exact dependency versions only after compatibility, license, and vulnerability checks. Dependency installation and any CI changes require their own authorized scope.

Deliver a one-command bootstrap and one-command verification workflow, with offline versus credentialed checks clearly described. Set package layout, supported Python/runtime versions, test tooling, validated configuration names/defaults, and artifact retention location. Formalize proposed AD-001 from the specification as an owner-reviewed decision record; retain unknown deployment/authorization metadata as unresolved rather than inventing it.

Gate: a clean environment can follow documented setup; verification invokes the agreed lint, tests, type/build checks, and relevant security scans. Record actual command output. This unblocks WP-02 and WP-03.

## WP-02 — Gateway proof

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review. Implemented mounted gateway, bounded Monty execution, catalog discovery, and stdio entry point. See [verification](verification/WP-02-WP-03.md).

Proposed scope: `src/regulatory_mcp/gateway/`, `tests/gateway/`.

Build two minimal conventional child tools, mount them under namespaces, and prove discovery plus data transfer between calls in a single CodeMode execution. Check actual exposed tool names, startup collision failure, bounded execution, child lifecycle, and conventional-mode equivalence. Inspect and document CodeMode execution permissions and isolation.

Gate: AC-01 passes using the real pinned FastMCP runtime. Stubs may supply child data, but cannot replace the gateway/runtime being tested. If composition fails, record the observed incompatibility and return AD-001 for review before expanding adapters.

## WP-03 — Evidence and result contracts

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review. Implemented schema-v1 contracts, immutable records, content-addressed bytes, reviewed-reference enforcement, and read-only tools. See [verification](verification/WP-02-WP-03.md).

Proposed scope: `src/regulatory_mcp/contracts/`, `src/regulatory_mcp/evidence/`, matching tests.

Implement versioned results, coverage status, structured errors, immutable artifact versions, evidence locators, labeled assumptions, and calculation-run manifests. Define validated storage references and configuration contracts for consumers.

Gate: AC-02 tests show that changing bytes creates a new version, inputs remain resolvable, missing/null/false distinctions survive serialization, and broken references fail explicitly. Contract changes require updates to every downstream consumer and fixture.

## WP-04 — Regulations.gov adapter

**Owner:** unassigned. **Status:** blocked on WP-03 and source access.

Implementation update: OpenCode AI agent implemented the six read tools and offline contract tests. **Acceptance remains blocked** on configured credentials, live response verification, and authoritative GET limits. Remaining bounded scope: normalize source results to shared response envelopes and implement/test timestamp-window continuation with overlap/progress handling if exhaustive retrieval is required. These are tracked WP-04 subitems; trigger is verified live paging behavior and owner-approved bulk scope. Current tools explicitly return one page. See [source verification](verification/WP-04-WP-05.md).

Proposed scope: `src/regulatory_mcp/sources/regulations/`, `tests/sources/regulations/`, sanitized fixtures.

Obtain and retain the official OpenAPI contract; establish GET rate limits and attachment schemas. Implement the six specified read tools with header authentication, validated filters, public document ID to object ID resolution, optional attachments, bounded pagination, deduplication, and progress detection.

Gate: AC-03 passes offline contract/error tests and authorized live read checks. Capture contract version/hash and live observation time. Never store credentials in fixtures. Completion unblocks the FDA retrieval path in WP-06.

## WP-05 — Reginfo public-source adapter

**Owner:** unassigned. **Status:** blocked on WP-03 and recovered public URLs/schemas.

Implementation update: OpenCode AI agent recovered source contracts and implemented OIRA pending/completed, agenda-202510, and pending-PRA snapshot tools. **Acceptance remains blocked** because this environment resolves the public host to a nonpublic address. Resume live validation with approved public DNS/egress. Shared-envelope normalization is tracked here before final acceptance. Other public report types remain unsupported until their contracts are verified. See [source verification](verification/WP-04-WP-05.md).

Proposed scope: `src/regulatory_mcp/sources/reginfo/`, matching tests and public snapshot fixtures.

Recover the public XML source described in the handoff and document its actual coverage. Establish separate contracts for agenda entries, OIRA reviews, and PRA collections as supported. Record any unavailable category as a capability gap within this task. Resolve whether any ROCIS-specific integration is publicly supported before proposing tools for it.

Gate: safely parse a real retained snapshot with provenance, reject malformed/entity-expanding XML, and expose supported record types with stable identifiers. Cross-link candidate RIN matches without claiming record equivalence.

## WP-06 — Documents and FDA fixture

**Owner:** unassigned. **Status:** blocked on WP-03 and WP-04.

Proposed scope: `src/regulatory_mcp/documents/`, `tests/documents/`, provenance manifests and permitted public fixtures.

Confirm the candidate FDA docket and original RIA version. Retrieve attachment metadata and bytes through bounded approved origins. Implement extraction and row inspection with source locators. Verify the cost tables and narrative values in the plan against the original; record corrections and distinguish PDF page positions from printed labels.

Gate: AC-04 passes; FDA inputs have reviewed transcription and persistent evidence references. Record the intended discount valuation date and payment timing, or mark the interpretation unresolved. Retain a lawful reproducible fixture or retrieval manifest according to source access terms.

## WP-07 — Deterministic analysis

**Owner:** unassigned. **Status:** blocked on WP-03; FDA integration also needs WP-06.

Implementation update: OpenCode AI agent implemented six deterministic tools, typed bounded requests, decimal arithmetic, evidence-linked manifests, and both-mode gateway integration. Independent numerical tests and handoff-derived FDA cases pass. **Source-grounded acceptance remains blocked on WP-06**, and human interpretation review is pending. See [tool usage](ANALYSIS.md) and [verification](verification/WP-07.md). The source-access recheck still finds no API key and nonpublic DNS for both source hosts.

Proposed scope: `src/regulatory_mcp/analysis/deterministic/`, matching tests and FDA expected-result fixtures.

Implement discounting, annualization, break-even, reported-value reconciliation, cost-to-receipts, and bounded deterministic parameter grids. Add independently derived simple cases before the FDA fixture: a one-payment stream, a zero-rate annuity, shifted valuation/payment dates, rounding boundaries, and invalid unit/denominator cases.

Gate: AC-05 passes. Reproduce the plan's handoff-derived numbers and then the verified original-document inputs. Any difference must be explained through source precision, timing, definitions, or a tracked reproducible defect. Mathematical unit tests can proceed while WP-06 completes; source-grounded FDA acceptance cannot.

## WP-08 — Cost-model reconstruction

**Owner:** unassigned. **Status:** blocked on WP-06, WP-07, and referenced cost-model reports.

Proposed scope: `src/regulatory_mcp/analysis/reconstruction/`, matching tests and parameter manifests.

Retrieve FDA references 26 and 28 after verifying their identity. Reconstruct labeling coordination assumptions and reformulation formulas. Inventory missing proprietary counts, distribution parameters, draw structure, and dependence assumptions. Implement bounded seeded simulation only for adequately specified models.

Gate: AC-07 passes with declared tolerances and uncertainty. Exact agency simulation reproduction remains blocked unless required inputs and random-process details become available. Public substitutes must be labeled as scenarios with coverage differences. The trigger for independent proprietary-input validation is lawful access plus a reproducible extraction specification; maintain that subtask here until satisfied or explicitly removed by the owner.

## WP-09 — Economic-source adapters

SUSB source update (user-supplied page): [2022 SUSB Annual Datasets by Establishment Industry](https://www.census.gov/data/datasets/2022/econ/susb/2022-susb.html), released April 2025, page revised 2025-08-04. Delivery is comma-delimited download files; 2017 NAICS describes establishment industry, with tabulation by enterprise employment/receipts size. Listed files: U.S./states 6-digit NAICS (55.2 MB); detailed employment sizes (6.9 MB, U.S. 6-digit and state sectors); MSA 3-digit NAICS (47.3 MB). The July 22 revision applies specifically to the MSA file. Zero mid-March employment can coexist with paid employment elsewhere in the year. Do not infer receipts columns or dollar units from the general program description. The 6.9 MB file is the initial candidate within the default 25 MB response bound. **Remaining trigger:** owner provides the direct detailed-employment-size download link and Record Layouts documentation (column order, units, size codes, flags). The page fetch failed in this environment, so link targets and layouts remain unverified. Implement the SUSB-specific download/parser after those contracts are available; the generic Census API tools are not SUSB retrieval. AI documentation update verified with local documentation checks.

Documentation follow-up: supplied BLS v2 signatures resolve GET IDs/envelopes/default-window and discovery contracts. Implemented corrected ID handling, list/object Results parsing, latest selection, popular-series and survey tools. Registered historical/multi-series POST support remains a distinct WP-09 subitem; implement bounded JSON queries and registration-key handling using the supplied contract, then verify quotas and live access. Supplied Census API inventory lists CBP but not SUSB; SUSB delivery/data dictionaries still require documentation. See [source contract notes](SOURCES.md).

Prototype update: Census catalog/variable discovery, bounded table retrieval/inspection, and BLS single-series retrieval are implemented and fixture-tested. **Acceptance remains blocked** on official source documentation and live access. Owner documentation was requested. SUSB distribution/vintages, BLS metadata/history support, SBA definitions, and FDA-specific series selection remain tracked subitems; resume when their contracts/original RIA are available. See [verification](verification/WP-09.md).

**Owner:** unassigned. **Status:** blocked on WP-03 and source requirements from WP-06.

Proposed scope: `src/regulatory_mcp/sources/census/`, `src/regulatory_mcp/sources/bls/`, associated SBA mapping, matching tests.

Identify the SUSB vintage and business definitions relevant to the RIA, available receipts measures, and applicable SBA size standards. Verify actual wage/price series used for dollar-year conversions before choosing substitute series. Retain source queries and all unit/classification transformations.

Gate: AC-06 passes, including suppression and missing-value fixtures. Comparisons identify mismatched entity units and employee versus sales thresholds. Do not silently distribute sector averages across firms.

## WP-10 — Research and references

**Owner:** unassigned. **Status:** blocked on WP-03 and WP-06.

Proposed scope: `src/regulatory_mcp/sources/research/`, matching tests and reference fixtures.

Resolve studies supporting reformulation probabilities and transferability from other labeling policies. Preserve bibliographic identity, accessible versions, retrieval provenance, passages, and limits of access. Choose a search provider only when its contract, access terms, and authorization are established.

Gate: evidence references resolve to retained accessible material; inaccessible full text is explicitly reported. A citation match or abstract must not be represented as full-text review.

## WP-11 — Skills and report bundle

**Owner:** unassigned. **Status:** blocked on WP-02, WP-06, and WP-07.

Proposed scope: project analysis skills, `src/regulatory_mcp/reporting/`, report templates and tests.

Implement the workflow from source discovery to evidence extraction, calculation, and cited review memo. Include executive findings, verification level, source versions, timing assumptions, reconciliation tables, retrieval coverage, unresolved inputs, and a reproducibility manifest. Optional reconstruction and external-source sections consume WP-08–WP-10 only when available.

Gate: AC-08 passes. Every factual/numerical finding resolves to evidence or an explicit assumption; unsupported claims fail report validation. Draft comments remain locally reviewable artifacts. Reports must identify AI assistance and the scope of human review.

## WP-12 — Independent review and live demonstration

**Owner:** unassigned. **Status:** blocked on WP-11 and relevant upstream gates.

Proposed scope: integration/evaluation tests, verification transcripts, and review findings.

Use a review session separate from the implementation session. Review source authenticity, gateway registration, error paths, download boundaries, evidence integrity, mathematical conventions, and completeness claims. Run the live FDA source-to-report workflow and capture actual outputs. Compare CodeMode and conventional mode on the same task using correctness, tool/request counts, elapsed time, and returned data volume; record variability rather than claim a performance improvement from one run.

Gate: AC-09 passes and the human reviewer accepts the economic interpretation. Credentials or unavailable sources yield `BLOCKED`, not a mocked live pass. File reproducible defects in the tracker, fix them, and rerun affected checks. Revisit downstream tasks when their blocking dependency completes.

## Agent roles and handoff

These are planned roles, not agents launched by this documentation task. Assign separate sessions only when delegation is authorized.

- **Implementer:** works within the assigned package and records assumptions, changes, and observed verification output.
- **Reviewer:** independently checks the implementation against the source contract and acceptance criteria; cannot be the implementer's self-approval.
- **Integration tester:** exercises the actual composed gateway and live workflow when authorized; reports blocked environments honestly.
- **Human owner/economic reviewer:** accepts scope and architecture, resolves methodological judgments, and approves release.

Every handoff includes task ID, revision, changed files, exact public contracts, configuration requirements, test commands and observed outputs, source/fixture provenance, remaining tracked blockers, and the next unblocking event.

## Verification transcript and pull-request template

For each implementation package record:

1. Context and approved scope, with work-package and acceptance IDs.
2. Plan-to-change mapping and architectural decisions.
3. Environment and dependency versions.
4. Exact lint, test, type/build, and security-scan commands, observed output summaries, and `PASS`, `FAIL`, or `BLOCKED` status. Explain genuinely inapplicable categories.
5. Live checks separately from fixtures/mocks, including timestamps and retained evidence identifiers.
6. Rollback procedure and any artifact/schema compatibility considerations.
7. Security impact, AI assistance disclosure, human reviewer, and tracked remaining work.

After changes, rerun affected verification. A package is done only when its required gates pass and its downstream registration, exports, namespaces, fixtures, and documentation are updated.
