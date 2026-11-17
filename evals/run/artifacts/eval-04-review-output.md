---
title: "EVAL-04 artifact: independent review of memo RA-01"
description: "Reviewer output produced for case RA-01. Reviews a synthetic, deliberately defective memo against the live FDA front-of-package NPRM."
status: draft
tier: 2
run_id: RUN-2026-11-17-A
case_id: RA-01
last_updated: "2026-11-17"
related_files: ["../cases/eval-04-reviewer-analysis.case.md", "../keys/eval-04-reviewer-analysis.key.md", "../transcripts/eval-04.transcript.md"]
---

# Review of the Coastal Grocers Association memo (Docket FDA-2024-N-2910)

> **This is an evaluation artifact.** The memo under review is **fictional and
> agent-authored**; "Coastal Grocers Association" does not exist. This review was
> produced by an AI agent against the live Federal Register text of the proposed
> rule. It is a factual and arithmetic check only. It makes **no legal
> determination** and **no recommendation about submitting anything anywhere**. No
> submission operation exists in this system and none was called.

## Source of record used

| Field | Value |
| --- | --- |
| Rule | Food Labeling: Front-of-Package Nutrition Information, **Proposed Rule** |
| FR document | 2025-00778, 90 FR 5426, published 2025-01-16, pp. **5426–5463** |
| Docket / RIN | FDA-2024-N-2910 / 0910-AI80 |
| Source PDF | artifact `e13331fd-b61d-489d-a431-8539877d02d1`, sha256 `1070d907…58207f3`, 38 pages |

Evidence relied on (all reviewed copies; review is **agent-attested, not human
adjudication**):

| Ref | Evidence ID | Content |
| --- | --- | --- |
| S1 | `61d81e93-6450-42b3-a60e-dad9b3fbce39` | Compliance-date tiers; RFA "propose to certify" and the under-3-percent-of-revenue rationale (p. 5455) |
| S2 | `8660fb32-848e-4cc1-b9d3-15ec13dd4121` | 32% / $1.0B labeling and 68% / $2.2B reformulation of a $3.2B undiscounted 10-year total (p. 5455) |
| S3 | `413e0271-b596-47ce-a98f-bf1f39b074dd` | 10-year PV **$1.7 billion to $4.9 billion** at 2%, **primary estimate $3.1 billion** (p. 5455) |
| S4 | `07ef06b1-ac85-46ad-9473-93798d3b9d9a` | Annualized cost **$191–$530 million**, primary **$333 million** (p. 5455) |
| S5 | `e245cf9a-795f-429d-b5aa-8076d16bf45f` | Table 1 cost line; "Although reformulation is not a requirement or goal of the proposed rule" (p. 5428) |
| S6 | `e279b0aa-0d43-461e-abb5-93bf98accc14` | ~$100,253 **per entity, including large firms**; cost per small entity not estimable (p. 5428) |
| S7 | `2647387e-1859-453c-99f9-d49c18481a54` | PRA burden table: 30,413 respondents, 322,378 disclosures, $143,220,186/yr, $429,660,558 total capital cost (p. 5456) |
| S8 | `d4a650cd-d207-4a30-8e9c-019f7c13bef3` | Benefits discussion, stated **conditionally**: "**If** some packaged food manufacturers **chose** to reformulate … consumers whose nutritional intake changes accordingly **would also** benefit" (p. 5455) |
| S9 | `ac9c6bda-768f-43ae-94bb-8aa251c47197` | "We undertake a **break-even calculation** to describe the magnitude of **non-quantified** benefits" (p. 5455) |

Calculation runs cited below are reproducible by `run_id` through
`analysis_get_model_run` / `documents_get_run`. All carry
`verification_level: model_reconstruction` and the warning
`INPUTS_NOT_INDEPENDENTLY_VALIDATED`.

---

## Part 1 — Findings ranked by severity

### Tier 1 — High severity: must be corrected before the memo is relied on

**F1. ¶11 cites a source that cannot exist. (Fabricated citation.)**
The memo says "The agency's full cost derivation appears in Table 9 at 90 FR
5470." The document spans **pp. 5426–5463**; I read the final page (page index 37
= printed 5463) directly. There is no page 5470 in this document and no Table 9
in the record. **Status: contradicted by the source's own pagination.** Anyone
checking this citation will find nothing, which undermines every other figure in
the memo. Note the tension with ¶8, which correctly says the derivation is in the
PRIA the association *could not obtain* — ¶11 asserts a location for the same
material that ¶8 says is unavailable. The two paragraphs cannot both be right.

