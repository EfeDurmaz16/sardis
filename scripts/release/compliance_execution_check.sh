#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[compliance-exec] validating compliance execution artifacts"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[compliance-exec][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[compliance-exec][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/compliance-execution-track-q1-2026.md"
require_file "docs/audits/control-testing-cadence-q1-2026.md"
require_file "docs/design-partner/pci-approvals-and-db-hardening-checklist.md"
require_file "docs/design-partner/acquirer-sponsor-bank-qsa-ownership.md"
require_file "docs/audits/evidence/turnkey-outage-drill-latest.json"

require_match 'PCI Scope Boundary' docs/design-partner/compliance-execution-track-q1-2026.md "compliance track must define PCI scope boundary"
require_match 'SOC2 Evidence Automation' docs/design-partner/compliance-execution-track-q1-2026.md "compliance track must define SOC2 evidence automation"
require_match 'Weekly Controls' docs/audits/control-testing-cadence-q1-2026.md "cadence doc must define weekly controls"
require_match 'Monthly Controls' docs/audits/control-testing-cadence-q1-2026.md "cadence doc must define monthly controls"
require_match 'QSA' docs/design-partner/acquirer-sponsor-bank-qsa-ownership.md "ownership doc must mention QSA"

if [[ "$failures" -gt 0 ]]; then
  echo "[compliance-exec] completed with $failures failure(s)"
  exit 1
fi

echo "[compliance-exec] generating SOC2/PCI evidence manifest"
python3 scripts/release/generate_soc2_evidence_manifest.py --root . --output artifacts/compliance/soc2-evidence-manifest.json

echo "[compliance-exec] running control test pack"
python3 -m pytest -q \
  packages/sardis-core/tests/test_nl_policy_parser_hard_limits.py \
  packages/sardis-core/tests/test_policy_attestation.py
python3 -m pytest -q packages/sardis-api/tests/test_compliance_gate.py
python3 -m pytest -q packages/sardis-compliance/tests/test_audit_store_async.py

echo "[compliance-exec] pass"
