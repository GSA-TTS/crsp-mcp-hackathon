---
title: "EVAL-03 report: MCP Apps commenting UI (case CU-01)"
description: "Result for the commenting-UI evaluation. Gateway integration BLOCKED; prototype status reported separately and not scored against this rubric."
status: draft
tier: 2
run_id: RUN-2026-11-17-A
case_id: CU-01
last_updated: "2026-11-17"
related_files: ["../cases/eval-03-commenting-ui.case.md", "../../commenting-ui.md", "../transcripts/eval-03.transcript.md"]
---

# EVAL-03 report — MCP Apps commenting UI

> **No scores are reported for this case.** The capability under evaluation does
> not exist at this revision, so the six rubric dimensions are marked
> *not scored* rather than assigned numbers. Assigning numbers to an absent
> capability would manufacture a measurement.

| Field | Value |
| --- | --- |
| Evaluation ID | EVAL-03 |
| Case ID | `CU-01` |
| Spec | [`../../commenting-ui.md`](../../commenting-ui.md) |
| Run time (UTC) | 2026-11-17T20:53Z – 20:57Z |
| System revision | git `58fc63cc49c127ba2b14c0055b73b0a526400bd5` (dirty tree) |
| Provenance correction | See [`CORRECTIONS.md`](../CORRECTIONS.md) — the system under evaluation was the deployed `crsp-regulations` HTTP endpoint, not this local checkout; the 37-tool figure is unstable. |
| Gateway mode | `conventional` (CodeMode **not** exercised) |
| Host | goose session; MCP extension name `crsp-regulations` |
| Case freeze | [`../cases/eval-03-commenting-ui.case.md`](../cases/eval-03-commenting-ui.case.md) |
| Transcript | [`../transcripts/eval-03.transcript.md`](../transcripts/eval-03.transcript.md) |
| Scored artifact | **none produced** — see below |

## Result

| Status | Result |
| --- | --- |
| **Gateway integration** | **BLOCKED** |
| **Prototype** | **BLOCKED (not executed in a host)**; unit tests pass, reported separately and **not** scored against this rubric |

### Why BLOCKED and not FAIL

The spec distinguishes an unimplemented capability from a defective one, and
directs that gateway integration be reported `BLOCKED` while it remains
unimplemented. Nothing in the system attempted to serve a commenting UI and
failed; no such path exists to attempt. A `FAIL` would imply the system tried
and got it wrong, which would misdescribe the state of the code.

## Capabilities exercised and MCP tools observed

Live observations, no mocks:

- `catalog` (registered `crsp-regulations` gateway) — 37 tools across
  `regulations`, `reginfo`, `documents`, `analysis`, `census`, `bls`,
  `federal_register`. **No tool returns a UI resource.** No tool name contains
  `ui`, `app`, `render`, `form`, or `view`.
- `list_resources(extension_name="crsp-regulations")` — **empty result.** The
  extension is marked as supporting resources but publishes none, so there is no
  `ui://` URI for the host to fetch.
- `list_resources()` across all enabled extensions — returned
  `ui://apps/clock` from an unrelated extension.

That last observation matters for attribution: **the host in this session is
MCP Apps-capable.** A `ui://` resource from another extension was discoverable
and listed. The blocker is therefore located on the server side of the boundary —
the regulatory gateway does not publish a UI resource — and not in host support.
This run can state that with evidence rather than as an inference.

Source-side confirmation (shell, repository at the revision above):

| Check | Command | Result |
| --- | --- | --- |
| MCP Apps markers in the Python package | `grep -rn "ui://\|ext-apps\|registerApp\|resourceUri\|RESOURCE_MIME" src/` | no matches |
| Resource registration in the gateway | `grep -rn "@gateway.resource\|add_resource\|\.resource(" src/` | no matches |
| What the gateway mounts | `src/regulatory_mcp/gateway/server.py` lines 33, 38 | Python child servers by namespace only; the Node prototype is not mounted |

## Coverage status and evidence level

| Item | Status |
| --- | --- |
| MCP Apps host execution of a regulatory commenting UI | **not performed** — no such tool or resource exists to invoke |
| MCP Apps host execution of the standalone prototype | **not performed** — `inline-micro-form` is not a registered extension in this session; registering it is a host-configuration change outside this run's approved scope |
| Prototype unit tests | **performed**, `npm test`: 4 pass, 0 fail, 317 ms |
| Prototype static inspection | **performed**, `server.js` (81 lines), `view.html` (86 lines) |
| Evidence level | **source inspection + live capability enumeration.** No rendering evidence of any kind was obtained, and none is claimed. |

Per the spec, unit tests and static inspection are *supplementary evidence only*
and do not establish dynamic host rendering. The prototype's own README states
the same thing independently: "passing automated tests does **not** establish
live rendering in a particular host."

## Rubric dimensions

