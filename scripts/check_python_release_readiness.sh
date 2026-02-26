#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY_SDK_DIR="$ROOT_DIR/packages/sardis-sdk-python"

# Make local monorepo packages importable during readiness checks.
# This avoids false negatives when optional integrations exist in-repo
# but are not pre-installed in the active interpreter.
MONOREPO_PYTHONPATH=""
for src_dir in "$ROOT_DIR"/packages/*/src; do
  if [[ -d "$src_dir" ]]; then
    if [[ -z "$MONOREPO_PYTHONPATH" ]]; then
      MONOREPO_PYTHONPATH="$src_dir"
    else
      MONOREPO_PYTHONPATH="${MONOREPO_PYTHONPATH}:$src_dir"
    fi
  fi
done
if [[ -n "$MONOREPO_PYTHONPATH" ]]; then
  export PYTHONPATH="$MONOREPO_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi

echo "[1/5] Checking Python package version consistency"
python3 - <<'PY'
import re
import tomllib
from pathlib import Path

errors = []
checked = 0

for pyproject in sorted(Path("packages").glob("*/pyproject.toml")):
    data = tomllib.loads(pyproject.read_text())
    project = data.get("project", {})
    name = project.get("name")
    version = project.get("version")
    if not name or not version:
        continue

    src_dir = pyproject.parent / "src"
    version_files = []
    if src_dir.exists():
        for init_file in src_dir.rglob("__init__.py"):
            match = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', init_file.read_text())
            if match:
                version_files.append((init_file, match.group(1)))

    for init_file, init_version in version_files:
        checked += 1
        if init_version != version:
            errors.append(
                f"{name}: pyproject={version} vs {init_file.as_posix()}={init_version}"
            )

if errors:
    print("Version mismatches detected:")
    for err in errors:
        print(f"  - {err}")
    raise SystemExit(1)

print(f"Version consistency OK ({checked} package __init__ files checked).")
PY

echo "[2/5] Running Python SDK test suite"
python3 -m pytest -q "$PY_SDK_DIR/tests"

echo "[3/5] Running protocol conformance suite"
python3 -m pytest -m protocol_conformance \
  "$ROOT_DIR/tests/" \
  --ignore="$ROOT_DIR/tests/integration" \
  --ignore="$ROOT_DIR/tests/e2e" \
  --strict-markers \
  -v --tb=short \
  2>&1 | tee /tmp/protocol-results.txt

# Count results from pytest summary (fallback to 0 if missing).
read -r PASSED FAILED SKIPPED <<<"$(python3 - <<'PY'
import re
from pathlib import Path

text = Path("/tmp/protocol-results.txt").read_text().lower()

summary_line = ""
for line in text.splitlines():
    stripped = line.strip()
    if stripped.startswith("=") and "passed" in stripped:
        summary_line = stripped

def extract_count(label: str, source: str) -> int:
    match = re.search(rf"(\d+)\s+{label}\b", source)
    return int(match.group(1)) if match else 0

source = summary_line or text

passed = extract_count("passed", source)
failed = extract_count("failed", source) + extract_count("error", source)
skipped = extract_count("skipped", source)
print(f"{passed} {failed} {skipped}")
PY
)"

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
