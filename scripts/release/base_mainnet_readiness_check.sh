#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[base-mainnet] validating base mainnet deployment readiness"

failures=0
warnings=0
strict_mode=0
environment="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"
strict_gates="$(echo "${SARDIS_STRICT_RELEASE_GATES:-0}" | tr '[:upper:]' '[:lower:]')"

if [[ "$environment" == "prod" || "$environment" == "production" ]]; then
  strict_mode=1
fi
if [[ "$strict_gates" == "1" || "$strict_gates" == "true" || "$strict_gates" == "yes" || "$strict_gates" == "on" ]]; then
  strict_mode=1
fi

warn_or_fail() {
  local message="$1"
  if [[ "$strict_mode" == "1" ]]; then
    echo "[base-mainnet][fail] $message"
    failures=$((failures + 1))
  else
    echo "[base-mainnet][warn] $message"
    warnings=$((warnings + 1))
  fi
}

require_fail() {
  local message="$1"
  echo "[base-mainnet][fail] $message"
  failures=$((failures + 1))
}

is_evm_address() {
  local value="$1"
  [[ "$value" =~ ^0x[a-fA-F0-9]{40}$ ]]
}

read_manifest_field() {
  local field="$1"
  python3 - "$field" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path

field = sys.argv[1]
path = Path("contracts/deployments/base.json")
if not path.exists():
    print("")
    raise SystemExit(0)

try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print("")
    raise SystemExit(0)

contracts = payload.get("contracts", {})

if field == "status":
    print(str(payload.get("status", "")))
    raise SystemExit(0)

aliases = {
    "policy_module": ("policy_module", "policyModule"),
    "ledger_anchor": ("ledger_anchor", "ledgerAnchor"),
}

for key in aliases.get(field, (field,)):
    value = contracts.get(key)
    if isinstance(value, str) and value.strip():
        print(value.strip())
        break
else:
    print("")
PY
}

manifest_policy_module="$(read_manifest_field policy_module)"
manifest_ledger_anchor="$(read_manifest_field ledger_anchor)"
manifest_status="$(read_manifest_field status | tr '[:upper:]' '[:lower:]')"

policy_module_address="${SARDIS_BASE_POLICY_MODULE_ADDRESS:-$manifest_policy_module}"
ledger_anchor_address="${SARDIS_BASE_LEDGER_ANCHOR_ADDRESS:-$manifest_ledger_anchor}"

if [[ -z "$policy_module_address" ]]; then
  warn_or_fail "Base policy module address is missing (set SARDIS_BASE_POLICY_MODULE_ADDRESS or contracts/deployments/base.json contracts.policyModule)"
elif ! is_evm_address "$policy_module_address"; then
  require_fail "Base policy module address is not a valid EVM address: $policy_module_address"
fi

if [[ -z "$ledger_anchor_address" ]]; then
  warn_or_fail "Base ledger anchor address is missing (set SARDIS_BASE_LEDGER_ANCHOR_ADDRESS or contracts/deployments/base.json contracts.ledgerAnchor)"
elif ! is_evm_address "$ledger_anchor_address"; then
  require_fail "Base ledger anchor address is not a valid EVM address: $ledger_anchor_address"
fi

if [[ "$strict_mode" == "1" ]]; then
  if [[ "$manifest_status" != "deployed" ]]; then
    require_fail "contracts/deployments/base.json status must be 'deployed' in strict mode (current: ${manifest_status:-unset})"
  fi
elif [[ "$manifest_status" != "deployed" ]]; then
  echo "[base-mainnet][warn] contracts/deployments/base.json status is '${manifest_status:-unset}'"
  warnings=$((warnings + 1))
fi

if ! rg -q '"USDC": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"' packages/sardis-chain/src/sardis_chain/executor.py; then
  require_fail "Base USDC canonical address is missing from chain executor"
fi
if ! rg -q '"EURC": "0x60a3E35Cc302bFA44Cb288Bc5a4F316Fdb1adb42"' packages/sardis-chain/src/sardis_chain/executor.py; then
  require_fail "Base EURC canonical address is missing from chain executor"
fi

paymaster_provider="$(echo "${SARDIS_PAYMASTER_PROVIDER:-circle}" | tr '[:upper:]' '[:lower:]')"
if [[ "$paymaster_provider" == "circle" ]]; then
  if [[ -z "${SARDIS_PIMLICO_BUNDLER_URL:-}" && -z "${SARDIS_PIMLICO_PAYMASTER_URL:-}" && -z "${SARDIS_PIMLICO_API_KEY:-}" ]]; then
    warn_or_fail "Circle paymaster selected but no bundler/paymaster endpoint is configured (set SARDIS_PIMLICO_BUNDLER_URL or SARDIS_PIMLICO_API_KEY)"
  fi
fi

x402_enabled="$(echo "${SARDIS_CIRCLE_GATEWAY__X402_ENABLED:-${CIRCLE_GATEWAY_X402_ENABLED:-false}}" | tr '[:upper:]' '[:lower:]')"
if [[ "$x402_enabled" == "1" || "$x402_enabled" == "true" || "$x402_enabled" == "yes" || "$x402_enabled" == "on" ]]; then
  if [[ -z "${SARDIS_CIRCLE_GATEWAY__API_KEY:-}" && -z "${CIRCLE_GATEWAY_API_KEY:-}" ]]; then
    warn_or_fail "Circle Gateway x402 is enabled but API key is missing (set SARDIS_CIRCLE_GATEWAY__API_KEY or CIRCLE_GATEWAY_API_KEY)"
  fi
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[base-mainnet] completed with $failures failure(s)"
  exit 1
fi

echo "[base-mainnet] pass (warnings=$warnings strict=$strict_mode)"
