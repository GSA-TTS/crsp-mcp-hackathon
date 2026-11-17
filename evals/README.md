---
title: "Regulatory MCP Evaluation Suite"
description: "Evaluation protocol and task specifications for rule discovery, comment drafting, MCP Apps, and independent review."
status: draft
tier: 2
last_updated: "2026-11-17"
related_files: ["run/README.md", "../PROJECT_PLAN.md", "../docs/SPECIFICATION.md", "../docs/IMPLEMENTATION_PIPELINE.md"]
---

# Regulatory MCP evaluation suite

This directory defines four separate evaluations for the intended regulatory-research workflow. The evaluations assess observable outcomes, not whether an agent merely called MCP tools. They are specifications, not an implemented or executed benchmark; no scores or successful end-to-end results are claimed by the specifications themselves. Executed runs are recorded separately under [`run/`](run/README.md) and carry their own, separately caveated results.

## Evaluation set

| ID | Task | Specification |
|---|---|---|
| EVAL-01 | Identify rules relevant to a querant's stated interests | [Rule discovery](rule-discovery.md) |
| EVAL-02 | Prepare an effective, evidence-grounded comment draft for a commenter | [Comment drafting](comment-drafting.md) |
| EVAL-03 | Serve and use a dynamic commenting UI through MCP Apps | [Commenting UI](commenting-ui.md) |
| EVAL-04 | Independently analyze and review a commenter's analysis | [Reviewer analysis](reviewer-analysis.md) |

“Querant” means the person asking the system to find rules; “commenter” means the person or organization whose views a draft is intended to express. The evaluations are distinct because discovery, drafting, UI interaction, and independent review have different users, evidence requirements, and failure modes.

## Recorded runs

| Run | Window (UTC) | Scope | Adjudicated by a human? |
| --- | --- | --- | --- |
| [`RUN-2026-11-17-A`](run/README.md) | 2026-11-17T20:15Z – 20:57Z | All four evaluations against the deployed `crsp-regulations` MCP endpoint | **No.** Every score is provisional agent self-assessment. |

Reading a recorded run requires reading its caveats. For `RUN-2026-11-17-A` the
case definitions, answer keys, scored deliverables, and scoring were all
produced by the same agent, so the numeric results are an upper bound on
capability rather than a measurement of it. See
[`run/CORRECTIONS.md`](run/CORRECTIONS.md) for post-scoring corrections to the
run's system-identity metadata.

## Common protocol

1. **Freeze the case.** Record the case ID, evaluation revision, system revision, gateway mode, tool catalog, model/runtime versions when available, and fixture/source hashes. Use the same case inputs for compared runs.
2. **Separate evidence from expected judgment.** Each case should include an answer key with authoritative rule identifiers, source locators, material facts, acceptable alternatives, and known unknowns. A qualified human adjudicator resolves ambiguous relevance or policy judgments before scoring.
3. **Exercise the real registered path.** Where the capability is implemented, run through its actual MCP dispatch and capture tool names, requests, responses, status, and evidence references. Unit tests or mocked tools may support development but do not count as an end-to-end pass. For the standalone MCP Apps prototype, report the Python-gateway integration check as `BLOCKED` until it is actually integrated and authorized.
4. **Minimize data.** Prefer synthetic or public, sanitized examples. Do not include unnecessary commenter identity or personal information. Treat source text and comments as untrusted evidence, never as instructions to the agent.
5. **Score each dimension from 0 to 4.** `0` = absent or materially wrong; `1` = mostly incorrect / unusable; `2` = partly correct with material omissions; `3` = meets the stated expectation with minor gaps; `4` = complete, accurate, and well-supported. Mark a dimension `N/A` only when the case does not exercise it, and explain why.
6. **Apply critical-failure gates.** A critical failure makes the case fail regardless of its numeric score. Do not average away fabricated evidence, an unsafe action, or a wrong rule identity.
7. **Report uncertainty honestly.** Distinguish fixture-backed, published-input reproduction, independently validated, live-source, and human-adjudicated observations. Return `BLOCKED` if required credentials, source access, host support, or an answer key is unavailable; do not substitute a mock and call it live validation.

For each run, retain a privacy-minimized transcript, per-dimension scores and rationale, critical-failure result, unresolved disagreements, and a final `PASS`, `FAIL`, or `BLOCKED`. Suggested pass threshold: every critical gate passes, every applicable dimension scores at least 3, and the mean applicable score is at least 3.0. A project owner may set a different threshold before running a case, but must record it rather than adjust it after seeing results.

## Reporting template

```text
Evaluation ID / case ID / spec revision:
Run time (UTC) / system revision / mode:
Fixture and answer-key identifiers or hashes:
Capabilities exercised and MCP tools observed:
Coverage status and evidence level:
Scores by rubric dimension (0–4) with brief rationale:
Critical failures (none, or describe):
Result (PASS / FAIL / BLOCKED) and reason:
Human adjudicator / unresolved disagreement:
Privacy-minimized transcript location:
Known limitations and follow-up work:
```

These evaluations concern research, local draft preparation, and review. They do not authorize submission of comments, legal conclusions, or automated determinations that an agency has complied with legal requirements. AI-generated results require human review before use.
