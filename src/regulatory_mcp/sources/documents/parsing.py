"""Run fixed parser workers in subprocesses for enforceable extraction deadlines."""

import base64
import json
import re
import subprocess  # nosec B404
import sys
from typing import Any

from regulatory_mcp.evidence import StoreError

MAX_UPLOAD_BYTES = 5_000_000


def parse(data: bytes, media_type: str) -> dict[str, Any]:
    if not data or len(data) > MAX_UPLOAD_BYTES:
        raise StoreError("INVALID_INPUT: upload must contain 1–5000000 bytes")
    kind = {"application/pdf": "pdf", "text/csv": "csv"}.get(media_type)
    if kind is None or (kind == "pdf" and not data.startswith(b"%PDF-")):
        raise StoreError("INVALID_INPUT: expected PDF or UTF-8 comma-delimited CSV")
    payload = json.dumps({"kind": kind, "data": base64.b64encode(data).decode()})
    try:
        # No shell or document-controlled argv; uploaded bytes are data on stdin only.
        result = subprocess.run(  # noqa: S603  # nosec B603
            [sys.executable, "-m", "regulatory_mcp.sources.documents.worker"],
            input=payload,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise StoreError("EXTRACTION_TIMEOUT: document parser exceeded 20 seconds") from None
    except OSError:
        raise StoreError("EXTRACTION_FAILED: document parser could not start") from None
    if result.returncode or len(result.stdout) > 15_000_000:
        raise StoreError("EXTRACTION_FAILED: malformed, encrypted, or oversized document")
    try:
        parsed = json.loads(result.stdout)
    except ValueError:
        raise StoreError("EXTRACTION_FAILED: invalid parser result") from None
    if not isinstance(parsed, dict) or parsed.get("kind") != kind:
        raise StoreError("EXTRACTION_FAILED: unexpected parser result")
    return parsed


def table_candidates(text: str, first_line: int, line_count: int) -> list[dict[str, Any]]:
    rows = []
    offset = 0
    for index, line in enumerate(text.splitlines(keepends=True)):
        if first_line <= index < first_line + line_count:
            cells = []
            for match in re.finditer(r"\S(?:.*?\S)?(?= {2,}|\t|\r?$)", line.rstrip("\r\n")):
                cells.append(
                    {"text": match[0], "start": offset + match.start(), "end": offset + match.end()}
                )
            rows.append({"line_index": index, "cells": cells})
        offset += len(line)
    return rows
