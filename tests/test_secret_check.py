"""Exercise the scanner against real Git file selection and a synthetic marker."""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/check_secrets.py"


def test_scans_new_files_but_excludes_ignored_files(tmp_path: Path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)  # noqa: S603, S607
    (tmp_path / ".gitignore").write_text("ignored/\n")
    ignored = tmp_path / "ignored"
    ignored.mkdir()
    # Synthetic private-key header, not key material or a usable credential.
    marker = "-----BEGIN " + "RSA PRIVATE KEY-----\n"
    (ignored / "fixture.txt").write_text(marker)
    clean = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert clean.returncode == 0, clean.stderr
    (tmp_path / "new-file.txt").write_text(marker)
    detected = subprocess.run(  # noqa: S603
        [sys.executable, str(SCRIPT)], cwd=tmp_path, capture_output=True, text=True, check=False
    )
    assert detected.returncode == 1, detected.stderr
    assert "new-file.txt:1" in detected.stdout
    assert marker not in detected.stdout
