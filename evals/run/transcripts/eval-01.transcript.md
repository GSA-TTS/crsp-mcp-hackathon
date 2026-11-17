---
title: "EVAL-01 transcript (privacy-minimized)"
description: "Tool calls, artifact identifiers, and returned record identities for case RD-01."
status: draft
tier: 2
last_updated: "2026-11-17"
---

# EVAL-01 transcript — case RD-01

No personal information is present. All records are public agency documents. No
submitter names, addresses, or comment text appear.

## Tool calls in order

| # | Tool (as surfaced in host) | Key request fields | Status | Artifact |
| --- | --- | --- | --- | --- |
| 1 | `federal_register_search_documents` | `search_term` = Q1 | ok, 5 items, `reported_total` 709, `retrieval_status` partial | `816635a7-e96d-43bb-95d1-8d210eb893d2` |
| 2 | `federal_register_search_documents` | `search_term` = Q2 | ok, 5 items, `reported_total` 36, partial | `8517492c-91ae-4b00-b4c7-7171393345de` |
| 3 | `federal_register_search_documents` | `search_term` = Q3 | ok, 5 items, `reported_total` 10000, partial | `941126d5-8dae-4ea0-b4c3-3f56790524b0` |
| 4 | `federal_register_search_documents` | `search_term` = Q4 | ok, 2 items, `reported_total` 2, `retrieval_status` unknown | `9e49bd9c-4654-4f30-b8f1-b33576567615` |
| 5 | `federal_register_search_documents` | `search_term` = Q5 | ok, 2 items, `reported_total` 2, unknown | `804b1a00-47f1-4103-8f15-c284af2e2dcb` |
| 6 | `regulations_search_dockets` | `search_term` = Q6, `page_size` 5 | ok, 1 item, `reported_total` 1 | `d45015d2-4658-421d-beed-1be3674bae98` |
| 7 | `federal_register_search_documents` | `search_term` = Q7 (nonsense) | **error** `SCHEMA_MISMATCH: invalid Federal Register search response` | none returned |
| 8 | `regulations_search_dockets` | `search_term` = Q7 (nonsense) | ok, 0 items, `reported_total` 0 | `278c87f3-c5ed-4693-b2d5-58d31d2a1e86` |
| 9 | `federal_register_get_document` | `document_number` = 2025-08204 | ok | `076a753f-edb8-40af-b668-811308a58a74` |
| 10 | `reginfo_fetch_report` | `report` = `agenda_202510` | ok, 3954 records, `RUN_DATE` 2026-07-03-04:00, sha256 `4dc85fe08251eed1499dee5f2a2f7e3fcf4717baf468409c1f884dd68782b75f` | `8929994e-72ca-49f6-9d55-321341c2d9c4` |
| 11 | `reginfo_inspect_report` | `query` = `0910-AI80` on the agenda snapshot | ok, 1 match, stage "Final Rule Stage" | same artifact, `record_id` `7f4e9b9f1b062608e1bca0c13eb48bdbc6cf32baf194ab37be6c1c12257a3243` |
| 12 | `reginfo_inspect_report` | `query` = `0910-AI80` on `oira_pending` snapshot `64bb1a87-...` | ok, **0 matches** | `64bb1a87-30fd-4509-bea8-df129c20e849` |
| 13 | `regulations_search_documents` | `docket_id` FDA-2024-N-2910, `search_term` "Preliminary Regulatory Impact Analysis" | ok, **0 items** | `1bd9d123-26b3-457a-b94f-178bb742902b` |

Earlier in the same session (pre-freeze probing, same system revision) the
following were also retrieved and are reused as corroboration for the key:
FR search `0df9a7a3-77dc-4f11-97d8-044b24bec623`, FR get `2025-00778`
`a2a9f208-3771-4e4f-9e6e-244ecc553679`, docket detail
`05134df1-0579-46b3-8ff8-a1dbeb2e7123`, document detail `FDA-2024-N-2910-0001`
`5dbc5758-0f65-421f-9200-642a9dd064a1`, file metadata
`acb89b62-3069-4edc-8189-fe3fd074ab7f`, NPRM PDF
`e13331fd-b61d-489d-a431-8539877d02d1` (sha256
`1070d907ac8163538af8483a7af82c24c708a16b3c1fda42dcf4383b758207f3`, 997,979
bytes, 38 pages, `extraction_version` pypdf-7.0.0-layout).

## Returned record identities, per query

**Q1** (plain language) — `2025-00778` **[G1]**, `2024-29957` [near miss],
`2025-11605`, `2026-13674`, `2025-01149`.

**Q2** (agency terminology) — `2025-00778` **[G1]**, `2025-08204` **[G2]**,
`2024-29957` [near miss], `2026-16597`, `2025-18328`.

**Q3** (underspecified) — `2025-18152`, `2024-31419` [near miss], `2024-27810`,
`2026-06935`, `2025-00778` **[G1]**.

**Q4** (no federal match expected) — `2024-23549` (lead and copper drinking
water), `2024-14824` (heat injury prevention). Neither is relevant; the tool
returned them without any no-match signal, with `retrieval_status` `unknown`.

**Q5** (near-miss heavy) — `2014-27833` [near miss], `2014-27834` [near miss].
Gold record **not returned**.

**Q6** (docket search) — `FDA-2024-N-2910` **[G3]**, exact single match with
highlighted matching preamble text.

**Q7** (nonsense control) — Federal Register: error. Regulations.gov: clean
empty result.

## Observed warnings (verbatim, deduplicated)

- "Keyword matches may only mention a docket; results are not verified docket members or a proposed/final version chain."
- "One mutable search page, not an exhaustive or transactional snapshot. Upstream relevance order is preserved, not chronological order."
- "Full response including agency metadata and excerpts is retained in artifact_id; result links are metadata, not downloaded content."
- "Single bounded page; no exhaustive or transactional snapshot guarantee."
- "Source-reported relationships, not independently verified version lineage."
- "Snapshot-relative IDs require artifact_id for cross-snapshot identity."
- "Downloaded report only; excludes other history and private ROCIS data."
