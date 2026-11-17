---
title: "Evaluation Run 2026-11-17"
description: "Frozen case definitions, answer keys, and reports for one execution of the Regulatory MCP evaluation suite."
status: draft
tier: 2
last_updated: "2026-11-17"
related_files: ["CORRECTIONS.md", "../README.md", "../rule-discovery.md", "../comment-drafting.md", "../commenting-ui.md", "../reviewer-analysis.md"]
---

# Evaluation run 2026-11-17

This directory holds one execution of the suite described in [`../README.md`](../README.md).

## Case freeze

| Field | Value |
| --- | --- |
| Run identifier | `RUN-2026-11-17-A` |
| Run start (UTC) | 2026-11-17T20:15:40Z |
| Run end (UTC) | 2026-11-17T20:57:00Z |
| System revision | git `58fc63cc49c127ba2b14c0055b73b0a526400bd5`, working tree dirty (`README.md`, `docs/IMPLEMENTATION_PIPELINE.md` modified; `crsp-mcp-journal/`, `evals/` untracked) |
| Provenance correction | See [`CORRECTIONS.md`](CORRECTIONS.md) — this hash identifies the harness checkout, **not** the evaluated build; the evaluated system was the deployed `crsp-regulations` HTTP endpoint. |
| Analysis code revision reported by the server | `sha256:29b50f8979785c5525205f6e3d7d61efe2415e25370f8680c9a0c2803aa20d55` |
| Gateway mode | `conventional` (config default in `src/regulatory_mcp/config.py`; CodeMode **not** exercised) |
| Transport / host | goose session, MCP extension name `crsp-regulations`, tools surfaced as `crsp-regulations__<namespace>_<tool>` |
| Tool catalog observed | 37 tools: `regulations` (9), `reginfo` (2), `documents` (8), `analysis` (10), `census` (4), `bls` (3), `federal_register` (4), plus `catalog` |
| Resources published by the extension | **none** (`list_resources` on `crsp-regulations` returns empty, although the extension is surfaced as resource-capable) |
| Namespaces not exercised | `research` (no tools observed in this session) |
| Evidence level | **live-source** for Federal Register, Regulations.gov, Reginfo, BLS, Census catalog; **model_reconstruction** for every `analysis` run (server-reported `verification_level`) |
| Human adjudicator | **none** — no human has reviewed any case, key, or score |
| Pass threshold | Suite default from `../README.md` §5 as interpreted here: every critical gate passes, every applicable dimension >= 3, mean applicable score >= 3.0. Recorded before scoring; not changed during the run. |

## Integrity statement

1. All scores in this directory are **agent self-assessment**. The suite protocol requires a human
   adjudicator to resolve ambiguity and to confirm fidelity findings. Every result is therefore
   marked **provisional**.
2. The EVAL-02 commenter brief and the EVAL-04 commenter analysis package are **synthetic and
   agent-authored**, labeled as such in their case files. Because the same agent authored the
   EVAL-04 seeded defects and then reviewed them, EVAL-04 detection rates are **not** an
   independent measurement; this is recorded as the primary limitation of that case.
3. `documents_record_review` calls in this run are **caller attestation by the agent**, not human
   review. Review notes say so explicitly.
4. No comment-submission tool exists in the catalog and none was called. No draft in this
   directory has been submitted to any agency.

## Contents

```
cases/    frozen case definitions (inputs given to the system under test)
keys/     answer / adjudication keys (withheld from the system during execution)
artifacts/    the deliverables actually produced and scored (draft comment, review output)
reports/  per-case reports using the suite reporting template, plus the suite summary
transcripts/  privacy-minimized record of tool calls and identifiers
CORRECTIONS.md  post-scoring corrections to system-identity and catalog metadata
```

## Results at a glance (provisional)

| Case | Result | Mean applicable score | Note |
| --- | --- | --- | --- |
| EVAL-01 rule discovery | **FAIL (provisional)** | 3.17 | No fabrication, but a zero-result query returns an opaque `SCHEMA_MISMATCH` error and one near-miss-heavy query missed the gold rule entirely. Coverage/recall scored 2, below the per-dimension floor. |
| EVAL-02 comment drafting | **PASS (provisional)** | 3.71 | Local labeled draft, claim-by-claim grounding, no submission path. Requires human fidelity review. |
| EVAL-03 commenting UI | **BLOCKED** | not scored | No `ui://` resource, no MCP Apps tool, no mount of the Node prototype in the Python gateway. The host *is* MCP Apps-capable in this session, so the gap is server-side. Six rubric dimensions marked not-scored rather than numbered. |
| EVAL-04 reviewer analysis | **PASS (provisional, non-independent)** | 3.83 | 10/10 scored defects detected, 0 false positives — but the memo, the key, and the review were authored by the same agent. Read the detection rate as an upper bound, not a capability measurement. |

Suite summary: [`reports/suite-summary.report.md`](reports/suite-summary.report.md).
