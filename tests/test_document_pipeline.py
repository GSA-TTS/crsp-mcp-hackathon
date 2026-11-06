"""Real parser and MCP chains with synthetic documents; no external source claims."""

import asyncio
import base64
import io
from uuid import UUID

import pytest
from fastmcp import Client
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

from regulatory_mcp.analysis.server import create_analysis_server
from regulatory_mcp.config import Settings
from regulatory_mcp.contracts import Locator
from regulatory_mcp.evidence import EvidenceStore, StoreError
from regulatory_mcp.evidence.server import create_evidence_server
from regulatory_mcp.gateway import create_gateway
from regulatory_mcp.sources.documents.parsing import parse
from regulatory_mcp.sources.documents.pipeline import Documents


def sample_pdf():
    writer = PdfWriter()
    page = writer.add_blank_page(width=612, height=792)
    font = DictionaryObject(
        {
            NameObject("/Type"): NameObject("/Font"),
            NameObject("/Subtype"): NameObject("/Type1"),
            NameObject("/BaseFont"): NameObject("/Helvetica"),
        }
    )
    page[NameObject("/Resources")] = DictionaryObject(
        {NameObject("/Font"): DictionaryObject({NameObject("/F1"): writer._add_object(font)})}
    )
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 72 700 Td (Total cost   1000) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


def test_pdf_ingestion_search_selection_and_immutable_review(tmp_path):
    docs = Documents(EvidenceStore(tmp_path))
    result = docs.ingest(base64.b64encode(sample_pdf()).decode(), "application/pdf", "Fixture")
    artifact_id = UUID(result["artifact"]["artifact_id"])
    page = docs.page(artifact_id, 0, 0, 8000)
    assert "1000" in page["text"]
    assert docs.search(artifact_id, "total COST", 0, 1)["items"][0]["page_index"] == 0
    candidates = docs.table(artifact_id, 0, 0, 10)
    assert candidates["warnings"]
    start = page["text"].index("1000")
    locator = Locator(
        kind="pdf",
        page_index=0,
        start=start,
        end=start + 4,
        table_label="Fixture total",
        row="Total cost",
        column="USD",
    )
    evidence = docs.create_evidence(artifact_id, locator)
    assert evidence.content == "1000" and evidence.review_state == "unreviewed"
    reviewed = docs.review(evidence.evidence_id, "reviewed", "Confirmed fixture", True)
    assert reviewed.evidence_id != evidence.evidence_id
    assert docs.store.evidence(evidence.evidence_id).review_state == "unreviewed"
    assert str(evidence.evidence_id) in reviewed.transformations[-1]
    with pytest.raises(StoreError, match="confirmation"):
        docs.review(evidence.evidence_id, "reviewed", "Unconfirmed", False)
    with pytest.raises(StoreError, match="span outside"):
        docs.create_evidence(artifact_id, locator.model_copy(update={"end": 999999}))


@pytest.mark.parametrize("mode", ["conventional", "codemode"])
def test_csv_to_reviewed_calculation_through_gateway(tmp_path, mode):
    async def run():
        store = EvidenceStore(tmp_path)
        gateway = await create_gateway(
            {
                "documents": create_evidence_server(store),
                "analysis": create_analysis_server(store),
            },
            Settings(gateway_mode=mode),
        )
        async with Client(gateway) as client:

            async def call(name, args):
                if mode == "codemode":
                    return (
                        await client.call_tool(
                            "execute", {"code": f"return await call_tool({name!r}, {args!r})"}
                        )
                    ).data
                return (await client.call_tool(name, args)).structured_content

            uploaded = await call(
                "documents_ingest_upload",
                {
                    "content_base64": base64.b64encode(b"cost,flag\r\n1000,D\r\n,\r\n").decode(),
                    "media_type": "text/csv",
                    "title": "Synthetic cost",
                },
            )
            artifact = uploaded["artifact"]["artifact_id"]
            preview = await call("documents_extract_tables", {"artifact_id": artifact})
            assert preview["rows"][1]["cells"] == ["", ""]
            evidence = await call(
                "documents_create_evidence",
                {
                    "artifact_id": artifact,
                    "locator": {
                        "kind": "table",
                        "table_label": "cost.csv",
                        "row": "0",
                        "column": "cost",
                    },
                },
            )
            amount = {
                "name": "Synthetic cost",
                "value": evidence["content"],
                "unit": "USD",
                "dollar_year": 2014,
                "entity_definition": "Synthetic fixture",
                "basis": "reported",
                "evidence_refs": [evidence["evidence_id"]],
            }
            request = {
                "present_value": amount,
                "rate": "0",
                "payment_times": [1, 2],
                "monetary_basis": "real",
                "assumption_rationale": "Synthetic two-payment test",
            }
            with pytest.raises(Exception, match="INSUFFICIENT_EVIDENCE|Error calling"):
                await call("analysis_annualize_present_value", {"request": request})
            reviewed = await call(
                "documents_record_review",
                {
                    "evidence_id": evidence["evidence_id"],
                    "state": "reviewed",
                    "note": "Test fixture reviewed",
                    "confirmed": True,
                },
            )
            amount["evidence_refs"] = [reviewed["evidence_id"]]
            result = await call("analysis_annualize_present_value", {"request": request})
            assert float(result["outputs"]["payment"]) == 500
            saved = await call("documents_get_run", {"run_id": result["run_id"]})
            assert saved["inputs"][0]["evidence_refs"] == [reviewed["evidence_id"]]

    asyncio.run(run())


@pytest.mark.parametrize("data", [b"a,a\n1,2", b"a,b\n1", b"\xff", b'a\n"broken'])
def test_invalid_csv_retains_failed_artifact(tmp_path, data):
    docs = Documents(EvidenceStore(tmp_path))
    with pytest.raises(StoreError, match="retained artifact_id=") as error:
        docs.ingest(base64.b64encode(data).decode(), "text/csv", "Malformed")
    identifier = UUID(str(error.value).split("artifact_id=")[1])
    artifact = docs.store.artifact(identifier)
    assert docs.store.read_bytes(artifact.sha256) == data


def test_invalid_upload_and_parser_timeout(tmp_path, monkeypatch):
    import subprocess

    docs = Documents(EvidenceStore(tmp_path))
    with pytest.raises(StoreError, match="base64"):
        docs.ingest("not base64!", "text/csv", "Bad")
    with pytest.raises(StoreError, match="EXTRACTION_FAILED"):
        parse(b"%PDF-broken", "application/pdf")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired("parser", 20)

    monkeypatch.setattr("regulatory_mcp.sources.documents.parsing.subprocess.run", timeout)
    with pytest.raises(StoreError, match="EXTRACTION_TIMEOUT"):
        parse(b"a\n1", "text/csv")
