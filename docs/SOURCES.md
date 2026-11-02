---
title: "Public Source Adapters"
description: "Implemented read tools, verified source contracts, and live acceptance blockers."
status: draft
tier: 2
last_updated: "2026-10-30"
related_files: ["DEVELOPMENT.md", "IMPLEMENTATION_PIPELINE.md", "verification/WP-04-WP-05.md"]
---

# Public source adapters

## Regulations.gov

The stdio gateway registers `regulations_search_dockets`, `regulations_get_docket`, `regulations_search_documents`, `regulations_get_document`, `regulations_search_comments`, and `regulations_get_comment`. Provide `REGULATIONS_GOV_API_KEY` through the process environment. Missing credentials fail before network access. Keys are sent only in `X-Api-Key` to the fixed Regulations.gov origin.

Searches return one page, page numbers 1–20 and sizes 5–250, further bounded by configured page limits. Comments resolve a public document ID to its `objectId` before applying `filter[commentOnId]`. A result supplies query scope, next page where available, reported total, coverage warnings, observation times, and retained response artifact ID. Duplicate IDs within a page are removed. Cross-page aggregation, timestamp-window continuation, and exhaustive retrieval remain tracked WP-04 work. No cursor or bulk-completeness guarantee is exposed.

Document/comment details request `include=attachments` only when selected. Returned attachment resources preserve metadata, including `fileFormats`; binary download belongs to WP-06. Docket attributes preserve available RIN values without treating them as proof of cross-source identity. Optional submitter identity fields are omitted from comment attributes. Free text and retained raw responses can contain personal information; raw artifacts stay in ignored private local storage.

The implementation validates resource identity/type/attributes and search paging metadata, not the entire upstream schema. Detail parsing accepts a standard top-level `data` wrapper or the direct resource described in GSA's OpenAPI. The adapter returns source-specific dictionaries with explicit artifact IDs; it does not yet use the generic `ToolResponse`/`SearchPage` envelope throughout. Normalization into that envelope is tracked in WP-04/WP-05 before their final acceptance.

The official OpenAPI was retrieved from GSA's repository:
`https://raw.githubusercontent.com/GSA/open-gsa-redesign/master/_apidocs/regulationsgov/v4/openapi.yaml`.
SHA-256: `be43c866f5ca424a456bde36ea03cb9326c454ef4e1894a13df80b6dc6e22488`.
Local retained artifact: `8f625563-43e4-4f0d-b49a-6e984b701ed8`. This ignored artifact is not distributed with the repository; retrieve and hash-check the source to reproduce inspection.

Live Regulations.gov acceptance is **BLOCKED**: no API key was configured. GET quota verification is also pending because api.data.gov's rate-limit page was unreachable. Four-second pacing is a conservative local default, not a claim about the official quota.

## Reginfo public XML

`reginfo_fetch_report(report)` downloads and retains one validated snapshot and returns its manifest. `reginfo_inspect_report(artifact_id, query, offset, limit)` searches selected fields in that immutable snapshot, returning up to 50 records. Queries are case-insensitive substrings over projected fields. Empty query matches all projected records.

Supported reports, discovered from public Reginfo report indexes:

| Report | Record type | Public endpoint |
|---|---|---|
| `oira_pending` | OIRA review | `/public/do/XMLViewFileAction?f=EO_RULES_UNDER_REVIEW.xml` |
| `oira_completed_30_days` | OIRA review | `/public/do/XMLViewFileAction?f=EO_RULE_COMPLETED_30_DAYS.xml` |
| `agenda_202510` | Agenda entry | `/public/do/XMLViewFileAction?f=REGINFO_RIN_DATA_202510.xml` |
| `pra_pending` | PRA request | `/public/do/PRAXML?type=pending` |

All use `https://www.reginfo.gov`. Agenda vintage is explicit, not labeled “current.” Other vintages and PRA report types require verified contracts before registration. This adapter does not access private ROCIS systems.

