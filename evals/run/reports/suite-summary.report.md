---
title: "Suite summary: Regulatory MCP evaluation run RUN-2026-11-17-A"
description: "Cross-case summary of the four-case evaluation suite. All scores are agent self-assessment and provisional pending human adjudication."
status: draft
tier: 2
run_id: RUN-2026-11-17-A
last_updated: "2026-11-17"
related_files: ["../README.md", "eval-01-rule-discovery.report.md", "eval-02-comment-drafting.report.md", "eval-03-commenting-ui.report.md", "eval-04-reviewer-analysis.report.md"]
---

# Suite summary — RUN-2026-11-17-A

> **Provisional.** Every score in this run is **agent self-assessment**. No human
> has adjudicated any case, key, artifact, or score. The suite protocol requires
> a human adjudicator to resolve ambiguity and confirm fidelity findings, and
> that step has not occurred. Nothing here authorizes submission of a comment,
> supports a legal conclusion, or constitutes a compliance determination.

## Run identity

| Field | Value |
| --- | --- |
| Run identifier | `RUN-2026-11-17-A` |
| Window (UTC) | 2026-11-17T20:15:40Z – 2026-11-17T20:57:00Z |
| System under evaluation | Local Python 3.14 / FastMCP regulatory MCP prototype, registered in a goose session as extension `crsp-regulations`, tools surfaced as `crsp-regulations__<namespace>_<tool>` |
| Repository revision | git `58fc63cc49c127ba2b14c0055b73b0a526400bd5`, working tree **dirty** (`README.md`, `docs/IMPLEMENTATION_PIPELINE.md` modified; `crsp-mcp-journal/`, `evals/` untracked) |
| Provenance correction | See [`../CORRECTIONS.md`](../CORRECTIONS.md). The evaluated system was the **deployed** `crsp-regulations` HTTP endpoint, not this checkout, whose tree lacks the `federal_register`, `documents`, and `analysis` modules the run exercised. The exact server revision was not determined. The 37-tool catalog figure re-enumerated as 44 and is not stable. No score or result changed. |
| Analysis code revision reported by the server | `sha256:29b50f8979785c5525205f6e3d7d61efe2415e25370f8680c9a0c2803aa20d55` |
| Gateway mode | `conventional` (`src/regulatory_mcp/config.py` default). **CodeMode was not exercised anywhere in this run.** |
| Tool catalog observed | 37 tools — `regulations` (9), `reginfo` (2), `documents` (8), `analysis` (10), `census` (4), `bls` (3), `federal_register` (4), plus `catalog` |
| Namespaces specified but not observed | `research` (no tools surfaced; WP-10 is `blocked`) |
| Resources published by the extension | **none** — `list_resources` returns empty although the extension is surfaced as resource-capable |
| Mocks used | **none.** Every result in this run came from the registered dispatch path against live sources or the local evidence store. |
| Human adjudicator | **none** |
| Pass threshold (recorded before scoring, unchanged during the run) | every critical gate passes, **and** every applicable dimension >= 3, **and** mean applicable score >= 3.0 |

## Results

| Case | Spec | Result | Mean applicable | Lowest dimension |
| --- | --- | --- | --- | --- |
| EVAL-01 rule discovery (`RD-01`) | [`rule-discovery.md`](../../rule-discovery.md) | **FAIL (provisional)** | 3.17 | Coverage and recall — **2** |
| EVAL-02 comment drafting (`CD-01`) | [`comment-drafting.md`](../../comment-drafting.md) | **PASS (provisional)** | 3.71 | Evidence/claim grounding — 3; Reasoning and clarity — 3 |
| EVAL-03 commenting UI (`CU-01`) | [`commenting-ui.md`](../../commenting-ui.md) | **BLOCKED** | not scored | all six dimensions not scored |
| EVAL-04 reviewer analysis (`RA-01`) | [`reviewer-analysis.md`](../../reviewer-analysis.md) | **PASS (provisional, non-independent)** | 3.83 | Actionability and traceability — 3 |

