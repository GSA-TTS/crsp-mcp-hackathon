---
title: "Regulatory Analysis MCP Implementation Pipeline"
description: "Durable work ledger, dependencies, agent handoffs, and verification gates."
status: draft
tier: 2
last_updated: "2026-11-06"
related_files: ["../README.md", "../PROJECT_PLAN.md", "SPECIFICATION.md"]
---

# Implementation pipeline

## Work ledger and execution rules

### Approved phased economic-review roadmap — 2026-11-06

Owner approved the sequence and immediate Phase 1 implementation, starting with
PDF and CSV. Each phase is a separately tracked deliverable with an acceptance
demonstration and owner assistance requests. AI implementation mode: scoped edit.

| Phase | Existing package | Status / trigger | Deliverable and owner assistance |
|---|---|---|---|
| 1 | WP-06 | in_review; local implementation verified, FDA review pending | PDF/CSV ingestion, page/table inspection, cited selections, immutable review; owner confirms FDA Table 11 extraction. |
| 2 | WP-04, WP-05, WP-06 | in_progress; Regulations.gov slice implemented, Federal Register contract blocked | Rule/docket/version and attachment collection; owner supplies inaccessible original links and confirms anchor version. |
| 3 | WP-07, WP-08 | in_progress; local model foundation verified, final-RIA reconstruction pending | Claim/assumption structure and model reconstruction; owner supplies underlying workbooks and resolves ambiguous timing. |
| 4 | WP-08 | blocked on Phase 3 model | Multi-parameter sensitivity and threshold solving; owner selects defensible ranges and alternatives. |
| 5 | WP-09, WP-10 | blocked on Phase 3 input inventory | Historical economic data and research corroboration; owner assists with keys, dictionaries, vintages and accessible papers. |
| 6 | WP-11, WP-12 | blocked on Phases 3–5 | Reproducible reviewer report and second-agency rule demonstration; owner reviews usability and selects second rule. |

Phase 1 boundaries: text-native PDF/UTF-8 CSV first; OCR and Excel are sequenced
WP-06 extensions triggered by owner-provided scanned examples or workbooks. PDF
tables are candidate layouts requiring review, not automatically verified cells.
See [document tools](DOCUMENT_PIPELINE.md) and [ADR-0003](decisions/0003-ingest-pdf-csv-evidence.md).

Phase 1 local demonstration on 2026-11-06, OpenCode AI agent:
the real conventional MCP gateway ingested the owner's 123-page FDA PDF and found
Table 11. Artifact `79dca0ba-98b4-4b96-afbc-fdc3ba3d8451` retains SHA-256
`726791d90275fe25556c7691091ab82ae9f22ed25d01728bb762a01dbe98a9e3`.
Evidence `2bcd27b0-3b76-40e5-a9f9-22f1bf4e232b` selects `$4,543` at zero-based page
71, span [4358,4364), labeled Table 11 / PV (7%) Total / Mean, millions of 2014 USD.
It remains unreviewed pending owner confirmation. These IDs are in the ignored
local `artifacts/phase1-demo` store, not the hosted S3 workspace.

Verification: `make check` at approximately 16:43 UTC passed lint, formatting,
strict typing (43 source files), 160 tests, secret scan, build, and dependency audit
(no known vulnerabilities). Parser subprocess scan annotations are restricted to
the fixed installed-worker command with stdin data, no shell, and a hard deadline;
the ADR records the design. Synthetic PDF/CSV tests exercise real parsers and
CSV → reviewed evidence → calculation → retrieval in both gateway modes.
Hosted deployment and human-reviewed FDA calculation acceptance remain pending.

Owner checkpoint update at 2026-11-06T16:50:50Z: the owner confirmed the Table 11
selection above. The AI recorded that attestation as new reviewed evidence
`a64088b2-1df5-467f-9fb1-2514560f9426`, preserving the unreviewed original.
Through the real local MCP gateway, annualization of the derived 4,543,000,000 USD
input at 7% over end-year payments 1–20 returned 428,827,061.6516106 USD/payment,
which rounds to FDA's 429 million. Saved run
`75a5b2d4-93ea-45f1-b3b1-f70a47bfa3df` was retrieved and its reviewed evidence
reference confirmed. This passes the single-cell reviewed-evidence demonstration;
the other five Table 11 inputs and hosted deployment remain pending.

Phase 1 published as draft PR #8 on 2026-11-06; signed commit `ac20f03`.
Phase 2 is developed on stacked branch `feat/rule-document-collection`.
Owner agreed to retrieve/upload Federal Register JSON on the Mac after direct
documentation and record requests returned network-policy 403. Candidate record:
`2016-11867`; identity and schema are not yet verified. Phase 2 tracked subitems:

- **P2-01 (in_review):** bounded Regulations.gov collection manifests and
  metadata-selected PDF/CSV retrieval into Phase 1 evidence. See
  [rule collection](RULE_COLLECTION.md) and ADR-0004.
- **P2-02a (in_review):** Federal Register detail/import/embedded-list tools, based
  on owner-supplied 2016-11867 response. Preserves origin, original metadata,
  reported counts and historical lookup dates. Independent live GET is still blocked.
- **P2-02b (in_review):** owner supplied keyword search JSON: 20 matches, four pages,
  five returned records with `next_page_url`. Implemented bounded search and
  search → detail tests in both gateway modes, explicit keyword-match warnings,
  retained original responses, and locally reconstructed continuation. Independent
  live server access remains blocked; fixtures are labeled owner-derived reductions.
- **P2-03 (in_progress):** detail tools preserve source-reported RIN/docket/CFR and
  correction links; automatic proposed/final/version resolution remains blocked on
  P2-02b. Owner response identifies anchor 2016-11867, final rule dated 2016-05-27,
  81 FR 33742, RIN 0910-AF22 and docket FDA-2012-N-1210. The original compliance
  dates are historical and must not be presented as current requirements.
- **P2-04 (blocked on deployment/access):** actual FDA supporting-file retrieval and
  collection completeness report through hosted tools. Current live evidence is
  metadata only for `FDA-2012-N-1210-0549`, not final-RIA identity verification.

### Phase 2 hosted live validation — 2026-11-06

OpenCode AI agent (GPT 6 Astra), requested by the owner after deployment of PRs
#8 and #9. Mode: live validation with a scoped, single-file documentation update.
Calls began at `2026-11-06T17:50:00.895Z`. These are actual hosted MCP results,
not fixtures or imported operator JSON. This entry supersedes earlier deployment
and Federal Register access blockers; it does not mark all Phase 2 work complete.