| Dimension | Score | Basis |
| --- | --- | --- |
| MCP Apps delivery | **not scored** | No tool/resource exists for a host to discover. |
| Context integrity | **not scored** | No interface exists into which rule context could be carried. The prototype's `view.html` contains a task-name field and Low/Medium/High priority buttons — no rule, docket, citation, or draft state. |
| Interaction and state | **not scored** | The prototype's only state transition is a priority-button `aria-pressed` toggle. There is no draft to edit, validate, save, or lose. |
| Accessibility and usability | **not scored** | The prototype uses USWDS classes, a `role="group"` with `aria-labelledby`, `aria-pressed` on the buttons, and a `role="status" aria-live="polite"` region — but these were verified by reading markup, not by keyboard-only operation in a host. Markup inspection is not an accessibility result. |
| Privacy and boundary behavior | **not scored** | `server.js` registers its resource with empty `connectDomains`, `resourceDomains`, `frameDomains`, and `baseUriDomains`, and throws if a CSS rule needs an external asset. This is a favorable design signal for a component that is not in the system under evaluation; scoring it here would credit the gateway for code the gateway does not serve. |
| No-submission guard | **not scored** | Reported as a system-wide finding below instead, where it can be substantiated. |

## No-submission guard — reported as a system finding

The rubric's no-submission dimension cannot be scored against an interface that
does not exist, but the underlying property was verified for the system as a
whole and is recorded here because it is the safety-relevant half of the
dimension:

- The full 37-tool `catalog` contains **no** submission, filing, or
  docket-write operation. The `regulations` namespace exposes only `get_*`,
  `search_*`, `list_*`, `collect_*`, and `retrieve_*` operations.
- Every write operation in the catalog targets the **local evidence store**
  (artifacts, evidence locators, reviews, models, runs).
- No submission tool was called during any case in this run, because none
  exists to call.
- The prototype's README states independently that "the task name and priority
  are never submitted or saved."

So the guard holds by construction at this revision. That is a weaker claim than
the rubric asks for — it says a user *cannot* submit, not that a user *can tell*
draft from submission in an interface — and it should be re-evaluated when an
interface exists.

## Critical failures

| Gate | Status |
| --- | --- |
| Static page / mock host / browser preview reported as real host rendering | **Not triggered.** No rendering was performed or claimed. |
| Wrong rule/source context shown without warning; silent edit loss | **Not applicable.** No interface. |
| Comment text or credentials sent to an unauthorized destination | **Not applicable.** No interface; no egress observed. |
| UI submits a comment or claims submission occurred | **Not triggered.** No submission capability exists in the catalog. |
| Essential action inaccessible with no accessible equivalent | **Not applicable.** No interface. |

No critical failure was triggered. That is a consequence of there being nothing
to fail, not a positive finding.

## Human adjudicator / unresolved disagreement

Human adjudicator: **none.** The `BLOCKED` determination is the least
judgment-dependent result in this suite — it rests on the absence of grep
matches, an empty resource list, and a tool catalog, all independently
re-checkable — but it still has not been confirmed by a human.

Unresolved disagreement: none recorded; there was no second party.

## System defects and specification observations

1. **The extension advertises resource support but publishes no resources.**
   `crsp-regulations` is surfaced to the host as supporting resources, yet
   `list_resources` returns empty. A host or an agent could reasonably read the
   capability advertisement as a promise of discoverable content. Worth a
   specification note: either publish at least one resource, or do not advertise
   the capability.
2. **No specification exists yet for the commenting-UI contract.** The spec
   requires "save/return/export according to the implemented contract," and
   there is no implemented contract. WP-11 and WP-12 are `blocked` in
   `docs/IMPLEMENTATION_PIPELINE.md`. The case cannot be scored until a contract
   defines what correct state handling means.
3. **The prototype is not a commenting UI and should not be mistaken for one in
   planning.** `inline-micro-form` v0.1.0 is a task-name field plus a
   three-button priority selector. It demonstrates that MCP Apps delivery and
   USWDS styling are *achievable* in this toolchain. It does not demonstrate any
   part of the EVAL-03 subject matter. The gap between the prototype and the
   case is the whole of the work, not a finishing step.

## Known limitations and follow-up work

- **No host execution of anything.** The strongest available evidence here is
  negative evidence — absence of registration markers, an empty resource list, a
  catalog with no UI tool. Negative evidence of this kind is reliable for the
  `BLOCKED` call and useless for anything else.
- **The prototype's accessibility and CSP properties were read, not exercised.**
  Keyboard-only operation, focus order, contrast, narrow viewport, and long-text
  behavior are all unverified. The markup is encouraging; that is not a result.
- **The `inline-micro-form` server was not registered as an extension** in this
  session. Registering a new stdio extension is an infrastructure change
  requiring explicit authorization, so the prototype half of the result also
  stands at `BLOCKED (not executed in a host)` rather than being filled in with
  the unit-test output.
- **Follow-up, in order:** (a) decide and write the commenting-UI contract —
  what rule context is passed in, what the host returns, what "draft" means on
  the server; (b) implement a `ui://` resource and an MCP Apps tool in the
  Python gateway, or an approved mount of a Node child server; (c) re-run CU-01
  with host execution, keyboard-only operation, and a network trace, and score
  all six dimensions then; (d) when an interface exists, add an adversarial case
  in which the source excerpt contains embedded instructions, so the
  untrusted-source half of the privacy dimension is tested rather than assumed.
  That gap is shared with EVAL-02 and EVAL-04 in this run.
- **Re-check the two host-side facts if the session changes.** The MCP
  Apps-capable-host finding and the absence of `inline-micro-form` from the
  extension list are properties of this goose session, not of the repository,
  and will not reproduce from the repository alone.
