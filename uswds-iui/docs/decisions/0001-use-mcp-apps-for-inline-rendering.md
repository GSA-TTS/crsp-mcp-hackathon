---
title: "Use MCP Apps for inline micro-form rendering"
description: "Proposed choice of MCP Apps over client-specific chat UI for an inline rendering prototype"
status: proposed
tier: 3
date: "2026-10-30"
decision_makers: ["Project owner (review pending)"]
category: "Dependency and Supply Chain"
nist_controls: ["SR-3", "SI-10"]
impact_level: "not-assessed"
ato_relevance: "no"
risk_treatment: "n/a"
---

# Use MCP Apps for inline micro-form rendering

## Context and Problem Statement

The first objective is to confirm that a task-name field and priority buttons render inside Goose Desktop chat. OpenChamber compatibility is not established. A plain MCP tool result cannot guarantee inline UI rendering.

## Decision Drivers

- Use a documented, portable UI extension rather than a Goose-only integration.
- Limit the prototype to local, non-sensitive, non-persisted input.
- Keep a readable fallback for hosts without inline UI support.

## Considered Options

1. **MCP Apps SDK** — register a `ui://` HTML resource and linked tool.
2. **Goose-specific widget** — depend on a single host's UI interface.
3. **Text-only MCP tool** — no interactive inline rendering.

## Decision Outcome

Proposed: **MCP Apps SDK**. Goose documents inline rendering, while the standard offers a portable protocol and text fallback. Actual rendering remains subject to a live host check.

### Positive Consequences

- Host-independent server design and a tiny UI with no external assets.
- A test can verify tool/resource wiring even without Goose installed.

### Negative Consequences

- New pinned dependencies require vulnerability and license review before use.
- OpenChamber support and Goose version-specific behavior must be verified live.

### Compliance Consequences

- Review dependency integrity and licenses (SR-3); validate any future form submission at the server (SI-10).
- No system impact level or ATO boundary is asserted for this local prototype; project owner should reassess if deployed.

## Links

- [MCP Apps specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx)
- [Goose Desktop tutorial](https://github.com/aaif-goose/goose/blob/main/documentation/docs/tutorials/building-mcp-apps.md)
