---
title: "PDF and CSV document evidence tools"
description: "Ingest public documents, inspect source selections, and record review attestations."
status: draft
tier: 2
last_updated: "2026-11-06"
related_files: ["IMPLEMENTATION_PIPELINE.md", "decisions/0003-ingest-pdf-csv-evidence.md"]
---

# Document evidence pipeline

The document tools close the source-to-calculation gap: original bytes are retained,
extraction provides stable coordinates, and reviewed evidence can back calculation
inputs. The shared workspace and bearer authentication remain the same.

## Tools (both stdio and hosted HTTP)

| Tool | Inputs and behavior |
|---|---|
| `documents_ingest_upload` | Base64 bytes, `application/pdf` or `text/csv`, title. At most 5 MB decoded and the configured download limit. Returns artifact metadata and page/data-row count. |
| `documents_read_page` | Artifact ID, zero-based PDF page, character offset and limit. Returns text, next offset and extraction version. |
| `documents_search_passages` | Artifact ID, literal query, start page and up to 20 pages. Case-insensitive, first matching excerpt per page; next page identifies continuation. |
| `documents_extract_tables` | Artifact ID, PDF page (CSV ignores it), row/line offset and up to 20 rows. CSV returns strings and headers; PDF returns layout candidates with exact spans. |
| `documents_create_evidence` | Artifact ID plus locator. PDF requires `kind=pdf`, zero-based page and half-open text span; CSV requires `kind=table`, table label, zero-based data row as a string, and exact header as column. |
| `documents_record_review` | Evidence ID, `reviewed` or `ambiguous`, note, and explicit `confirmed=true`. Creates a new immutable evidence record with review trail. |

Existing `documents_get_artifact`, `documents_get_evidence`, and `documents_get_run`
resolve retained records. A corrected selection creates new evidence. Review does
not overwrite or correct the source content. Caller-supplied table labels, units
in annotations, and printed-page labels must be confirmed against the source.

## Evidence to calculation

1. Encode the uploaded bytes in the client; server-local paths are not accepted.
2. Ingest and retain the returned artifact ID.
3. Inspect page text/table candidates, including surrounding headers and footnotes.
4. Select a cell or exact passage into unreviewed evidence.
5. Have a reviewer confirm its context and record that attestation. AI agents must
   not infer human approval. Store the returned **new** reviewed evidence ID.
6. Use that ID in `CalculationInput.evidence_refs`, with `basis=reported` and
   explicit units/dollar year. Derived normalization (millions to USD, for example)
   must be explained in the calculation rationale. A reference establishes lineage,
   not automatic proof that the supplied number matches the source.

## Limits

- PDF: text-native documents, at most 300 pages and two million extracted characters.
  Scanned pages with no text report that OCR is unavailable. Layout-based columns
  need review, especially merged headers, footnotes, negatives, and split rows.
- CSV: UTF-8/BOM, comma-delimited, at most 100 columns and 20,000 data rows; unique
  nonempty headers and rectangular records. No type coercion or formula execution.
- Parser: subprocess, 20-second deadline; Linux 256 MB address-space limit. PDF
  expanded page content is limited to 10 MB. Mac uses the time and logical limits.
- Failed extraction retains the original and reports its artifact ID. Invalid
  encoding or upload size fails before retention. Page reads and previews are bounded;
  reduce requested rows if a preview exceeds its byte budget.
- Search covers only the requested page range and reports first matches, not all
  occurrences. Parsing is repeated on reads; this version has no extraction cache.
- The remote server cannot read a sandbox upload path. Clients must transfer bytes.
  The uploaded PDF does not automatically become an independently retrieved original.

## Verification

Synthetic PDF/CSV tests exercise parsing, exact selections, immutable review,
malformed inputs, parser deadline handling, and a reviewed-input calculation through
both gateway modes. The FDA upload is a separate published-input demonstration.