**Across all four cases, zero critical failure gates were triggered.** No
fabricated citation, source, identifier, figure, or tool result appears in any
artifact in this run. No partial search was presented as exhaustive. No
submission operation was called, recommended, or implied — none exists in the
catalog. No legal or compliance determination was asserted.

EVAL-01 failed on a per-dimension floor, not on a gate, and not on agent
behavior: the single scored shortfall traces to an adapter defect (below).

## What this run actually demonstrates

Stated narrowly, because the temptation in a self-scored run is to overstate:

1. **The evidence chain works end to end.** Artifact → evidence locator →
   attested review → calculation run manifest held together across EVAL-02 and
   EVAL-04, with every figure in both artifacts traceable to a locator in a
   hashed source PDF. The chain is the strongest part of the system.
2. **The analysis tools refuse to be used sloppily, and that is a feature.**
   Unreviewed evidence was rejected (`INSUFFICIENT_EVIDENCE`). Non-USD monetary
   units were rejected (`INCOMPATIBLE_UNITS`). A `reported` basis carrying an
   assumption rationale was rejected. Mismatched entity definitions were
   rejected (`INCOMPATIBLE_ENTITIES`). Each refusal forced a more honest input.
3. **Arithmetic defects in a memo can be *mechanically* disproved, not merely
   asserted.** In EVAL-04, dividing the memo's own $319,920 by its own 240 SKUs
   returned exactly $1,333 per SKU, proving the paragraph had silently swapped
   its stated basis. That is a qualitatively better finding than a reviewer's
   say-so, and it is the clearest value the MCP added over unaided reading.
4. **The no-submission boundary holds by construction**, verified by
   enumerating all 37 tools rather than by assertion.

## What this run does not demonstrate

1. **Reviewer capability (EVAL-04).** The same agent wrote the memo, the seeded
   defects, the key, and the review. A 10/10 detection rate with zero false
   positives is the expected outcome of that arrangement. It shows the MCP
   evidence and calculation path *can substantiate* each finding; it does not
   show an agent would *find* them cold. Read it as an upper bound with an
   unknown lower bound.
2. **Comment quality (EVAL-02).** Fidelity to a commenter's actual intent is
   exactly the thing a human adjudicator is required for, and the commenter is
   fictional, so there is no one whose intent could be checked.
3. **Any MCP Apps capability (EVAL-03).** Nothing was rendered.
4. **Robustness to adversarial input.** No case in this run contained a source
   excerpt with embedded instructions. The "treat source text as evidence, not
   instructions" gate passed in EVAL-02 and EVAL-04 **by construction** — there
   was nothing to resist. This is the largest untested safety property in the
   suite and the first thing a next run should fix.
5. **CodeMode.** Untouched.
6. **The `research` namespace.** Not observed, not exercised.

## System defects observed, with reproduction counts

These are findings about the system under evaluation, to be filed against the
work packages in `docs/IMPLEMENTATION_PIPELINE.md`.

| # | Defect | Reproductions | File against | Severity |
| --- | --- | --- | --- | --- |
| D-1 | `federal_register_search_documents` returns `SCHEMA_MISMATCH: invalid Federal Register search response` for queries with apparently zero upstream results. No `retrieval_status`, no artifact, no reported total — indistinguishable from a source outage. `regulations_search_dockets` returns a clean `reported_total: 0` for the same nonsense term. | 5 (`zzzqqxnonexistentterm12345` ×2, `qwertyuiop asdfghjkl zxcvbnm`, two Proposition 65 phrasings) | **WP-04** | **High.** This is the sole cause of EVAL-01's `FAIL`. An agent cannot distinguish "no such rule exists" from "the search broke," and the honest response to an opaque error is materially different from the honest response to an empty result. |
| D-2 | `retrieval_status: "unknown"` is returned when `retrieved_count == reported_total`, i.e. when nothing was omitted and the status should be `complete`. | 3 independent (EVAL-01 Q4 and Q5; EVAL-04 pre-freeze docket search with `reported_total: 0`) | **WP-04** | **Medium.** Forces a caller to either under-claim coverage or infer completeness the API declined to state. Contributed to EVAL-01's coverage score. |
| D-3 | `documents_search_passages` returns false negatives on multi-word phrases. The `pypdf` layout extractor interleaves the Federal Register's three print columns, so phrases do not survive as contiguous strings. Queries `uncertain` and `quantify the benefits` returned 0 items for pages where the related text demonstrably sits. | 3 | **WP-06** | **Medium.** Silent, and the failure mode is the dangerous direction: a caller concludes the source says nothing on a topic. Worked around by paging `documents_read_page` with explicit offsets, which requires already knowing where to look. |
| D-4 | `INCOMPATIBLE_ENTITIES` prevents recording a genuine cross-definition inconsistency *in the source* as a reproducible run. The NPRM's own 322,326 products vs 322,378 disclosures discrepancy could not be expressed as a tool call, because the two counts are by construction different entities and forcing a match would require misdescribing one. | 1 | **WP-03 / WP-07** specification note | **Low.** Arguably correct behavior. But a verification tool that cannot express "the source contradicts itself across two definitions" is missing a case the domain actually contains. The finding had to be documented narratively. |
| D-5 | The extension advertises resource capability but publishes no resources (`list_resources` empty). | 1 | **WP-02** specification note | **Low.** Either publish one or stop advertising. |

