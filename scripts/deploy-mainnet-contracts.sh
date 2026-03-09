#!/usr/bin/env bash
# Deploy Sardis contracts to Base mainnet.
#
# Prerequisites:
#   - forge installed (foundry)
#   - Deployer wallet funded with ~0.001 ETH on Base
#   - Alchemy API key for Base mainnet RPC
#
# Usage:
#   export PRIVATE_KEY=<deployer-private-key>
#   export SARDIS_ADDRESS=<deployer-address>  # becomes arbiter for RefundProtocol
#   export BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<key>
#   export BASESCAN_API_KEY=<basescan-key>    # optional, for verification
#   export FEE_RECIPIENT=<fee-recipient>      # optional, defaults to SARDIS_ADDRESS
#   export FEE_BPS=100                        # optional, default 1% (max 500)
#   ./scripts/deploy-mainnet-contracts.sh
set -euo pipefail

cd "$(dirname "$0")/../contracts"

# Validate required env vars
: "${PRIVATE_KEY:?Set PRIVATE_KEY to deployer wallet private key}"
: "${SARDIS_ADDRESS:?Set SARDIS_ADDRESS to Sardis platform address (arbiter)}"
: "${BASE_RPC_URL:?Set BASE_RPC_URL to Alchemy Base mainnet RPC URL}"

# Base mainnet USDC
export USDC_ADDRESS="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# ERC-8183 defaults — conservative caps for pre-audit deployment
export FEE_RECIPIENT="${FEE_RECIPIENT:-$SARDIS_ADDRESS}"
export FEE_BPS="${FEE_BPS:-100}"  # 1%, max 500 (5%)

echo "=== Sardis Mainnet Contract Deployment ==="
echo "  Chain:          Base (8453)"
echo "  Deployer:       will be derived from PRIVATE_KEY"
echo "  Arbiter:        $SARDIS_ADDRESS"
echo "  USDC:           $USDC_ADDRESS"
echo "  Fee Recipient:  $FEE_RECIPIENT"
echo "  Fee BPS:        $FEE_BPS"
echo "  RPC:            ${BASE_RPC_URL:0:50}..."
echo ""
echo "Contracts to deploy:"
echo "  1. SardisLedgerAnchor  — on-chain audit trail anchoring"
echo "  2. RefundProtocol      — Circle's audited escrow (Apache 2.0)"
echo "  3. SardisJobRegistry   — ERC-8183 on-chain reputation store"
echo "  4. SardisJobManager    — ERC-8183 job escrow and lifecycle"
echo "  5. SardisTrustHook     — trust-gated lifecycle transitions (disabled)"
echo "  6. SardisReputationHook — auto reputation on lifecycle events"
echo ""
echo "Pre-deployed (no action needed):"
echo "  - Zodiac Roles:    0x9646fDAD06d3e24444381f44362a3B0eB343D337"
echo "  - Circle Paymaster: 0x0578cFB241215b77442a541325d6A4E6dFE700Ec"
echo "  - Safe ProxyFactory: 0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2"
echo ""

read -p "Proceed with deployment? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo "Aborted."
  exit 1
fi

# Build first
echo "Compiling contracts..."
forge build --force

# Deploy
VERIFY_FLAG=""
if [[ -n "${BASESCAN_API_KEY:-}" ]]; then
  VERIFY_FLAG="--verify"
  echo "Contract verification enabled (BaseScan)"
fi

echo "Deploying LedgerAnchor + RefundProtocol to Base mainnet..."
forge script script/DeploySafeModules.s.sol:DeploySafeModules \
  --rpc-url base \
  --broadcast \
  $VERIFY_FLAG \
  -vvv 2>&1 | tee /tmp/sardis-mainnet-deploy.log

echo ""
echo "Deploying ERC-8183 contracts to Base mainnet..."
echo "  Fee BPS: $FEE_BPS (conservative, max 500)"
echo "  Trust hooks: disabled (MIN_CLIENT_TRUST=0, MIN_PROVIDER_JOBS=0, MIN_EVALUATOR_TRUST=0)"
echo "  Allowed tokens: USDC only"
forge script script/DeployERC8183.s.sol:DeployERC8183 \
  --rpc-url base \
  --broadcast \
  $VERIFY_FLAG \
  -vvv 2>&1 | tee -a /tmp/sardis-mainnet-deploy.log

echo ""
echo "=== Deployment complete ==="
echo "Check /tmp/sardis-mainnet-deploy.log for addresses"
echo ""
echo "Next steps:"
echo "  1. Copy deployed addresses from the log above"
echo "  2. Update contracts/deployments/base.json with per-contract lifecycle:"
echo '     "ledgerAnchor": { "address": "<addr>", "lifecycle": "canonical_live" }'
echo '     "refundProtocol": { "address": "<addr>", "lifecycle": "canonical_live" }'
echo '     "jobRegistry": { "address": "<addr>", "lifecycle": "canonical_live" }'
echo '     "jobManager": { "address": "<addr>", "lifecycle": "canonical_live" }'
echo '     "trustHook": { "address": "<addr>", "lifecycle": "canonical_live" }'
echo '     "reputationHook": { "address": "<addr>", "lifecycle": "canonical_live" }'
echo "  3. Update Cloud Run env vars:"
echo "     gcloud run services update sardis-api-staging \\"
echo "       --region us-central1 \\"
echo "       --update-env-vars \\"
echo "         SARDIS_BASE_LEDGER_ANCHOR_ADDRESS=<addr>,\\"
echo "         SARDIS_BASE_REFUND_PROTOCOL_ADDRESS=<addr>,\\"
echo "         SARDIS_ERC8183_ENABLED=true,\\"
echo "         SARDIS_ERC8183_CONTRACT_ADDRESS=<jobManagerAddr>,\\"
echo "         SARDIS_BASE_JOB_REGISTRY_ADDRESS=<registryAddr>,\\"
echo "         SARDIS_BASE_JOB_MANAGER_ADDRESS=<jobManagerAddr>"
echo ""
echo "  Valid lifecycle values: canonical_live, experimental, deprecated, pending_deploy"
echo ""
echo "  Post-audit relaxation path:"
echo "    - Enable trust hooks: trustHook.setThresholds()"
echo "    - Add EURC: jobManager.setAllowedToken()"
echo "    - Increase fee: jobManager.setFeeBps() (max 500 = 5%)"
