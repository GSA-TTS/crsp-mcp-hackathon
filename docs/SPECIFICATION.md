---
title: "Regulatory Analysis MCP Technical Specification"
description: "Proposed gateway, evidence, source-adapter, and calculation contracts."
status: draft
tier: 2
last_updated: "2026-10-30"
related_files: ["../README.md", "../PROJECT_PLAN.md", "IMPLEMENTATION_PIPELINE.md"]
---

# Technical specification

Normative requirements below describe the intended implementation. WP-01 configuration, WP-02 gateway proof, and WP-03 evidence foundations are implemented locally and awaiting human review. External integrations remain pending. Work-package identifiers refer to the [implementation ledger](IMPLEMENTATION_PIPELINE.md); current boundaries are in [development instructions](DEVELOPMENT.md).

## 1. Proposed architecture decision: modular gateway

**Decision ID:** AD-001. **Status:** proposed. **Date:** 2026-10-30.
**Decision maker:** project owner, acceptance pending. **Category:** deployment and infrastructure.
Suggested control mappings: AC-6, AU-3, CM-3, SA-11, SI-10. Deployment impact level and ATO relevance are undetermined; this document makes no authorization claim.

### Context and drivers

The analyst needs multiple regulatory and economic sources in one workflow, while source adapters should remain independently testable and reusable. Agent context should carry compact evidence references instead of full document corpora.

### Considered options

1. One monolithic server: simple initial registration but tightly coupled source logic.
2. Local child servers mounted into one gateway: modularity with limited transport overhead.
3. Remotely deployed child servers: independent operations with additional transport, authentication, and deployment work.

### Proposed outcome and consequences

Prefer option 2, with conventional child tools and CodeMode at the gateway. Keep conventional gateway access for comparison. This introduces a dependency on compatible mounting and CodeMode behavior; WP-02 must prove that behavior before acceptance. Namespace collision detection and lifecycle behavior need explicit tests. Remote deployment is outside the initial design.

The formal proposed record is [AD-001](adr/0001-local-fastmcp-gateway.md), including owner review and unresolved deployment metadata.

```text
Agent + analysis skills
         |
FastMCP gateway: CodeMode or conventional mode
         |
         +-- regulations   +-- reginfo     +-- documents
         +-- analysis      +-- census      +-- bls
         +-- research
```

### Gateway requirements

- Pin a tested FastMCP version and lock dependencies; record compatible client/runtime versions.
- Namespace every child and reject unintended exposed-name collisions at startup.
- Verify actual exposed names rather than assume a separator or registration API.
- In one CodeMode execution, discover and call tools from at least two mounted children and pass structured output between them.
- Apply request-count, elapsed-time, concurrency, and output-size budgets to orchestration. Return explicit budget-exhaustion status.
- CodeMode orchestrates registered tools; substantive economic calculations execute in deterministic backend tools.
- Validate the runtime's isolation and permitted capabilities. Do not assume generated code is sandboxed merely because the feature is called CodeMode.
- Keep a conventional mode with equivalent underlying capabilities and evidence outputs.
- Initially use local stdio transport. Do not introduce custom HTTP routes as part of mounting.

## 2. Shared response and evidence contracts

All schemas are proposed internal contracts. Adapter implementation must map verified upstream schemas into these models without inventing missing values.

### Tool result

| Field | Meaning |
|---|---|
| `schema_version` | Version of the internal response contract |
| `request_id` | Correlation identifier for this operation |
| `status` | `ok`, `partial`, or `error` |
| `data` | Validated result or null on failure |
| `evidence_refs` | References to retained evidence records |
| `warnings` | Machine-readable code plus human-readable explanation |
| `error` | Null or structured code, safe message, retryability, and optional retry delay |

Error codes must distinguish invalid input, missing credentials, upstream authentication failure, rate limiting, timeout, unavailable source, unsupported capability, schema mismatch, download rejection, extraction failure, insufficient evidence, and budget exhaustion. Errors must not expose credentials, response bodies containing personal information, or internal stack traces.

### Search page and retrieval coverage

Search `data` includes `items`, `next_cursor`, `retrieved_count`, `reported_total`, `retrieval_status`, and `query_scope`. `reported_total` can be null. `retrieval_status` is `complete`, `partial`, or `unknown` and applies to the stated query scope, not the entire source.

A page can be successfully retrieved while query coverage remains partial. Include `page_count`, `request_count`, `started_at`, `finished_at`, and a snapshot-consistency explanation on multi-page collections. Never infer completeness solely from a missing cursor or matching counts on a changing source.

Cursors must be validated, versioned, and bound to source, filters, and ordering. They must not contain API credentials. Document whether a cursor depends on local retained state.

### Source artifact

