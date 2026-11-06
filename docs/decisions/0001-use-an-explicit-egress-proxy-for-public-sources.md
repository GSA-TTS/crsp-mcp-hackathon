---
title: "Use an Explicit Egress Proxy for Public Sources"
description: "Permit approved proxy egress without weakening fixed target or direct-DNS controls."
status: proposed
tier: 2
date: "2026-11-05"
last_updated: "2026-11-05"
decision_makers: ["project owner"]
nist_controls: ["AC-4", "CM-7", "SC-7", "SC-8", "SI-10"]
impact_level: "not claimed"
ato_relevance: "no"
risk_treatment: "mitigate"
related_files: ["../DEVELOPMENT.md", "../SOURCES.md", "../../src/regulatory_mcp/sources/http.py"]
---

# Use an explicit egress proxy for public sources

## Context and problem statement

The local sandbox resolves approved public-source hostnames through nonpublic egress addresses. The source transport intentionally rejects nonpublic DNS answers to reduce SSRF and network-boundary risk, so live source checks cannot run directly. How can an environment with an administratively approved egress proxy reach the fixed public sources without disabling the direct-mode protection?

## Decision drivers

- Preserve the fixed application target allowlist and fail-closed defaults.
- Preserve target TLS certificate and hostname verification.
- Prevent ambient process proxy variables from silently changing network behavior.
- Keep Regulations.gov credentials restricted to its approved target origin.
- Support environments where an approved proxy, rather than the application, resolves target DNS and enforces network egress.
- Avoid adding a dependency or a general-purpose URL retrieval capability.

## Considered options

1. **Remove public-address checks.** Rejected because direct requests could reach loopback, private, link-local, or metadata services after unsafe DNS resolution.
2. **Automatically trust standard proxy environment variables.** Rejected because ambient configuration would silently expand the trusted network boundary and could expose credentials to an unintended proxy.
3. **Add an explicit, opt-in HTTPS CONNECT proxy setting.** Selected. Direct mode remains unchanged; proxy mode delegates destination connection enforcement to a specifically configured trusted proxy while retaining application-layer target controls.
4. **Require public DNS/direct egress only.** Secure but does not support the approved proxy architecture used by constrained environments.

## Decision outcome

Add a masked `REGULATORY_MCP_HTTPS_PROXY` setting accepting one explicit HTTP(S) proxy origin. When absent, the client retains its local public-address DNS preflight. When present, the client does not resolve the fixed target locally and sends the original HTTPS hostname through an HTTP CONNECT tunnel. Generic proxy environment variables remain disabled with `trust_env=False`.

The application continues to require a fixed HTTPS target hostname, port 443, configured allowlisting, target TLS verification, no redirects, bounded response handling, and credential-to-target matching. The approved proxy becomes part of the trusted security boundary and must prevent CONNECT requests to prohibited destinations. This decision does not authorize arbitrary caller-provided URLs or attachment hosts.

## Consequences

### Positive

- Live public-source requests can use approved egress infrastructure.
- Existing direct-mode SSRF checks remain the default and are not weakened.
- Proxy configuration is explicit, reviewable, and masked because URLs may include credentials.
- No new package or custom tunneling implementation is introduced.

### Negative

- The application cannot validate the proxy's ultimate socket destination; proxy-mode safety depends on administrative proxy policy.
- Changing proxy configuration requires restarting the MCP process.
- Live acceptance still requires an approved proxy value and source credentials where applicable.

## Verification and review

Automated tests must prove direct private-DNS rejection, absence of local target DNS in proxy mode, explicit proxy use, disabled ambient proxy trust, redirect rejection, and credential-origin containment. An authorized live source check must be captured after the MCP process is restarted with approved proxy configuration. This proposed record requires project-owner review before acceptance.