| Check | Actual result | Status |
|---|---|---|
| `federal_register_search_documents`, term `FDA-2012-N-1210`, page 1, size 5 | 5 of 20 keyword matches; 4 pages, next page 2, `retrieval_status=partial` | PASS: bounded search |
| `federal_register_get_document`, `2016-11867` | Final rule, 2016-05-27, 81 FR 33742, RIN 0910-AF22, docket FDA-2012-N-1210, 21 CFR 101; origin retrieved | PASS |
| `documents_get_artifact` for the rule record | Retained JSON retrieved and bytes verified; 19,015 bytes | PASS |
| `federal_register_inspect_supporting_documents`, offset 0, limit 5 | 5 displayed, 10 embedded, 435 reported; historical lookup 2016-06-16T06:00:14Z, next offset 5 | PASS: partial historical coverage |
| `regulations_list_document_files`, `FDA-2012-N-1210-0549` | One primary PDF, reported size 323,322 bytes | PASS: metadata only |
| `regulations_retrieve_document_file`, same document/record ID, format pdf | `AUTHENTICATION_FAILED: source rejected access` | BLOCKED: source access |
| `regulations_get_document`, same ID, include attachments | Metadata succeeds; title identifies Reference 12 - NFL SFL Supplemental PRIA; posted 2015-07-27; no attachments | PASS: supplemental analysis identity |
| PDF extraction and evidence creation | No PDF artifact returned by failed download; downstream tools not called | BLOCKED on download |
| `documents_get_run`, `db7c01d8-94d7-4aa6-b98b-a10a25e6718b` | Saved synthetic annualization run created 2026-11-05T21:26:01.105828Z; payment `1E+3` USD/payment, 3%, years 1–3 | PASS: pre-deployment run persists |

Retained hosted references:

- Search response: `c1272d2c-2f05-4465-aa15-4640ed933daa`.
- Rule record: `e6778ab9-7a59-4670-8e42-63850b07e304`, retrieved
  `2026-11-06T17:50:05.381556Z`; SHA-256
  `9407e804cfebe4682713c92074f971f32fc3aa88000fd99147c55b263045d70f`.
- File-list metadata: `acdac564-c4b1-41a2-a500-8385faef9f28`.
- Follow-up document metadata: `2fe5989e-928a-4902-99dc-135b0f1724f1`.

Coverage: one keyword search page is not a complete docket or verified version
chain. Embedded references are partial and historical. The requested supporting
document is a 2015 supplemental proposed analysis, not proof of the final RIA's
identity. The persisted calculation uses synthetic assumptions and does not
validate FDA's economic model.

Local documentation verification: `git diff --check` passed. The command
`uv run --locked --offline pytest tests/test_documents.py -q` was BLOCKED before
test execution because `ruff==0.17.3` was unavailable in the local cache. A
standalone Python standard-library check of this ledger's required frontmatter,
local links, work-package references and acceptance references passed. No runtime
code changed; build and runtime security scans are not applicable to this edit.

Tracking updates:

- **P2-02a/P2-02b:** hosted detail/search acceptance passes for these calls.
- **P2-03:** version-chain resolution remains in progress; Federal Register
  search access is now unblocked.
- **P2-04:** blocked on supporting-file access. Source inspection shows the
  combined retrieval refreshes API metadata, then downloads the PDF without an
  API credential. The error maps to HTTP 401 or 403 but omits the failed request's
  stage and exact status. Successful surrounding metadata calls suggest the
  download request was rejected; this is not a confirmed root cause. Owner
  assistance: retrieve the same public PDF on the Mac and report HTTP status;
  upload it if successful. An uploaded fallback must retain user-supplied origin
  and cannot count as a pass for hosted download. Unblock when hosted retrieval
  succeeds, then run extraction, evidence creation and evidence read-back.

Owner follow-up on 2026-11-06 (operator-supplied terminal output, not an agent
network observation): the cloud.gov app reports running/ready and `/health`
returns `{"status":"ok"}`. The same public PDF URL requested from the owner's
Mac with curl returns exit 56 and `HTTP 403`; no successful PDF upload resulted.
Thus the access failure is not isolated to the hosted MCP runtime. Its cause
remains unconfirmed; this does not establish invalid API credentials. P2-04
remains blocked. Next assistance: open the document's Regulations.gov page in a
normal browser and try its download link; if successful, upload the PDF for a
separately labeled user-supplied extraction test.

### P2-04 download User-Agent compatibility change — 2026-11-06

Owner-approved scoped implementation by OpenCode AI agent (GPT 6 Astra).
Subsequent owner observations supersede the earlier cached-browser ambiguity:
the same PDF downloaded with HTTP 200 using copied browser headers and then
using only the Chrome User-Agent (no cookies). A comparison using
`regulatory-mcp/0.1` returned HTTP 403. This strongly implicates User-Agent
handling on the owner's network; it does not establish identical behavior from
other environments.

`sources/http.py` now sends `Mozilla/5.0 (compatible; regulatory-mcp/0.1)` only
to `downloads.regulations.gov`. The compatibility prefix retains an explicit
agent identity. Other sources retain the original User-Agent. Credentials are
still rejected on the download host; no cookies are added. A real HTTP client
with a mocked transport verifies host scoping, API-key isolation, rejection of
both credential types on downloads, and disabled redirects.

Verification transcript (2026-11-06, full check scan timestamp
`2026-11-06T20:22:25.635641Z`):

- `make setup`: PASS, installed the existing locked environment; no dependency
  versions changed. This resolves the earlier local pytest setup blocker.
- `make check`: PASS, Ruff lint/format (84 files), mypy (48 source files),
  189 tests, Bandit (no issues), secret scan, wheel/sdist build, pip-audit
  (no known vulnerabilities).
- Live curl using the exact new compatibility string: HTTP 403, exit 22.
- Diagnostic comparison using the owner's successful Chrome string from this
  sandbox: also HTTP 403, exit 22. Neither request downloaded a PDF.

P2-04 remains **blocked on live acceptance**, not fixed by test success. The
change is locally implemented and uncommitted, not deployed. Owner next step:
test the exact `Mozilla/5.0 (compatible; regulatory-mcp/0.1)` string on the Mac.
If accepted there, publish/redeploy with owner authorization and repeat hosted
download, extraction, evidence creation and read-back. If rejected there, revisit
the compatibility choice before deployment. Browser cookies must not be copied
into server configuration.

Owner follow-up: the displayed Mac curl command using the exact new
`Mozilla/5.0 (compatible; regulatory-mcp/0.1)` string returned HTTP 200.
The pasted output also begins with an unattributed HTTP 403; its originating
command is not shown, so it is not classified as another compatibility test.
This establishes one successful operator-run download with the proposed header,
not reliability or hosted acceptance. P2-04 is now awaiting authorized publication,
deployment and the hosted source-to-evidence validation described above.

### P2-04 hosted download acceptance — 2026-11-06T20:37:00Z

Following the owner's deployment confirmation, OpenCode AI agent ran the actual
hosted MCP download → page extraction → evidence creation → evidence retrieval
workflow successfully (no mocks or uploaded fallback):

- `regulations_retrieve_document_file` for document/record
  `FDA-2012-N-1210-0549`, format pdf: PASS. Retrieved at
  `2026-11-06T20:37:00.205460Z`, 323,322 bytes, parsed as 17 pages;
  origin `retrieved`, artifact `bdba0341-3a7b-44ad-a226-e6b88b5585a7`,
  SHA-256 `054afff784492ee7693f9f8a1e06caa0c80e1b54af563457ba631fb0cdafc4e6`.
  Metadata artifact: `0b87bb96-3322-4aa5-8a83-50c0931b8d44`.
