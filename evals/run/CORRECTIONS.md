---
title: "Evaluation run RUN-2026-11-17-A — provenance corrections"
description: "Corrections to system-identity and tool-catalog metadata recorded during the run."
status: draft
tier: 2
last_updated: "2026-11-17"
related_files: ["README.md", "reports/suite-summary.report.md"]
---

# Provenance corrections for RUN-2026-11-17-A

These corrections were made at 2026-11-17T22:04Z, after scoring and before the
run was committed to version control. **No score, finding, defect, case, answer
key, or result was changed.** Only statements about the identity of the system
under evaluation and the size of its tool catalog are corrected here.

The corrections were made by the same agent that executed and self-scored the
run. They have not been reviewed by a human.

## C-1 — The system under evaluation was the deployed server, not this working tree

**As recorded during the run.** Every report, the run README, and the EVAL-03
transcript carry a line of the form:

> System revision | git `58fc63cc49c127ba2b14c0055b73b0a526400bd5`, working tree dirty

**Why that is wrong.** That hash identifies the local checkout the agent was
sitting in, not the process that answered the tool calls. The registered MCP
extension `crsp-regulations` was configured in the host as a
`streamable_http` endpoint pointing at a remotely deployed instance of this
project (`https://crsp-regulatory-mcp.app.cloud.gov/mcp`, shared bearer token
held in host configuration and deliberately not reproduced here). The local
working tree at `58fc63cc` does **not** contain the `federal_register`,
`documents`, or `analysis` source modules that the run exercised, so it cannot
be the build that served those calls.

**Corrected statement.** The system under evaluation is the deployed
`crsp-regulations` HTTP server reached at
`https://crsp-regulatory-mcp.app.cloud.gov/mcp` during the window
2026-11-17T20:15:40Z – 20:57:00Z. Its exact source revision was **not
determined**; the server does not report one. The only build identifier the
server emitted is the analysis code digest
`sha256:29b50f8979785c5525205f6e3d7d61efe2415e25370f8680c9a0c2803aa20d55`,
which appears in `analysis` run manifests and covers the analysis module only.
`58fc63cc` should be read as the revision of the *harness checkout*, which is
not under evaluation.

**Consequence for reproducibility.** This run is not reproducible against a
pinned source revision. Re-running it requires either the same deployed
endpoint in the same state or a named server revision, which a future run
should capture explicitly. Treat the recorded results as bound to a deployment,
not to a commit.

## C-2 — The 37-tool catalog figure is not stable

**As recorded during the run.** `catalog` was enumerated once before the case
freeze and reported as 37 tools: `regulations` 9, `reginfo` 2, `documents` 8,
`analysis` 10, `census` 4, `bls` 3, `federal_register` 4, plus `catalog`.

**Re-enumeration at 2026-11-17T22:04Z** against the same endpoint returned 44
namespaced tools plus `catalog`:

| Namespace | Recorded during run | Re-enumerated 22:04Z |
| --- | --- | --- |
| `documents` | 8 | 9 |
| `analysis` | 10 | 13 |
| `regulations` | 9 | 9 |
| `federal_register` | 4 | 4 |
| `census` | 4 | 4 |
| `bls` | 3 | 3 |
| `reginfo` | 2 | 2 |
| **Total (excluding `catalog`)** | **36** | **44** |

The additional tools are `documents_get_artifact` and the `analysis` model
tools (`create_model`, `get_model`, `inspect_model_readiness`,
`evaluate_model`, `reconcile_model_output`, `get_model_run`,
`inspect_model_run`).

**Unresolved.** Two explanations are consistent with the evidence and this run
cannot distinguish them: the first enumeration undercounted, or the deployed
server changed between 20:15Z and 22:04Z. Both figures are preserved above
rather than silently reconciled.

**Does this change any result?** It does not change the EVAL-03 finding. The
re-enumerated catalog still contains no tool that returns a UI resource, no
tool whose name contains `ui`, `app`, `render`, `form`, or `view`, and no
comment-submission, filing, or docket-write operation. The EVAL-03 `BLOCKED`
status and the EVAL-02 "no submission tool exists" observation both hold under
the larger catalog. It does mean any statement of the form "all 37 tools were
enumerated" overstates the completeness of the catalog sweep.

## C-3 — The gateway-mode claim was inferred, not inspected

**As recorded during the run.** The run README and suite summary attribute
gateway mode `conventional` to the default in
`src/regulatory_mcp/config.py`.

**Corrected statement.** What was actually observed is that every tool was
dispatched directly and individually by name, which is conventional-mode
behaviour, and that CodeMode was never exercised. The deployed server's
configured `gateway_mode` value was not inspected, and the cited local
`config.py` is from the harness checkout, not the evaluated build. The
substantive point stands: **CodeMode was not exercised anywhere in this run**,
so no CodeMode conclusion may be drawn from these results.

## What is not corrected

- All per-dimension scores, rationales, critical-gate determinations, and
  `PASS` / `FAIL` / `BLOCKED` results stand exactly as recorded.
- All live source identifiers, artifact UUIDs, and content hashes stand; those
  were returned by the server and are independently checkable.
- The absence of a human adjudicator stands. Every score in this run remains
  **provisional agent self-assessment**.