DTD, entity, and external-reference resolution are forbidden. Root and record types are checked, and each record needs identity/title. Contact fields are omitted from the projected results. Raw dates and quantity strings remain unchanged; empty elements differ from absent elements. Record IDs are snapshot-relative and must be paired with artifact ID. A RIN can appear in multiple reviews and is not a unique review identifier.

Live transport acceptance is **BLOCKED** here: DNS resolves Reginfo to a nonpublic address and the adapter rejects it. Earlier direct documentation requests reached the report indexes and sampled XML, establishing source shape but not passing the adapter's live gate. Resume in an environment with approved public DNS/egress; do not disable the destination check.

## Transport and limitations

### Census and BLS prototypes

These tools are registered; live verification remains **blocked**. The owner supplied the Census Available APIs page (revised 2026-09-17) and BLS v2 signatures (modified 2020-10-05). Tests use documentation-derived synthetic payloads, not live responses. The Census list includes CBP but does not list SUSB; that absence does not prove SUSB has no downloadable data.

- `census_discover_datasets(query, limit)`: search the API catalog. SUSB availability is not assumed.
- `census_get_variables(dataset, query, limit)`: inspect definitions for a year-qualified dataset path.
- `census_fetch_table(dataset, variables, geography, predicates)`: validate requested variables against metadata; retain raw table, query, metadata, and vintage. Supports up to 40 variables, 10 predicates, and `us:1`, `state:NN`, or `state:*` geography. Relevant suppression flags and industry/size labels must be selected explicitly. Dataset definitions determine whether counts represent firms or establishments.
- `census_inspect_table(artifact_id, offset, limit)`: inspect retained rows without converting nulls or suppression markers to numeric values.
- `bls_get_series(series_id, latest=False)`: retrieve the documented past-three-year default window or the latest observation. IDs allow uppercase letters, digits, underscores, dashes, and hashes; hashes are percent-encoded. The 100-character cap is a local bound. Both documented `Results` object/list envelopes are accepted. Raw periods, values, footnotes, aspects, and catalog are retained. Seasonal adjustment copies `catalog.seasonality` when available; units remain unknown rather than inferred from measure descriptions.
- `bls_get_popular_series(survey=None)`: discover popular series, optionally by two-letter survey abbreviation. This is not a complete series catalog.
- `bls_get_surveys(survey=None)`: list surveys or retrieve one survey's metadata; preserve string-valued capability flags as returned.

The supplied BLS documentation establishes registered POST queries for up to 50 series and time frames up to 20 years, with optional catalog/calculations/annualaverage/aspects. Query transport and environment-supplied registration-key support are tracked in WP-09. Future keys must be sent in the JSON body, not copied into query URLs or retained request metadata. Daily/rate quotas are not established by the supplied signature page.

No Census/BLS key is sent. If registration is needed, requests fail explicitly; credential support requires verified documentation. See [WP-09 verification](verification/WP-09.md). The fixed transport origins now also include `api.census.gov` and `api.bls.gov`, subject to the same destination checks.

Only fixed public origins are reachable through the source transport, also constrained by configured allowed hosts. HTTPS uses certificate verification and TLS 1.2 minimum, environment proxies are not automatically used, and all redirects fail. Time, decoded bytes, retries, and attempt spacing are bounded. Authentication/schema failures are not retried; selected transient failures use bounded backoff and Retry-After guidance. Gateway execution deadlines bound the overall operation.

Public-address DNS preflight is an additional check on these fixed, non-user-controlled origins; it does not pin the subsequent HTTP connection to that DNS answer. A future general-purpose attachment downloader needs connection-level destination validation and redirect checks in WP-06. Callers cannot pass arbitrary URLs into these public tools.

Errors are safe MCP tool errors. Raw payloads and keys are not included in error messages. HTTPX2 and defusedxml were already installed transitively; both are now exact direct dependencies because adapters import them. HTTPX2 declares BSD-3-Clause and defusedxml PSF licensing (confirm metadata on dependency upgrades).