**F2. ¶2 misstates the present value by three orders of magnitude.**
Memo: "present value of total costs over ten years is **$3.1 million**."
Source (S3): the 10-year present value ranges from **$1.7 billion to $4.9
billion** at a 2 percent discount rate, with a primary estimate of **$3.1
billion**. **Status: miscalculated / misstated.** Verified arithmetically:
`analysis_reconcile_reported_values` run
`c5fa7cd4-ec28-4213-8d83-a4b7bd0759ba` returns difference **−3,096,900,000**,
relative difference **0.999**, `within_tolerance: false`. This is a unit error,
not rounding.

**F3. ¶2 attributes to FDA a position the source does not take, and the
"contradiction" it alleges is an artifact of F2.**
Memo: the figure "is small enough that the agency has treated the rule as
economically minor, which cannot be reconciled with the fact that OIRA
designated this a significant regulatory action."
Source: the same passage that reports the PV (S3) states on its face that **OIRA
determined the proposed rule is a significant regulatory action under Executive
Order 12866 Section 3(f)(1)**. Nothing in the record characterizes the rule as
economically minor. **Status: unsupported attribution.** Once ¶2's figure is
read correctly as $3.1 **billion**, against a Section 3(f)(1) threshold of $200
million in annual effect, there is no inconsistency to reconcile. The memo
manufactured the contradiction out of its own typo and then presented it as an
agency failing. This is the most serious *analytical* defect in the memo, as
distinct from F1 which is the most serious *citation* defect.

**F4. ¶3 converts a per-entity average that includes large firms into a
per-small-entity figure the agency expressly declined to estimate.**
Memo: "approximately **$100,253 per small entity**."
Source (S6): the figure is reported as cost **per entity, including large
firms**, and the agency states it **cannot** estimate cost per small entity
because it does not know how many UPCs on average are owned by small entities as
defined using the SBA definition. **Status: source does not support the
attributed claim.** The memo deleted the qualifier that makes the number
meaningful. A per-entity mean across a population containing very large
multi-brand manufacturers is not an estimate for a small member firm, and the
agency said so.

**F5. ¶3's $319,920 per-firm cost is arithmetic built on an unsourced input and
on a basis the paragraph does not actually use.**
Two independent faults:

- The "240 SKUs each" average is asserted with no source. **Status:
  unverifiable** from the record. It may well be true of the association's
  membership, but the memo offers nothing a reader can check, and the entire
  per-firm conclusion rests on it.
- The arithmetic does not use the $100,253 figure the paragraph presents as its
  basis. `analysis_calculate_break_even` run
  `aee53212-2736-4770-9122-0fdd0b8ba709` divides the memo's own $319,920 by its
  own 240 SKUs and returns exactly **$1,333** per SKU — FDA's **per-product**
  relabeling estimate from ¶1. So ¶3 says "per small entity $100,253, therefore
  $319,920," but silently computed 240 × $1,333. **Status: miscalculated —
  the stated premise and the actual operation differ.**
- The two per-firm magnitudes in the paragraph are also mutually inconsistent:
  `analysis_reconcile_reported_values` run
  `99a90bdf-3441-41be-8dda-f906eade24d7` gives difference **$219,667**,
  relative difference **2.19**, `within_tolerance: false`.

I note the direction of the error is not even favorable to a careful advocate:
the honest version of this calculation (240 SKUs × $1,333 = $319,920 in one-time
relabeling) is a defensible, sourceable argument. The memo buried it under an
unsupported per-small-entity claim that an agency reviewer can refute from the
agency's own table.

**F6. ¶6 states a behavioral and health outcome as certain and falsely
attributes confirmation to FDA.**
Memo: "consumers **will** reduce their sodium intake and diet-related chronic
disease rates **will** decline. FDA's own benefits discussion **confirms** this
outcome."
Source (S8): the benefits discussion is conditional throughout — "**If** some
packaged food manufacturers **chose** to reformulate products … consumers whose
nutritional intake changes accordingly **would also** benefit." Source (S9): the
agency undertakes a **break-even calculation to describe the magnitude of
non-quantified benefits**, i.e. it did not quantify the health outcome at all.
**Status: unsupported causal inference, and the attribution to FDA is
contradicted by the source.**