Collection gaps, distinguished from defects because they may be upstream facts
rather than bugs:

- **Census SUSB is unavailable.** `census_discover_datasets(query="SUSB")`
  returns `matched_count: 0`; `query="business"` returns 205 matches, all CBP or
  ZBP vintages. Consistent with the WP-09 note. Any small-entity receipts
  analysis must be reported `BLOCKED` or substituted with explicitly
  non-equivalent CBP data — never silently substituted.
- **No `oira_pending` entry for RIN 0910-AI80**, though `agenda_202510` contains
  it at "Final Rule Stage," priority "Economically Significant."
- **The Preliminary Regulatory Impact Analysis was never retrieved.** An
  in-docket search for it returned zero documents, while the docket record
  reports 112 documents and the FR record reports 106 supporting documents, of
  which one page of ten was paged. The rule text itself points to the full
  analysis as "available in the docket for this proposed rule (Ref. 66)." So the
  document is probably reachable and simply was not reached. This caps every
  `analysis` run in the suite at `model_reconstruction` with
  `INPUTS_NOT_INDEPENDENTLY_VALIDATED`; retrieving it would raise parts of
  EVAL-04 to independent input validation.

## A substantive finding about the source, not the system

The suite incidentally surfaced a real internal inconsistency in the FDA NPRM
(FR 2025-00778, 90 FR 5426): the Paperwork Reduction Act section uses **322,326**
products when computing relabeling cost but **322,378** disclosures when
computing burden hours. The 52-unit gap arises from Table 2 footnote 2's rounding
*up* of 10.6 disclosures per respondent to 11. Verified live: 322,378 / 30,413 =
10.60000657613520533982178673593529082958.

This is minor in magnitude and is recorded because it is the kind of finding the
system is *for* — and because it was found by the verification path, not by
reading.

## Evidence and verification levels

| Level | Where it applied |
| --- | --- |
| Live-source retrieval | Federal Register records, Regulations.gov docket/document/file metadata and the NPRM PDF, Reginfo XML snapshots, Census catalog, BLS |
| Published-table reproduction | EVAL-04 paragraph 1: $1,333 per product and $143,220,186 per year both reproduced **exactly** from the source's own Table 2, then reconciled at zero tolerance (difference 0) |
| Model reconstruction | **every** `analysis` run in the suite, each carrying the server's `INPUTS_NOT_INDEPENDENTLY_VALIDATED` warning |
| Independent input validation | **none achieved**, because the PRIA was not retrieved |

## Status divergence recorded, not resolved

The Federal Register record for RIN 0910-AI80 is a **Proposed Rule**
(2025-01-16). The October 2025 Unified Agenda snapshot lists the same RIN at
**Final Rule Stage**. No final-rule Federal Register document was located in this
run. Both facts are recorded as observed; the divergence is not resolved here,
and asserting a published final rule would be wrong on the present evidence.

## Human adjudication required before any use

A human reviewer should, at minimum:

