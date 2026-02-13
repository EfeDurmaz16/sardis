#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[migrations] validating alembic and SQL migration alignment"

python3 - <<'PY'
import pathlib
import re
import sys

sql_dir = pathlib.Path("packages/sardis-api/migrations")
alembic_dir = pathlib.Path("packages/sardis-api/alembic/versions")

sql_versions = sorted(
    int(m.group(1))
    for p in sql_dir.glob("[0-9][0-9][0-9]_*.sql")
    if (m := re.match(r"^([0-9]{3})_", p.name))
)

alembic_versions = {}
for p in alembic_dir.glob("*.py"):
    text = p.read_text(encoding="utf-8")
    rev_match = re.search(r"^revision:\s*str\s*=\s*['\"]([0-9]{3})['\"]", text, re.M)
    down_match = re.search(r"^down_revision:\s*Union\[str,\s*None\]\s*=\s*['\"]?([0-9]{3}|None)['\"]?", text, re.M)
    if rev_match:
        revision = int(rev_match.group(1))
        down = down_match.group(1) if down_match else None
        alembic_versions[revision] = down

if not sql_versions:
    print("[migrations][fail] no SQL migrations found")
    sys.exit(1)

if not alembic_versions:
    print("[migrations][fail] no Alembic revisions found")
    sys.exit(1)

sql_set = set(sql_versions)
alembic_set = set(alembic_versions.keys())

missing_alembic = sorted(sql_set - alembic_set)
if missing_alembic:
    print(f"[migrations][fail] missing Alembic revisions for SQL migrations: {missing_alembic}")
    sys.exit(1)

sql_head = max(sql_set)
alembic_head = max(alembic_set)
if sql_head != alembic_head:
    print(f"[migrations][fail] head mismatch: sql={sql_head:03d}, alembic={alembic_head:03d}")
    sys.exit(1)

expected = list(range(min(sql_set), sql_head + 1))
missing_numbers = [n for n in expected if n not in alembic_set]
if missing_numbers:
    print(f"[migrations][fail] Alembic revision gaps detected: {missing_numbers}")
    sys.exit(1)

print(f"[migrations][pass] aligned heads at revision {sql_head:03d} with contiguous Alembic chain")
PY

echo "[migrations] alignment checks passed"
