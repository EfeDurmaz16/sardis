#!/usr/bin/env bash
set -euo pipefail

# Sardis On-Chain Contract Monitor
# Uses Foundry's cast to monitor wallet factory, escrow, and agent wallet events.
# Usage: BASE_RPC_URL=https://... FACTORY_ADDRESS=0x... ESCROW_ADDRESS=0x... ./monitor_contracts.sh

BASE_RPC_URL="${BASE_RPC_URL:-https://mainnet.base.org}"
FACTORY_ADDRESS="${FACTORY_ADDRESS:-}"
ESCROW_ADDRESS="${ESCROW_ADDRESS:-}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
LOOKBACK_BLOCKS="${LOOKBACK_BLOCKS:-100}"
LARGE_TX_THRESHOLD="${LARGE_TX_THRESHOLD:-10000000000}"  # 10,000 USDC (6 decimals)
RAPID_CREATION_THRESHOLD="${RAPID_CREATION_THRESHOLD:-10}" # wallets per lookback window

# Event signatures
EVT_WALLET_CREATED="WalletCreated(address,address,address)"
EVT_ESCROW_CREATED="EscrowCreated(uint256,address,address,uint256)"
EVT_ESCROW_DISPUTED="EscrowDisputed(uint256,address)"
EVT_TRANSFER="Transfer(address,address,uint256)"

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

send_alert() {
  local severity="$1" message="$2"
  if [[ -n "$WEBHOOK_URL" ]]; then
    local payload
    payload=$(cat <<EOF
{"text":"[$severity] Sardis Contract Monitor: $message"}
EOF
)
    curl -s -X POST -H "Content-Type: application/json" -d "$payload" "$WEBHOOK_URL" >/dev/null 2>&1 || true
  fi
  echo "[$(timestamp)] [$severity] $message" >&2
}

require_cast() {
  if ! command -v cast &>/dev/null; then
    echo '{"error": "cast (foundry) not found in PATH"}' >&2
    exit 1
  fi
}

get_block_number() {
  cast block-number --rpc-url "$BASE_RPC_URL" 2>/dev/null || echo "0"
}

get_logs() {
  local address="$1" event_sig="$2" from_block="$3"
  cast logs --rpc-url "$BASE_RPC_URL" --from-block "$from_block" --address "$address" "$event_sig" 2>/dev/null || true
}

require_cast

NOW=$(timestamp)
CURRENT_BLOCK=$(get_block_number)
if [[ "$CURRENT_BLOCK" == "0" ]]; then
  echo "{\"timestamp\":\"$NOW\",\"error\":\"Cannot reach RPC at $BASE_RPC_URL\"}"
  send_alert "critical" "RPC endpoint unreachable: $BASE_RPC_URL"
  exit 2
fi

FROM_BLOCK=$((CURRENT_BLOCK - LOOKBACK_BLOCKS))
[[ $FROM_BLOCK -lt 0 ]] && FROM_BLOCK=0

ANOMALIES=()
WALLET_COUNT=0
ESCROW_COUNT=0
DISPUTE_COUNT=0
LARGE_TX_COUNT=0

# --- Monitor Wallet Factory ---
if [[ -n "$FACTORY_ADDRESS" ]]; then
  WALLET_LOGS=$(get_logs "$FACTORY_ADDRESS" "$EVT_WALLET_CREATED" "$FROM_BLOCK")
  if [[ -n "$WALLET_LOGS" ]]; then
    WALLET_COUNT=$(echo "$WALLET_LOGS" | grep -c "^- address:" 2>/dev/null || echo "$WALLET_LOGS" | wc -l | tr -d ' ')
    # Normalize: each log entry has topics, count unique entries
    WALLET_COUNT=$(echo "$WALLET_LOGS" | grep -ci "blockNumber\|transactionHash\|blockHash" 2>/dev/null || echo "0")
    # Simpler: count occurrences of "transactionHash"
    WALLET_COUNT=$(echo "$WALLET_LOGS" | grep -c "transactionHash" 2>/dev/null || echo "0")
  fi

  if [[ "$WALLET_COUNT" -ge "$RAPID_CREATION_THRESHOLD" ]]; then
    ANOMALIES+=("rapid_wallet_creation:${WALLET_COUNT}_in_${LOOKBACK_BLOCKS}_blocks")
    send_alert "warning" "Rapid wallet creation detected: $WALLET_COUNT wallets in $LOOKBACK_BLOCKS blocks"
  fi
