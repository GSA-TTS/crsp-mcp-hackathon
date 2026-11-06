"""Bounded parser subprocess. Its input and output are JSON on private pipes."""

import base64
import csv
import io
import json
import sys
from typing import Any

from pypdf import PdfReader

MAX_TEXT = 2_000_000
MAX_PAGES = 300
MAX_ROWS = 20_000


def parse_pdf(data: bytes) -> dict[str, Any]:
    reader = PdfReader(io.BytesIO(data), strict=True)
    if reader.is_encrypted:
        raise ValueError("Encrypted PDFs are unsupported")
    if len(reader.pages) > MAX_PAGES:
        raise ValueError("PDF exceeds page limit")
    pages = []
    size = 0
    for page in reader.pages:
        content = page.get_contents()
        if content is not None and len(content.get_data()) > 10_000_000:
            raise ValueError("PDF page content exceeds limit")
        text = page.extract_text(extraction_mode="layout")
        size += len(text)
        if size > MAX_TEXT:
            raise ValueError("Extracted text exceeds limit")
        pages.append(text)
    return {"kind": "pdf", "pages": pages, "version": "pypdf-7.0.0-layout"}


def parse_csv(data: bytes) -> dict[str, Any]:
    text = data.decode("utf-8-sig")
    if "\x00" in text or len(text) > MAX_TEXT:
        raise ValueError("Invalid or oversized CSV text")
    reader = csv.reader(io.StringIO(text, newline=""), strict=True)
    header = next(reader, [])
    if not header or len(header) > 100 or any(not h.strip() for h in header):
        raise ValueError("CSV needs 1–100 named columns")
    if len(set(header)) != len(header):
        raise ValueError("Duplicate CSV column names")
    rows: list[list[str]] = []
    for row in reader:
        if len(row) != len(header) or len(rows) >= MAX_ROWS:
            raise ValueError("CSV is ragged or exceeds row limit")
        rows.append(row)
    return {"kind": "csv", "header": header, "rows": rows, "version": "stdlib-csv-1"}


def main() -> None:
    # Memory limits are available on the Linux deployment; the parent always enforces time.
    if sys.platform == "linux":
        import resource

        resource.setrlimit(resource.RLIMIT_AS, (256_000_000, 256_000_000))
    try:
        request = json.loads(sys.stdin.buffer.read(7_000_001))
        data = base64.b64decode(request["data"], validate=True)
        result = parse_pdf(data) if request["kind"] == "pdf" else parse_csv(data)
        sys.stdout.write(json.dumps(result))
    except Exception:
        # Parser exceptions may contain document text or paths. Only emit a safe code.
        sys.stdout.write(json.dumps({"error": "EXTRACTION_FAILED"}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