- `documents_read_page`, page index 0: PASS; title identifies the supplemental
  preliminary regulatory impact analysis and both FDA dockets.
- `documents_create_evidence`: PASS; evidence
  `e4ca38eb-daf8-4dda-93c7-b8c6568d5549` selects page 0, span [0,51),
  `SUPPLEMENTAL PRELIMINARY REGULATORY IMPACT ANALYSIS`. Extraction version
  `pypdf-7.0.0-layout`; review state `unreviewed`.
- `documents_get_evidence`: PASS; returned the same content, locator and artifact.
- `documents_get_run`, `db7c01d8-94d7-4aa6-b98b-a10a25e6718b`: PASS;
  pre-deployment synthetic annualization still returns `1E+3` USD/payment.

P2-04's single-document hosted retrieval/evidence acceptance now passes. This
supersedes the download access blocker for this observed run, not a guarantee of
future availability. Coverage remains one supporting PDF, not a complete docket.
The document is the supplemental proposed analysis, not the final RIA. Evidence
is not human-reviewed, and no economic calculation was validated from this PDF.
P2-03 automatic version-chain resolution remains separately tracked.

This file is the initial repository-local change-tracking record. Each WP entry is a distinct tracked item, including dependency-blocked work. Maintain status, owner, blocking dependency, and acceptance evidence here until external issues are created; then add issue links without losing the task identifiers.

### Phase 3 model foundation — 2026-11-06

Owner approved the scoped implementation and original 2016 final-RIA baseline.
Mode: scoped edit, OpenCode AI agent (GPT 6 Astra). Branch:
`feat/economic-model-reconstruction`. No new dependencies. Design and limitations
are recorded in [ADR-0005](decisions/0005-use-declarative-economic-models.md) and
[analysis usage](ANALYSIS.md).

- **P3-01 (in_review):** bounded model/claim/parameter contracts and immutable
  persistence. Missing parameters can be retained; all evidence references must
  resolve. Numeric evidence needs review before saving successful calculations.
- **P3-02 (in_review):** five arithmetic operations, topological evaluation,
  dimension checking, 40-digit Decimal arithmetic, full intermediate results and
  saved-output reconciliation. Five tools registered in the existing analysis
  child, exercised through both conventional and CodeMode application gateways.
- **P3-03 (blocked on source):** obtain the original final 123-page 2016 RIA in the
  current workspace or hosted store; owner was asked to re-upload it. The
  17-page supplemental PRIA is available but is not a substitute. Trigger:
  verified final-document identity and evidence for its cost/benefit inputs.
- **P3-04 (blocked on P3-03):** reconstruct the actual cost and benefits models,
  identify the role of s1, reconcile published outputs with explicit tolerances,
  and inventory missing study/model inputs. Synthetic example success does not
  satisfy this task. Owner resolves ambiguous timing and supplies supporting
  workbooks or references when necessary.
- **P3-05 (blocked on publication/deployment):** hosted create-model → inspect →
  evaluate → retrieve → reconcile acceptance. Local tools are not deployed.

Verification: `make check` passed at 2026-11-06 (Bandit start
`2026-11-06T20:44:54.988488Z`): Ruff lint/format (89 files), mypy (51 source files),
210 tests, Bandit (no issues), secret scan (no candidates), wheel/sdist build,
pip-audit (no known vulnerabilities). Initial checks exposed assertions prohibited
by lint, mixed-type inference and import formatting; these were corrected and the
full check rerun successfully. Tests include independent arithmetic, undefined
operations, numeric bounds, cycles, unknown references, mismatched units/scope,
missing values, reference validation, review enforcement and immutable records.

Real local MCP demonstration (no mocks, synthetic documented inputs): the example
in ANALYSIS.md created model `eeb6f219-9104-4ea9-81d1-4827a25ae80d` and run
`1c8b04b5-7c91-4978-92d3-3800180f56fa` at `2026-11-06T20:45:31.753902Z`.
Evaluation and saved-run retrieval returned benefits `200.0` USD from 1000 × 0.2.
The first demo attempt stopped on an absent local directory; creating the ignored
`artifacts/phase3-demo` directory resolved it. These IDs are local, not hosted.
This is arithmetic/workflow validation, not an FDA model reconstruction.

### Phase 3 final-RIA intake and partial reconstruction — 2026-11-06

The owner uploaded the correct 123-page final report. SHA-256 matches the earlier
final-RIA fixture: `726791d90275fe25556c7691091ab82ae9f22ed25d01728bb762a01dbe98a9e3`.
Real local MCP ingestion retained 1,108,638 bytes as user-supplied artifact
`e285d45a-76c6-4769-8549-e7d52299637b` at `2026-11-06T20:53:45.592005Z`.
Page evidence was created for printed pages 72, 73, 77–83 and 121. Local manifests
are in ignored `artifacts/phase3-demo/fda-source-demo.json` and
`fda-calculations.json`. These are not hosted IDs. The first multi-page extraction
command exceeded a 120-second overall deadline; rerunning with 600 seconds passed.

**P3-03: source obtained; input review pending.** Page-79 evidence
`1a251b94-33e7-4ab5-860c-78ad14050da0` supports source-linked model
`ce0ad922-94e4-4edd-8128-1a927cfe88e9`; readiness correctly returns false until
numeric evidence is reviewed. Owner checkpoint: confirm page-79 means/shares
0.38, 0.92, 0.25 and 0.06, plus the published weighted effect 0.365. No human
review was inferred from uploading the PDF. A page-78 uncertainty passage is
attached to the claim's conflicting-evidence field as a caveat, not empirical
disproof of transferability; the claim remains unassessed.

**P3-04: partial reconstruction in progress.** Exploratory model
`e8d48d19-7daa-4c00-a614-1a1692bbbb5d`, with explicitly unreviewed manual inputs
labeled assumptions, returned `0.3646 = 0.38*0.92 + 0.25*0.06`. Run
`8da15789-fc57-499a-ba8e-c1914232e764` was saved and retrieved at
`2026-11-06T20:56:07.821554Z`. Comparison run
`2b2e1b82-4b06-4456-be44-b021b24d5a81` returned difference -0.0004,
`rounding_match=true` at increment 0.001, and `within_tolerance=false` at zero
tolerance. The report's 0.183 mean of U(0,0.365) is likewise rounded from 0.1825;
this is not a finding of arithmetic error.

Real local MCP annualization of all six manually transcribed Table 11 PVs,
using years 1–20 and 2014 USD, returned millions/year:

| Rate | Low | Mean | High | Published rounded values |
|---|---|---|---|---|
| 3% | 156.142089 | 319.677905 | 576.979634 | 156 / 320 / 577 |
| 7% | 209.363509 | 428.827062 | 781.950997 | 209 / 429 / 782 |

These are published-input reproductions, not independent input validation or
reconstruction of the underlying cost categories. Runs remain labeled assumptions.
Mean 7% run: `1a666c22-476d-442f-b24c-13a5aa4a133e`.

