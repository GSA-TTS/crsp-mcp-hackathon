---
title: "Local Development"
description: "Bootstrap, verification, dependency decisions, and environment configuration."
status: draft
tier: 2
last_updated: "2026-11-05"
related_files: ["../README.md", "IMPLEMENTATION_PIPELINE.md", "SPECIFICATION.md"]
---

# Local development

## Setup and verification

Prerequisites: Python 3.14, `uv`, Git, and GNU Make. The initial environment was tested with CPython 3.14.4 on Linux. Python 3.14 is the initial supported minor release, not a claim that other versions cannot work. `uv` uses the installed interpreter; the Makefile disables automatic Python downloads and keeps its cache in `.cache/uv`.

From the repository root:

```bash
make setup
make check
```

`make setup` creates `.venv` and installs exact dependencies from `uv.lock`. It requires access to the package registry unless the artifacts are already cached. Run it after pulling dependency changes. Direct dependencies and the build backend are exactly pinned in `pyproject.toml`; the lockfile retains transitive versions and artifact hashes.

`make check` runs Ruff lint/format checks, strict source type checking, pytest, Bandit, secret detection, source/wheel builds, and a dependency vulnerability audit. The audit contacts PyPI with package names and versions. It fails when the advisory service is unavailable or findings are returned.

After setup, `make check-offline` runs all local checks without the dependency advisory query. This is useful offline but does not replace the full release check. No live regulatory API check is implemented yet; those are tracked in WP-04–WP-06 and WP-12.

## Layout

- `src/regulatory_mcp/config.py`: validated process-environment settings.
- `tests/`: configuration boundaries and documentation integrity.
- `scripts/check_secrets.py`: turns secret findings into a failing check, including new files.
- `artifacts/`: ignored, project-local source/derived evidence storage, to be implemented in WP-03.

## Running the gateway

Launch the local stdio server with `uv run --locked python -m regulatory_mcp`. An MCP client launches it as a subprocess and communicates over stdin/stdout; logs go to stderr. Set `REGULATORY_MCP_GATEWAY_MODE=codemode` for CodeMode; conventional mode is the default.

Registered tools are `documents_get_artifact`, `documents_get_evidence`, and `documents_get_run`, plus `catalog`. CodeMode exposes discovery and `execute`. Inside a block, `await call_tool("catalog", {})` discovers backend schemas; FastMCP wraps this list in a `result` field. Use the discovered names for subsequent calls.

`create_gateway(children, settings)` mounts independently usable children. Each must enable `mask_error_details=True` and finish registration before assembly. Actual exposed names are checked for collisions. Catalogs must remain static after assembly; rebuild to change registration. The masking check uses FastMCP 4.1.4's private `_mask_error_details` attribute, covered by upgrade-sensitive integration tests.

Real FastMCP/Monty tests establish cross-child chaining, conventional parity, and lifespan behavior using deterministic fixture children. Subprocess tests exercise stdio in both modes. External regulatory integrations remain pending.

### Execution boundary

Monty 1.4.0 supplies restricted Python with only the registered `call_tool` callback. Tests reject file reads, environment/module access, and sockets, and terminate an infinite loop. These targeted checks are not an exhaustive sandbox certification. Monty and Pydantic declare MIT licenses; exact dependencies are locked and audited.

CodeMode counts callbacks, including catalog discovery, against `max_tool_calls`. Middleware separately bounds concurrent sandbox executions and backend calls, plus wall time and serialized results including intermediate outputs. Both concurrency pools use `max_concurrency`; separate pools avoid blocking a sandbox on the permit it holds. Monty also has a 100 MB memory bound and execution-time bound. Limits report tool errors instead of truncating results. Host callbacks must use asynchronous bounded I/O; deadlines cannot interrupt arbitrary blocking host code.

### Evidence library

Use `EvidenceStore(project_root, settings)` from authorized backend code to retain bytes/provenance, evidence, and calculation runs. Read tools resolve existing IDs, not paths. Contracts are exported from `regulatory_mcp.contracts`, schema version `1.0`.

`retain` accepts `source_system`, `origin`, `media_type`, and `source_url` for retrieved material. It assigns a UUID and SHA-256 content reference. Changed bytes create a new version; equal bytes can share a blob with separate retrieval records. Evidence records contain locators, extraction metadata, and review state. Run inputs require evidence or assumption rationales; evidence must be reviewed before a run can be saved/resolved.

Storage uses generated filenames, exclusive creation, private permissions, no-follow directory-relative opens, bounded reads, and digest verification. It rejects symlinks and conflicting overwrites, and revalidates records before persistence. This is a single-user local store, not a multiwriter database. An interrupted write may leave an incomplete object, which fails explicit manifest/integrity checks rather than being silently overwritten.

