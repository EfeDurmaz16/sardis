#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[readiness] starting checks"

failures=0

check_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[readiness][fail] required command missing: $cmd"
    failures=$((failures + 1))
  fi
}

check_cmd git
check_cmd rg
check_cmd node
check_cmd pytest
check_cmd pnpm

if [[ "$failures" -gt 0 ]]; then
  echo "[readiness] failed preflight ($failures issue(s))"
  exit 1
fi

echo "[readiness] validating env documentation parity"
if ! bash scripts/release/env_doc_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating SDK/package version consistency"
if ! bash scripts/release/version_consistency_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating package metadata and licenses"
if ! bash scripts/release/package_metadata_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating migration alignment"
if ! bash scripts/release/migration_alignment_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating webhook conformance checks"
if ! bash scripts/release/webhook_conformance_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating idempotency/replay e2e checks"
if ! bash scripts/release/idempotency_replay_e2e_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating deployment config consistency"
if ! bash scripts/release/deployment_config_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating ops readiness artifacts"
if ! bash scripts/release/ops_readiness_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating payment hardening gate"
if ! bash scripts/release/payment_hardening_gate.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating strict contracts gate"
if ! bash scripts/release/contracts_strict_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating live A2A settlement path"
if ! bash scripts/release/a2a_live_settlement_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating live multi-agent settlement path"
if ! bash scripts/release/multi_agent_live_settlement_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating mainnet proof and incident drill artifacts"
if ! bash scripts/release/mainnet_ops_drill_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating reconciliation chaos/load readiness"
if ! bash scripts/release/reconciliation_chaos_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating custody posture"
if ! bash scripts/release/non_custodial_posture_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating compliance execution track"
if ! bash scripts/release/compliance_execution_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating policy signer and MPC key governance"
if ! bash scripts/release/key_governance_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating escrow governance timelock controls"
if ! bash scripts/release/escrow_governance_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating GA prep execution pack"
if ! bash scripts/release/ga_prep_check.sh; then
  failures=$((failures + 1))
fi

echo "[readiness] validating demo proof assets"
if ! bash scripts/release/demo_proof_assets_check.sh; then
  failures=$((failures + 1))
fi

tmp_pytest="$(mktemp)"
trap 'rm -f "$tmp_pytest"' EXIT

echo "[readiness] validating MCP tool registry parity"
pnpm -C packages/sardis-mcp-server run build >/dev/null
registry_summary="$(
  node --input-type=module -e "
    import { validateToolRegistry } from './packages/sardis-mcp-server/dist/tools/index.js';
    const v = validateToolRegistry();
    console.log([v.definitionCount, v.handlerCount, v.isValid ? '1' : '0', v.missingHandlersForDefinitions.join(','), v.missingDefinitionsForHandlers.join(',')].join('|'));
  "
)"

def_count="$(echo "$registry_summary" | cut -d'|' -f1)"
handler_count="$(echo "$registry_summary" | cut -d'|' -f2)"
registry_valid="$(echo "$registry_summary" | cut -d'|' -f3)"
missing_handlers="$(echo "$registry_summary" | cut -d'|' -f4)"
missing_definitions="$(echo "$registry_summary" | cut -d'|' -f5)"

if [[ "$registry_valid" != "1" ]]; then
  echo "[readiness][fail] MCP definitions ($def_count) != handlers ($handler_count)"
  [[ -n "$missing_handlers" ]] && echo "[readiness][fail] missing handlers: $missing_handlers"
  [[ -n "$missing_definitions" ]] && echo "[readiness][fail] missing definitions: $missing_definitions"
  failures=$((failures + 1))
else
  echo "[readiness][pass] MCP registry parity: $def_count definitions = $handler_count handlers"
fi

echo "[readiness] collecting pytest test inventory"
pytest --collect-only -q >"$tmp_pytest"
collected_count="$(awk '/collected [0-9]+ items/{for(i=1;i<=NF;i++) if($i=="collected"){print $(i+1); exit}}' "$tmp_pytest")"
selected_count="$(awk '{ if (match($0, /[0-9]+\/[0-9]+ tests collected/)) { print substr($0, RSTART, RLENGTH) } }' "$tmp_pytest" | awk -F'/' '{print $1}' | head -n1)"

if [[ -z "$collected_count" ]]; then
  echo "[readiness][fail] unable to parse pytest collected count"
  failures=$((failures + 1))
else
  echo "[readiness][pass] pytest collected items: $collected_count (selected: ${selected_count:-unknown})"
  if [[ "$collected_count" -lt 150 ]]; then
    echo "[readiness][fail] collected tests below README claim threshold (150+)"
    failures=$((failures + 1))
  fi
fi

echo "[readiness] validating package count claim"
python_package_count="$(( $(find packages -maxdepth 2 -name pyproject.toml | wc -l | tr -d ' ') + 1 ))"
js_package_count="$(find packages -maxdepth 2 -name package.json | wc -l | tr -d ' ')"
total_package_count="$(( python_package_count + js_package_count ))"

minimum_expected_package_count=19
if [[ "$total_package_count" -lt "$minimum_expected_package_count" ]]; then
  echo "[readiness][fail] package count below minimum: expected >=$minimum_expected_package_count, got $total_package_count"
  failures=$((failures + 1))
else
  echo "[readiness][pass] package count: $total_package_count (python=$python_package_count, js=$js_package_count)"
fi

echo "[readiness] validating mainnet chain claim"
mainnet_chain_count="$(
  rg -o -P '^\s+"(base|polygon|ethereum|arbitrum|optimism)"\s*:' \
    packages/sardis-chain/src/sardis_chain/executor.py \
    | sed -E 's/^[[:space:]]*"([^"]+)".*/\1/' \
    | sort -u | wc -l | tr -d ' '
)"
if [[ "$mainnet_chain_count" -ne 5 ]]; then
  echo "[readiness][fail] expected 5 mainnet chains, got $mainnet_chain_count"
  failures=$((failures + 1))
else
  echo "[readiness][pass] mainnet chain count: $mainnet_chain_count"
fi

echo "[readiness] validating protocol implementation presence"
protocol_files=(
  "packages/sardis-protocol/src/sardis_protocol/schemas.py"
  "packages/sardis-protocol/src/sardis_protocol/tap.py"
  "packages/sardis-protocol/src/sardis_protocol/x402.py"
  "packages/sardis-ucp/src/sardis_ucp/__init__.py"
  "packages/sardis-a2a/src/sardis_a2a/__init__.py"
)

for file in "${protocol_files[@]}"; do
  if [[ ! -f "$file" ]]; then
    echo "[readiness][fail] missing protocol implementation file: $file"
    failures=$((failures + 1))
  fi
done

if [[ "$failures" -gt 0 ]]; then
  echo "[readiness] completed with $failures failure(s)"
  exit 1
fi

echo "[readiness] all checks passed"