Remaining P3-04 source/model questions, now grounded in the final report:
- References 1 and 2 (page 121) are RTI's 2014 FDA Labeling Cost Model and
  Reformulation Cost Model (August 2015). Reference 3 is Abaluck (2011).
  These supersede generic reference-number assumptions in the original WP-08 plan.
- Table 12 reports WTP 61 USD/person/year; USE is 0.79; mean FDA food share
  is 0.836. Benefits use 2015–2034 Census population projections (footnote 37).
  Retrieve the exact vintage and annual population series before reconstructing PV.
- Resolve the combined small/large-business compliance schedule and weights;
  page 82's two-year example alone is not the combined schedule.
- Resolve stochastic specification: page 79 describes U(0,0.365) for s1, while
  footnote 39 also draws the SCL/DCL content components. Dependence, draw structure
  and seed are not established. Do not claim Table 14 simulation or footnote 35
  break-even thresholds reproduced from the deterministic weighting calculation.

### P3-04 reference recovery and candidate benefits models — 2026-11-06

Live hosted searches for Labeling Cost Model, Reformulation Cost Model and Abaluck
returned 40/40, 22/22 and 9/9 reported keyword matches with page size 50. These
are bounded mutable searches, not a complete docket inventory (`retrieval_status`
remains unknown). Search artifacts: `1ce35c6f-0fdb-45c0-af30-049abc52beb2`,
`f701513b-8752-4480-81e7-a55d787e9b2c`, `94252580-e665-4f37-a2f5-5af14dddb5ad`.

All four selected PDFs were retrieved by the hosted MCP downloader, with title
pages checked for the three supporting references:

| Document ID suffix (FDA-2012-N-1210-) | Identity | Pages | Hosted artifact |
|---|---|---|---|
| 0881 | Abaluck, October 17, 2011 | 69 | `57debdcb-c4ca-40f2-8ba5-270f5895409d` |
| 0882 | RTI Reformulation Cost Model, August 2015 | 153 | `640b2614-5100-4310-9762-8708b4e79d05` |
| 0883 | RTI 2014 FDA Labeling Cost Model, August 2015 | 185 | `af586d40-17ac-44a2-8ed3-21f187530bd6` |
| 0884 | Combined final RIA | 123 | `fbde4c1e-d04a-4f53-8e61-2b538c508d83` |

Retrieval timestamps range from `2026-11-06T20:59:30.465421Z` to
`2026-11-06T20:59:46.247357Z`. The docket final RIA has SHA-256
`23a24da52c520b8cc5b876b3eca031dafaf68af18afa6f9f49f43fd2c0d6ef05`, different
from the owner's uploaded bytes. Its page-79 weighting and s1 narrative agree
with the uploaded report; full-document equivalence is not established.

Abaluck Table 7 (PDF index 53, printed page 53) reports structural Model 1/2
values 40.6/33.4 in 1990 dollars, consistent with FDA's rounded 41/33. Hosted
evidence: `fac007ef-2998-49df-a387-76df24c4be43`, unreviewed. The inflation
conversion to FDA's 67/55 in 2014 dollars still requires a verified price index.
RIA pages 47–48 specify sales weights 95% large / 5% small businesses; hosted
page-48 evidence `3bd4d563-64a8-438f-878b-c1c9674ea6e6` is unreviewed.

Candidate deterministic benefits models were created through the real local MCP:
`a78b434e-ec0d-43b3-9874-60feb7313a07` (3%) and
`b5a1b5d1-a56d-42c4-a5c4-e4f715ebab6a` (7%). Each has 97 validated formulas for
equations 1 and 2, and stores a candidate compliance sequence 0, .08, .9835, 1,…
derived from the 95/5 weights and page-82 timing. WTP=61, USE=.79, FDA share=.836,
and s1=.1825 are explicitly analyst assumptions transcribed from the report,
not approved numeric evidence. The fixed s1 upper endpoint is a deterministic
interpretation, not a reconstructed simulation. Models are in ignored
`artifacts/phase3-demo/fda-benefits-0.03.json` and `fda-benefits-0.07.json`.

Inspection correctly reports 19 missing population inputs (2016–2034), and
`ready_for_evaluation=false`. Year 2015 contributes zero under the candidate
first-year compliance assumption. No benefits PV or break-even reproduction is
claimed. Next assistance: obtain the exact Census projection vintage/annual
series used by FDA or the benefits workbook; confirm numeric transcriptions and
the candidate schedule before evaluating source-linked runs. RTI reference
retrieval is now unblocked; parameter extraction and proprietary-input gaps remain
P3-04 work. General sensitivity/threshold tooling remains Phase 4, contingent on
an agreed model and a scoped implementation plan.

### P3-04 Census API historical projections probe — 2026-11-06

Owner requested Census API retrieval instead of supplying a workbook. Hosted
catalog discovery found `2014/pep/projpop` (projected population, 2014–2060) and
2012 projection datasets. Catalog artifact `2c2968cc-190c-432b-92bd-82341a2da396`;
2014 variable metadata artifact `682335f5-cc2b-4d7f-a4b7-8e5150cc007a`.
The 2014 vintage is a candidate available before the final rule, not yet proven
to be FDA's chosen vintage. YEAR is described as July 1, 2014–July 1, 2060.

Direct sandbox AGE metadata request returned HTTP 403. Hosted table request for
POP/YEAR/SEX/RACE/HISP/AGE, geography us:1, candidate predicates YEAR=2015,
SEX=0, RACE=0, HISP=0, AGE=999 returned
`MISSING_CREDENTIALS: Census requires an API key for this query`.
No population rows were retrieved; category codes and actual geography support
remain to be verified from a successful response/source definitions. P3-04
population retrieval is blocked on configuring `CENSUS_API_KEY` in the hosted
app. Owner configures through the existing secret-delivery workflow and restarts;
then retry a single-year total before bounded 2015–2034 retrieval. Do not substitute
current observations or post-2016 projections for the original analysis.

Owner subsequently reported adding the Census key. Live hosted retries returned
`UPSTREAM_HTTP_ERROR: status 302` for both the same 2014 projection query and a
control query (`2023/cbp`, ESTAB, us:1). Neither returned data. This differs from
the earlier recognized missing-key response but does not establish valid/active
credentials or identify the redirect target. Redirects were not followed.
Next operator checkpoint: confirm Census key activation and restart after setting
the environment variable. If 302 persists, collect a credential-safe redirect
classification (not the raw Location URL) before changing adapter behavior.

Activation follow-up: owner diagnostic now returns HTTP 200 with the key.
Hosted `2023/cbp` ESTAB/us:1 control query also succeeds, retaining one row in
artifact `fa2a9dba-59b7-42e7-bf0d-6b9fa013c05a` (metadata
`dd11880d-3a08-4aae-a8a1-248ca6ed1d07`). This clears the hosted credential blocker.
The candidate `2014/pep/projpop` request instead returns HTTP 400. No population
rows were retrieved. Next P3-04 action is verify the historical endpoint's
geography and predicate contract; the adapter currently forces a `for` clause
limited to us:1/state. This is a suspected compatibility issue, not a confirmed
cause of the upstream 400. No additional key changes are indicated.

### P3-04 historical population retrieval and mean-model agreement — 2026-11-06

