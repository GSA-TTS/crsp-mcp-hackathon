---
title: "Collect metadata-selected Regulations.gov documents"
description: "Fixed-host attachment retrieval and traceable bounded collection manifests."
status: proposed
tier: 2
last_updated: "2026-11-06"
date: "2026-11-06"
decision_makers: ["Project owner"]
nist_controls: ["SC-7", "SI-10", "AU-3"]
impact_level: not-assessed
ato_relevance: no
risk_treatment: mitigate
related_files: ["../RULE_COLLECTION.md", "../IMPLEMENTATION_PIPELINE.md"]
---

# Collect metadata-selected Regulations.gov documents

## Context and Decision Drivers

Owner authorized publishing Phase 1 and starting Phase 2 on the FDA dockets.
Phase 1 parses supplied bytes; reviewers also need independently retrieved originals
and a traceable inventory of relevant supporting materials.

## Considered Options

1. Manual uploads only: no added download destination, but manual source discovery.
2. Record-ID selected files on a fixed host: one additional allowed hostname and
   reuse of existing transport, storage and parser limits.
3. General URL crawler: unbounded origin scope and unverifiable completeness.

## Decision Outcome

Use option 2. Add `downloads.regulations.gov` to explicit default origins and
configuration; require fresh document metadata to select a file. Record ID and
format avoid relying on unstable attachment ordering. Download without source API
credentials; require HTTPS and a path rooted in the selected document ID. Preserve
transport redirects rejection, deadline, byte bounds, and DNS/proxy policy.

## Consequences

Reuse immutable artifact IDs and Phase 1 parsing with no new dependencies or
services. Unsupported hosts/formats fail explicitly. Docket inventories remain
bounded pages and make no exhaustive-collection or automatic-version-link claim.
Federal Register integration is blocked on source contract/access verification;
owner assistance is recorded in the task ledger.

Owner-supplied Federal Register JSON subsequently established the document-detail
contract. Add `www.federalregister.gov` to the fixed origins and register detail,
user-supplied JSON import, and embedded-supporting-list inspection tools. Preserve
source-reported RIN/docket/CFR/correction fields without claiming complete version
resolution. Imported JSON remains user-supplied; live GET remains blocked by the
sandbox network policy. No new dependencies or additional download hosts are needed.
The owner subsequently supplied the keyword search response for
`conditions[term]=FDA-2012-N-1210`, `per_page=5`, `page=1`: count 20, total_pages 4,
next_page_url and five results. Implement bounded keyword search from this contract,
preserving result order and reconstructing page requests without following returned
URLs. Cross-agency mentions must not be treated as exact docket membership.

## Verification and Rollback

Fixture tests run source metadata → file download → retained table inspection in
both gateway modes and exercise partial manifests and rejected locations. Live
upstream validation is distinct. Revert tool registration/host addition while
retaining artifacts. AI implementation awaits human review.
