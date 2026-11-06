---
title: "Deploy the shared Regulatory MCP prototype to cloud.gov"
description: "Build, provision, configure, verify, and roll back the hosted MCP service."
status: draft
tier: 2
last_updated: "2026-11-05"
related_files: ["../manifest.yml", "../Makefile", "DEVELOPMENT.md", "IMPLEMENTATION_PIPELINE.md", "decisions/0002-host-regulatory-mcp-on-cloudgov.md"]
---

# Hosted Regulatory MCP

The hosted prototype lets sandboxes use a stable HTTPS `/mcp` endpoint while the
operator updates server code independently. It serves one shared workspace:
every holder of the shared bearer credential can retrieve records by ID and
create calculations. This is not per-user isolation or an OAuth login service.
The owner approved a shared bearer token for this prototype. AI-assisted code
requires human review before production use.

## Runtime and storage

- Local stdio: `uv run --locked python -m regulatory_mcp` uses local artifacts.
- HTTP: `python -m regulatory_mcp.http_server` requires a bearer token and public URL.
- FastMCP serves stateless Streamable HTTP with JSON responses at `/mcp`.
- `/health` is an unauthenticated process-liveness endpoint; it does not prove S3 or upstream health.
- cloud.gov terminates TLS; one Uvicorn process listens on the supplied `PORT`.
- A private S3 binding retains JSON records and content-addressed blobs under
  `evidence/v1/`. Existing schema-v1 IDs and hashes are preserved. No SQL service is needed.
- S3 writes use `If-None-Match: *` and server-side AES256 encryption. A conflicting
  object is never overwritten. Reads revalidate manifests and content digests.
  Bucket-level versioning/retention/recovery policy must be verified by the operator;
  conditional writes are not a replacement for backups or Object Lock.
- Synchronous storage SDK calls run in worker threads. SDK connect/read timeouts
  are 5/10 seconds with at most two attempts. Cancellation may leave a write
  completing in its worker; successful results always include the persisted run ID.

## Configuration

All settings come from the server process environment, not `.env` files. Do not
commit secret values, CF service bindings, or client credentials.

| Variable | Meaning |
|---|---|
| `REGULATORY_MCP_BEARER_TOKEN` | Required secret, 32–512 non-whitespace ASCII characters. Generate at least 32 random bytes with an approved secret manager. Share only with authorized clients. |
| `REGULATORY_MCP_PUBLIC_URL` | Required external HTTPS origin, without `/mcp`, credentials, query, or fragment. HTTP is allowed only for `127.0.0.1` tests. |
| `REGULATORY_MCP_BIND_HOST` | `127.0.0.1` by default; manifest uses `0.0.0.0`. Public binding requires HTTPS public URL and S3. |
| `PORT` | Valid TCP port; defaults to 8000 locally, supplied by cloud.gov when hosted. |
| `REGULATORY_MCP_STORAGE_BACKEND` | `s3` by default. `local` is for loopback tests only. |
| `REGULATORY_MCP_S3_SERVICE_NAME` | Exact bound service instance name; defaults to `regulatory-mcp-evidence`. |
| `VCAP_SERVICES` | Platform-injected JSON. Exactly one named binding must contain `bucket`, `region`, `access_key_id`, and `secret_access_key`. Supported regions: `us-gov-west-1`, `us-gov-east-1`. Other fields are ignored. |
| `REGULATIONS_GOV_API_KEY` | Optional to start; required for Regulations.gov tool calls. Sent only as `X-Api-Key` to the fixed source origin. |
| `CENSUS_API_KEY` | Optional secret token; required for authenticated Census table queries. Per repository `AGENTS.md` exception, transmitted only over HTTPS to `api.census.gov` via query parameter, never logged or stored in artifact provenance. |

