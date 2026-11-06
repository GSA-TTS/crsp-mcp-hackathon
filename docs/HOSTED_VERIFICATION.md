---
title: "Hosted implementation verification transcript"
description: "AI implementation checks and explicitly blocked cloud.gov acceptance gates."
status: draft
tier: 2
last_updated: "2026-11-05"
related_files: ["DEPLOYMENT.md", "IMPLEMENTATION_PIPELINE.md", "decisions/0002-host-regulatory-mcp-on-cloudgov.md"]
---

# Hosted implementation verification

AI assistance: OpenCode / GPT 6 Astra. Mode: owner-approved scoped implementation,
including a subsequently approved shared bearer token. Target selected by owner:
`sandbox-gsa / gsa.mcp.registry`. Human review remains pending.

## Context and approved changes

WP-14–WP-16 implement shared stdio/HTTP tool assembly, authenticated stateless
HTTP, an S3 byte-store beneath the existing schema/integrity checks, worker-thread
storage calls, and a locked deployment payload. New runtime dependency: boto3
1.43.125 (Apache-2.0), with resolved dependencies retained in `uv.lock`. Existing
Uvicorn 0.54.0 and Starlette 1.10.0 are now explicit direct dependencies.
PyYAML 6.0.3 is explicitly declared for deployment tests.

Existing uncommitted proxy changes and their tests were present before this
task. The baseline `make check-offline` passed 111 tests at 2026-11-05 20:32 UTC.

## Commands and observed results

Environment: Linux, Python 3.14.4, FastMCP 4.1.4.

Deployment-runtime correction after owner preflight: upstream Python buildpack
v1.9.4 lists 3.14.7 for the target stacks, not 3.14.4. The generated runtime and
build manifest now both pin 3.14.7. This is a deployment configuration correction;
it does not establish execution on that patch or successful CF staging.

| Command / check | Observed result |
|---|---|
| `uv lock`, `uv sync --locked` | PASS; added boto3 and five transitive dependencies without changing existing resolved versions |
| `make check` | PASS at 2026-11-05 20:44 UTC: Ruff lint/format, strict mypy, 137 tests, Bandit, secret scan, sdist/wheel build, dependency audit |
| `make package-cloudgov` | PASS; generated hashed runtime requirements, wheel, runtime pin, upload allowlist and build digests |
| `uv pip sync --require-hashes --offline requirements.txt` in a fresh local environment | PASS; 74 runtime packages installed from the generated payload/cache |
| Final payload import and SHA-256 check | PASS; packaged HTTP entry point imports and wheel digest matches build manifest |
| `git diff --check` | PASS |
| Real ASGI/MCP tests | PASS; health, 401 for missing/wrong token, initialization, catalog, calculation, retrieval after app recreation, untrusted Origin rejection |
| S3 SDK Stubber tests | PASS; bound credentials, fixed GovCloud endpoint, conditional creates/conflicts, bounded closed streams, masked errors, records/blobs and digest verification |
| Local filesystem / stdio tests | PASS; original integrity and gateway tests remain active |
| CF staging and live S3 persistence | BLOCKED; no CF CLI/session in implementation sandbox |
| Hosted upstream calls and actual remote OpenCode client | BLOCKED on provisioned app and operator credentials; not inferred from fixture/ASGI tests |

Initial failures were resolved: missing work-package headings, a synthetic
quantity incorrectly carrying a dollar year, import/export/style issues, and
secret-scanner matches on dummy credential literals (now runtime-generated).
The all-interface address declaration has one reviewed B104/S104 exception:
cloud.gov needs that binding, loopback remains default, and public configuration
requires authentication, HTTPS external origin and durable storage.

## Review focus and limits

- Shared token gives every holder access to the shared workspace; no individual identity claim.
- Immutable S3 creates and schema/hash checks preserve evidence semantics; Stubber
  is not live service verification. WP-17 requires restart/redeploy retrieval.
- SDK calls in worker threads can complete after request cancellation; bounded
  SDK timeouts do not make remote writes cancellable.
- Keep one instance/process and stop/start updates until WP-18 coordinates quotas.
- Existing nested tool-registration functions exceed the 50-line guideline when
  measured including their nested handlers. `create_analysis_server` is cohesive
  registration of six tools; the only relevant change is offloaded persistence.
  Existing Regulations registration and proxy transport exceptions predate this
  task. All new production modules remain below 400 lines and new standalone
  functions below 50 logic lines.

## Rollback

Revert the hosted implementation through review, preserving any unrelated proxy
work. For an already deployed instance, stop it and push the previous reviewed
package to the same route and S3 binding. Never delete the bucket for application
rollback. No deployment, commit, push, service provisioning, or secret mutation
was performed by this implementation session.