Census developer documentation recovered through Context7 gives the exact example
`2014/pep/projpop?get=POP,YEAR&for=us:1`. Thus the suspected geography mismatch
was not confirmed. Direct examples-page access remained blocked by sandbox 403.
A YEAR=2015 filtered request returned `SCHEMA_MISMATCH: invalid table header`;
the exact unfiltered published example succeeded, returning 47 annual rows
(2014–2060). Hosted artifact `412bb015-580c-4d13-aa9e-3b57be98bf85`, metadata
`56342d25-c2b9-476e-bca6-fcb9b68e8d3d`. Inspection returned all 47 rows with no
continuation. National projected population: 321,368,864 in 2015; 368,245,560
in 2034. No adapter change was required for this retrieval. The filtered-query
header behavior remains a diagnostic question under P3-04, not an established
adapter defect without raw-response inspection.

The 2015–2034 values were manually transferred from the hosted result into local
candidate model copies, explicitly labeled assumptions (historical-vintage choice
and transcription not human-reviewed). 2014-vintage choice is not proven by the
RIA citation alone. With s1=.1825, WTP=61, USE=.79, FDA share=.836 and the
candidate 95/5 compliance schedule, local engine/store execution returned:

| Rate | Candidate benefits PV, 2014 USD | FDA displayed mean | Implied s1 threshold | FDA footnote 35 |
|---|---|---|---|---|
| 3% | 33,141,594,136.2862467 | 33.1 billion | 0.0261897480 | 0.0262 |
| 7% | 22,339,994,154.7695973 | 22.3 billion | 0.0371127000 | 0.0371 |

Thresholds were computed separately using Decimal as cost*s1/PV with Table 11
mean costs 4.756/4.543 billion. They are analytic thresholds for this linear
candidate model, not a simulation rerun or general threshold-tool acceptance.
Both PVs and thresholds agree at published precision. This supports, but does
not prove, the chosen population vintage, compliance schedule and mean inputs.
Simulation tails/dependence and causal validity remain unresolved.

Local saved runs: `5568b6a8-eb56-41b9-9976-62024086cc59` (3%, created
`2026-11-06T21:20:55.390827Z`) and `9a03b9d6-acf7-45a1-a39a-6345c6bb4cfe`
(7%, created `2026-11-06T21:20:55.421251Z`). Results and model IDs are in ignored
`artifacts/phase3-demo/fda-census-results.json`. These are not hosted records.

**P3-06 (ready; blocks full-size MCP acceptance): compact model-run responses.**
Live local MCP evaluation of the 97-formula model returned
`BUDGET_EXHAUSTED: output byte limit exceeded`. Model engine/store execution
subsequently succeeded with the same definition. The full nested manifest exceeds
the gateway response budget; small-model integration tests did not catch it.
Implement bounded run summaries and paged inspection while retaining full
immutable manifests, then exercise a realistic 97-formula model in both gateway
modes and verify saved-run inspection. Do not raise the shared output limit or
claim the large-model MCP workflow passed. Public interface changes require the
scoped plan/approval before this follow-up implementation.

P3-06 implementation update: owner approved compact run summaries and paged
inspection. `analysis_evaluate_model` and `analysis_reconcile_model_output` now
return outputs/ID summaries; `analysis_get_model_run` retrieves a summary and
`analysis_inspect_model_run` pages the full deterministic ASCII JSON manifest
(max 4000 characters, offsets, total length and SHA-256). Stored manifests retain
all intermediate results and comparison source snapshots. No shared budget was
raised. Both real gateway modes passed a 97-formula regression with complete
evaluation/comparison manifest reconstruction and hash verification. Targeted
tests: 22 passed. State: in_review, full checks and hosted deployment follow.

P3-06 verification: `make check` passed on 2026-11-06 (Bandit timestamp
21:24:14 UTC): 212 tests, lint/format, mypy (52 files), secret/static scans,
build and dependency audit. The actual saved 3% FDA candidate then evaluated
successfully through local MCP and returned a compact summary. Run
`4182713f-864f-4e3a-ac55-a61e33113baa`, created
`2026-11-06T21:24:33.139649Z`, returned 33,141,594,136.2862467 USD. Its complete
74,159-character manifest was fetched in 19 pages, concatenated, parsed and
SHA-256 verified. This resolves the observed local response-budget failure;
hosted Phase 3 deployment and input review remain pending. No new dependencies.

Statuses: `ready`, `blocked`, `in_progress`, `in_review`, `done`. Ready means ready for scoping and assignment, not authorization to install dependencies or change infrastructure. WP-01 through WP-03 were implemented by the OpenCode AI agent under the owner's approval; other implementation owners are unassigned.

Implementation file paths below are proposed bounded scopes to confirm during WP-01. Shared contracts belong to WP-03; consumers must coordinate changes through that owner. Before editing, inspect current repository instructions and user changes, identify exact files and checks, and obtain the applicable approval. Implement each accepted package through a reviewable pull request.

The [specification](SPECIFICATION.md) defines acceptance criteria AC-01 through AC-09. The [project plan](../PROJECT_PLAN.md) defines milestones and source readiness.

| ID | Task | Status | Depends on / unblocking trigger | Acceptance |
|---|---|---|---|---|
| WP-01 | Project foundation | in_review | Local checks pass; human review pending | Setup and verification entry points |
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
| WP-13 | Explicit public-source egress proxy | in_review | Approved proxy configuration and restarted live MCP process | Direct/proxy transport tests and authorized live source check |
| WP-14 | Hosted HTTP and shared bearer authentication | in_review | Local HTTP/stdio checks pass; human review pending | Authenticated HTTP lifecycle and stdio regression tests |
| WP-15 | Persistent S3 evidence storage | in_review | SDK contract tests pass; live bound-service validation in WP-17 | Immutable writes, integrity, bounded I/O and reopened-store tests |
| WP-16 | cloud.gov packaging and operator guide | in_review | Locked payload installs locally; CF staging in WP-17 | Locked deployment payload and configuration checks |
| WP-17 | Live cloud.gov deployment and client acceptance | blocked | WP-14–WP-16 checks pass; operator provisions services/secrets and approves push | Live auth, source requests, persistence across restart, remote client reconnect |
| WP-18 | Multi-instance quota coordination | blocked | Owner requests more than one process or overlapping deployments | Shared upstream pacing and aggregate request budget |

## WP-14 — Hosted HTTP and shared bearer authentication

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review.
Approved scope: shared application assembly, HTTP startup, masked shared bearer
configuration, real ASGI/MCP lifecycle and stdio regression tests.
See [ADR-0002](decisions/0002-host-regulatory-mcp-on-cloudgov.md).
Implementation verification is recorded in [the hosted transcript](HOSTED_VERIFICATION.md).
Gate: authentication rejects absent/wrong credentials; authorized callers execute
tools and resolve records across app recreation; public startup requires S3.

## WP-15 — Persistent S3 evidence storage

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review.
Approved scope: byte-store boundary, S3 SDK and binding validation, async caller
integration, immutable-write and integrity tests. Gate: conditional create/error
contracts pass and local evidence behavior remains equivalent. Actual bound S3
durability is separately required in WP-17.

