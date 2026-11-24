#!/usr/bin/env bash
# Prevents an agent from getting green by weakening tests.
#
# Fails if, in the diff between two commits, files under tests/ were deleted,
# assertions disappear on net, or tests are skipped.
#
# Usage: ./scripts/test_tamper_check.sh <base-sha> <head-sha>
set -euo pipefail

BASE="${1:?base sha missing}"
HEAD="${2:?head sha missing}"

fail() {
    echo "TAMPER: $1" >&2
    exit 1
}

# 1. Deleted or renamed test files
deleted=$(git diff --name-only --diff-filter=DR "$BASE" "$HEAD" -- 'tests/*' || true)
if [ -n "$deleted" ]; then
    fail "test files deleted or renamed:"$'\n'"$deleted"
fi

diff_tests=$(git diff -U0 "$BASE" "$HEAD" -- 'tests/*' || true)
if [ -z "$diff_tests" ]; then
    echo "OK: no changes under tests/"
    exit 0
fi

added=$(printf '%s\n' "$diff_tests" | grep -E '^\+' | grep -vE '^\+\+\+' || true)
removed=$(printf '%s\n' "$diff_tests" | grep -E '^-' | grep -vE '^---' || true)

# 2. Skipped tests
if printf '%s\n' "$added" | grep -qE 'pytest\.(skip|xfail)|@pytest\.mark\.(skip|skipif|xfail)|return  *# *(skip|todo)'; then
    fail "new skip or xfail marker in tests"
fi

# 3. Net fewer assertions
count_asserts() { printf '%s\n' "$1" | grep -cE '(^.)[[:space:]]*(assert |self\.assert|pytest\.raises)' || true; }
a_added=$(count_asserts "$added")
a_removed=$(count_asserts "$removed")
if [ "$a_removed" -gt "$a_added" ]; then
    fail "net $((a_removed - a_added)) assertion(s) removed (added: $a_added, removed: $a_removed)"
fi

# 4. Disabled checks in the gate itself
if git diff --name-only "$BASE" "$HEAD" -- check.sh pyproject.toml | grep -q .; then
    echo "NOTE: check.sh or pyproject.toml changed. The reviewer checks this separately."
fi

echo "OK: assertions added=$a_added removed=$a_removed, no skip markers"
