#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

API_URL="${SARDIS_API_URL:-http://localhost:8000}"
USERNAME="${SARDIS_ADMIN_USERNAME:-admin}"
PASSWORD="${SARDIS_ADMIN_PASSWORD:-demo123}"
MODE="${SARDIS_DEMO_MODE:-hybrid-live}"
OUTPUT_DIR="${SARDIS_DEMO_OUTPUT_DIR:-artifacts/investor-demo}"
STRICT_DEMO_PROOF="${STRICT_DEMO_PROOF:-0}"

echo "[demo-proof] running investor demo flow"
python3 scripts/investor_demo_flow.py \
  --api-url "$API_URL" \
  --username "$USERNAME" \
  --password "$PASSWORD" \
  --mode "$MODE" \
  --output-dir "$OUTPUT_DIR"

LATEST_JSON="$(ls -1t "$OUTPUT_DIR"/investor-demo-*.json 2>/dev/null | head -n1 || true)"
if [[ -z "$LATEST_JSON" ]]; then
  echo "[demo-proof][fail] no demo artifact generated under $OUTPUT_DIR"
  exit 1
fi

echo "[demo-proof] validating artifact: $LATEST_JSON"
python3 - "$LATEST_JSON" "$STRICT_DEMO_PROOF" <<'PY'
import json
import sys
from pathlib import Path

artifact_path = Path(sys.argv[1])
strict = sys.argv[2] == "1"

payload = json.loads(artifact_path.read_text(encoding="utf-8"))
steps = {s["name"]: s for s in payload.get("steps", [])}

required = [
    "admin_login",
    "bootstrap_api_key",
    "create_agent",
    "create_payment_identity",
    "apply_policy",
    "simulate_denied_purchase",
    "simulate_allowed_purchase",
]
missing = [name for name in required if name not in steps]
if missing:
    raise SystemExit(f"[demo-proof][fail] missing steps: {missing}")

bad = [name for name in required if steps[name].get("status") != "ok"]
if bad:
    raise SystemExit(f"[demo-proof][fail] required steps not ok: {bad}")

denied = steps["simulate_denied_purchase"].get("details", {})
allowed = steps["simulate_allowed_purchase"].get("details", {})

deny_signal = (
    str(denied.get("policy_outcome", "")).lower() in {"denied", "blocked"}
    or bool(denied.get("decline_reason"))
)
if not deny_signal:
    raise SystemExit("[demo-proof][fail] denied scenario missing deny signal")

allow_signal = (
    str(allowed.get("policy_outcome", "")).lower() in {"allowed", "approved", ""}
    and str(allowed.get("decline_reason", "")).strip() in {"", "none", "null"}
)
if not allow_signal:
    raise SystemExit("[demo-proof][fail] allowed scenario does not look approved")

verify = steps.get("verify_ledger_entry")
if not verify:
    raise SystemExit("[demo-proof][fail] missing verify_ledger_entry step")

if verify.get("status") == "ok":
    if verify.get("details", {}).get("valid", True) is False:
        raise SystemExit("[demo-proof][fail] ledger verification returned invalid")
elif strict:
    raise SystemExit("[demo-proof][fail] verify_ledger_entry is not ok in strict mode")

print("[demo-proof][pass] allow/deny proof artifact is valid")
print(f"[demo-proof] run_id={payload.get('run_id')}")
PY
