"""Build a small deployment payload from the lockfile and the built project wheel."""

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Python buildpack v1.9.4 supplies this patch on cflinuxfs4 and cflinuxfs5.
DEPLOYMENT_PYTHON = "3.14.7"


def main() -> None:
    destination = ROOT / "dist/cloudgov"
    destination.mkdir(parents=True, exist_ok=True)
    export = subprocess.run(  # noqa: S603
        [  # noqa: S607 -- fixed developer-tool invocation
            "uv",
            "export",
            "--locked",
            "--offline",
            "--no-dev",
            "--no-emit-project",
            "--no-header",
            "--no-annotate",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    wheels = list((ROOT / "dist").glob("regulatory_mcp-*.whl"))
    # Select the declared version rather than any stale artifact from a prior release.
    import tomllib

    version = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    wheel = ROOT / "dist" / f"regulatory_mcp-{version}-py3-none-any.whl"
    if wheel not in wheels:
        raise ValueError("Run make build before packaging the declared project version")
    data = wheel.read_bytes()
    shutil.copyfile(wheel, destination / wheel.name)
    digest = hashlib.sha256(data).hexdigest()
    requirements = export + f"\n./{wheel.name} --hash=sha256:{digest}\n"
    (destination / "requirements.txt").write_text(requirements)
    (destination / "runtime.txt").write_text(f"python-{DEPLOYMENT_PYTHON}\n")
    (destination / ".cfignore").write_text(
        "*\n!requirements.txt\n!runtime.txt\n!.cfignore\n!build-manifest.json\n!"
        + wheel.name
        + "\n"
    )
    (destination / "build-manifest.json").write_text(
        json.dumps(
            {
                "wheel": wheel.name,
                "sha256": digest,
                "lock_sha256": hashlib.sha256((ROOT / "uv.lock").read_bytes()).hexdigest(),
                "python": DEPLOYMENT_PYTHON,
            },
            indent=2,
        )
        + "\n"
    )
    print("PASS: cloud.gov payload generated in dist/cloudgov with locked hashed requirements")


if __name__ == "__main__":
    main()
