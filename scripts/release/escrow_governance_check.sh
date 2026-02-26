#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[escrow-governance] validating timelock governance controls"

failures=0
strict_mode="${SARDIS_STRICT_RELEASE_GATES:-0}"
environment="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"
if [[ "$environment" == "prod" || "$environment" == "production" ]]; then
  strict_mode=1
fi

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[escrow-governance][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[escrow-governance][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

RUNBOOK_FILE="docs/design-partner/escrow-governance-timelock-runbook.md"
CONTRACT_FILE="contracts/src/SardisEscrow.sol"

require_file "$RUNBOOK_FILE"
require_match 'ARBITER_UPDATE_TIMELOCK' "$CONTRACT_FILE" "timelock constant must exist"
require_match 'GOVERNANCE_EXECUTOR_UPDATE_TIMELOCK' "$CONTRACT_FILE" "executor timelock constant must exist"
require_match 'OWNERSHIP_TRANSFER_TIMELOCK' "$CONTRACT_FILE" "ownership timelock constant must exist"
require_match 'pendingArbiter' "$CONTRACT_FILE" "pending arbiter state must exist"
require_match 'pendingArbiterEta' "$CONTRACT_FILE" "pending ETA state must exist"
require_match 'pendingGovernanceExecutor' "$CONTRACT_FILE" "pending governance executor state must exist"
require_match 'pendingGovernanceExecutorEta' "$CONTRACT_FILE" "pending governance executor ETA state must exist"
require_match 'governanceStrictMode' "$CONTRACT_FILE" "strict governance mode flag must exist"
require_match 'pendingOwner' "$CONTRACT_FILE" "pending ownership state must exist"
require_match 'ownershipTransferEta' "$CONTRACT_FILE" "pending ownership ETA must exist"
require_match 'function proposeArbiter' "$CONTRACT_FILE" "propose function must exist"
require_match 'function executeArbiterUpdate' "$CONTRACT_FILE" "execute function must exist"
require_match 'function cancelArbiterUpdate' "$CONTRACT_FILE" "cancel function must exist"
require_match 'function proposeGovernanceExecutor' "$CONTRACT_FILE" "governance executor propose function must exist"
require_match 'function executeGovernanceExecutorUpdate' "$CONTRACT_FILE" "governance executor execute function must exist"
require_match 'function cancelGovernanceExecutorUpdate' "$CONTRACT_FILE" "governance executor cancel function must exist"
require_match 'function enableGovernanceStrictMode' "$CONTRACT_FILE" "strict governance mode function must exist"
require_match 'function executeOwnershipTransfer' "$CONTRACT_FILE" "ownership transfer execution function must exist"
require_match 'function cancelOwnershipTransfer' "$CONTRACT_FILE" "ownership transfer cancel function must exist"

if [[ "$failures" -gt 0 ]]; then
  echo "[escrow-governance] completed with $failures failure(s)"
  exit 1
fi

if command -v forge >/dev/null 2>&1; then
  if ! (cd contracts && forge test --match-contract SardisEscrowTest -q); then
    if [[ "$strict_mode" == "1" ]]; then
      echo "[escrow-governance][fail] forge governance tests failed in strict mode"
      exit 1
    fi
    echo "[escrow-governance][warn] forge tests failed; non-strict mode allows warning"
  fi
else
  if [[ "$strict_mode" == "1" ]]; then
    echo "[escrow-governance][fail] forge not found in strict mode"
    exit 1
  fi
  echo "[escrow-governance][warn] forge not found; skipped contract tests"
fi

echo "[escrow-governance] pass"