The same `EvidenceStore` validation now supports a byte-storage backend. Local
storage implements the filesystem behavior above; hosted S3 uses conditional
creates for both blobs and JSON records. Async tool callers move blocking storage
operations to worker threads. See [hosted configuration and deployment](DEPLOYMENT.md)
for shared-workspace authentication, service bindings and persistence gates.

Structured payloads preserve missing keys, nulls, and false values. Citations alone do not establish independent validation or transcription accuracy.

## Configuration

The gateway also registers six `analysis_*` tools for deterministic calculations and persists their manifests. See [analysis tools](ANALYSIS.md) for request formats, monetary units, timing conventions, and verification limits.

Construct `regulatory_mcp.config.Settings` at runtime initialization and pass it to consumers. Construction validates values but performs no network/filesystem I/O. These settings establish the shared configuration contract; enforcement in downloads and orchestration belongs to their respective work packages.

Process environment is used directly; `.env` files are not automatically loaded. Set credentials through your environment or approved secret manager. `SecretStr` masks credentials in model representations and JSON serialization; consumers must never log unwrapped secrets.

| Environment variable | Default | Format / bounds |
|---|---|---|
| `REGULATIONS_GOV_API_KEY` | unset | Secret string; required by future Regulations.gov calls |
| `CENSUS_API_KEY` | unset | Secret string; required for authenticated Census table queries |
| `REGULATORY_MCP_ARTIFACT_DIR` | `artifacts` | Relative directory; absolute paths, `..`, and project root rejected |
| `REGULATORY_MCP_GATEWAY_MODE` | `conventional` | `conventional` or `codemode` |
| `REGULATORY_MCP_ALLOWED_HOSTS` | `["api.regulations.gov","downloads.regulations.gov","www.federalregister.gov","www.reginfo.gov","api.census.gov","api.bls.gov"]` | JSON array of explicit lowercase DNS names; `[]` disables all destinations |
| `REGULATORY_MCP_HTTPS_PROXY` | unset | Optional explicit `http://` or `https://` proxy origin; treated as a masked secret because it may contain credentials |
| `REGULATORY_MCP_SOURCE_REQUEST_INTERVAL_SECONDS` | `4` | Finite seconds between attempts, 0.1–60; local pacing, not a verified source quota |
| `REGULATORY_MCP_REQUEST_TIMEOUT_SECONDS` | `30` | Finite number, greater than 0, at most 300 |
| `REGULATORY_MCP_MAX_RETRIES` | `2` | Integer, 0–5 |
| `REGULATORY_MCP_MAX_PAGES` | `20` | Integer, 1–100 |
| `REGULATORY_MCP_MAX_DOWNLOAD_BYTES` | `25000000` | Integer bytes, 1–100000000 |
| `REGULATORY_MCP_MAX_TOOL_CALLS` | `20` | Integer, 1–100 |
| `REGULATORY_MCP_MAX_CONCURRENCY` | `4` | Integer, 1–16 |
| `REGULATORY_MCP_EXECUTION_TIMEOUT_SECONDS` | `120` | Finite number, greater than 0, at most 600 |
| `REGULATORY_MCP_MAX_OUTPUT_BYTES` | `100000` | Integer bytes, 1–1000000 |

The initial host list does not imply that attachment hosts have been approved. WP-06 must verify those origins and redirect handling. DNS-name validation is not an SSRF defense by itself: the network adapter must also check resolved addresses. Storage must verify resolved paths and symlink containment before writes; syntactic path validation alone does not establish containment.

Direct source access rejects any fixed target hostname whose local DNS answers include a nonpublic address. In environments where an approved egress proxy performs target DNS and connection enforcement, set `REGULATORY_MCP_HTTPS_PROXY` explicitly. The application never reads generic `HTTP_PROXY`, `HTTPS_PROXY`, `ALL_PROXY`, or `NO_PROXY` variables. Proxy mode retains the fixed target allowlist, HTTPS target certificate and hostname verification, credential-origin restriction, redirect rejection, and request budgets. The proxy is part of the trusted network boundary and must independently prevent CONNECT requests from reaching prohibited destinations; see [ADR-0001](decisions/0001-use-an-explicit-egress-proxy-for-public-sources.md).

## Dependency selection

Direct package metadata was checked on PyPI during WP-01. FastMCP 4.1.4 and its `FastMCP.mount(..., namespace=...)` method imported successfully under Python 3.14.4. `fastmcp.experimental.transforms.code_mode.CodeMode` also imported; this establishes API availability, not cross-child execution or sandbox behavior.

FastMCP, Bandit, pip-audit, and detect-secrets declare Apache licensing; pydantic-settings, pytest, Ruff, mypy, and Hatchling declare MIT licensing. Preserve upstream licenses in redistribution. PyPI listed no advisories for the direct versions at selection time; the full locked dependency audit is part of verification. See `uv.lock` for the complete dependency inventory. New dependencies require reviewing package identity, compatibility, license, and advisories.
