---
title: "EVAL-03: MCP Apps Commenting UI"
description: "Evaluate dynamic serving and safe, usable interaction for a commenting UI delivered through MCP Apps."
status: draft
tier: 2
last_updated: "2026-11-09"
related_files: ["README.md", "../uswds-iui/README.md", "../docs/IMPLEMENTATION_PIPELINE.md"]
---

# EVAL-03: MCP Apps commenting UI

## Objective

Evaluate whether an MCP Apps host can dynamically display rule context and a local comment-drafting/review interface, support the intended interactions, and return or preserve the draft without losing source context or implying submission. A rendered mock or browser-only preview is not proof of delivery through MCP Apps.

The current `uswds-iui/` prototype is documented as standalone and not mounted in the Python regulatory MCP gateway. Therefore the evaluation has separate prototype and integrated-host results. Do not claim integrated success until that boundary changes through approved implementation work.

## Case design

Prepare cases with a rule title/identifier, source excerpts and locators, a commenter brief, an existing draft (including empty and long drafts), validation warnings, and deterministic expected UI state transitions. Include loading, partial-data, error, and unsupported-host cases. Use synthetic or sanitized content and accessible interaction tasks. Record the MCP Apps host/client versions and tool/resource registration used.

## Procedure

1. Launch through the actual MCP Apps-capable host and invoke the registered tool that returns the UI resource. Record server registration, resource metadata, host version, and tool result.
2. Confirm that the component is served dynamically from the returned MCP resource and displays the case's correct rule/source context.
3. Perform a scripted interaction: review evidence, compose/edit a draft, surface a missing-information warning, save/return/export according to the implemented contract, and recover from an error or reload.
4. Verify keyboard-only operation and accessible names/focus for all essential controls. Test narrow viewport and long text.
5. Inspect network and tool traces for unauthorized destinations, unexpected data transfer, or any comment-submission capability.

If no supported host is available, mark host execution `BLOCKED`. A local unit test or screenshot may be supplementary evidence only.

## Rubric (0–4 each)

| Dimension | What to assess |
|---|---|
| MCP Apps delivery | Host discovers the intended tool/resource and renders the dynamically returned UI; host/resource failures are explicit. |
| Context integrity | Rule identity, source excerpts, citations, and draft state correspond to the invocation; stale or mismatched context is detectable. |
| Interaction and state | Draft editing, validation, return/save behavior, and error recovery work as specified without silent data loss. |
| Accessibility and usability | Essential flow works via keyboard, has meaningful labels/focus, handles long text and narrow display, and communicates status/errors. |
| Privacy and boundary behavior | Only necessary data is transferred; no unexpected network egress or credential exposure; source text is treated as untrusted. |
| No-submission guard | User can distinguish draft/review from submission; no submission action is exposed or invoked in this prototype scope. |

## Critical failures

- The purported MCP Apps pass uses only a static page, mock host, or browser preview while being reported as real host rendering.
- Wrong rule/source context is shown without warning, or a user edit is silently lost.
- Comment text or credentials are sent to an unauthorized destination.
- The UI submits a comment or claims submission occurred.
- An essential action is inaccessible and no equivalent accessible path exists.

## Result

Report two statuses when applicable: **prototype** (what the standalone MCP Apps package does in its supported host) and **gateway integration** (whether the regulatory MCP workflow actually serves and connects that app). Apply the common threshold in [the suite protocol](README.md) to each; report gateway integration as `BLOCKED` while it remains unimplemented. Do not infer that UI styling tests prove dynamic host rendering.
