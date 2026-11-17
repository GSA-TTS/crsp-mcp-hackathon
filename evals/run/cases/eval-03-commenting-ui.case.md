---
title: "EVAL-03 case CU-01: MCP Apps commenting UI"
description: "Frozen commenting-UI case for run RUN-2026-11-17-A. Records the intended exercise and the observed system state at freeze time."
status: draft
tier: 2
run_id: RUN-2026-11-17-A
case_id: CU-01
last_updated: "2026-11-17"
related_files: ["../../commenting-ui.md", "../reports/eval-03-commenting-ui.report.md"]
---

# EVAL-03 case CU-01

**Case ID:** `CU-01`
**Spec:** [`../../commenting-ui.md`](../../commenting-ui.md)

## Part 1 — Intended exercise

The evaluation requires launching a commenting interface **through an actual MCP
Apps-capable host**, with the rule context of a specific docket carried into the
interface, and verifying six things: MCP Apps delivery, context integrity,
interaction and state, accessibility and usability, privacy and boundary
behavior, and the no-submission guard.

Intended steps:

1. Call a tool on the registered `crsp-regulations` gateway that returns a
   `ui://` resource for a commenting interface.
2. Confirm the host renders it, and that the rule identity (docket
   FDA-2024-N-2910, FR 2025-00778, 90 FR 5426) arrives in the interface
   unaltered.
3. Exercise interaction and state across at least one round trip.
4. Check keyboard navigation, focus order, labelling, and contrast.
5. Confirm no personal information leaves the host and no external network
   origin is reachable from the resource.
6. Confirm no submission path exists from the interface.

## Part 2 — System state at freeze (observed, not assumed)

| Observation | Method | Result |
| --- | --- | --- |
| MCP Apps markers in the Python package | `grep -rn "ui://\|ext-apps\|registerApp\|resourceUri\|RESOURCE_MIME" src/` | **No matches.** |
| Any resource registration in the gateway | `grep -rn "@gateway.resource\|add_resource\|\.resource(" src/` | **No matches.** |
| Gateway mounts | `src/regulatory_mcp/gateway/server.py` lines 33, 38 | Mounts Python child servers by namespace only. The Node prototype is **not** mounted. |
| Registered tool catalog | `catalog` tool, live | 37 tools across `regulations`, `reginfo`, `documents`, `analysis`, `census`, `bls`, `federal_register`. **No tool returns a UI resource.** |
| Node prototype present | `ls uswds-iui/` | `server.js` (81 lines), `view.html` (86 lines), `server.test.js`, `README.md`, `docs/` |
| Node prototype identity | `uswds-iui/package.json` | `inline-micro-form` v0.1.0; deps `@modelcontextprotocol/ext-apps` 2.0.4, `@modelcontextprotocol/server` 2.4.0, `@uswds/uswds` 3.14.0, `zod` 4.6.7 |
| Node prototype unit tests | `npm test` | **4 pass, 0 fail**, duration 317 ms |
| Node prototype content | `uswds-iui/view.html` | A generic task-name input and a Low/Medium/High priority button group. **No rule, docket, or comment context of any kind.** |
| Resources advertised by the registered extension | `list_resources(extension_name="crsp-regulations")`, live | **Empty result.** The gateway advertises resource capability but publishes no resource, so there is no `ui://` URI for a host to fetch. |
| Host MCP Apps capability | `list_resources()` across all enabled extensions, live | The host **is** MCP Apps-capable in this session: an unrelated extension publishes `ui://apps/clock`, and an `mcpapps` extension is loaded. The blocker is therefore a **server-side gap, not a host limitation.** |
| Node prototype registered in this session | enabled/disabled extension listing, live | **Not registered.** `inline-micro-form` appears in neither the enabled nor the disabled extension list, so its tool could not be invoked through the host. Registering it would be a host-configuration change outside the approved scope of this evaluation run. |

## Part 3 — Frozen determination

The capability under evaluation — a commenting interface delivered over MCP Apps
from the registered regulatory gateway — **does not exist in the system at this
revision**. There is no `ui://` resource, no MCP Apps tool registration, and no
mount connecting the standalone Node prototype to the Python gateway.

Per the suite protocol, the result is reported **BLOCKED** rather than satisfied
with a mock, a hand-built host, or a narrative description of what the interface
would do. The Node prototype's status is reported **separately** and is not
scored against the EVAL-03 rubric, because scoring a generic micro form against a
commenting-UI rubric would produce a number with no referent.
