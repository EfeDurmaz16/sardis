#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[escrow-governance] validating timelock governance controls"

failures=0
strict_mode="${SARDIS_STRICT_RELEASE_GATES:-0}"
environment="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"
mode=""
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

require_file "$RUNBOOK_FILE"

if [[ -f "contracts/src/RefundProtocol.sol" ]]; then
  CONTRACT_FILE="contracts/src/RefundProtocol.sol"
  mode="refund-protocol"
  require_match 'modifier onlyArbiter' "$CONTRACT_FILE" "arbiter-only controls must exist"
  require_match 'MAX_LOCKUP_SECONDS' "$CONTRACT_FILE" "lockup cap constant must exist"
  require_match 'EARLY_WITHDRAWAL_TYPEHASH' "$CONTRACT_FILE" "typed early-withdraw signature guard must exist"
  require_match 'withdrawalHashes' "$CONTRACT_FILE" "replay protection mapping must exist"
  require_match 'function setLockupSeconds' "$CONTRACT_FILE" "arbiter lockup policy update must exist"
  require_match 'function refundByArbiter' "$CONTRACT_FILE" "arbiter refund control must exist"
  require_match 'function earlyWithdrawByArbiter' "$CONTRACT_FILE" "arbiter early withdrawal control must exist"
  require_match 'function updateRefundTo' "$CONTRACT_FILE" "refund destination governance path must exist"
  require_match 'LockupSecondsExceedsMax' "$CONTRACT_FILE" "lockup ceiling validation must exist"
elif [[ -f "contracts/src/SardisEscrow.sol" ]]; then
  CONTRACT_FILE="contracts/src/SardisEscrow.sol"
  mode="legacy-sardis-escrow"
elif [[ -f "contracts/deprecated/SardisEscrow.sol" ]]; then
  CONTRACT_FILE="contracts/deprecated/SardisEscrow.sol"
  mode="legacy-sardis-escrow"
else
  echo "[escrow-governance][fail] missing supported escrow contract surface"
  failures=$((failures + 1))
fi

if [[ "$mode" == "legacy-sardis-escrow" ]]; then
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
  require_match 'modifier onlyOwnershipAdmin' "$CONTRACT_FILE" "ownership operations must use ownership admin modifier"
  require_match 'function transferOwnership\(address newOwner\) public override onlyOwnershipAdmin' "$CONTRACT_FILE" "ownership transfer must be governance-gated in strict mode"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[escrow-governance] completed with $failures failure(s)"
  exit 1
fi

if command -v forge >/dev/null 2>&1; then
  if [[ "$mode" == "legacy-sardis-escrow" ]]; then
    test_cmd=(forge test --match-contract SardisEscrowTest -q)
  else
    # RefundProtocol source tree currently ships with policy module tests.
    # We still require forge compilation/test execution here for strict mode.
    test_cmd=(forge test --match-path test/SardisPolicyModule.t.sol -q)
  fi

  if ! (cd contracts && "${test_cmd[@]}"); then
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
