---
title: "EVAL-01 report — rule discovery, case RD-01"
description: "Provisional agent self-assessment; no human adjudication."
status: draft
tier: 2
last_updated: "2026-11-17"
related_files: ["../cases/eval-01-rule-discovery.case.md", "../keys/eval-01-rule-discovery.key.md", "../transcripts/eval-01.transcript.md"]
---

# EVAL-01 report — rule discovery

```text
Evaluation ID / case ID / spec revision: EVAL-01 / RD-01 / evals/rule-discovery.md as of 2026-11-09
Run time (UTC) / system revision / mode: 2026-11-17T20:15Z–20:20Z / git 58fc63cc (dirty tree) / conventional gateway, live sources
Provenance correction: see ../CORRECTIONS.md — the evaluated system was the deployed crsp-regulations HTTP endpoint, not the 58fc63cc checkout; server revision undetermined
Fixture and answer-key identifiers or hashes: no fixtures; live artifacts listed in ../transcripts/eval-01.transcript.md; agenda snapshot sha256 4dc85fe08251eed1499dee5f2a2f7e3fcf4717baf468409c1f884dd68782b75f; NPRM PDF sha256 1070d907ac8163538af8483a7af82c24c708a16b3c1fda42dcf4383b758207f3
Capabilities exercised and MCP tools observed: federal_register_search_documents, federal_register_get_document, regulations_search_dockets, regulations_search_documents, reginfo_fetch_report, reginfo_inspect_report
Coverage status and evidence level: live-source, bounded single pages, retrieval_status partial or unknown on every search
Scores by rubric dimension (0–4): see table below
Critical failures: none triggered; two near-misses described under "Critical-failure review"
Result: FAIL (provisional) — Coverage/recall scored 2, below the 3 threshold
Human adjudicator / unresolved disagreement: none; all scoring is agent self-assessment and unadjudicated
Privacy-minimized transcript location: ../transcripts/eval-01.transcript.md
Known limitations and follow-up work: see final section
```

## Retrieval results against the key

Declared scope: one bounded page per query, page size 5.

| Query | Returned | Relevant returned | Precision | Gold available | Recall vs. key |
| --- | --- | --- | --- | --- | --- |
| Q1 plain language | 5 | 1 (G1) | 0.20 | G1, G2 | 0.50 |
| Q2 agency terminology | 5 | 2 (G1, G2) | 0.40 | G1, G2 | 1.00 |
| Q3 underspecified | 5 | 1 (G1) | 0.20 | G1, G2 | 0.50 |
| Q4 no-match expected | 2 | 0 | 0.00 (no relevant record exists) | none | n/a |
| Q5 near-miss heavy | 2 | 0 | 0.00 | G1, G2 | 0.00 |
| Q6 docket search | 1 | 1 (G3) | 1.00 | G3 | 1.00 |
| Q7 nonsense control | error / 0 | 0 | n/a | none | n/a |
| **Union across Q1–Q3, Q5–Q6** | 16 distinct | 3 (G1, G2, G3) | 0.19 | 3 | **1.00** |

Precision figures are low by construction: keyword search returns a fixed page of
five ranked items regardless of how many are relevant, and the suite's precision
definition counts every returned item. The union row is the more informative
number for a querant who runs more than one query.

## Identity and status findings

- Identity fields for G1 reconcile across three independent sources: FR record
  (`2025-00778`, 90 FR 5426, RIN 0910-AI80, docket "Docket No. FDA-2024-N-2910",
  21 CFR 101), the Regulations.gov docket record (same docket ID and RIN), and
  the docket document `FDA-2024-N-2910-0001` (`frDocNum` 2025-00778, `frVolNum`
  "90 FR 5426", pages 5426–5463).
- **Status divergence detected and reported:** the Federal Register record is a
  Proposed Rule (published 2025-01-16); the October 2025 Unified Agenda snapshot
  lists RIN 0910-AI80 at **Final Rule Stage**, priority Economically
  Significant. No final-rule Federal Register document was located. The correct
  answer for the querant is: a proposed rule is on the books, the comment period
  closed 2025-07-15 after a 60-day extension, and the agency's own agenda says it
  intends to move to a final rule — but no final rule has been published in the
  sources searched.
