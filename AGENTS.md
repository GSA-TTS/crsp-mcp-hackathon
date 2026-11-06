---
title: "Regulatory MCP Project Instructions"
description: "Project-specific context and verification commands for AI coding agents."
status: draft
tier: 1
last_updated: "2026-11-05"
contract:
  role: project-layer
  requires_contract: ">=1.0"
related_files: ["PROJECT_PLAN.md", "docs/DEVELOPMENT.md", "docs/IMPLEMENTATION_PIPELINE.md"]
---

# Regulatory MCP project instructions

## Prerequisite

This is an additive project layer for the Federal AI Agent Behavioral Best Practices universal contract, version 1.x or later, supplied by the agent environment. Its canonical source is the GSA-TTS agentic-coding-playbook `AGENTS.md`. Load the universal contract from the supplied context or `~/.agentic-coding-playbook/AGENTS.md` before work. If unavailable, stop and ask the owner to provide it. This project layer is not a substitute for that contract.

## Context and scope

Local Python 3.14/FastMCP prototype for public-source regulatory research. No FIPS impact level or ATO is claimed. Public comment text can contain personal information; fixtures and logs must minimize it. No comment-submission tools are in scope.

The approved hosted extension uses cloud.gov (`sandbox-gsa / gsa.mcp.registry`),
one shared bearer-authenticated workspace, and persistent S3 storage. Follow
`docs/DEPLOYMENT.md` and ADR-0002. Public HTTP startup must require authentication
and durable storage. One process/instance only until WP-18 quota coordination.

Use `docs/IMPLEMENTATION_PIPELINE.md` as the durable task ledger. Read the assigned package and corresponding specification before changing interfaces. Preserve existing user work. Keep source adapters under `src/regulatory_mcp/sources/`, the gateway under `gateway/`, and shared evidence contracts under `contracts/` and `evidence/` as those packages are implemented.

## Commands

- `make setup`: synchronize the locked local environment.
- `make check`: lint, format check, type check, tests, security checks, build, and online dependency audit.
- `make check-offline`: local checks after setup; does not establish current advisory status.
- `make package-cloudgov`: build a minimal deployment payload from locked runtime dependencies.

Run commands from the repository root. Keep package versions exact and lockfile changes explicit. Configuration is defined in `src/regulatory_mcp/config.py` and documented in `docs/DEVELOPMENT.md`; update consumers and tests when changing it.

## Evidence and handoff

Identify AI assistance in handoffs. Preserve UTC timestamps and actual verification output. Label mocks, published-input reproduction, independent validation, and blocked live checks accurately. Human review is required before production use. Do not silently register unavailable sources or present partial searches as exhaustive.

Dependency installation and external source access must be within the owner's approved task scope. Infrastructure, CI configuration, publication, commits, and pushes require explicit authorization. Keep an architecture record for new services or module-boundary changes.

### Upstream Query-Parameter Authentication Exception

- **System:** `https://api.census.gov`
- **Scope:** Read-only Census Bureau statistical data queries.
- **Rationale:** The Department of Commerce / Census Data API requires the `key` parameter in GET query strings and does not support authorization headers.
- **Compensating Controls:**
  - Key must be loaded from server environment secrets (`SecretStr`), never hardcoded.
  - Outbound requests must enforce HTTPS and reject HTTP redirects.
  - The parameter must be stripped from all logs, error messages, stored artifacts, and calculation manifests (`source_url`).