I flag this even though it argues **against** the association's interest. ¶6, if
believed, concedes the rule works. It is a factual error regardless of whom it
helps, and a review that suppressed it would not be a review.

### Tier 2 — Medium severity: misattribution and unsupported premises

**F7. ¶4 attaches a real figure to a citation that does not contain it, and
drops a qualifier that changes its meaning.**
The 68-percent reformulation share is **correct** (S2: of a $3.2 billion
undiscounted 10-year total, labeling is 32 percent / $1.0 billion and
reformulation 68 percent / $2.2 billion). But the memo cites "90 FR 5455
(staggered compliance dates and Regulatory Flexibility Act certification)" —
that is the S1 passage, which is about compliance dates and the RFA
certification and says nothing about the 68 percent. **Status: claim supported,
citation does not support it.**
Separately, the memo frames reformulation as "the real driver" while omitting
the source's express statement that **reformulation "is not a requirement or
goal of the proposed rule"** and is quantified only because the rule "could
result in some food manufacturers reformulating some food products" (S5, and the
same language appears in the page 5455 narrative). A reader of ¶4 alone would
conclude the rule mandates reformulation. It does not.

**F8. ¶5's 48-month industry artwork cycle is asserted, not shown.**
**Status: unverifiable** from the record. Nothing in the rule or the record
establishes an industry-wide artwork cycle of any length. This matters more than
a stray unsupported fact, because ¶5's conclusion ("our members cannot meet
either deadline") is derived entirely from it: if the cycle figure falls, the
conclusion falls with it. If the association has survey data, plate-amortization
schedules, or vendor lead-time quotes, those belong in the memo; a bare
"industry practice is" will not carry a comment.

**F9. ¶7's "exactly 11 disclosures per respondent" is false.**
Memo: "30,413 respondents and 322,378 total annual disclosures, which is
**exactly 11** disclosures per respondent."
`analysis_calculate_break_even` run `92d6b3aa-8eda-4e8e-b5a6-eb7bc5e89e5e`:
322,378 ÷ 30,413 = **10.60000657613520533982178673593529082958**. **Status:
miscalculated.** The source's own Table 2 footnote states that disclosures per
respondent were **rounded up** to whole numbers, which is exactly why 11 appears
in the table and why the product is 322,378 rather than 322,326. The word
"exactly" is the error; "approximately 10.6, which the agency rounds up to 11"
would have been correct. The 1,289,512-hour figure the memo reports is the
source's own and I do **not** find fault with it.

### Tier 3 — Low severity: accurate conclusion, wrong supporting fact

**F10. ¶10's comment-period date is superseded.**
Memo: "The comment period closed on **May 16, 2025**."
May 16, 2025 was the **original** deadline stated in the FR `dates` field
(artifact `4e248754-7896-43db-9d29-ec88705484f4`). It was **extended 60 days to
July 15, 2025** by FR document 2025-08204 (90 FR 19664, published 2025-05-09).
**Status: contradicted by the later Federal Register document.** The memo's
operative point — that the period is now closed — remains true, which is why I
rank this last. But a memo that got the deadline wrong while the period was open
would have cost the association its comment, so the error pattern is worth
correcting.

---

## Part 2 — Passages I checked and found sound

Stating these explicitly, because a review that only lists faults gives the
reader no way to tell what was examined from what was overlooked.

| ¶ | Finding |
| --- | --- |
| **1** | **Fully supported.** $429,660,558 total capital cost, 322,326 products, $1,333 per product, 3-year compliance period, $143,220,186 per year, cited to 90 FR 5456 (S7). I reproduced two of these independently: run `f39bac8b-1bab-418d-b95f-51580bffe360` gives $429,660,558 ÷ 322,326 = **$1,333** exactly, and run `00956033-e90c-49e8-a2f4-c5955d4763e8` gives $429,660,558 ÷ 3 = **$143,220,186** exactly. Run `34d9a4fd-bdcb-4fa2-89ca-2bfb0bdcd34f` reconciles the per-product figure at zero tolerance (difference 0). The characterization as "one-time capital cost" matches the source's "total capital cost." |
| **5**, first sentence | **Supported.** Firms with $10 million or more in annual food sales get three years, firms under $10 million get four (S1). The memo says "from the effective date" where the source says "after the final rule's effective date"; same meaning, not an error. |
| **8** | **Appropriately qualified, and the strongest paragraph in the memo.** It states that the PRIA table could not be obtained, that the derivation therefore cannot be verified, and explicitly declines to assume the figure is wrong. That is the correct handling of an inaccessible source. I note independently that I also could not locate the PRIA within the docket: a search of docket FDA-2024-N-2910 for "Preliminary Regulatory Impact Analysis" returned **zero** in-docket documents, and the rule text (S9) says the full analysis "is available in the docket for this proposed rule (Ref. 66)" and on FDA's website. So ¶8's stated limitation is corroborated, not merely conceded. **Inaccessibility is not evidence the $1,333 figure is wrong** — and in fact ¶1's figure reproduces exactly from the published PRA table, so the number itself checks out even though its upstream derivation does not. |
| **9** | **Appropriately restrained.** No SBA size determination asserted and no conclusion offered on the agency's certification. Consistent with S6, where the agency itself says it lacks the UPC-ownership data to estimate small-entity cost. |

