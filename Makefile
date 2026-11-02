export UV_CACHE_DIR := $(CURDIR)/.cache/uv
export UV_PYTHON_DOWNLOADS := never

.PHONY: setup check check-offline lint test security build audit

setup:
	uv sync --locked

check: check-offline audit

check-offline: lint test security build

lint:
	uv run --locked --offline ruff check .
	uv run --locked --offline ruff format --check .
	uv run --locked --offline mypy

test:
	uv run --locked --offline pytest

security:
	uv run --locked --offline bandit -c pyproject.toml -r src
	uv run --locked --offline python scripts/check_secrets.py

build:
	uv build --no-build-isolation --offline

audit:
	uv export --locked --offline --all-groups --no-emit-project --output-file .venv/audit-requirements.txt > /dev/null
	uv run --locked pip-audit --disable-pip --require-hashes -r .venv/audit-requirements.txt