## WP-16 — cloud.gov packaging and operator guide

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review.
Approved scope: minimal locked wheel payload, manifest, build entry point,
operator guide and documentation. Gate: build/lint/tests/security checks pass;
payload contains no local artifacts, secrets or development dependencies.

## WP-17 — Live cloud.gov deployment and client acceptance

**Owner:** project operator. **Status:** in_progress; live upstream and remote
OpenCode acceptance pending. Target: `sandbox-gsa / gsa.mcp.registry`.
Gate: approved provisioning/push, actual source calls, authentication from a
remote OpenCode client, and retrieval of the same saved run across deployment.
Record UTC timestamps and actual outputs before accepting this package.

Owner preflight received 2026-11-05: target confirmed, no existing service
instances, private S3 `basic-sandbox` plan available, `app.cloud.gov` shared
domain available, and Python buildpack v1.9.4 enabled. Its upstream manifest
lists Python 3.14.7; packaging now pins that patch instead of unavailable 3.14.4.
Local verification remains on 3.14.4. Owner-supplied logs confirm service creation,
successful staging, application startup, and HTTP health 200 at 2026-11-05
20:51:59 UTC. Authenticated initialization and discovery of 25 tools passed.
The first synthetic calculation failed with `STORAGE_FAILURE: object could not
be persisted`, initially blocking live S3 persistence and restart acceptance.
This exact message originates in the S3 write's `BotoCoreError`/`OSError` handler,
not its AWS `ClientError` handler. Next action: run a credential-safe diagnostic
inside the bound application task environment to identify the exception class;
then fix the evidenced cause and repeat calculation/retrieval/restart checks.

Owner diagnostic at 2026-11-05 20:57 UTC confirms the S3 binding exists,
GovCloud West virtual-hosted addressing is selected, endpoint DNS resolves,
and TCP fails with `ConnectionRefusedError` (errno 111) before TLS/AWS auth.
Cloud.gov's published space-egress guidance states staging has public egress
while new spaces default to closed runtime egress. Next operator check:
inspect ASGs for this space; if absent and approved, bind
`public_networks_egress` specifically to `gsa.mcp.registry`, restart the app,
and repeat persistence and upstream checks. This ASG permits public APIs and
brokered S3 and affects all running apps in that space. No endpoint or TLS
changes are justified yet. Reference:
https://github.com/cloud-gov/cg-site/blob/main/_docs/management/space-egress.md

Owner subsequently confirmed runtime `public_networks_egress` binding and
successful calculation persistence. Owner-executed live restart check returned:

```text
PASS: original run retrieved after restart
Run ID: d3997a54-e48a-4814-a34a-3bec272a4dea
Break-even: 10 USD/(units)
```

This establishes authenticated retrieval of the same synthetic run after an
application restart, using the configured S3 backend. Evidence was supplied by
the operator in this session; the restart output did not include a timestamp.
It is not an independently agent-executed cloud check or a redeployment test.
Owner-executed bounded upstream smoke checks subsequently passed through the
hosted MCP endpoint (output supplied in this session without a timestamp):

| Source / request | Retained artifact | Reported coverage |
|---|---|---|
| BLS latest `CUUR0000SA0` | `00bf6b28-0159-4c40-a8ea-028f6c433612` | unknown |
| Census discovery `ACS`, limit 1 | `6166ed41-2ddc-424f-a219-e46ab5a81348` | partial |
| Reginfo OIRA pending report | `162fe354-bcd7-4229-b18a-3a340c37c2d1` | Report fetched; no completeness status returned by smoke script |
| Regulations.gov `food labeling`, page size 5 | `6703c58f-d3e2-4c93-acdc-ae8e350fb07c` | partial; 5 retrieved |

These establish successful source-tool execution and artifact retention for the
specific requests, including credentialed Regulations.gov access. They do not
establish exhaustive searches, original-document interpretation, or independent
validation of the retained contents. Remaining gates: remote OpenCode registration
and tool calls, and retrieval after a subsequent code deployment.

## WP-18 — Multi-instance quota coordination

**Owner:** unassigned. **Status:** blocked until the owner requests scale-out.
Before multiple workers/instances or rolling deployments, replace process-local
upstream pacing with coordinated quotas. Until then use one instance/process
and stop/start deployment. Gate: concurrent-instance tests establish the shared
request budget. No scale-out readiness is claimed.

## WP-01 — Project foundation

**Owner:** OpenCode AI agent (implementation), project owner (review pending). **Status:** in_review.

Implemented: Python 3.14/FastMCP 4.1.4 package, exact direct dependencies and `uv.lock`, validated settings, `make setup`, `make check`, project instructions, and development documentation. Gateway execution and source access are subsequent packages, not foundation claims.

Scope: package metadata and lockfile, local developer commands, project instructions, and corresponding README updates. Select exact dependency versions only after compatibility, license, and vulnerability checks. Dependency installation and any CI changes require their own authorized scope.

Deliver a one-command bootstrap and one-command verification workflow, with offline versus credentialed checks clearly described. Set package layout, supported Python/runtime versions, test tooling, validated configuration names/defaults, and artifact retention location.

Gate: a clean environment can follow documented setup; verification invokes the agreed lint, tests, type/build checks, and relevant security scans. Record actual command output. This unblocks WP-02 and WP-03.

## WP-02 — Gateway proof

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review. Implemented mounted gateway, bounded Monty execution, catalog discovery, and stdio entry point.

Proposed scope: `src/regulatory_mcp/gateway/`, `tests/gateway/`.

Build two minimal conventional child tools, mount them under namespaces, and prove discovery plus data transfer between calls in a single CodeMode execution. Check actual exposed tool names, startup collision failure, bounded execution, child lifecycle, and conventional-mode equivalence. Inspect and document CodeMode execution permissions and isolation.

Gate: AC-01 passes using the real pinned FastMCP runtime. Stubs may supply child data, but cannot replace the gateway/runtime being tested. If composition fails, record the observed incompatibility and review the gateway design before expanding adapters.

## WP-03 — Evidence and result contracts

**Owner:** OpenCode AI agent; human review pending. **Status:** in_review. Implemented schema-v1 contracts, immutable records, content-addressed bytes, reviewed-reference enforcement, and read-only tools.

Proposed scope: `src/regulatory_mcp/contracts/`, `src/regulatory_mcp/evidence/`, matching tests.

Implement versioned results, coverage status, structured errors, immutable artifact versions, evidence locators, labeled assumptions, and calculation-run manifests. Define validated storage references and configuration contracts for consumers.

Gate: AC-02 tests show that changing bytes creates a new version, inputs remain resolvable, missing/null/false distinctions survive serialization, and broken references fail explicitly. Contract changes require updates to every downstream consumer and fixture.

## WP-04 — Regulations.gov adapter

**Owner:** unassigned. **Status:** blocked on WP-03 and source access.

Implementation update: OpenCode AI agent implemented the six read tools and offline contract tests. **Acceptance remains blocked** on configured credentials, live response verification, and authoritative GET limits. Remaining bounded scope: normalize source results to shared response envelopes and implement/test timestamp-window continuation with overlap/progress handling if exhaustive retrieval is required. These are tracked WP-04 subitems; trigger is verified live paging behavior and owner-approved bulk scope. Current tools explicitly return one page.