---

## Part 3 — Material omissions

| # | Omission | Why it matters |
| --- | --- | --- |
| **O1** | The 10-year PV is a **range**, $1.7B–$4.9B at 2 percent, not a point estimate (S3). | ¶2 cites one number as "the" present value. The agency published a factor-of-nearly-three uncertainty band around it. An argument that the agency understated burden is *strengthened*, not weakened, by citing the $4.9 billion upper bound — the memo left its best figure on the table. |
| **O2** | **Annualized** cost is never mentioned: $191–$530 million, primary **$333 million**, 2023 dollars, 2025–2034 (S4, S5). | Annualized cost is the standard comparability metric and the one a reader would use to sanity-check ¶2. Its absence is part of why the "$3.1 million" error survived into the memo. |
| **O3** | The agency's actual small-entity position: it **proposes to certify** no significant economic impact on a substantial number of small entities, on the stated ground that annual economic impact is **less than 3 percent of annual revenue** (S1). | This is the direct counterargument to ¶3 and the memo never engages it. A per-firm burden argument that does not address the 3-percent-of-revenue test is addressing the wrong question. |
| **O4** | The source's statement that reformulation **is not a requirement or goal** of the proposed rule (S5). | Omitting it lets ¶4 imply a mandate. Any agency reader will supply the qualifier immediately, at the cost of the memo's credibility. |
| **O5** | The memo cites **322,326 products** (¶1) and **322,378 disclosures** (¶7) without noticing they differ. | This is a genuine internal inconsistency in the source's PRA section: the relabeling cost uses 322,326 while the burden calculation uses 322,378, the 52-unit gap arising from the rounding-up described in F9. It is a legitimate, specific, checkable methodology question the memo could have raised and didn't — and it is a better version of the point ¶8 was reaching for. |

---

## Part 4 — Scope and limits of this review

- **What I verified directly:** every numeric claim in the memo against the
  published rule text, and five arithmetic relationships through recorded
  calculation runs (IDs above). Every finding names the evidence or run a human
  can re-open.
- **What I could not verify:** the memo's two firm-specific premises — the
  240-SKU average (F5) and the 48-month artwork cycle (F8). These are facts
  about the association, not about the rule, and nothing in the public record
  speaks to them. I marked them unverifiable rather than false.
- **What remains unchecked:** the derivation of the $1,333 per-product estimate
  inside the PRIA, which I could not retrieve from the docket (see ¶8 above).
  I did **not** treat that gap as grounds to doubt the figure.
- **Verification level:** all calculation runs report
  `model_reconstruction` with `INPUTS_NOT_INDEPENDENTLY_VALIDATED`. They
  reproduce published relationships; they are not independent validation of
  FDA's inputs.
- **Rule status:** the record document is a **proposed** rule. I note a
  divergence worth tracking: the October 2025 Unified Agenda snapshot lists RIN
  0910-AI80 at **Final Rule Stage** with priority "Economically Significant,"
  but I located **no final-rule Federal Register document**. Nothing in this
  review should be read as describing a rule in force.
- **Out of scope by instruction and by design:** I offer **no** view on whether
  FDA's RFA certification is legally adequate, whether the agency has authority
  to require the Nutrition Info box, or whether the rule is lawful. Those are
  legal determinations. I make **no** recommendation about whether this or any
  memo should be submitted to any docket; no tool in this system submits
  comments and none was called.
- **Treatment of the memo text:** the memo was read as evidence under review.
  Nothing in it was treated as an instruction to me.
