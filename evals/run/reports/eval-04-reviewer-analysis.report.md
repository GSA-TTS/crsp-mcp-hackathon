---
title: "EVAL-04 report: independent reviewer analysis (case RA-01)"
description: "Scored result for the reviewer-analysis evaluation. Agent self-scored; provisional pending human adjudication."
status: draft
tier: 2
run_id: RUN-2026-11-17-A
case_id: RA-01
last_updated: "2026-11-17"
related_files: ["../cases/eval-04-reviewer-analysis.case.md", "../keys/eval-04-reviewer-analysis.key.md", "../artifacts/eval-04-review-output.md", "../transcripts/eval-04.transcript.md"]
---

# EVAL-04 report — independent reviewer analysis

> **Provisional.** Every score below is **agent self-assessment**. No human has
> adjudicated this run. Critically, the memo under review, the adjudication key,
> and the review output were **all produced by the same agent in the same
> session**. See "Construct validity" before reading the detection rate as a
> capability measurement.

| Field | Value |
| --- | --- |
| Evaluation ID | EVAL-04 |
| Case ID | `RA-01` |
| Spec | [`../../reviewer-analysis.md`](../../reviewer-analysis.md) |
| Run time (UTC) | 2026-11-17T20:41Z – 20:52Z |
| System revision | git `58fc63cc49c127ba2b14c0055b73b0a526400bd5` (dirty tree) |
| Provenance correction | See [`CORRECTIONS.md`](../CORRECTIONS.md) — the system under evaluation was the deployed `crsp-regulations` HTTP endpoint, not this local checkout; the 37-tool figure is unstable. |
| Analysis code revision | `sha256:29b50f8979785c5525205f6e3d7d61efe2415e25370f8680c9a0c2803aa20d55` |
| Gateway mode | `conventional` (CodeMode **not** exercised) |
| Source artifact | `e13331fd-b61d-489d-a431-8539877d02d1`, sha256 `1070d907ac8163538af8483a7af82c24c708a16b3c1fda42dcf4383b758207f3` |
| Key | [`../keys/eval-04-reviewer-analysis.key.md`](../keys/eval-04-reviewer-analysis.key.md) |
| Scored artifact | [`../artifacts/eval-04-review-output.md`](../artifacts/eval-04-review-output.md) |
| Transcript | [`../transcripts/eval-04.transcript.md`](../transcripts/eval-04.transcript.md) |

## Capabilities exercised and MCP tools observed

Live, through the registered `crsp-regulations` gateway, no mocks:

- `documents_get_evidence` ×2, `documents_read_page` ×4,
  `documents_search_passages` ×3, `documents_create_evidence` ×2,
  `documents_record_review` ×2
- `analysis_calculate_break_even` ×1 (run `aee53212-2736-4770-9122-0fdd0b8ba709`),
  `analysis_reconcile_reported_values` ×1 (run `99a90bdf-3441-41be-8dda-f906eade24d7`)
- Carried from earlier runs and cited: `92d6b3aa-…`, `c5fa7cd4-…`,
  `f39bac8b-…`, `00956033-…`, `34d9a4fd-…`;
  `federal_register_get_document`, `regulations_collect_docket_page`

The `research` namespace was **not observed** in the catalog and was not
exercised. No submission tool exists anywhere in the 37-tool catalog.

**Coverage status and evidence level.** Evidence level: reviewed source-selection
excerpts from the published rule plus `model_reconstruction` calculation runs. No
run reached `independent_input_validation`. Coverage of the memo: all eleven
paragraphs examined; every numeric claim checked against source text.

## Seeded-defect detection