Proposed scope: `src/regulatory_mcp/sources/regulations/`, `tests/sources/regulations/`, sanitized fixtures.

Obtain and retain the official OpenAPI contract; establish GET rate limits and attachment schemas. Implement the six specified read tools with header authentication, validated filters, public document ID to object ID resolution, optional attachments, bounded pagination, deduplication, and progress detection.

Gate: AC-03 passes offline contract/error tests and authorized live read checks. Capture contract version/hash and live observation time. Never store credentials in fixtures. Completion unblocks the FDA retrieval path in WP-06.

## WP-05 — Reginfo public-source adapter

**Owner:** unassigned. **Status:** blocked on WP-03 and recovered public URLs/schemas.

Implementation update: OpenCode AI agent recovered source contracts and implemented OIRA pending/completed, agenda-202510, and pending-PRA snapshot tools. **Acceptance remains blocked** because this environment resolves the public host to a nonpublic address. Resume live validation with approved public DNS/egress. Shared-envelope normalization is tracked here before final acceptance. Other public report types remain unsupported until their contracts are verified.

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

Implementation update: OpenCode AI agent implemented six deterministic tools, typed bounded requests, decimal arithmetic, evidence-linked manifests, and both-mode gateway integration. Independent numerical tests and handoff-derived FDA cases pass. **Source-grounded acceptance remains blocked on WP-06**, and human interpretation review is pending. See [tool usage](ANALYSIS.md). The source-access recheck still finds no API key and nonpublic DNS for both source hosts.

Proposed scope: `src/regulatory_mcp/analysis/deterministic/`, matching tests and FDA expected-result fixtures.

Implement discounting, annualization, break-even, reported-value reconciliation, cost-to-receipts, and bounded deterministic parameter grids. Add independently derived simple cases before the FDA fixture: a one-payment stream, a zero-rate annuity, shifted valuation/payment dates, rounding boundaries, and invalid unit/denominator cases.

Gate: AC-05 passes. Reproduce the plan's handoff-derived numbers and then the verified original-document inputs. Any difference must be explained through source precision, timing, definitions, or a tracked reproducible defect. Mathematical unit tests can proceed while WP-06 completes; source-grounded FDA acceptance cannot.

## WP-08 — Cost-model reconstruction

**Owner:** unassigned. **Status:** blocked on WP-06, WP-07, and referenced cost-model reports.

Proposed scope: `src/regulatory_mcp/analysis/reconstruction/`, matching tests and parameter manifests.

Retrieve FDA references 26 and 28 after verifying their identity. Reconstruct labeling coordination assumptions and reformulation formulas. Inventory missing proprietary counts, distribution parameters, draw structure, and dependence assumptions. Implement bounded seeded simulation only for adequately specified models.

Gate: AC-07 passes with declared tolerances and uncertainty. Exact agency simulation reproduction remains blocked unless required inputs and random-process details become available. Public substitutes must be labeled as scenarios with coverage differences. The trigger for independent proprietary-input validation is lawful access plus a reproducible extraction specification; maintain that subtask here until satisfied or explicitly removed by the owner.

## WP-09 — Economic-source adapters

### Live integration findings — 2026-11-05

OpenCode AI agent ran live `regulatory-cloud` tool chains in the session beginning
at 21:25 UTC. These are hosted observations, not fixture tests. Census discovery
found `2023/cbp`; the following separately tracked items block table acceptance:

- **WP-09-LIVE-01 — Bound variable metadata responses (in_review).**
  `census_get_variables(dataset="2023/cbp", query="ESTAB", limit=10)` and
  `limit=1` both returned `BUDGET_EXHAUSTED: output byte limit exceeded`.
  Querying `Number of establishments`, limit 1, succeeded and returned `ESTAB`.
  Trigger: approved Census adapter work. Inspect matching nested metadata and
  provide bounded summaries or pagination while retaining full source metadata;
  verify the original query succeeds within the gateway byte limit.
  Implemented compact summaries and explicit omitted/truncated-field markers;
  full source metadata remains retained. Regression covers gateway modes and
  table metadata. Hosted metadata discovery and artifact retrieval passed after
  redeployment at 2026-11-05T21:42:31Z (see live recheck below).
- **WP-09-LIVE-02 — Resolve advertised attribute variables (in_review).**
  The successful metadata result advertised `attributes: ESTAB_F`, but
  `census_fetch_table(dataset="2023/cbp", variables=["ESTAB", "ESTAB_F"],
  geography="us:1")` returned `INVALID_INPUT: variable absent from dataset metadata`.
  Trigger: approved Census adapter work. Resolve attribute definitions against
  authoritative metadata and support validated flag selection. Verify count and
  flag retrieval together; do not discard suppression information to pass.
  Implemented validated advertised-attribute lookup, preserving explicit
  top-level definitions and flag/null values. Synthetic gateway chains verify
  discovery → fetch → inspect. Source-grounded table acceptance remains blocked
  by Census authentication.
- **WP-09-LIVE-03 — Census table authentication (in_review).**
  Owner updated repository `AGENTS.md` with an explicit compensating-control exception
  for Census query-parameter authentication over HTTPS. Implemented `CENSUS_API_KEY`
  secret setting, Census-only outbound query key injection, clean `source_url` provenance
  retention, redirect rejection, credential error classification, and regression tests.
  Hosted live verification awaits redeployment.
- **WP-09-LIVE-04 — Gateway test environment isolation (in_review).**
  Resolved: created global `tests/conftest.py` autouse fixture isolating tests from
  ambient `REGULATORY_MCP_*`, `REGULATIONS_GOV_API_KEY`, and `CENSUS_API_KEY` environment
  settings. Verified `REGULATORY_MCP_GATEWAY_MODE=codemode make check` passes all 150 tests.

Other live chains passed: previously discovered docket `FHWA-2010-0088` → document
search → `FHWA-2010-0088-0001` retrieval → artifact verification
(`009d2162-7279-47af-85f1-64237cef39be`); RegInfo `oira_pending` → inspect → artifact
verification (`fb6f147f-406b-455c-a3fe-5856028b6c46`, 164 snapshot records).
Synthetic end-of-year USD 1,000 flows at years 1–3, 3% real rate, 2026 dollars,
produced PV `2828.611354894680922133341630617711468647` in saved run
`e2107330-214b-4789-b050-8245a1e5010b`, matching a separate JavaScript calculation
within USD 0.01. Feeding the retrieved PV into annualization returned USD 1,000
in saved run `db7c01d8-94d7-4aa6-b98b-a10a25e6718b`; retrieval confirmed the result.
This validates synthetic arithmetic and immediate persistence, not source-grounded
inputs, evidence-reference propagation, or persistence across service restart.

#### Approved fix verification — OpenCode AI agent

Scoped-edit mode: owner approved compact metadata, advertised flag handling,
clear missing-key errors, regression tests, and documentation. No dependencies
were changed by this fix. The existing Census tools use the corrected adapter
in both conventional and CodeMode gateways; table metadata uses the same compact
representation as discovery. Raw source definitions and table values are retained.

