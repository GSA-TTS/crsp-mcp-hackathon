---
title: "Rule document collection"
description: "Bounded docket manifests and metadata-selected public document downloads."
status: draft
tier: 2
last_updated: "2026-11-06"
related_files: ["DOCUMENT_PIPELINE.md", "IMPLEMENTATION_PIPELINE.md", "decisions/0004-collect-regulations-documents.md"]
---

# Rule document collection

Phase 2 begins with Regulations.gov. The adapter can assemble one bounded docket
page and retrieve selected source files into the existing evidence workflow.

- `regulations_collect_docket_page(docket_id, search_term, page, page_size)`
  retains a derived manifest containing docket and search artifact IDs, source
  document types/dates/FR citations, retrieval scope, and next page. Maximum 25
  documents per page; the existing 20-page retrieval-window limit remains.
- `regulations_list_document_files(document_id)` returns primary and included
  attachment record IDs, formats, sizes, and URLs from fresh API metadata.
- `regulations_retrieve_document_file(document_id, record_id, format_name)`
  re-fetches metadata, requires exactly one matching file, and downloads PDF/CSV
  bytes from `downloads.regulations.gov` under the document's path. API credentials
  are never forwarded. Queries, fragments, traversal, and redirects are rejected.

Successful downloads return the retained source artifact plus the metadata
artifact ID and can be passed directly to `documents_read_page`,
`documents_extract_tables`, and `documents_create_evidence`. The 5 MB parser ceiling
applies. Failed parsing preserves the download and reports its artifact ID.

Collection manifests are derived, not agency-authored source artifacts. The source
metadata IDs are retained inside the manifest. A file that changed upstream gets
new retained bytes/hash; matching titles, dates, docket IDs, or RINs alone do not
prove a proposed/final/revised relationship. Unsupported file formats remain
visible in listings. Source content and reviewer attestations remain distinct.

## Federal Register prerequisite

FederalRegister.gov documentation and API requests returned sandbox network-policy
403 responses on 2026-11-06. A GitHub source-path lookup also failed with 404.
The owner agreed to upload a public document JSON response from the Mac, using
`https://www.federalregister.gov/api/v1/documents/2016-11867.json` as a candidate.
The owner supplied that response: final rule, publication 2016-05-27, citation
81 FR 33742, RIN 0910-AF22, docket FDA-2012-N-1210, 21 CFR part 101. This verifies
the sample's identity and field shapes, not independent live retrieval here.

Implemented tools:

- `federal_register_get_document(document_number)` requests the fixed HTTPS
  document endpoint, verifies identity, retains full JSON, and returns selected
  source fields including RINs, docket strings, CFR references and correction links.
- `federal_register_import_document_json(document_number, content_json)` accepts
  JSON obtained by the operator, retains it explicitly as user-supplied with no
  independently retrieved URL claim, and validates the same schema.
- `federal_register_inspect_supporting_documents(artifact_id, offset, limit)` pages
  through the retained embedded list, preserving its lookup timestamp and reported
  count. The sample reports 435 supporting documents but embeds ten, checked in
  June 2016. Exhausting those ten does not imply complete or current coverage.

Linked PDF/XML/HTML URLs are metadata only. Dates and correction relationships are
source assertions, not verified current compliance dates or complete version history.
The original publication's compliance dates may have changed in subsequent rules.
`federal_register_search_documents(search_term, page=1, page_size=5)` now implements
the keyword search request and envelope supplied by the owner. It supports 1–5
results per page and at most 20 pages (also constrained by configured max_pages).
It preserves source order, reported count/total_pages, next page, and the full raw
response artifact. The next request is rebuilt from typed parameters rather than
following the upstream URL. A final page is not proof of a complete snapshot.

The supplied `FDA-2012-N-1210` query reports 20 matches over four pages. Results
include a later compliance-date extension (2018-09476), technical amendments
(2018-27431), a small-entity guide (2020-01165), and documents merely mentioning
the docket, including USDA's bioengineered-food disclosure rule (2018-27283).
Therefore this is keyword discovery, not exact docket membership or a chronological
version chain. Fetch selected document details to inspect source relationships.
Automatic proposed/final version resolution is not implemented.
Tests use a clearly labeled reduced transcription of the supplied record, not a
byte-identical copy of the operator's downloaded response.

## Live input observation

The existing hosted MCP returned `FDA-2012-N-1210-0549`, a supporting-material record,
with a primary PDF at `https://downloads.regulations.gov/FDA-2012-N-1210-0549/content.pdf`
and reported size 323322 bytes. That is a supplemental proposed-analysis reference,
not a verified match for the owner's final RIA. Local tests use synthetic fixtures;
live download availability must be established after deployment/egress approval.
