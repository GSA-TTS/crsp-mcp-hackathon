---
title: "Use Local FastMCP Children Under a Namespaced Gateway"
description: "Formal proposed record of AD-001 and the initial Python dependency choices."
status: draft
tier: 2
last_updated: "2026-10-30"
date: "2026-10-30"
decision_status: proposed
decision_makers: ["Project owner — review pending"]
category: "Deployment and Infrastructure"
nist_controls: ["AC-6", "AU-3", "CM-3", "SA-11", "SI-10"]
impact_level: undetermined
ato_relevance: undetermined
risk_treatment: mitigate
related_files: ["../SPECIFICATION.md", "../DEVELOPMENT.md", "../IMPLEMENTATION_PIPELINE.md"]
---

# AD-001: Local FastMCP gateway

## Context and problem statement

Regulatory analysis needs several reusable source adapters and deterministic calculations in one agent workflow. The project owner authorized a local public-source prototype, with deployment classification and authorization still undetermined. This record formalizes the proposal in the specification without claiming architecture acceptance before WP-02.

## Decision drivers

- Independently usable source servers and testable boundaries.
- Compact agent context and evidence references across tool calls.
- Reproducible local setup with finite execution budgets.
- Conventional access for evaluating CodeMode's behavior.

## Considered options

1. A monolithic server: fewer registration points, greater coupling.
2. Local children mounted in one gateway: modularity without separate deployments.
3. Remote child servers: independent operations with additional transport and identity requirements.

## Proposed decision outcome

Prefer option 2. Pin FastMCP 4.1.4 and Python 3.14 for the initial proof. Use pydantic-settings 2.16.2, already in FastMCP's dependency graph, for explicit validated configuration and secret masking. Use Hatchling for packaging and `uv.lock` for reproducible dependencies.

Conventional child tools remain the source of capabilities. CodeMode is a gateway transform; its experimental status and execution-provider requirements must be evaluated in WP-02. API import and mount signature inspection succeeded, but composition, collisions, lifecycle, and isolation remain acceptance gates.

## Consequences

Positive: bounded module scopes, shared evidence contracts, inexpensive local iteration, and comparable conventional access.

Negative: the initial Python support range is narrow; CodeMode's experimental API can change; dependencies must be upgraded through compatibility checks. Mounted namespaces and actual tool exposure require runtime verification.

Control considerations: request budgets and explicit source access support least privilege; evidence manifests and verification transcripts support traceability. Neither the selected libraries nor this record establish FIPS validation or an ATO. Impact level and ATO relevance await a deployment decision.

## Acceptance and rollback

WP-02 now passes real FastMCP/Monty composition, bounded execution, and stdio tests. WP-03 implements the shared evidence contracts and local immutable artifact store described in the specification. Monty 1.4.0 (MIT) is pinned as the restricted execution provider, and Pydantic 2.14.2 is pinned directly for contracts. See [verification](../verification/WP-02-WP-03.md). The decision remains proposed pending human review of these results and the documented storage/execution boundaries.

The human owner may accept the architecture after AC-01 and review of execution isolation. If the proof fails, revise this proposed record with observed evidence before expanding adapters. Foundation changes can be reverted as a scoped version-control change; no stored source artifacts or deployed infrastructure are migrated by this package.