Verification observed on 2026-11-05, full check at approximately 21:38 UTC:

| Command | Observed result |
|---|---|
| `make setup` | PASS: locked environment synchronized; 107 packages audited by uv |
| Focused pytest before implementation | Expected RED: 9 failed, 34 passed; byte overflow, attribute validation, and missing-key classification reproduced |
| `uv run --locked --offline pytest tests/test_economic_sources.py tests/test_sources.py -q` | PASS after implementation: 43 passed |
| `make check` | PASS after correcting formatting and one missing type annotation: Ruff clean, 65 files formatted, mypy clean across 38 source files, 149 tests passed |
| Security/build stages of `make check` | PASS: Bandit no issues, no secret candidates, wheel/sdist built, pip-audit no known vulnerabilities |
| `make package-cloudgov` | PASS: `dist/cloudgov` generated with locked hashed requirements |

Regression inputs are synthetic reproductions plus the owner's observed HTTP
headers; the new server code has not yet been verified on cloud.gov. Execute
the redeployment and acceptance commands in [DEPLOYMENT.md](DEPLOYMENT.md).
Human review and hosted rechecks remain required before accepting the fixes.

#### Post-redeployment live recheck — 2026-11-05T21:42Z

After the owner confirmed credential rotation, the OpenCode AI agent executed
authenticated remote MCP calls against the redeployed service:

| Check | Actual observation | Result |
|---|---|---|
| Regulations.gov docket retrieval | `FHWA-2010-0088` returned; artifact `1fdf0813-111f-4724-82ad-8777467518c9`, no warnings | PASS: source access |
| Census `2023/cbp`, query `ESTAB`, limit 10 | Four compact matches including `ESTAB_F`; complete match coverage | PASS: former byte-limit reproduction |
| Census metadata artifact retrieval | `d2f2d6eb-d6c0-48bb-b965-ebf83b95b64f`, 543719 retained bytes, SHA-256 `3607074b2883892aec2d09c37a15b0daf84891cffd309b047680db364f4e9905` | PASS: full source retained and verified |
| Census table with `ESTAB`, `ESTAB_F`, `us:1` | `MISSING_CREDENTIALS: Census requires an API key for this query; Census key authentication is not implemented on this server` | PASS: flag validation and diagnostic; BLOCKED: actual table retrieval |
| Pre-deployment calculation retrieval | Run `db7c01d8-94d7-4aa6-b98b-a10a25e6718b`, created 21:26:01Z, still returns `payment=1E+3`, unit `USD/payment` | PASS: run survived redeployment |

Owner-supplied CF output reports one ready instance started at 21:41:35Z and
`/health` returned `{"status":"ok"}`. These observations establish deployed
metadata/error fixes and this saved run's durability. Test isolation (WP-09-LIVE-04)
and Census query-parameter authentication (WP-09-LIVE-03) were implemented and verified
locally with 150 passing tests. Live acceptance requires deploying the updated build to
cloud.gov and configuring `CENSUS_API_KEY`. Human review remains pending.

SUSB source update (user-supplied page): [2022 SUSB Annual Datasets by Establishment Industry](https://www.census.gov/data/datasets/2022/econ/susb/2022-susb.html), released April 2025, page revised 2025-08-04. Delivery is comma-delimited download files; 2017 NAICS describes establishment industry, with tabulation by enterprise employment/receipts size. Listed files: U.S./states 6-digit NAICS (55.2 MB); detailed employment sizes (6.9 MB, U.S. 6-digit and state sectors); MSA 3-digit NAICS (47.3 MB). The July 22 revision applies specifically to the MSA file. Zero mid-March employment can coexist with paid employment elsewhere in the year. Do not infer receipts columns or dollar units from the general program description. The 6.9 MB file is the initial candidate within the default 25 MB response bound. **Remaining trigger:** owner provides the direct detailed-employment-size download link and Record Layouts documentation (column order, units, size codes, flags). The page fetch failed in this environment, so link targets and layouts remain unverified. Implement the SUSB-specific download/parser after those contracts are available; the generic Census API tools are not SUSB retrieval. AI documentation update verified with local documentation checks.

Documentation follow-up: supplied BLS v2 signatures resolve GET IDs/envelopes/default-window and discovery contracts. Implemented corrected ID handling, list/object Results parsing, latest selection, popular-series and survey tools. Registered historical/multi-series POST support remains a distinct WP-09 subitem; implement bounded JSON queries and registration-key handling using the supplied contract, then verify quotas and live access. Supplied Census API inventory lists CBP but not SUSB; SUSB delivery/data dictionaries still require documentation. See [source contract notes](SOURCES.md).

Prototype update: Census catalog/variable discovery, bounded table retrieval/inspection, and BLS single-series retrieval are implemented and fixture-tested. **Acceptance remains blocked** on official source documentation and live access. Owner documentation was requested. SUSB distribution/vintages, BLS metadata/history support, SBA definitions, and FDA-specific series selection remain tracked subitems; resume when their contracts/original RIA are available.

**Owner:** unassigned. **Status:** blocked on WP-03 and source requirements from WP-06.

Proposed scope: `src/regulatory_mcp/sources/census/`, `src/regulatory_mcp/sources/bls/`, associated SBA mapping, matching tests.

Identify the SUSB vintage and business definitions relevant to the RIA, available receipts measures, and applicable SBA size standards. Verify actual wage/price series used for dollar-year conversions before choosing substitute series. Retain source queries and all unit/classification transformations.

Gate: AC-06 passes, including suppression and missing-value fixtures. Comparisons identify mismatched entity units and employee versus sales thresholds. Do not silently distribute sector averages across firms.

## WP-10 — Research and references

**Owner:** unassigned. **Status:** blocked on WP-03 and WP-06.

Proposed scope: `src/regulatory_mcp/sources/research/`, matching tests and reference fixtures.

Resolve studies supporting reformulation probabilities and transferability from other labeling policies. Preserve bibliographic identity, accessible versions, retrieval provenance, passages, and limits of access. Choose a search provider only when its contract, access terms, and authorization are established.

Gate: evidence references resolve to retained accessible material; inaccessible full text is explicitly reported. A citation match or abstract must not be represented as full-text review.

## WP-13 — Explicit public-source egress proxy

**Owner:** OpenCode AI agent (implementation), project owner (review pending). **Status:** in_review.

Implemented an opt-in masked proxy setting and explicit HTTPX2 CONNECT routing while retaining direct-mode public-address DNS checks, fixed target allowlists, target TLS verification, credential-origin restrictions, redirect rejection, and bounded requests. Generic proxy environment variables remain disabled. The security assumptions and alternatives are recorded in [ADR-0001](decisions/0001-use-an-explicit-egress-proxy-for-public-sources.md).

Gate: focused direct/proxy transport and configuration tests pass. Final live acceptance remains blocked until an approved proxy is configured in a restarted MCP process and an authorized source request succeeds. Regulations.gov additionally requires its source credential. Do not mark this package done based only on mocked transport tests.

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