fi

# --- Monitor Escrow Contract ---
if [[ -n "$ESCROW_ADDRESS" ]]; then
  ESCROW_LOGS=$(get_logs "$ESCROW_ADDRESS" "$EVT_ESCROW_CREATED" "$FROM_BLOCK")
  if [[ -n "$ESCROW_LOGS" ]]; then
    ESCROW_COUNT=$(echo "$ESCROW_LOGS" | grep -c "transactionHash" 2>/dev/null || echo "0")
  fi

  DISPUTE_LOGS=$(get_logs "$ESCROW_ADDRESS" "$EVT_ESCROW_DISPUTED" "$FROM_BLOCK")
  if [[ -n "$DISPUTE_LOGS" ]]; then
    DISPUTE_COUNT=$(echo "$DISPUTE_LOGS" | grep -c "transactionHash" 2>/dev/null || echo "0")
  fi

  if [[ "$DISPUTE_COUNT" -gt 0 ]]; then
    ANOMALIES+=("escrow_disputes:$DISPUTE_COUNT")
    send_alert "warning" "$DISPUTE_COUNT escrow dispute(s) detected in last $LOOKBACK_BLOCKS blocks"
  fi

  # Check for large escrow amounts via Transfer events to escrow
  TRANSFER_LOGS=$(get_logs "$ESCROW_ADDRESS" "$EVT_TRANSFER" "$FROM_BLOCK")
  if [[ -n "$TRANSFER_LOGS" ]]; then
    # Extract amounts from data fields and check thresholds
    while IFS= read -r line; do
      if [[ "$line" =~ data:\ *(0x[0-9a-fA-F]+) ]]; then
        HEX_AMOUNT="${BASH_REMATCH[1]}"
        AMOUNT=$(cast --to-dec "$HEX_AMOUNT" 2>/dev/null || echo "0")
        if [[ "$AMOUNT" -ge "$LARGE_TX_THRESHOLD" ]]; then
          LARGE_TX_COUNT=$((LARGE_TX_COUNT + 1))
          ANOMALIES+=("large_transfer:${AMOUNT}")
          send_alert "critical" "Large transfer detected: $AMOUNT (raw) to escrow contract"
        fi
      fi
    done <<< "$TRANSFER_LOGS"
  fi
fi

# --- Check gas price ---
GAS_PRICE=$(cast gas-price --rpc-url "$BASE_RPC_URL" 2>/dev/null || echo "0")
GAS_GWEI=$(cast --to-unit "$GAS_PRICE" gwei 2>/dev/null || echo "0")

# Alert on high gas (>50 gwei on Base is very unusual)
GAS_THRESHOLD="${GAS_THRESHOLD:-50}"
GAS_INT=${GAS_GWEI%%.*}
if [[ "${GAS_INT:-0}" -ge "$GAS_THRESHOLD" ]]; then
  ANOMALIES+=("high_gas:${GAS_GWEI}gwei")
  send_alert "warning" "Gas price spike: ${GAS_GWEI} gwei (threshold: ${GAS_THRESHOLD})"
fi

# --- Build JSON output ---
ANOMALIES_JSON="[]"
if [[ ${#ANOMALIES[@]} -gt 0 ]]; then
  ANOMALIES_JSON=$(printf '%s\n' "${ANOMALIES[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")
fi

cat <<EOF
{
  "timestamp": "$NOW",
  "rpc_url": "$BASE_RPC_URL",
  "current_block": $CURRENT_BLOCK,
  "lookback_blocks": $LOOKBACK_BLOCKS,
  "gas_price_gwei": "$GAS_GWEI",
  "factory": {
    "address": "$FACTORY_ADDRESS",
    "new_wallets": $WALLET_COUNT
  },
  "escrow": {
    "address": "$ESCROW_ADDRESS",
    "new_escrows": $ESCROW_COUNT,
    "disputes": $DISPUTE_COUNT,
    "large_transactions": $LARGE_TX_COUNT
  },
  "anomalies": $ANOMALIES_JSON
}
EOF

if [[ ${#ANOMALIES[@]} -gt 0 ]]; then
  exit 1
fi
exit 0