The S3 client uses explicit binding credentials, verified HTTPS and the SDK's
GovCloud S3 endpoint. It does not use ambient proxies or metadata credentials.
The existing source allowlist, redirect rejection, request limits, and direct-mode
public DNS validation apply to upstream APIs. Leave `REGULATORY_MCP_HTTPS_PROXY`
unset on cloud.gov unless an approved proxy is deliberately required.

## Operator preflight (on the Mac with CF access)

The selected target is `sandbox-gsa / gsa.mcp.registry`. Login remains interactive;
the agent's Linux sandbox does not inherit the Mac's CF session.

```sh
cf target -o sandbox-gsa -s gsa.mcp.registry
cf buildpacks
cf marketplace -e s3
cf services
cf domains
```

Before pushing, verify:

1. The selected Python buildpack supplies **Python 3.14.7** and can install the
   pinned Linux dependencies (including Monty). `runtime.txt` pins that runtime;
   do not silently fall back to an unsupported Python minor version.
2. This space permits an S3 service plan with the binding shape above, private
   encrypted objects, and conditional PutObject. Use the actual marketplace
   plan name, rather than assuming a plan available to another organization.
3. Available memory/disk/service quotas cover the proposed 512 MB app and bucket.
   Verify sandbox expiration and data-retention terms before retaining real work.
4. The chosen app route is available, and router request timeouts accommodate
   the configured tool deadline. Keep one app instance and one worker process.

