"""Fetch fixed public reports and inspect retained snapshots with stable locators."""

import hashlib
from typing import Any, Literal
from uuid import UUID

from defusedxml.common import DefusedXmlException
from defusedxml.ElementTree import ParseError, fromstring

from regulatory_mcp.evidence import EvidenceStore
from regulatory_mcp.sources.http import PublicHTTP, SourceError

Report = Literal["oira_pending", "oira_completed_30_days", "agenda_202510", "pra_pending"]
REPORTS: dict[str, tuple[str, str, str]] = {
    "oira_pending": (
        "https://www.reginfo.gov/public/do/XMLViewFileAction?f=EO_RULES_UNDER_REVIEW.xml",
        "OIRA_DATA",
        "REGACT",
    ),
    "oira_completed_30_days": (
        "https://www.reginfo.gov/public/do/XMLViewFileAction?f=EO_RULE_COMPLETED_30_DAYS.xml",
        "OIRA_DATA",
        "REGACT",
    ),
    "agenda_202510": (
        "https://www.reginfo.gov/public/do/XMLViewFileAction?f=REGINFO_RIN_DATA_202510.xml",
        "REGINFO_RIN_DATA",
        "RIN_INFO",
    ),
    "pra_pending": (
        "https://www.reginfo.gov/public/do/PRAXML?type=pending",
        "InformationCollectionRequestList",
        "InformationCollectionRequest",
    ),
}


def parse(raw: bytes, report: str) -> Any:
    try:
        root = fromstring(raw, forbid_dtd=True, forbid_entities=True, forbid_external=True)
    except (ParseError, DefusedXmlException) as exc:
        raise SourceError("SCHEMA_MISMATCH: malformed or unsafe XML") from exc
    if root.tag != REPORTS[report][1]:
        raise SourceError("SCHEMA_MISMATCH: unexpected report root")
    if any(child.tag != REPORTS[report][2] for child in root):
        raise SourceError("SCHEMA_MISMATCH: unexpected report record type")
    return root


def fields(node: Any, report: str, index: int) -> dict[str, Any]:
    if report.startswith("oira"):
        mapping = {
            "rin": "RIN",
            "title": "TITLE",
            "agency_code": "AGENCY_CODE",
            "stage": "STAGE",
            "date_received": "DATE_RECEIVED",
            "date_completed": "DATE_COMPLETED",
            "decision": "DECISION",
            "economically_significant": "ECONOMICALLY_SIGNIFICANT",
        }
        record_type = "oira_review"
    elif report.startswith("agenda"):
        mapping = {
            "rin": "RIN",
            "title": "RULE_TITLE",
            "agency_code": "AGENCY/CODE",
            "publication_id": "PUBLICATION/PUBLICATION_ID",
            "stage": "RULE_STAGE",
            "priority": "PRIORITY_CATEGORY",
            "abstract": "ABSTRACT",
        }
        record_type = "agenda_entry"
    else:
        mapping = {
            "omb_control_number": "OMBControlNumber",
            "icr_reference": "ICRReferenceNumber",
            "title": "Title",
            "agency_code": "AgencyCode",
            "submission_date": "SubmissionDate/Date",
            "requested_hours": "RequestBurden/TotalRequestHour",
            "requested_responses": "RequestBurden/TotalRequestResponse",
            "requested_cost": "RequestBurden/TotalRequestCost",
        }
        record_type = "pra_request"
    result: dict[str, Any] = {
        key: node.findtext(path) for key, path in mapping.items() if node.find(path) is not None
    }
    identity = result.get("icr_reference") if record_type == "pra_request" else result.get("rin")
    if not identity or not result.get("title"):
        raise SourceError("SCHEMA_MISMATCH: record lacks identity or title")
    # Snapshot position disambiguates repeated reviews sharing a RIN.
    result.update(
        record_type=record_type,
        snapshot_index=index,
        record_id=hashlib.sha256(f"{report}:{index}:{identity}".encode()).hexdigest(),
    )
    return result


class Reginfo:
    def __init__(self, store: EvidenceStore, http: PublicHTTP):
        self.store, self.http = store, http

    async def fetch(self, report: Report) -> dict[str, Any]:
        if report not in REPORTS:
            raise SourceError("UNSUPPORTED_CAPABILITY: unknown report")
        url = REPORTS[report][0]
        raw = await self.http.get(url)
        root = parse(raw, report)
        for index, node in enumerate(root):
            fields(node, report, index)
        artifact = self.store.retain(
            raw,
            source_system="reginfo.gov",
            source_url=url,
            source_record_id=report,
            origin="retrieved",
            media_type="application/xml",
            dataset_vintage="202510" if report == "agenda_202510" else None,
        )
        return {
            "artifact_id": str(artifact.artifact_id),
            "sha256": artifact.sha256,
            "report": report,
            "record_count": len(root),
            "source_attributes": root.attrib,
            "retrieved_at": artifact.retrieved_at.isoformat(),
            "coverage": "Downloaded report only; excludes other history and private ROCIS data.",
        }

    def inspect(
        self, artifact_id: UUID, query: str = "", offset: int = 0, limit: int = 10
    ) -> dict[str, Any]:
        if not 0 <= offset or not 1 <= limit <= 50 or len(query) > 500:
            raise SourceError(
                "INVALID_INPUT: require nonnegative offset, limit 1–50, query length at most 500"
            )
        artifact = self.store.artifact(artifact_id)
        report = artifact.source_record_id
        if artifact.source_system != "reginfo.gov" or report not in REPORTS:
            raise SourceError("INVALID_REFERENCE: expected a Reginfo report artifact")
        root = parse(self.store.read_bytes(artifact.sha256), report)
        matches = []
        for index, node in enumerate(root):
            record = fields(node, report, index)
            if query.casefold() in " ".join(str(v) for v in record.values()).casefold():
                matches.append(record)
        end = offset + limit
        return {
            "items": matches[offset:end],
            "artifact_id": str(artifact_id),
            "report": report,
            "matched_count": len(matches),
            "next_offset": end if end < len(matches) else None,
            "retrieval_status": "partial" if offset > 0 or end < len(matches) else "complete",
            "query_scope": {"query": query, "artifact_id": str(artifact_id)},
            "warnings": [
                "Snapshot-relative IDs require artifact_id for cross-snapshot identity.",
                "Original dates/quantities are preserved as strings; contact fields omitted.",
            ],
        }
