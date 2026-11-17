---
title: "Regulatory Analysis MCP Suite"
description: "Evidence-linked regulatory research and reproducible economic analysis."
status: draft
tier: 1
last_updated: "2026-11-17"
related_files: ["PROJECT_PLAN.md", "docs/SPECIFICATION.md", "docs/IMPLEMENTATION_PIPELINE.md", "evals/README.md"]
---

# Regulatory Analysis MCP Suite

A planned modular MCP suite for researching federal regulations, retrieving supporting evidence, and checking regulatory economic analyses. The initial demonstration is the FDA front-of-package nutrition labeling analysis identified in the planning handoff.

## Project documents

- [Project plan](PROJECT_PLAN.md): scope, milestones, sources, and demonstration.
- [Technical specification](docs/SPECIFICATION.md): proposed architecture and contracts.
- [Implementation pipeline](docs/IMPLEMENTATION_PIPELINE.md): tracked work packages and acceptance gates.
- [Analysis tools](docs/ANALYSIS.md): deterministic calculations, input formats, and run provenance.
- [Source adapters](docs/SOURCES.md): Regulations.gov, Reginfo, and Census/BLS prototypes with explicit live-verification limits.
- [Hosted deployment](docs/DEPLOYMENT.md): shared-token HTTP, persistent S3 storage, cloud.gov packaging, and operator acceptance steps.
- [Evaluation suite](evals/README.md): task specifications for rule discovery, comment drafting, MCP Apps, and independent review, plus recorded runs and their limitations.

## Current status

**Local gateway, evidence storage, and read adapters implemented.** Conventional/CodeMode, immutable evidence storage, Regulations.gov read tools, and Reginfo snapshot tools have offline coverage. Live adapter acceptance remains blocked by missing Regulations.gov credentials and this environment's Reginfo DNS boundary. See [source adapters](docs/SOURCES.md).

The intended design mounts separately usable source and analysis servers under one namespaced FastMCP gateway, with CodeMode for bounded orchestration and a conventional mode for comparison. Research results carry citations, retrieval completeness, and reproducibility metadata.

The analysis distinguishes published-table reproduction, model reconstruction, and independent input validation. Reproducing a calculation using agency-reported inputs does not independently verify proprietary source data.

## Development

With Python 3.14, `uv`, Git, and GNU Make installed:

```bash
make setup
make check
```

Setup installs into `.venv`; verification includes an online dependency audit. Use `make check-offline` for local checks after setup. See [development instructions](docs/DEVELOPMENT.md) for configuration and check details, and the [technical specification](docs/SPECIFICATION.md) for the architecture. WP-02 and WP-03 are implemented and awaiting review; the next source packages are **WP-04** (Regulations.gov) and **WP-05** (Reginfo).

Launch the stdio server with `uv run --locked python -m regulatory_mcp`. Set `REGULATORY_MCP_GATEWAY_MODE=codemode` to enable CodeMode. Tools expose source reads and inspection of retained artifacts, evidence, and calculation manifests. Set `REGULATIONS_GOV_API_KEY` to enable Regulations.gov requests.

Implementation and documents were prepared with AI assistance and remain subject to project-owner review.

For cloud.gov, `make package-cloudgov` prepares the locked application payload.
The hosted entry point is `python -m regulatory_mcp.http_server`; it requires
authentication and storage configuration. Live deployment acceptance is tracked
in WP-17 and is not established by local tests.
