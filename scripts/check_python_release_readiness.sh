#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_SDK_DIR="$ROOT_DIR/packages/sardis-sdk-python"

echo "[1/5] Checking Python SDK version consistency"
PYPROJECT_VERSION="$(python3 - <<'PY'
import tomllib
from pathlib import Path
data = tomllib.loads(Path("packages/sardis-sdk-python/pyproject.toml").read_text())
print(data["project"]["version"])
PY
)"
INIT_VERSION="$(python3 - <<'PY'
from pathlib import Path
text = Path("packages/sardis-sdk-python/src/sardis_sdk/__init__.py").read_text()
needle = '__version__ = "'
start = text.index(needle) + len(needle)
end = text.index('"', start)
print(text[start:end])
PY
)"
if [[ "$PYPROJECT_VERSION" != "$INIT_VERSION" ]]; then
  echo "Version mismatch: pyproject=$PYPROJECT_VERSION __init__=$INIT_VERSION"
  exit 1
fi
echo "Version OK: $PYPROJECT_VERSION"

echo "[2/5] Running Python SDK test suite"
python3 -m pytest -q "$PY_SDK_DIR/tests"

echo "[3/5] Running protocol conformance suite"
python3 -m pytest -m protocol_conformance \
  "$ROOT_DIR/tests/" \
  "$ROOT_DIR/packages/sardis-ucp/tests/" \
  --strict-markers \
  -v --tb=short \
  2>&1 | tee /tmp/protocol-results.txt

# Count results
PASSED=$(grep -c "PASSED" /tmp/protocol-results.txt || true)
FAILED=$(grep -c "FAILED" /tmp/protocol-results.txt || true)
SKIPPED=$(grep -c "SKIPPED" /tmp/protocol-results.txt || true)

echo "Protocol conformance: $PASSED passed, $FAILED failed, $SKIPPED skipped"

if [ "$FAILED" -gt 0 ]; then
  echo "FATAL: Protocol conformance tests failed"
  exit 1
fi

if [ "${STRICT_MODE:-0}" = "1" ] && [ "$SKIPPED" -gt 0 ]; then
  echo "STRICT_MODE: $SKIPPED tests were skipped - treating as failure"
  exit 1
fi

echo "[3b/5] Running protocol package suites (A2A/UCP)"
(
  cd "$ROOT_DIR/packages/sardis-a2a"
  PYTHONPATH=src python3 -m pytest -q tests
)
(
  cd "$ROOT_DIR/packages/sardis-ucp"
  PYTHONPATH=src python3 -m pytest -q tests
)

echo "[4/5] Running compliance package smoke test"
(
  cd "$ROOT_DIR/packages/sardis-compliance"
  python3 -m pytest -q tests/test_audit_store_async.py
)

echo "[5/5] Attempting offline package build validation"
if python3 - <<'PY'
import importlib.util
mods = ["build", "twine", "hatchling"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
print(",".join(missing))
raise SystemExit(0 if not missing else 1)
PY
then
  (
    cd "$PY_SDK_DIR"
    python3 -m build --no-isolation
    python3 -m twine check dist/*
  )
else
  echo "Skipping build/twine check: missing one of build, twine, hatchling"
  echo "Install and re-run for full release confidence:"
  echo "  python3 -m pip install build twine hatchling"
fi

echo "Python release readiness checks completed."
