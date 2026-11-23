#!/usr/bin/env bash
# Das Gate. Muss grün sein, bevor ein Review angefordert wird.
# Deterministisch, ohne Netzzugriff, ohne Hintergrundprozesse.
set -euo pipefail

cd "$(dirname "$0")"

echo "== 1/4 uv sync"
uv sync --quiet

echo "== 2/4 ruff format --check"
uv run ruff format --check .

echo "== 3/4 ruff check"
uv run ruff check .

echo "== 4/4 pytest"
uv run pytest

echo "CHECK OK"
