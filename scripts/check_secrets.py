"""Fail verification on secret findings, including in new untracked source files."""

import subprocess
import sys
from pathlib import Path

from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings


def main() -> int:
    # Fixed developer-tool invocation; git ignores exclude local artifacts and environments.
    result = subprocess.run(  # noqa: S603
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],  # noqa: S607
        capture_output=True,
        text=True,
        check=True,
    )
    secrets = SecretsCollection()
    with default_settings():
        for filename in sorted(set(result.stdout.split("\0")) - {""}):
            path = Path(filename)
            if path.is_file() and not path.is_symlink():
                secrets.scan_file(filename)
    findings = secrets.json()
    if findings:
        for path, entries in findings.items():
            for entry in entries:
                print(f"Secret candidate: {path}:{entry['line_number']} ({entry['type']})")
        return 1
    print("PASS: no secret candidates in non-ignored project files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
