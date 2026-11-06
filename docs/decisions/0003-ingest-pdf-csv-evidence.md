---
title: "Ingest PDF and CSV into immutable reviewable evidence"
description: "Bounded parsers, source locations, and caller-attested evidence review."
status: proposed
tier: 2
last_updated: "2026-11-06"
date: "2026-11-06"
decision_makers: ["Project owner"]
category: "Data processing"
nist_controls: ["SI-10", "SA-11", "AU-3"]
impact_level: not-assessed
ato_relevance: no
risk_treatment: mitigate
related_files: ["../DOCUMENT_PIPELINE.md", "../IMPLEMENTATION_PIPELINE.md"]
---

# Ingest PDF and CSV into immutable reviewable evidence

## Context and Problem Statement

The owner approved Phase 1 with PDF and CSV. Existing MCP tools retrieved evidence
but could not create it from a supplied document. The FDA reproduction therefore
used manually transcribed assumptions rather than cited source selections.

## Decision Drivers

- Preserve the current artifact/evidence/run schemas and shared workspace.
- Support both stdio and hosted clients without exposing server filesystem paths.
- Distinguish extracted content, caller annotations, and review attestations.
- Bound parser work and explicitly report unsupported scanned documents.

## Considered Options

1. Manual transcription only: no parser dependency, but weak source traceability.
2. Pinned pypdf plus stdlib CSV in subprocesses: one dependency, text-native PDF
   support, 20-second parser deadline, 5 MB upload ceiling.
3. OCR service and spreadsheet execution: additional services and interfaces;
   unnecessary for the initial text-native FDA document.

## Decision Outcome

Implement option 2. Add pypdf 7.0.0 (BSD-3-Clause; PyPI reported no vulnerabilities
at the dependency check) and preserve its version in extracted evidence. Submit
base64 bytes through MCP, retaining original bytes before parsing so failures
can reference the retained source. Each read reparses the immutable artifact;
no search service or mutable extraction cache is introduced in this phase.

PDF tables are explicitly layout candidates, not verified semantic tables.
Offsets refer to pypdf layout text, not raw PDF byte offsets. CSV supports UTF-8
with optional BOM and comma-separated rectangular tables with unique headers.
Empty cells and suppression codes remain strings.

Review creates a new evidence UUID retaining the old content and locator, with
previous ID, note, and UTC time in the transformation trail. It is a caller
attestation, not authenticated individual identity or automatic human approval.
Corrections use a new source selection; old evidence is never rewritten.

## Consequences

Existing calculations can consume reviewed evidence IDs without changing schemas.
Parser subprocesses enforce a 20-second deadline and Linux address-space limit;
these are resource limits, not a general-purpose sandbox. Scanned/encrypted or
oversized PDFs fail or return explicit OCR-unavailable status. Reparsing increases
latency; large documents and OCR are separately sequenced work.

## Verification and Rollback

Exercise real parsers and both gateway modes with synthetic fixtures; demonstrate
the owner's FDA upload separately and request source confirmation. Revert tool
registration and dependency changes without removing existing evidence artifacts.
AI-assisted implementation remains subject to human review.