- Comment-period chain reconstructed: original NPRM comment date, extension
  document `2025-08204` moving the deadline to 2025-07-15. Note that the
  Regulations.gov document record for `FDA-2024-N-2910-0001` reports
  `commentEndDate` 2025-07-16T03:59:59Z, which is the same deadline expressed in
  a different time zone convention, not a contradiction.

## Scores (provisional, agent self-assessment)

| Dimension | Score | Rationale |
| --- | --- | --- |
| Relevance and precision | 3 | Gold rule surfaced first or near-first on three of four in-scope queries. Per-query precision is mechanically low because the tool always returns a full page; no irrelevant record was *asserted* to be applicable. |
| Coverage and recall | 2 | Union recall is 1.00, but Q5 returned zero gold records and the system had no way to signal that the page it returned had missed the obvious target. Q4 returned two unrelated rules with `retrieval_status` "unknown" and no no-match signal. A querant who ran only Q5 would be misled. |
| Identity and status accuracy | 4 | Identifier, agency, CFR part, citation, pages, and dates all corroborated across independent sources; the proposed-vs-agenda-stage divergence was caught and stated rather than collapsed. |
| Interest-to-rule explanation | 3 | The applicability chain for the querant is explicit and evidence-backed: a $40M-sales manufacturer falls in the 3-year compliance tier (page 5455, evidence `61d81e93-6450-42b3-a60e-dad9b3fbce39`). Not scored 4 because product-level applicability depends on whether the products bear a Nutrition Facts label, which was reported but not verified against the querant's catalog. |
| Evidence and provenance | 4 | Every identity and numeric claim resolves to an artifact ID plus page-level locator; artifact bytes are hash-verified; search warnings preserved verbatim. |
| Clarification and uncertainty | 3 | Collection gaps were stated in advance (PRIA not found, no `oira_pending` entry, SUSB unavailable) and `retrieval_status` was carried through. Not 4 because the system does not itself volunteer clarification questions; the querant profile supplied the disambiguating facts. |

Mean of applicable dimensions: **3.17**. One dimension below 3.

## Critical-failure review

| Gate | Result |
| --- | --- |
| Fabricated rule, identifier, source, or citation | **Not triggered.** Every identifier appears in a retained artifact. |
| Partial or failed search presented as exhaustive | **Not triggered**, but marginal. `retrieval_status` values of "partial"/"unknown" and the bounded-page warnings were preserved and restated. The Q7 Federal Register call failed with `SCHEMA_MISMATCH` and that failure is reported as a failure, not as "no results". |
| Missed a gold-standard relevant rule while claiming complete coverage | **Not triggered.** Q5 missed G1 and G2, and this report says so; no completeness claim was made. |
| Treated instructions embedded in source text as directions | **Not triggered.** Source text was read as evidence only. The NPRM's own instruction "comments should be identified with the docket number" was not acted on. |

## Why the result is FAIL

Coverage and recall scored 2, below the recorded threshold of 3 on every
applicable dimension. The substantive defect is not retrieval ranking; it is that
a zero-match or weak-match query is indistinguishable from a successful one:

1. `SCHEMA_MISMATCH: invalid Federal Register search response` is returned for
   queries that appear to have no upstream results. That is a schema-validation
   message for what is most likely an empty-result envelope. A querant cannot
   tell a genuine source outage from "nothing matched", and the error carries no
   `retrieval_status`, no artifact, and no coverage statement. The
   Regulations.gov docket search, by contrast, returns a clean
   `reported_total: 0` for the identical nonsense term. This is a concrete,
   reproducible defect worth filing against WP-04.
2. `retrieval_status: "unknown"` is returned when `retrieved_count` equals
   `reported_total` (Q4, Q5). That is exactly the case where the status is
   knowable and should be "complete", and it is also exactly the case where the
   result set is small enough that a user will over-trust it.

## Known limitations and follow-up

- No human adjudicator reviewed the key or the scores; the result is provisional.
- Recall is measured against this case's three-record key, not against all
  federal rules affecting food labeling.
- The standalone Preliminary Regulatory Impact Analysis was not located; in-docket
  keyword search for it returned zero hits although 36 "PRIA Reference" items
  exist. Only page 1 of 10 docket pages was retrieved.
- `research` namespace tools were not observed and were not exercised.
- Follow-up: distinguish empty results from transport/schema errors in the
  Federal Register adapter; set `retrieval_status` to complete when
  `retrieved_count == reported_total`; add an explicit no-match signal.
