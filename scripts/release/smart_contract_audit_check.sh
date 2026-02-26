#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

evidence_file="docs/audits/evidence/smart-contract-audit-latest.json"
strict_mode="${SARDIS_STRICT_RELEASE_GATES:-0}"
environment="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"

if [[ "$environment" == "prod" || "$environment" == "production" ]]; then
  strict_mode=1
fi

if [[ ! -f "$evidence_file" ]]; then
  echo "[smart-contract-audit][fail] missing evidence file: $evidence_file"
  exit 1
fi

python3 - "$evidence_file" "$strict_mode" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
strict = sys.argv[2] == "1"

data = json.loads(path.read_text(encoding="utf-8"))
errors: list[str] = []

required_fields = [
    "status",
    "audit_firm",
    "owner",
    "started_at",
    "scope",
    "report",
]
for field in required_fields:
    if field not in data:
        errors.append(f"missing field: {field}")

status = str(data.get("status", "")).lower()
allowed_status = {"planned", "in_progress", "completed"}
if status not in allowed_status:
    errors.append("status must be one of planned|in_progress|completed")

scope = data.get("scope", {})
if not isinstance(scope, dict):
    errors.append("scope must be an object")
else:
    contracts = scope.get("contracts")
    if not isinstance(contracts, list) or not contracts:
        errors.append("scope.contracts must be a non-empty list")
    chains = scope.get("chains")
    if not isinstance(chains, list) or not chains:
        errors.append("scope.chains must be a non-empty list")

report = data.get("report", {})
if not isinstance(report, dict):
    errors.append("report must be an object")
else:
    if status == "completed":
        if not str(report.get("url", "")).strip():
            errors.append("completed status requires report.url")
        if not str(report.get("sha256", "")).strip():
            errors.append("completed status requires report.sha256")
        if not str(data.get("completed_at", "")).strip():
            errors.append("completed status requires completed_at")

if strict and status != "completed":
    errors.append("strict mode requires completed formal smart-contract audit")

if errors:
    for error in errors:
        print(f"[smart-contract-audit][fail] {error}")
    raise SystemExit(1)

print(
    f"[smart-contract-audit][pass] status={status} "
    f"firm={data.get('audit_firm')} strict={strict}"
)
PY
