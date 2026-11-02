"""Keep the documentation inventory and local references usable."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = sorted([*ROOT.glob("*.md"), *ROOT.joinpath("docs").rglob("*.md")])


@pytest.mark.parametrize("path", DOCUMENTS, ids=lambda path: str(path.relative_to(ROOT)))
def test_document_metadata_and_links(path: Path):
    text = path.read_text()
    assert text.startswith("---\n"), f"Missing frontmatter: {path}"
    frontmatter = text.split("---\n", 2)[1]
    for field in ("title", "description", "status", "tier", "last_updated"):
        assert re.search(rf"^{field}: .+", frontmatter, re.MULTILINE), (path, field)
    links = re.findall(r"\]\(([^)]+)\)", text)
    related = re.search(r"^related_files: \[(.*)\]$", frontmatter, re.MULTILINE)
    if related:
        links.extend(re.findall(r'"([^"]+)"', related.group(1)))
    for link in links:
        if "://" not in link and not link.startswith("#"):
            assert (path.parent / link.split("#")[0]).exists(), (path, link)


def test_work_package_and_acceptance_references():
    ledger = (ROOT / "docs/IMPLEMENTATION_PIPELINE.md").read_text()
    spec = (ROOT / "docs/SPECIFICATION.md").read_text()
    packages = set(re.findall(r"^## (WP-\d+) —", ledger, re.MULTILINE))
    criteria = set(re.findall(r"\*\*(AC-\d+):", spec))
    assert packages
    assert criteria
    for path in DOCUMENTS:
        text = path.read_text()
        assert set(re.findall(r"WP-\d+", text)) <= packages, path
        assert set(re.findall(r"AC-0[1-9]\b", text)) <= criteria, path