Owner preflight on 2026-11-05 confirms Python buildpack v1.9.4, the private
`s3 / basic-sandbox` plan, and the shared `app.cloud.gov` domain. The upstream
[v1.9.4 manifest](https://github.com/cloudfoundry/python-buildpack/blob/v1.9.4/manifest.yml)
lists Python 3.14.7 on cflinuxfs4 and cflinuxfs5. The deployment payload pins that
patch; local tests ran on 3.14.4. Actual staging, service binding shape and live
durability remain WP-17 gates. Use the private plan, not `basic-public-sandbox`.

## Package and configure

From the repository on a prepared Python 3.14 environment:

```sh
make setup
make check
make package-cloudgov
```

The package command creates `dist/cloudgov/`: the project wheel, hashed runtime
requirements exported from `uv.lock`, exact `runtime.txt`, upload allowlist, and
a build manifest with wheel/lock digests. It excludes development dependencies.
No application dependencies are installed during runtime startup.

Create the private service and choose an available route:

```sh
cf create-service s3 basic-sandbox regulatory-mcp-evidence
cf service regulatory-mcp-evidence
```

Wait until the service reports successful creation, then upload the application:

```sh
printf 'Available MCP hostname (no scheme/path): '
read -r MCP_ROUTE
cf push -f manifest.yml --var "mcp-route=$MCP_ROUTE" --no-start
```

On subsequent
deployments reuse the existing service. The manifest binds it by name.

Configure `REGULATORY_MCP_BEARER_TOKEN` and `REGULATIONS_GOV_API_KEY` through the
operator's approved cloud.gov secret-delivery workflow before starting. CF
supports app environment variables; avoid putting their literal values in shell
history, committed vars files, chat, or deployment logs. `acq secret set` only
configures sandbox secrets and does not configure the cloud.gov application.
Do not paste `cf env` output: it includes bound service credentials.

```sh
cf start regulatory-mcp
cf app regulatory-mcp
curl --fail --max-time 20 "https://$MCP_ROUTE/health"
```

An HTTP MCP request without the bearer token must return 401. Health success
alone is not deployment acceptance.

## Client configuration and sandbox kit

Register the HTTPS endpoint with a secret-sourced `Authorization: Bearer …`
header using the client's supported remote MCP configuration. Disable OAuth
auto-discovery for this shared-token prototype; it has no sign-in flow. Consult
the installed OpenCode V2 MCP CLI/config documentation for the exact header and
environment-substitution syntax. Never put the token directly into the kit.

The client sandbox kit only needs access to the chosen MCP hostname and remote
registration. It does not need Python dependencies, upstream API egress, or the
Regulations.gov key. Refresh the connection/tool catalog after server changes.
Rotate the shared token on both server and clients, then restart the app.

## Acceptance and repeatable updates

Record UTC timestamps, revision/build digests, and actual outputs under WP-17:

1. Missing/wrong bearer tokens yield 401; correct token initializes MCP and lists tools.
2. Run a synthetic `analysis_calculate_break_even` (1000 USD / 100 units = 10),
   retain its run ID, and retrieve it with `documents_get_run`.
3. Restart/redeploy, reconnect, and retrieve that same run. This is the durability gate.
4. Run bounded BLS, Census, Reginfo and credentialed Regulations.gov calls.
   Check destination validation, provenance and coverage; do not call a blocked
   source a pass based on fixture tests.
5. Run from an actual OpenCode/Paseo sandbox with the configured remote header.

Use stop/start updates for this prototype, because upstream pacing is per process:

```sh
make check
make package-cloudgov
cf stop regulatory-mcp
cf push -f manifest.yml --var "mcp-route=$MCP_ROUTE"
```

This deliberately has downtime. Multiple instances, workers, or rolling/blue-green
overlap require WP-18 quota coordination first. In-flight requests may be
interrupted; stateless transport does not guarantee request replay or resumption.

### Redeploy the Census integration and authentication fixes

Run on the Mac from the repository root after reviewing the AI-assisted changes.
The existing app route is `crsp-regulatory-mcp.app.cloud.gov`; reuse the existing
S3 binding and server credentials. Execute each command only after the preceding
command succeeds. If the CF session has expired, first run
`cf login -a https://api.fr.cloud.gov --sso`.

```sh
make setup
make check
make package-cloudgov
cf target -o sandbox-gsa -s gsa.mcp.registry
cf app regulatory-mcp
cf service regulatory-mcp-evidence
cf stop regulatory-mcp
cf push -f manifest.yml --var 'mcp-route=crsp-regulatory-mcp.app.cloud.gov'
```

If you have a Census API key/token to configure on the hosted server, set it as an
environment variable using cloud.gov CLI (do not paste it in chat or commits):

```sh
cf set-env regulatory-mcp CENSUS_API_KEY "<your-census-token>"
cf restart regulatory-mcp
```

Then check health:

```sh
cf app regulatory-mcp
curl --fail --silent --show-error --max-time 20 \
  'https://crsp-regulatory-mcp.app.cloud.gov/health'
curl --silent --show-error --max-time 20 --output /dev/null \
  --write-out '%{http_code}\n' \
  'https://crsp-regulatory-mcp.app.cloud.gov/mcp'
```

The health request must succeed and the unauthenticated MCP request must print
`401`. Reconnect the authenticated `regulatory-cloud` client and verify:

1. `census_get_variables(dataset="2023/cbp", query="ESTAB", limit=10)` returns
   compact summaries instead of a byte-limit error. Its metadata artifact resolves
   through `documents_get_artifact`.
2. `census_fetch_table(dataset="2023/cbp", variables=["ESTAB", "ESTAB_F"],
   geography="us:1")` passes flag validation. With `CENSUS_API_KEY` set, it
   retrieves and retains the table without leaking the key into `source_url`.
   Without the key, it returns `MISSING_CREDENTIALS`.
3. `documents_get_run(run_id="db7c01d8-94d7-4aa6-b98b-a10a25e6718b")` still returns
   the synthetic annualized payment `1000`; this pre-deployment run is the durable
   storage check. Record the real results under WP-17.

Rollback: stop the application, push the previously reviewed source/package at
the same route with the same service binding, then verify an existing run ID.
Do not delete/recreate the S3 service during rollback. Local artifact migration
was not requested; existing local records are not automatically uploaded.

## Verification labels

Local SDK Stubber tests establish expected S3 requests and error handling, not a
live S3 pass. In-process ASGI tests establish the real HTTP protocol/auth wiring,
not router or remote-client compatibility. Deployment remains blocked until the
operator completes the live acceptance sequence above.
