# Sardis Demo Runbook (Full: Cards + Stablecoins)

Bu runbook’ta “gönderen Sardis değil, **AI agent**” olacak şekilde ilerliyoruz:
- Agent, Sardis API’yi **X-API-Key** ile çağırır.
- Sardis, policy/limits/compliance kontrollerinden geçirir.
- On-chain imza, **agent’ın non‑custodial MPC cüzdanı (Turnkey)** ile atılır (Sardis private key tutmaz).

> Not: Kart satın alımı demo’da **simulated purchase** ile gösterilebilir. Stablecoin tarafında ise Base Sepolia’da **gerçek tx** gösterebiliriz.

## Required env vars (demo)

Core:
- `SARDIS_ENVIRONMENT=dev`
- `JWT_SECRET_KEY` (min 32 chars)
- `SARDIS_ADMIN_PASSWORD`

Turnkey (stablecoin live tx için):
- `SARDIS_CHAIN_MODE=live`
- `SARDIS_MPC_PROVIDER=turnkey` *(settings adınız farklıysa uyarlayın)*
- `TURNKEY_ORGANIZATION_ID`
- `TURNKEY_API_PUBLIC_KEY`
- `TURNKEY_API_PRIVATE_KEY`
- `BASE_SEPOLIA_RPC_URL`

Lithic (cards):
- `LITHIC_API_KEY`
- `LITHIC_WEBHOOK_SECRET` *(gerçek `/api/v2/cards/webhooks` için; simulate-purchase için şart değil)*

Optional:
- `DATABASE_URL` *(Postgres persistence için önerilir)*
- `REDIS_URL` *(JWT revocation + rate limiting için önerilir)*
- `SARDIS_DEFAULT_ORG_ID=org_demo`

Dashboard:
- `VITE_API_URL=http://localhost:8000`

## 0) Login (Admin JWT)

```bash
BASE_URL=http://localhost:8000

TOKEN=$(
  curl -sS -X POST "$BASE_URL/api/v2/auth/login" \
    -F "username=admin" \
    -F "password=$SARDIS_ADMIN_PASSWORD" \
  | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['access_token'])"
)
echo "$TOKEN" | head -c 24 && echo "…"
```

## 1) Bootstrap an admin API key (agent’lar bu key ile çağırır)

```bash
ADMIN_API_KEY=$(
  curl -sS -X POST "$BASE_URL/api/v2/auth/bootstrap-api-key" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Demo Admin Key","scopes":["admin","*"]}' \
  | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['key'])"
)
echo "$ADMIN_API_KEY" | head -c 18 && echo "…"
```

## 1.1) Create an agent-scoped API key (recommended)

Admin key ile daha kısıtlı bir “agent key” üretin; demo’da agent bu key ile çağırıyor gibi düşünebilirsiniz.

```bash
AGENT_API_KEY=$(
  curl -sS -X POST "$BASE_URL/api/v2/api-keys" \
    -H "X-API-Key: $ADMIN_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"name":"Demo Agent Key","scopes":["write"],"rate_limit":60}' \
  | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['key'])"
)
echo "$AGENT_API_KEY" | head -c 18 && echo "…"
```

## 2) Create agent wallet (Turnkey, non-custodial)

Bu adımda agent için Turnkey’de wallet oluşturulur ve EVM address’i döner.

```bash
AGENT_WALLET=$(
  curl -sS -X POST "$BASE_URL/api/v2/wallets" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"agent_id":"agent_demo_001","mpc_provider":"turnkey","wallet_name":"agent_demo_001"}'
)
echo "$AGENT_WALLET" | .venv/bin/python -m json.tool

WALLET_ID=$(echo "$AGENT_WALLET" | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['wallet_id'])")
ADDR=$(echo "$AGENT_WALLET" | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['addresses']['base_sepolia'])")
echo "wallet_id=$WALLET_ID"
echo "base_sepolia_address=$ADDR"
```

## 3) Apply policy (Natural language)

```bash
curl -sS -X POST "$BASE_URL/api/v2/policies/apply" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"agent_demo_001","natural_language":"Max $100 per transaction, block gambling","confirm":true}' \
| .venv/bin/python -m json.tool
```

## 4) Cards demo (Lithic)

Issue card:
```bash
CARD=$(
  curl -sS -X POST "$BASE_URL/api/v2/cards" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"wallet_id\":\"$WALLET_ID\",\"limit_per_tx\":\"100.00\"}"
)
echo "$CARD" | .venv/bin/python -m json.tool
CARD_ID=$(echo "$CARD" | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['card_id'])")
echo "card_id=$CARD_ID"
```

Simulate purchase (blocked MCC):
```bash
curl -sS -X POST "$BASE_URL/api/v2/cards/$CARD_ID/simulate-purchase" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":"25.00","currency":"USD","merchant_name":"Demo Casino","mcc_code":"7995"}' \
| .venv/bin/python -m json.tool
```

Show card tx history:
```bash
curl -sS "$BASE_URL/api/v2/cards/$CARD_ID/transactions" \
  -H "Authorization: Bearer $TOKEN" \
| .venv/bin/python -m json.tool
```

## 5) Stablecoin demo (Base Sepolia, agent is sender)

### 5.1 Fund the wallet on testnet
Bu demo’nun tek “manual” kısmı: `ADDR` adresine Base Sepolia ETH (gas) + Base Sepolia USDC gönderin.

### 5.2 Agent executes a stablecoin transfer (API key ile)

Bu çağrıyı “agent process” yapar: `X-API-Key` kullanır.
Demo açısından kritik nokta: bu çağrı bir “agent action”dır; tx’i imzalayan anahtar Turnkey’deki agent wallet’ıdır.

```bash
DEST=0x000000000000000000000000000000000000dEaD

STABLECOIN_TX=$(
  curl -sS -X POST "$BASE_URL/api/v2/wallets/$WALLET_ID/transfer" \
    -H "X-API-Key: $AGENT_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"destination\":\"$DEST\",\"amount\":\"1.00\",\"token\":\"USDC\",\"chain\":\"base_sepolia\",\"domain\":\"localhost\",\"memo\":\"demo stablecoin transfer\"}"
)
echo "$STABLECOIN_TX" | .venv/bin/python -m json.tool

TX_HASH=$(echo "$STABLECOIN_TX" | .venv/bin/python -c "import sys, json; print(json.load(sys.stdin)['tx_hash'])")
echo "tx_hash=$TX_HASH"
```

### 5.3 Show status + ledger

Tx status:
```bash
curl -sS "$BASE_URL/api/v2/transactions/status/$TX_HASH?chain=base_sepolia" \
  -H "Authorization: Bearer $TOKEN" \
| .venv/bin/python -m json.tool
```

Ledger recent:
```bash
curl -sS "$BASE_URL/api/v2/ledger/recent?limit=20" \
  -H "Authorization: Bearer $TOKEN" \
| .venv/bin/python -m json.tool
```