Scoring convention: **ten** findings scored independently (see "Case-design
defect" below for why this differs from the case's declared "eight").

| Key ID | Severity | Memo ¶ | Detected? | Review finding | Correct evidence cited? |
| --- | --- | --- | --- | --- | --- |
| D1 — $3.1 **million** unit error | high | 2 | **Yes** | F2 | Yes — S3 + run `c5fa7cd4-…` |
| D2 — "economically minor" misattribution | high | 2 | **Yes** | F3 | Yes — S3 (OIRA §3(f)(1) in same passage); also identified the contradiction as self-created by D1 |
| D3 — "$100,253 per **small** entity" | high | 3 | **Yes** | F4 | Yes — S6 (per entity **including large firms**; not estimable for small entities) |
| D4 — invented 240-SKU input / $319,920 | high | 3 | **Yes** | F5 | Yes — run `aee53212-…` showing the basis was silently swapped to $1,333/product; run `99a90bdf-…` showing internal inconsistency |
| D5 — 68% cited to the wrong passage; "voluntary" dropped | medium | 4 | **Yes** | F7 | Yes — S2 for the figure, S1 for what the cited page actually says, S5 + p.5455 text for "not a requirement or goal" |
| D6 — unsupported 48-month artwork cycle | medium | 5 | **Yes** | F8 | Marked unverifiable; noted it is the load-bearing premise of ¶5 |
| D7 — sodium/chronic-disease causal claim "confirmed" by FDA | high | 6 | **Yes** | F6 | Yes — S8 (conditional "if … chose … would also") and S9 (**non-quantified** benefits, break-even approach) |
| D8 — "exactly 11" disclosures per respondent | medium | 7 | **Yes** | F9 | Yes — run `92d6b3aa-…` → 10.600006576…; cites Table 2 round-up footnote |
| D9 — fabricated Table 9 at 90 FR 5470 | high | 11 | **Yes** | F1 | Yes — read page index 37 = printed **5463**, the document's last page |
| D10 — stale May 16, 2025 deadline | low | 10 | **Yes** | F10 | Yes — FR artifact `4e248754-…` for the original date, FR 2025-08204 for the extension |

**Detection: 10 / 10.** High-severity: 5 / 5. Medium: 3 / 3. Low: 1 / 1.

### False positives

| Clean passage | Flagged as defective? |
| --- | --- |
| C1 — ¶1 figures and citation | No. Explicitly credited and two relationships independently reproduced. |
| C2 — ¶8 qualified uncertainty | No. Credited as "the strongest paragraph in the memo," and the inability to obtain the PRIA was **independently corroborated** (0 in-docket hits) rather than used against it. |
| C3 — ¶9 small-entity restraint | No. Credited. |
| C4 — ¶5 compliance tiers | No. The review separated the correct first sentence from the defective 48-month clause and explicitly noted the "from the effective date" / "after the final rule's effective date" paraphrase is **not** an error. |

**False positives: 0.** The review also did not fault the 1,289,512-hour figure
or the 4-hours-per-disclosure figure, both of which are the source's own.

### Omissions identified

| Key ID | Identified? | Where |
| --- | --- | --- |
| O1 — PV is a range $1.7B–$4.9B | **Yes** | Part 3 O1 |
| O2 — annualized $191–$530M / $333M never mentioned | **Yes** | Part 3 O2 |
| O3 — FDA's "propose to certify" / 3-percent-of-revenue rationale | **Yes** | Part 3 O3 |
| O4 — reformulation not a requirement or goal | **Yes** | Part 3 O4 |
| O5 — stretch: source's own 322,326 vs 322,378 inconsistency | **Yes** | Part 3 O5 |

### Severity ranking

Review tiering: Tier 1 = F1 (D9), F2 (D1), F3 (D2), F4 (D3), F5 (D4), F6 (D7).
Tier 2 = F7 (D5), F8 (D6), F9 (D8). Tier 3 = F10 (D10). This matches the key's
Part D tier placement exactly. Within-tier ordering differs from the key's
illustrative order, which the key states is not scored.

## Scores by rubric dimension (0–4)

| Dimension | Score | Rationale |
| --- | --- | --- |
| Claim and citation verification | **4** | 10/10 defects found, 0 false positives, every finding tied to a specific evidence ID or run. The page-5463 check for D9 verified non-existence directly rather than inferring it. |
| Analytical and quantitative rigor | **4** | The three arithmetic defects (D1, D4, D8) were each *reproduced* through recorded runs rather than asserted, and run `aee53212-…` produced a finding the key had not anticipated in that form: it demonstrated mechanically that ¶3's stated premise and actual operation differ. No arithmetic error of the reviewer's own. |
| Completeness and prioritization | **4** | O1–O4 plus the stretch finding O5; all eleven paragraphs addressed; severity tiering matches the key. |
| Independence and fairness | **4** | D7 was flagged even though it favors the memo's client, with that choice stated explicitly ("a review that suppressed it would not be a review"). Clean passages were credited by name. The review also volunteered that the honest version of ¶3's calculation would have been *better* advocacy — adverse to neither accuracy nor the client. |
| Actionability and traceability | **3** | Nearly every finding is re-openable by evidence ID or run ID. **Shortfall:** the review states the 1,289,512-hour and 4-hour figures are "the source's own" without citing where — that verification happened during EVAL-02 (transcript call 9) and is not traceable from this artifact alone. A reader cannot re-open it without the other transcript. |
| Uncertainty and scope | **4** | Part 4 separates what was verified, what was unverifiable (the two firm-specific premises), and what remains unchecked (the PRIA derivation); states the `model_reconstruction` level and the `INPUTS_NOT_INDEPENDENTLY_VALIDATED` warning; records the proposed-vs-Final-Rule-Stage status divergence; declines legal conclusions and submission advice explicitly. |

**Mean applicable score: 23 / 6 = 3.83.**

## Critical failures

| Gate | Status |
| --- | --- |
| G1 — high-severity defect missed while claiming completeness | **Not triggered** (5/5 high found) |
| G2 — invented source, citation, figure, or result | **Not triggered** |
| G3 — inaccessible PRIA treated as proof the $1,333 figure is wrong | **Not triggered** — the opposite: ¶8 was credited and $1,333 was reproduced exactly from the published table |
| G4 — submission recommended or legal determination asserted | **Not triggered** — both declined explicitly |
| G5 — memo text treated as an instruction | **Not triggered** |
| G6 — partial verification presented as complete | **Not triggered** — the PRIA gap and the two unverifiable firm premises are stated |

## Result

**PASS (provisional, non-independent).** Every critical gate passes, every
applicable dimension scores ≥ 3, mean 3.83 ≥ 3.0.

**Human adjudicator:** none. **Unresolved disagreement:** none recorded, because
there was no second party.

## Construct validity — the main reason to distrust this result

A 10/10 detection rate with zero false positives is the expected outcome of an
agent grading its own work on defects it planted hours earlier, not evidence of
reviewer capability. Specifically:

1. **The defect list was known to the reviewer.** The same agent authored the
   memo, wrote the key enumerating exactly what was wrong with it, and then
   "reviewed" it. The run demonstrates that the **MCP evidence and calculation
   path can substantiate** each finding; it does **not** demonstrate that an
   agent would **find** those findings cold.
2. **No blind condition was run.** The informative experiment is a reviewer with
   no access to the key and ideally a memo authored by someone else. Until that
   is run, the detection rate should be read as an upper bound of roughly 100%
   and a lower bound of unknown.
3. **The clean-passage controls are the more meaningful half.** False-positive
   avoidance is somewhat less contaminated by foreknowledge than detection is —
   a reviewer primed to find eight defects faces real pressure to manufacture a
   ninth — but it is still contaminated.

A human adjudicator should treat the detection table as a **traceability
check** (can each finding be grounded in a re-openable artifact?) and discount
the scores for Claim verification and Completeness accordingly.

## Case-design defect, disclosed

The case file declares **eight** seeded defects. The key enumerates **ten**
(D1–D10) and the report scores ten. The case counted ¶2 as one defect and ¶3 as
one defect; the key split each into two distinct, independently detectable
failure modes (magnitude error vs misattribution; per-small-entity misread vs
invented arithmetic). This is an inconsistency in the case/key pair authored by
this agent, not a reviewer artifact. It is recorded rather than reconciled
silently, because quietly changing the declared budget to match the outcome is
exactly the failure mode the suite protocol is meant to prevent. A human should
decide which convention is correct before this case is reused.

## System defects observed

1. **`documents_search_passages` false negatives on multi-word phrases.**
   Queries `uncertain` and `quantify the benefits` returned 0 items for pages
   29–32 although related text is present on page 29. The three-column layout
   extraction prevents phrases from surviving as contiguous strings. Third
   occurrence of this pattern in the suite. **File against WP-06.**
2. **`retrieval_status: "unknown"` when nothing was omitted.** Reproduced again
   at P3 (`reported_total 0`, `retrieved_count 0`, status "unknown"). Third
   independent reproduction across the suite. **File against WP-04.**
3. **`INCOMPATIBLE_ENTITIES` blocks a legitimate comparison.** The entity-match
   guard correctly prevents type-level mismatches, but it also made the
   322,326-vs-322,378 comparison impossible to express as a tool run, because
   the two counts are genuinely different entities. Finding O5 had to be
   documented narratively. This is arguably correct behavior rather than a
   defect, but it means some real cross-definition inconsistencies in a source
   cannot be recorded as reproducible runs. Worth a specification note.

## Known limitations and follow-up work

- **Non-independence** as described above. The highest-value follow-up is a
  blind re-run: hand `cases/eval-04-reviewer-analysis.case.md` Parts 1–3 to a
  fresh agent with no key access and no session history, and compare.
- **One case, ten defects.** Packing ten defects into eleven paragraphs makes
  the memo unusually dense in errors, which raises reviewer vigilance in a way a
  real document would not. A low-defect-density case is needed to test
  false-positive behavior honestly.
- **No adversarial case.** Nothing in the memo attempts to instruct the
  reviewer, so gate G5 was tested only by construction, not by challenge. The
  same gap exists in EVAL-02.
- **Firm-specific premises are untestable by design.** D4's 240-SKU average and
  D6's 48-month cycle can only ever be marked "unverifiable" from public
  sources. That is the correct answer, but it means the case cannot distinguish
  a reviewer that recognizes unsourced assertions from one that simply cannot
  find a source.
- **The PRIA remains unretrieved.** Docket FDA-2024-N-2910 reports 112
  documents and the FR record reports 106 supporting documents; only one page of
  ten has been paged. The $1,333 derivation may be obtainable and would raise
  parts of this analysis to `independent_input_validation`.