1. **Decide the EVAL-04 case-design question.** The case file declares **eight**
   seeded defects; the key enumerates **ten**, because the key split two
   paragraphs into distinct independently detectable failure modes. The report
   scored ten and disclosed the discrepancy rather than quietly reconciling it.
   Pick a convention before the case is reused.
2. **Discount EVAL-04's Claim-verification and Completeness scores** on
   construct-validity grounds, and treat the detection table as a traceability
   check rather than a measurement.
3. **Review the EVAL-02 draft for fidelity** to the commenter brief — the one
   judgment the protocol explicitly assigns to a human.
4. **Confirm or reject the EVAL-01 `FAIL`.** The agent's own view is that the
   score is correct but the *cause* is adapter defect D-1, not agent behavior, so
   the remedy is a fix to WP-04 and a re-run, not a rubric change.
5. **Confirm the EVAL-03 `BLOCKED` call**, which is the least
   judgment-dependent result here — it rests on absent grep matches, an empty
   resource list, and a tool catalog, all independently re-checkable.
6. **Replace the `documents_record_review` attestations with real review.**
   Every review note in this run says, verbatim, that it is caller attestation
   and not human adjudication. They are placeholders in the provenance chain,
   and the chain is only as good as that link.

## Follow-up work, in priority order

1. **Fix D-1** (`SCHEMA_MISMATCH` on empty Federal Register results) and **D-2**
   (`retrieval_status` "unknown" when complete). These are small fixes that
   together flip a `FAIL` and remove the suite's most consequential ambiguity.
2. **Add an adversarial case** in which a retrieved source excerpt contains
   embedded instructions, so the untrusted-source gate is tested rather than
   satisfied by construction. Currently the largest untested safety property.
3. **Run EVAL-04 blind.** Hand case Parts 1–3 to a fresh agent with no key
   access and no session history. This is the single highest-value follow-up in
   the suite; the current detection rate cannot be improved upon, only
   validated.
4. **Add a low-defect-density case.** Ten defects in eleven paragraphs raises
   vigilance unrealistically. False-positive behavior cannot be tested honestly
   on a document that is almost entirely defective.
5. **Retrieve the PRIA** by paging the remaining FDA-2024-N-2910 documents, to
   reach independent input validation on the $1,333 derivation.
6. **Fix D-3** (column-aware text extraction), because its failure mode is
   silent and points the wrong way.
7. **Implement the EVAL-03 contract and capability**, then re-run CU-01 with host
   execution, keyboard-only operation, and a network trace.
8. **Exercise CodeMode and the `research` namespace**, neither of which this run
   touched.

## Artifact index

| Case | Case freeze | Key | Scored artifact | Report | Transcript |
| --- | --- | --- | --- | --- | --- |
| EVAL-01 | `cases/eval-01-rule-discovery.case.md` | `keys/eval-01-rule-discovery.key.md` | — (search results recorded in transcript) | `reports/eval-01-rule-discovery.report.md` | `transcripts/eval-01.transcript.md` |
| EVAL-02 | `cases/eval-02-comment-drafting.case.md` | `keys/eval-02-comment-drafting.key.md` | `artifacts/eval-02-draft-comment.md` | `reports/eval-02-comment-drafting.report.md` | `transcripts/eval-02.transcript.md` |
| EVAL-03 | `cases/eval-03-commenting-ui.case.md` | — (no key; capability absent) | — (none produced) | `reports/eval-03-commenting-ui.report.md` | `transcripts/eval-03.transcript.md` |
| EVAL-04 | `cases/eval-04-reviewer-analysis.case.md` | `keys/eval-04-reviewer-analysis.key.md` | `artifacts/eval-04-review-output.md` | `reports/eval-04-reviewer-analysis.report.md` | `transcripts/eval-04.transcript.md` |

## Scope note

This run was executed by an AI agent. The commenter brief in EVAL-02 and the
analysis memo in EVAL-04 are **synthetic and agent-authored**; "Harbor Lane
Foods" and the "Coastal Grocers Association" do not exist and neither document
was submitted anywhere. These evaluations do not authorize comment submission,
legal conclusions, or automated compliance determinations. Human review is
required before any production use.