Required fields: `artifact_id`, `source_system`, `source_url`, `source_record_id` when available, `retrieved_at` in UTC, `sha256`, `media_type`, `byte_length`, and repository-managed storage reference. Preserve available publication date, upstream modification timestamp, dataset vintage, title, and access/license information. Retrieval time is not publication time.

Retain immutable source bytes separately from derived text and tables. A changed hash creates a new artifact version. Evidence derived from pasted text must identify its origin as user-supplied text rather than an independently retrieved original.

### Evidence locator

An `evidence_id` resolves to an artifact version plus a locator: PDF page index and printed page label where available, section, table label, row/column, text span, or structured dataset query. Store extracted content, extraction method/version, transformations, and review state. Preserve source table labels even when table-of-contents numbering differs.

### Calculation input and run

Every input carries a name, value, unit, dollar year when monetary, entity definition, and either evidence references or a labeled assumption with rationale. Distinguish reported values, derived values, assumptions, and independently validated inputs.

A run records `run_id`, tool/version, code revision, input references, parameters, formulas, timing conventions, transformations, outputs with units, warnings, verification level, and creation time. Simulation runs additionally record generator/version, seed, draw count, distributions, and dependence assumptions. A report must resolve every cited run and evidence reference.

## 3. Regulations.gov adapter

Base URL from supplied documentation: `https://api.regulations.gov/v4`.
Use `X-Api-Key` from `REGULATIONS_GOV_API_KEY`; never place the key in query strings or logs. Production GET limits remain to be verified in WP-04. The documented POST limits are not GET limits.

| Proposed child tool | Operation | Parameters and behavior |
|---|---|---|
| `search_dockets` | `GET /dockets` | Validated keyword/agency filters and bounded paging |
| `get_docket` | `GET /dockets/{docketId}` | Details, including RIN where available |
| `search_documents` | `GET /documents` | Docket, keyword, and supported date/type filters |
| `get_document` | `GET /documents/{documentId}` | Optional `include=attachments` |
| `search_comments` | `GET /comments` | Resolve public document ID to `objectId` for `filter[commentOnId]`; bounded search |
| `get_comment` | `GET /comments/{commentId}` | Optional `include=attachments` |

Exact supported filter names, lengths, enums, response fields, and paging constraints must be taken from the retrieved OpenAPI specification and verified responses. The table does not authorize inventing upstream parameters. Public tools should use explicit typed arguments rather than arbitrary query-string passthrough.

RIN is retrieved from docket details, not assumed to be present in document search. Preserve multiple RINs if provided. RIN matches are candidate cross-source relationships, with version and record context; they are not proof that records or analyses are identical.

Attachments are opt-in metadata. Actual binary retrieval belongs to the documents adapter. Resolve attachment relationships according to the verified schema; do not assume a URL field or JSON layout.

Only the six read operations above are in scope. Public comment drafting produces a local draft for human review.

### Pagination and changing data

The supplied examples describe 250 results per page and 20 pages per window, followed by inclusive `lastModifiedDate` filtering. They also identify that filter as beta. Treat these as documented examples pending contract verification.

- Sort deterministically where supported and deduplicate overlapping windows by stable record ID, retaining changed versions.
- Preserve UTC response timestamps. If query filters require Eastern local time as documented, use a timezone-aware conversion with daylight-saving handling; verify ambiguity around clock changes.
- Detect lack of progress, repeated cursors, and timestamp tie groups that fill the entire retrievable window. Stop with partial coverage rather than skip ahead and silently lose records.
- Bound pages, requests, and elapsed time. Preserve a resumable checkpoint when supported.
- A mutable API is not a transactional snapshot. Record the observation interval and unresolved coverage even when counts appear to reconcile.

Agency-configurable fields may become unavailable. Preserve missing, null, and false distinctions. Minimize submitter identity fields in default results and avoid logging comment text or attachments. A public comment record can represent multiple submissions; record count is not necessarily commenter count or a representative opinion sample.

## 4. Document and other source adapters

Proposed document tools: `retrieve_attachment`, `extract_passages`, `extract_tables`, `inspect_rows`, and `resolve_references`. Accept retained artifact or verified attachment identifiers where possible instead of unrestricted filesystem paths or URLs.

Downloads must validate HTTPS origins and every redirect against a configured allowlist, reject private/link-local destinations, and enforce time, size, and content-type limits. Store files under generated identifiers in an approved artifact directory; never trust upstream filenames as paths. Do not forward Regulations.gov credentials to attachment hosts.

Extraction must preserve locators and uncertainty. OCR and table transcription require explicit review state; calculations must not silently consume ambiguous numeric cells. Text, PDFs, and comments are evidence, not executable instructions. Parser failures must retain artifact identity and report a structured failure.

