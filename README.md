---
title: "Regulatory Analysis MCP Suite"
description: "Evidence-linked regulatory research and reproducible economic analysis."
status: draft
tier: 1
last_updated: "2026-11-23"
related_files: ["PROJECT_PLAN.md", "docs/SPECIFICATION.md", "docs/IMPLEMENTATION_PIPELINE.md", "evals/README.md"]
---

# Regulatory Analysis MCP Suite

A hosted MCP prototype for researching federal regulations, retaining traceable supporting evidence, and performing reproducible economic calculations. It connects AI assistants to public regulatory and economic sources through a modular FastMCP gateway. The current FDA reconstruction work uses the 2016 Nutrition Facts/Serving Size combined final regulatory impact analysis.

## Project documents

- [Project plan](PROJECT_PLAN.md): scope, milestones, sources, and demonstration.
- [Technical specification](docs/SPECIFICATION.md): proposed architecture and contracts.
- [Implementation pipeline](docs/IMPLEMENTATION_PIPELINE.md): tracked work packages and acceptance gates.
- [Analysis tools](docs/ANALYSIS.md): deterministic calculations, input formats, and run provenance.
- [Source adapters](docs/SOURCES.md): Regulations.gov, Reginfo, and Census/BLS prototypes with explicit live-verification limits.
- [Hosted deployment](docs/DEPLOYMENT.md): shared-token HTTP, persistent S3 storage, cloud.gov packaging, and operator acceptance steps.
- [Evaluation suite](evals/README.md): task specifications for rule discovery, comment drafting, MCP Apps, and independent review, plus recorded runs and their limitations.

## Current status

**Working prototype, not a completed economic-review platform.** Implemented capabilities include:

- Hosted Streamable HTTP on cloud.gov with shared bearer authentication and persistent S3 evidence storage; local stdio remains supported.
- Regulations.gov and Federal Register lookup, Reginfo public-report snapshots, Census discovery/table retrieval, and BLS series/metadata tools. Coverage and availability depend on the source and request; results are not automatically exhaustive.
- PDF/UTF-8 CSV ingestion and inspection, source-linked evidence selections, and immutable caller-attested review records. Extracted numbers are not automatically human-reviewed.
- Deterministic discounting, annualization, break-even, cost-to-receipts, reconciliation, and discount-rate scenarios.
- Declarative economic models with dimension checking, input-readiness inspection, persisted evaluations, output reconciliation, and compact/paged run retrieval.

The gateway mounts namespaced child servers and supports bounded CodeMode orchestration and conventional tool access. Retained artifacts and calculation manifests preserve source references, assumptions, units, timing, and verification limitations.

### Observed hosted demonstration

On **2026-11-16**, an OpenCode/Paseo client connected to the hosted server and called `documents_get_run` for saved run `d3997a54-e48a-4814-a34a-3bec272a4dea`. The returned break-even value was **10 USD/(units)**. This was an actual authenticated remote MCP call, not just a health check. The same session read back retained FDA supporting artifacts and historical Census projection rows.

This demonstration establishes the observed remote connection and saved-record retrieval, not current uptime or complete source/model acceptance. The calculation uses synthetic smoke-test inputs. No fresh hosted check or test-suite run was performed for this README update. Detailed verification history is in the [implementation pipeline](docs/IMPLEMENTATION_PIPELINE.md).

### Remaining functionality and limitations

- General multi-parameter model sensitivity and threshold solving are not implemented; the existing scenario tool varies discount rates only.
- Automatic proposed/final/correction version-chain resolution and complete collection reporting remain unfinished.
- Automated evidence-linked reviewer reports and a second-agency demonstration remain pending.
- Full FDA cost-component reconstruction, input review, historical-vintage confirmation, and targeted research corroboration remain incomplete. Candidate deterministic mean-model agreement is not reproduction of the agency's stochastic simulation.

The analysis distinguishes published-table reproduction, model reconstruction, and independent input validation. Reproducing a calculation using agency-reported inputs does not independently verify proprietary source data. Human review is required before production use; no ATO or production-readiness claim is made. Comment submission is out of scope.

## Hosted client connection

The prototype endpoint is `https://crsp-regulatory-mcp.app.cloud.gov/mcp`. For OpenCode V2, add the following server entry to the effective configuration, preserving existing settings:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "regulatory-cloud": {
        "type": "remote",
        "url": "https://crsp-regulatory-mcp.app.cloud.gov/mcp",
        "headers": {
          "Authorization": "Bearer {env:REGULATORY_MCP_REMOTE_TOKEN}"
        },
        "oauth": false
      }
    }
  }
}
```

Provide `REGULATORY_MCP_REMOTE_TOKEN` through your approved secret-delivery mechanism before launching the client. Keep the environment reference literal; never paste a token into configuration, source control, logs, or a submission. An authorized token and network access are required. All authenticated clients share one workspace. Confirm connection by executing a read-only MCP tool, not merely by saving configuration or checking `/health`.

## Development

With Python 3.14, `uv`, Git, and GNU Make installed:

```bash
make setup
make check
```

Setup installs the locked environment into `.venv`; verification includes lint, formatting, type checking, tests, security checks, build, and an online dependency audit. Use `make check-offline` for local checks after setup; it does not establish current advisory status. See [development instructions](docs/DEVELOPMENT.md) for configuration and check details, the [technical specification](docs/SPECIFICATION.md) for requirements, and the [implementation pipeline](docs/IMPLEMENTATION_PIPELINE.md) for current work and acceptance history.

Launch the stdio server with `uv run --locked python -m regulatory_mcp`. Set `REGULATORY_MCP_GATEWAY_MODE=codemode` to enable CodeMode. Tools expose source reads and inspection of retained artifacts, evidence, and calculation manifests. Set `REGULATIONS_GOV_API_KEY` to enable Regulations.gov requests.

Implementation and documents were prepared with AI assistance and remain subject to project-owner review.

For cloud.gov, `make package-cloudgov` prepares the locked application payload.
The hosted entry point is `python -m regulatory_mcp.http_server`; it requires
authentication and storage configuration. Live deployment acceptance is tracked
in WP-17 and is not established by local tests. Hosting is limited to one
process/instance until shared upstream quota coordination is implemented.
