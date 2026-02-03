# Sardis Demo API Runbook (Investor-Ready)

This runbook is optimized for the **end-to-end demo flow**:
Login → Create Turnkey wallet → Apply “block gambling” policy → Issue Lithic card → Simulate purchase → Show enforcement.

## Required env vars (demo)

- `SARDIS_ENVIRONMENT=dev` (or `sandbox`)
- `JWT_SECRET_KEY` (min 32 chars)
- `SARDIS_ADMIN_PASSWORD`
- `TURNKEY_ORGANIZATION_ID`
- `TURNKEY_API_PUBLIC_KEY` (or `TURNKEY_API_KEY`)
- `TURNKEY_API_PRIVATE_KEY`
- `LITHIC_API_KEY`
- `LITHIC_WEBHOOK_SECRET` (optional for real webhook; **not required** for `/simulate-purchase`)

Optional but recommended:
- `SARDIS_DEFAULT_ORG_ID=org_demo`
- `REDIS_URL` (or `SARDIS_REDIS_URL` / `UPSTASH_REDIS_URL`)
- `SARDIS_AUTO_FREEZE_ON_POLICY_DENY=1` (default: enabled outside prod)

## 1) Login (JWT)

```bash
BASE_URL=http://localhost:8000

TOKEN=$(
  curl -sS -X POST "$BASE_URL/api/v2/auth/login" \
    -F "username=admin" \
    -F "password=$SARDIS_ADMIN_PASSWORD" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])"
)
echo "$TOKEN" | head -c 24 && echo "…"
```

## 2) (Optional) Bootstrap an admin API key using the JWT

```bash
API_KEY=$(
  curl -sS -X POST "$BASE_URL/api/v2/auth/bootstrap-api-key" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"name":"Demo Admin Key","scopes":["admin","*"]}' \
  | python -c "import sys, json; print(json.load(sys.stdin)['key'])"
)
echo "$API_KEY" | head -c 18 && echo "…"
```

## 3) Create a Turnkey wallet (real address)

```bash
WALLET=$(
  curl -sS -X POST "$BASE_URL/api/v2/wallets" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"agent_id":"agent_demo_001","mpc_provider":"turnkey","wallet_name":"agent_demo_001"}'
)
echo "$WALLET" | python -m json.tool

WALLET_ID=$(echo "$WALLET" | python -c "import sys, json; print(json.load(sys.stdin)['wallet_id'])")
echo "wallet_id=$WALLET_ID"
```

## 4) Apply policy: “block gambling”

```bash
curl -sS -X POST "$BASE_URL/api/v2/policies/apply" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"agent_demo_001","natural_language":"Max $100 per transaction, block gambling","confirm":true}' \
| python -m json.tool
```

## 5) Issue a virtual card

```bash
CARD=$(
  curl -sS -X POST "$BASE_URL/api/v2/cards" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"wallet_id\":\"$WALLET_ID\",\"limit_per_tx\":\"100.00\"}"
)
echo "$CARD" | python -m json.tool

CARD_ID=$(echo "$CARD" | python -c "import sys, json; print(json.load(sys.stdin)['card_id'])")
echo "card_id=$CARD_ID"
```

## 6) Simulate a purchase (Gambling MCC) → Policy denial + auto-freeze

MCC examples:
- `7995` gambling
- `5734` software

```bash
curl -sS -X POST "$BASE_URL/api/v2/cards/$CARD_ID/simulate-purchase" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"amount":"25.00","currency":"USD","merchant_name":"Demo Casino","mcc_code":"7995"}' \
| python -m json.tool
```

## 7) Show transactions

```bash
curl -sS "$BASE_URL/api/v2/cards/$CARD_ID/transactions" \
  -H "Authorization: Bearer $TOKEN" \
| python -m json.tool
```

