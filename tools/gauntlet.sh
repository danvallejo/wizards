#!/usr/bin/env bash
# Single entry point: every gauntlet layer. Any failure stops the run nonzero.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin

echo "== lint";      $PY/ruff check .
echo "== format";    $PY/ruff format --check .
echo "== types";     $PY/mypy
echo "== tests (random order, 100% line+branch coverage of app/)"
$PY/pytest -q -p randomly --cov=app --cov-branch --cov-report=term-missing --cov-fail-under=100
echo "== no game names in core"; $PY/python tools/check_no_game_names.py
echo "== mutation";  $PY/python tools/mutants.py
echo "GAUNTLET PASSED"
