---
title: "Host Regulatory MCP on cloud.gov with persistent object storage"
description: "Hosted transport, shared prototype authentication, and durable evidence decisions."
status: proposed
tier: 2
last_updated: "2026-11-05"
date: "2026-11-05"
decision_makers: ["Project owner"]
category: "Deployment Architecture"
nist_controls: ["AC-3", "SC-7", "SC-8", "SC-28", "CM-3"]
impact_level: not-assessed
ato_relevance: yes-boundary
risk_treatment: mitigate
related_files: ["../IMPLEMENTATION_PIPELINE.md", "0001-use-an-explicit-egress-proxy-for-public-sources.md"]
---

# Host Regulatory MCP on cloud.gov with persistent object storage

## Context and Problem Statement

The owner approved implementation targeting `sandbox-gsa / gsa.mcp.registry`,
with one shared evidence workspace. A stable remote MCP URL allows server updates
without rebuilding client sandboxes. The existing filesystem store cannot provide
durability across cloud.gov application replacements.

## Decision Drivers

- Preserve evidence schema v1, immutable writes, and content digest checks.
- Reuse the existing mounted tools and bounded source adapters.
- Keep client configuration independent of deployment revisions.
- Require access control for the publicly routed shared prototype.

## Considered Options

1. Local stdio only: zero hosted services, but each sandbox installs the server.
2. Hosted HTTP plus S3: one app and one storage service, sufficient for ID lookups.
3. Hosted HTTP plus S3 and SQL: two storage services; relational queries are not needed.

## Decision Outcome

Implement option 2. Use stateless Streamable HTTP at `/mcp`, one process/instance,
and one private S3 bucket for both JSON records and content-addressed blobs.
Conditional creates preserve immutability under concurrent writes. The local
stdio entry point continues to use filesystem storage. Storage I/O from async
tools runs in worker threads with bounded SDK requests.

The owner selected a shared bearer token for the prototype after considering
OAuth. Compare tokens in constant time and require an environment-provided
high-entropy token for HTTP startup. No browser sign-in or per-user ownership is
claimed. All token holders can access the shared workspace. Rotate the token
through server and client secret configuration. Public-source credentials stay
server-side and never substitute for client authentication.

### Positive Consequences

- Reuses schema v1 without database migrations.
- Persisted artifacts and calculations survive application replacement.
- One stable client endpoint; local development remains available.

### Negative Consequences

- Shared credentials do not identify individual users.
- SDK calls have bounded timeouts but a cancelled request may finish a storage write.
- Process-local pacing requires one instance and stop/start deployment to avoid overlap.
- Service availability, buildpack support, and live client compatibility need platform checks.

### Compliance Consequences

This is a public-source team prototype, not an ATO or FIPS impact-level claim.
Require TLS at the route, encrypted private storage, validated service bindings,
masked configuration, bounded requests, and no request-body/token logging.
Direct source destination validation remains active; the separately reviewed
explicit proxy is only used when deliberately configured.

## Verification and Rollback

WP-14 through WP-18 in the pipeline track implementation and live gates. Validate
HTTP auth, persistence conflicts/integrity, restart retrieval, upstream egress,
and client reconnect. Roll back the application revision without deleting the
bucket. Dependency upgrades and future identity-provider changes need review.
