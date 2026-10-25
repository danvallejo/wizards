#!/usr/bin/env bash
# Single entry point: every gauntlet layer. Any failure stops the run nonzero.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin

echo "== lint";      $PY/ruff check .
echo "== format";    $PY/ruff format --check .
echo "== types";     $PY/mypy
echo "== tests (random order, 100% line+branch coverage of app/ and seed.py)"
SEED=${SEED:-$RANDOM}  # rerun a given order with SEED=<n> tools/gauntlet.sh
echo "random order seed: $SEED"
$PY/pytest -q -p randomly --randomly-seed="$SEED" --cov=app --cov=seed --cov-branch --cov-report=term-missing --cov-fail-under=100
echo "== no game names in core"; $PY/python tools/check_no_game_names.py
echo "== mutation";  $PY/python tools/mutants.py
echo "== real run (server on :8000, end-to-end over HTTP)"; $PY/python tools/real_run.py
echo "GAUNTLET PASSED"
