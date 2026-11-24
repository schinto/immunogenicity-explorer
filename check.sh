#!/usr/bin/env bash
# The gate. Must be green before a review is requested.
# Deterministic, without network access, without background processes.
set -euo pipefail

cd "$(dirname "$0")"

echo "== 1/4 uv sync --frozen"
uv sync --quiet --frozen

echo "== 2/4 ruff format --check"
uv run ruff format --check .

echo "== 3/4 ruff check"
uv run ruff check .

echo "== 4/4 pytest"
uv run pytest

echo "CHECK OK"
