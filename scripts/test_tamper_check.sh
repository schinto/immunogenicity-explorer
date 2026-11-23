#!/usr/bin/env bash
# Verhindert, dass ein Agent grün wird, indem er Tests abschwächt.
#
# Scheitert, wenn im Diff zwischen zwei Commits unter tests/ Dateien gelöscht wurden,
# netto Assertions verschwinden oder Tests übersprungen werden.
#
# Aufruf: ./scripts/test_tamper_check.sh <base-sha> <head-sha>
set -euo pipefail

BASE="${1:?base sha fehlt}"
HEAD="${2:?head sha fehlt}"

fail() {
    echo "TAMPER: $1" >&2
    exit 1
}

# 1. Gelöschte oder umbenannte Testdateien
deleted=$(git diff --name-only --diff-filter=DR "$BASE" "$HEAD" -- 'tests/*' || true)
if [ -n "$deleted" ]; then
    fail "Testdateien gelöscht oder umbenannt:"$'\n'"$deleted"
fi

diff_tests=$(git diff -U0 "$BASE" "$HEAD" -- 'tests/*' || true)
if [ -z "$diff_tests" ]; then
    echo "OK: keine Änderungen unter tests/"
    exit 0
fi

added=$(printf '%s\n' "$diff_tests" | grep -E '^\+' | grep -vE '^\+\+\+' || true)
removed=$(printf '%s\n' "$diff_tests" | grep -E '^-' | grep -vE '^---' || true)

# 2. Übersprungene Tests
if printf '%s\n' "$added" | grep -qE 'pytest\.(skip|xfail)|@pytest\.mark\.(skip|skipif|xfail)|return  *# *(skip|todo)'; then
    fail "neue skip- oder xfail-Markierung in Tests"
fi

# 3. Netto weniger Assertions
count_asserts() { printf '%s\n' "$1" | grep -cE '(^.)[[:space:]]*(assert |self\.assert|pytest\.raises)' || true; }
a_added=$(count_asserts "$added")
a_removed=$(count_asserts "$removed")
if [ "$a_removed" -gt "$a_added" ]; then
    fail "netto $((a_removed - a_added)) Assertion(s) entfernt (hinzugefügt: $a_added, entfernt: $a_removed)"
fi

# 4. Abgeschaltete Prüfungen im Gate selbst
if git diff --name-only "$BASE" "$HEAD" -- check.sh pyproject.toml | grep -q .; then
    echo "HINWEIS: check.sh oder pyproject.toml geändert. Der Reviewer prüft das gesondert."
fi

echo "OK: Assertions hinzugefügt=$a_added entfernt=$a_removed, keine skip-Markierungen"