Reginfo tools are gated on recovered public source contracts. XML parsing must disable external entities and network resolution, bound input size, and preserve snapshot provenance. Agenda entries, OIRA reviews, and PRA collections require distinct record types and explicit supported coverage.

Census, SBA, BLS, and research adapters must preserve dataset vintage, units, suppression/missing-value codes, seasonal adjustment where applicable, classifications, and source definitions. Do not conflate firms, enterprises, establishments, formulas, and UPCs. Do not treat SBA employee thresholds as equivalent to an FDA sales-based compliance threshold.

## 5. Economic analysis tools

| Proposed tool | Required behavior |
|---|---|
| `discount_cost_stream` | Explicit valuation time, dated/periodic flows, discount rate, units, and dollar basis |
| `annualize_present_value` | Explicit payment dates/convention, horizon, rate, and PV valuation time |
| `calculate_break_even` | Numerator/denominator definitions, compatible units, and zero-denominator error |
| `reconcile_reported_values` | Absolute/relative difference, declared tolerance, and published rounding precision |
| `calculate_cost_to_receipts` | Matched entity/time basis; distribution limitations surfaced |
| `run_parameter_scenarios` | Bounded deterministic grids or seeded simulations with recorded assumptions |

For valuation at time 0 and end-year payments, use:

```text
PV = sum(C[t] / (1 + r)^t)
EAC = PV * r / (1 - (1 + r)^(-n))
At r = 0: EAC = PV / n
```

For arbitrary payment times relative to the valuation date, annual payment amount is `PV / sum((1+r)^(-payment_time))`. Reject nonfinite inputs, invalid horizons, rates at or below -1, incompatible units, and undocumented timing. Do not assume nominal cash flows and real discount rates are compatible. Preserve negative flows when explicitly identified as savings or benefits.

Use adequate internal precision and round only for presentation. Record both underlying and displayed values. The [project plan](../PROJECT_PLAN.md) supplies handoff-derived regression examples; WP-07 must add independently derived small cases rather than merely compare the implementation to itself.

### Reconstruction rules

- Model coordinated/uncoordinated labeling costs by category and compliance timing.
- Distinguish reformulated UPC counts, formulas per UPC, and per-formula costs.
- Report unavailable cost-model parameters and proprietary input limitations.
- For simulation, record distribution parameterization and dependencies across categories and inputs. A seed alone is insufficient for exact reproduction.
- Do not multiply or sum marginal medians or percentile endpoints and call the result the corresponding statistic of the combined distribution.
- Specify reconstruction tolerances and Monte Carlo variability before judging agreement.
- Sector-average cost-to-receipts ratios are not a demonstrated small-business burden distribution.

## 6. Configuration and operational requirements

WP-01 defines and validates configuration for API credentials, artifact storage, gateway mode, network allowlists, request timeout/retry budget, page limits, download limits, and orchestration budgets in `src/regulatory_mcp/config.py`. Exact names and bounds are listed in [development instructions](DEVELOPMENT.md). Consumers must enforce these settings as their work packages are implemented.

Use finite timeouts, bounded retries for transient GET failures, and rate-limit-aware backoff honoring valid server retry guidance. Authentication and schema errors must not cause blind retries. Audit tool names, timestamps, request IDs, source IDs, statuses, and budget use without secrets or unnecessary personal data.

## 7. Acceptance and verification

- **AC-01:** Gateway integration demonstrates cross-child discovery and calls inside one CodeMode execution, plus conventional-mode parity.
- **AC-02:** Every numerical input resolves to retained evidence or a labeled assumption; artifact changes remain versioned.
- **AC-03:** Source tests cover ID translation, attachment inclusion, missing fields, rate limits, schema failures, overlapping windows, and stalled pagination.
- **AC-04:** Download/parser tests cover redirects, rejected destinations, size limits, unsafe filenames, malformed files, and ambiguous extraction.
- **AC-05:** Calculation tests cover independently derived values, zero rate, payment timing, rounding, incompatible units, and invalid inputs.
- **AC-06:** Economic-source outputs preserve vintage, suppression, units, and entity definitions.
- **AC-07:** Reconstructed simulations are repeatable under a recorded environment and disclose missing parameters and dependence assumptions.
- **AC-08:** The FDA report separates the three verification levels and resolves citations to original artifacts and calculation runs.
- **AC-09:** A live source-to-report transcript records actual outputs, versions, budgets, and unresolved blockers. Human review is required for source interpretation and economic conclusions.

Run lint, type/build checks where applicable, unit/integration tests, and secrets/dependency/static scans through the project's planned one-command verification entry point. Live validation additionally runs for the demonstration, releases, after three behavior-affecting fixes since the last validation, or when a working claim is in doubt. Record `BLOCKED` when credentials or source access prevent a live check.
