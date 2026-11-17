---
title: "EVAL-03 transcript (case CU-01)"
description: "Privacy-minimized record of the observations supporting the BLOCKED determination for the commenting-UI case."
status: draft
tier: 2
run_id: RUN-2026-11-17-A
case_id: CU-01
last_updated: "2026-11-17"
related_files: ["../cases/eval-03-commenting-ui.case.md", "../reports/eval-03-commenting-ui.report.md"]
---

# EVAL-03 transcript — case CU-01

No personal information appears in this transcript. No comment text was drafted,
transferred, or submitted. No MCP Apps host rendering occurred.

Window (UTC): 2026-11-17T20:53Z – 20:57Z.
Repository revision: git `58fc63cc49c127ba2b14c0055b73b0a526400bd5`, working tree dirty.
Provenance correction: see [`../CORRECTIONS.md`](../CORRECTIONS.md). That hash is the harness
checkout, not the evaluated build, and the 37-tool catalog figure re-enumerated as 44.
The `BLOCKED` finding holds under the larger catalog.

## Live MCP / host calls

| # | Call | Result |
| --- | --- | --- |
| 1 | `catalog` (crsp-regulations gateway) | 37 tools: `regulations` (9), `reginfo` (2), `documents` (8), `analysis` (10), `census` (4), `bls` (3), `federal_register` (4). No tool returns a UI resource; no tool name contains `ui`, `app`, `render`, `form`, or `view`. No submission/filing/docket-write operation. *(Carried from the pre-freeze catalog enumeration; same session, same revision.)* |
| 2 | `list_resources(extension_name="crsp-regulations")` | **Empty result.** |
| 3 | `list_resources()` (all enabled extensions) | Returned exactly one resource: `ui://apps/clock`, published by the unrelated `apps` extension. |
| 4 | extension enable/disable enumeration | Enabled: `extensionmanager`, `summon`, `apps`, `tom`, `todo`, `skills`, `analyze`, `mcpapps`, `crsp-regulations`, `developer`. `inline-micro-form` appears in **neither** the enabled nor the available-to-enable list. |

Interpretation recorded at the time: call 3 establishes that the host in this
session can discover and list a `ui://` resource, so the absence of a regulatory
commenting UI is a server-side gap rather than a host limitation. Call 2
establishes the gateway publishes no resource despite being surfaced as
resource-capable. Call 4 establishes the standalone prototype could not have been
invoked through the host even if it had been in scope to try.

## Shell observations (repository source)

| # | Command | Result |
| --- | --- | --- |
| S1 | `grep -rn "ui://\|ext-apps\|registerApp\|resourceUri\|RESOURCE_MIME" src/` | no matches |
| S2 | `grep -rn "@gateway.resource\|add_resource\|\.resource(" src/` | no matches |
| S3 | read `src/regulatory_mcp/gateway/server.py` | line 23 constructs `FastMCP("Regulatory analysis", mask_error_details=True)`; line 33 collision-probe mount; line 38 `gateway.mount(child, namespace=namespace)`. Python child servers only. |
| S4 | `ls uswds-iui/` | `server.js`, `view.html`, `server.test.js`, `package.json`, `package-lock.json`, `README.md`, `docs/decisions/` |
| S5 | `cat uswds-iui/package.json` | `inline-micro-form` v0.1.0; deps `@modelcontextprotocol/ext-apps` 2.0.4, `@modelcontextprotocol/server` 2.4.0, `@modelcontextprotocol/client` 2.4.0, `@uswds/uswds` 3.14.0, `zod` 4.6.7; node >= 20 |
| S6 | `npm test` (in `uswds-iui/`) | 4 pass, 0 fail, duration 317 ms. Named tests: publishes an MCP App tool + readable HTML resource + text fallback; priority selection updates USWDS styles/pressed state/status; reports a comfortable height after host init; expands height when taller than minimum. |
| S7 | read `uswds-iui/server.js` | `RESOURCE_URI = 'ui://inline-micro-form/main'`; `registerAppTool(server, 'show_micro_form', ...)` with `_meta.ui.resourceUri`; `registerAppResource` with `connectDomains`, `resourceDomains`, `frameDomains`, `baseUriDomains` all **empty** and `prefersBorder: true`; renders `view.html` with selected local USWDS rules and throws if a rule needs an external asset. |
| S8 | read `uswds-iui/view.html` | `<title>Micro form</title>`; a `task` text input (`maxlength=80`); a `role="group"` with `aria-labelledby="priority-label"` containing Low/Medium/High `<button>` elements with `aria-pressed`; a `role="status" aria-live="polite"` region. **No rule, docket, citation, comment, or draft content.** |
| S9 | read `uswds-iui/README.md` | States the prototype is standalone, requires manual registration as a stdio extension in an MCP Apps host, and that "passing automated tests does **not** establish live rendering in a particular host." Also: "The task name and priority are never submitted or saved." |

## Errors encountered

| Error | Resolution |
| --- | --- |
| `bash: rg: command not found` | `rg` is not installed on this machine. Re-ran the same searches with `grep -rn` and alternation escaped for BRE. Results in S1 and S2 are from `grep`. |
| `bash: timeout: command not found` | macOS has no `timeout(1)`. Re-ran `npm test` without a wrapper; it completed in 317 ms (S6). |

## Operations deliberately not performed

| Operation | Why not |
| --- | --- |
| Registering `inline-micro-form` as a goose stdio extension | Adding an extension is a host/infrastructure configuration change requiring explicit authorization. Not within this run's approved scope. Consequence: the prototype half of the result stays `BLOCKED (not executed in a host)`. |
| Building a mock host, static preview, or screenshot to stand in for MCP Apps delivery | The spec names this as a critical failure when reported as real host rendering, and there is no honest way to report it as anything else. |
| Writing a `ui://` resource into `src/regulatory_mcp` to make the case runnable | The system under evaluation must not be modified by the evaluation. Implementing the capability is WP-11/WP-12 work requiring authorization. |
| Scoring the Node prototype against the EVAL-03 rubric | The prototype contains no commenting or rule context. A number scored against a commenting-UI rubric would have no referent. Its status is reported separately instead. |

## Human-control checks

| Check | Result |
| --- | --- |
| Submission/filing/docket-write tool called | **No.** None exists in the 37-tool catalog. |
| Submission recommended or implied | **No.** |
| Rendering claimed without host execution | **No.** The report states no rendering evidence was obtained. |
| Accessibility result claimed from markup inspection | **No.** Markup findings are labeled as markup findings; the dimension is marked not scored. |
| Personal information present | **None.** No commenter brief or draft was used in this case. |
| System under evaluation modified | **No.** All repository interaction was read-only (`grep`, `cat`, `ls`, `npm test`). |
