# Production Operations Runbook

> Owner: Engineering | Last updated: 2026-03-08

This document covers day-to-day operational procedures for the Sardis production environment. For incident-specific procedures, see also `docs/runbooks/incident-response.md` and `docs/runbooks/key-compromise.md`.

---

## 1. Health Checks

### Deep Health Check

The deep health check probes all critical subsystems (database, Redis, RPC, Turnkey, Stripe, contracts, kill switch) and returns a structured report.

```bash
curl -s https://api.sardis.sh/health | jq .
```

**Expected response (healthy):**

```json
{
  "status": "healthy",
  "environment": "production",
  "chain_mode": "live",
  "execution_mode": "production_live",
  "version": "2.0.0",
  "timestamp": "2026-03-08T12:00:00Z",
  "response_time_ms": 142,
  "checks": { "passed": 6, "total": 6 },
  "critical_failures": [],
  "non_critical_failures": [],
  "components": {
    "api": { "status": "up", "uptime_seconds": 86400 },
    "database": { "status": "connected", "type": "postgresql", "latency_ms": 12 },
    "chain_executor": { "status": "up", "mode": "live", "execution_mode": "production_live" },
    "custody": { "status": "non_custodial_mpc", "non_custodial": true, "configured_mpc": "turnkey" },
    "cache": { "status": "connected", "type": "redis", "latency_ms": 3 },
    "stripe": { "status": "connected", "latency_ms": 200 },
    "turnkey": { "status": "reachable", "latency_ms": 150 },
    "rpc": { "status": "configured", "chain": "base", "endpoint": "https://base-mainnet.g.alchemy.com" },
    "contracts": { "status": "configured", "policy_module": "0x9646fDAD...", "chain": "base" },
    "kill_switch": { "status": "clear", "global_active": false },
    "webhooks": { "status": "up" },
    "compliance": { "status": "check_required" }
  }
}
```

**Field reference:**

| Field | Meaning |
|-------|---------|
| `status` | Overall status: `healthy` (all checks pass), `partial` (non-critical failures), `degraded` (critical failures, returns HTTP 503), `shutting_down` (graceful shutdown in progress, returns HTTP 503) |
| `checks.passed / checks.total` | Number of component checks that passed vs total attempted |
| `critical_failures` | Array of failures that indicate service is unable to process payments (database down, Turnkey unreachable in live mode) |
| `non_critical_failures` | Array of failures that degrade but do not block operations (Redis down, Stripe unreachable) |
| `components.database.status` | `connected` = PostgreSQL responding, `disconnected` = connection failed, `in_memory` = dev mode |
| `components.cache.status` | `connected` = Redis PING succeeded, `error` = Redis unreachable, `in_memory` = no Redis configured |
| `components.kill_switch.global_active` | `true` = all agent payments are blocked globally |
| `components.custody.non_custodial` | `true` = MPC signing via Turnkey/Fireblocks (no private keys in memory) |

### Lightweight Health Check (API v2)

For load balancer probes or quick checks that skip deep component probing:

```bash
curl -s https://api.sardis.sh/api/v2/health | jq .
```

Returns `{"status": "ok", "version": "2.0.0", "timestamp": "..."}`.

### Liveness and Readiness Probes

Used by Cloud Run / Kubernetes:

```bash
# Liveness (is the process alive?)
curl -s https://api.sardis.sh/live
# {"status": "alive"}

# Readiness (is the process accepting traffic?)
curl -s https://api.sardis.sh/ready
# {"status": "ready"}  -- or 503 {"status": "shutting_down"} during graceful shutdown
```

### Database Connectivity Check

The `/health` endpoint runs `SELECT 1` against Neon PostgreSQL. If it fails, the `components.database` block will show:

```json
{ "status": "disconnected", "type": "postgresql", "error": "..." }
```

To manually verify database connectivity from a machine with `psql`:

```bash
psql "$DATABASE_URL" -c "SELECT 1;"
```

### Redis Connectivity Check

The `/health` endpoint sends a `PING` to Upstash Redis. If it fails, `components.cache` will show:

```json
{ "status": "error", "type": "redis", "error": "..." }
```

To manually verify:

```bash
redis-cli -u "$UPSTASH_REDIS_URL" PING
# Expected: PONG
```

---

## 2. Transaction Inspection

### Look Up a Transaction by ID

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/transactions/{tx_hash}/status | jq .
```

**Response fields:**

| Field | Description |
|-------|-------------|
| `tx_hash` | On-chain transaction hash |
| `chain` | Chain the transaction was submitted on |
| `status` | `pending`, `confirmed`, `failed` |
| `block_number` | Block in which the transaction was mined |
| `confirmations` | Number of blocks since the transaction was mined |
| `explorer_url` | Direct link to the block explorer |

### Verify On-Chain via BaseScan

For Base mainnet transactions, open the explorer URL directly:

```
https://basescan.org/tx/{tx_hash}
```

Or use `cast` from Foundry:

```bash
cast tx {tx_hash} --rpc-url "$SARDIS_BASE_RPC_URL"
```

To check receipt and confirm success:

```bash
cast receipt {tx_hash} --rpc-url "$SARDIS_BASE_RPC_URL"
```

Look for `status: 1` (success) or `status: 0` (reverted).

### Check Ledger Entries

The append-only ledger records every financial event. Query by transaction ID:

```bash
# Get all ledger entries
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/ledger/entries | jq .

# Get a specific entry by transaction ID
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/ledger/entries/{tx_id} | jq .

# Verify ledger integrity (hash chain)
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/ledger/entries/{tx_id}/verify | jq .
```

To check recent ledger activity:

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/ledger/recent | jq .
```

Ledger stats (total entries, volume):

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/ledger/stats | jq .
```

---

## 3. Cloud Run Operations

The API is deployed on Google Cloud Run as `sardis-api-staging`.

### View Logs

```bash
# Last 50 log entries
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=sardis-api-staging" \
  --limit=50 \
  --format="table(timestamp, textPayload)"

# Filter for errors only
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=sardis-api-staging AND severity>=ERROR" \
  --limit=20

# Filter by request ID (from X-Request-ID header)
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=sardis-api-staging AND textPayload:\"req_abc123\"" \
  --limit=10
```

### Check Current Revision

```bash
gcloud run services describe sardis-api-staging \
  --region=us-central1 \
  --format="table(status.traffic[].revisionName, status.traffic[].percent)"
```

### Rollback to a Previous Revision

```bash
# List recent revisions
gcloud run revisions list --service=sardis-api-staging --region=us-central1 --limit=5

# Route 100% traffic to a specific revision
gcloud run services update-traffic sardis-api-staging \
  --region=us-central1 \
  --to-revisions=REVISION_NAME=100
```

Replace `REVISION_NAME` with the target revision (e.g., `sardis-api-staging-00042-abc`).

### Scale

```bash
# Set min/max instance counts
gcloud run services update sardis-api-staging \
  --region=us-central1 \
  --min-instances=1 \
  --max-instances=10
```

Setting `--min-instances=1` keeps one instance warm to avoid cold starts.

### Update Environment Variables

**CRITICAL: Always use `--update-env-vars`, never `--set-env-vars`.** Using `--set-env-vars` wipes all existing environment variables.

```bash
# Add or update a single variable
gcloud run services update sardis-api-staging \
  --region=us-central1 \
  --update-env-vars KEY=VALUE

# Add or update multiple variables
gcloud run services update sardis-api-staging \
  --region=us-central1 \
  --update-env-vars KEY1=VALUE1,KEY2=VALUE2
```

### Redeploy

Use the deploy script:

```bash
./scripts/deploy-cloudrun.sh
```

---

## 4. Kill Switch

The kill switch is an emergency mechanism to stop agent payments. It operates at five scopes: global, organization, agent, payment rail, and blockchain chain. State is persisted in Redis (required for production multi-instance deployments).

### Check Status

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/kill-switch/status | jq .
```

**Response:**

```json
{
  "global": null,
  "organizations": {},
  "agents": {},
  "rails": {},
  "chains": {}
}
```

A `null` or empty object means the switch is inactive for that scope. An activation object looks like:

```json
{
  "reason": "manual",
  "activated_at": 1741392000.0,
  "activated_by": "admin-user-123",
  "notes": "Suspicious activity on agent agt_abc",
  "auto_reactivate_at": null
}
```

### Activate Kill Switch (Disable Payments)

**Activate by rail** (e.g., stop all USDC payments, all card payments):

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rail": "usdc", "reason": "manual", "notes": "Investigating suspicious transfers"}' \
  https://api.sardis.sh/api/v2/kill-switch/rails/activate | jq .
```

**Activate by chain** (e.g., stop all Base transactions):

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"chain": "base", "reason": "manual", "notes": "Chain congestion causing failures"}' \
  https://api.sardis.sh/api/v2/kill-switch/chains/activate | jq .
```

### Deactivate Kill Switch (Re-enable Payments)

```bash
# Re-enable a rail
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rail": "usdc"}' \
  https://api.sardis.sh/api/v2/kill-switch/rails/deactivate | jq .

# Re-enable a chain
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"chain": "base"}' \
  https://api.sardis.sh/api/v2/kill-switch/chains/deactivate | jq .
```

### When to Use the Kill Switch

| Scenario | Scope | Reason |
|----------|-------|--------|
| Suspected compromise of signing keys | Global | `fraud` |
| Runaway agent making unauthorized payments | Agent | `anomaly` |
| Compliance hold from legal team | Organization | `compliance` |
| Chain experiencing congestion or reorgs | Chain | `manual` |
| Suspected exploit on a payment rail | Rail | `fraud` |
| Policy engine returning unexpected results | Global | `policy_violation` |
| Coordinated attack across multiple agents | Global | `fraud` |

### Auto-Reactivation

Kill switches can be set to auto-deactivate after a period (e.g., temporary cooldown):

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rail": "usdc", "reason": "rate_limit", "auto_reactivate": 3600, "notes": "1-hour cooldown"}' \
  https://api.sardis.sh/api/v2/kill-switch/rails/activate | jq .
```

The `auto_reactivate` value is in seconds.

### Activation Reasons

| Reason | Code | Description |
|--------|------|-------------|
| Manual operator action | `manual` | Human decision to halt payments |
| Behavioral anomaly | `anomaly` | Unusual transaction patterns detected |
| Compliance violation | `compliance` | Regulatory or legal requirement |
| Suspected fraud | `fraud` | Unauthorized or fraudulent activity |
| Rate limit breach | `rate_limit` | Agent exceeded payment rate limits |
| Policy violation | `policy_violation` | Spending policy rule was violated |

---

## 5. Contract State

### Deployed Contracts

| Contract | Chain | Address |
|----------|-------|---------|
| Policy Module (Zodiac Roles) | Base | `0x9646fDAD06d3e24444381f44362a3B0eB343D337` |
| SardisLedgerAnchor | Base | Pending mainnet deployment |
| RefundProtocol (Circle) | Base | Pending mainnet deployment |

### Check Contract State via BaseScan

Open the contract address on BaseScan to view state, transactions, and events:

```
https://basescan.org/address/0x9646fDAD06d3e24444381f44362a3B0eB343D337
```

### Check Contract State via cast (Foundry)

```bash
# Check if a contract is deployed (returns bytecode)
cast code 0x9646fDAD06d3e24444381f44362a3B0eB343D337 --rpc-url "$SARDIS_BASE_RPC_URL"

# Read a storage slot
cast storage 0x9646fDAD06d3e24444381f44362a3B0eB343D337 0 --rpc-url "$SARDIS_BASE_RPC_URL"

# Call a view function (example: check module owner)
cast call 0x9646fDAD06d3e24444381f44362a3B0eB343D337 \
  "owner()(address)" \
  --rpc-url "$SARDIS_BASE_RPC_URL"
```

### Verify Safe Smart Account State

Agent wallets use Safe Smart Accounts (v1.4.1). To check a wallet's Safe state:

```bash
# Get Safe owners
cast call {SAFE_ADDRESS} "getOwners()(address[])" --rpc-url "$SARDIS_BASE_RPC_URL"

# Get Safe threshold
cast call {SAFE_ADDRESS} "getThreshold()(uint256)" --rpc-url "$SARDIS_BASE_RPC_URL"

# Check if a module is enabled
cast call {SAFE_ADDRESS} \
  "isModuleEnabled(address)(bool)" \
  0x9646fDAD06d3e24444381f44362a3B0eB343D337 \
  --rpc-url "$SARDIS_BASE_RPC_URL"
```

---

## 6. Wallet Operations

### List Wallets

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets | jq .
```

### Get Wallet Details

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id} | jq .
```

### Check Wallet Balance

Single chain:

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/balance | jq .
```

All chains:

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/balances | jq .
```

### Check Wallet Addresses

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/addresses | jq .
```

### Get Wallet by Agent ID

```bash
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/agent/{agent_id} | jq .
```

### Freeze a Wallet

Freezing a wallet blocks all outbound transactions from it. Use this when a specific agent or wallet is compromised.

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Suspected unauthorized access", "frozen_by": "ops-admin"}' \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/freeze | jq .
```

### Unfreeze a Wallet

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/unfreeze | jq .
```

### Update Wallet Spending Limits

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"limit_per_tx": "50.00", "limit_total": "500.00"}' \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/limits | jq .
```

---

## 7. Incident Response Playbook

For the full incident response procedure, see `docs/runbooks/incident-response.md`. Below is the condensed operational checklist.

### Step 1: Activate Kill Switch

If the incident involves financial risk, activate the kill switch immediately. Scope it as narrowly as possible.

```bash
# Global halt (nuclear option -- use only when scope is unknown)
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"rail": "usdc", "reason": "fraud", "notes": "Incident INC-001: investigating unauthorized transfers"}' \
  https://api.sardis.sh/api/v2/kill-switch/rails/activate | jq .
```

If the issue is isolated to a single wallet, freeze it instead:

```bash
curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Incident INC-001", "frozen_by": "ops-team"}' \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/freeze | jq .
```

### Step 2: Check Transaction Logs

```bash
# Check API health
curl -s https://api.sardis.sh/health | jq '.status, .critical_failures'

# Check recent ledger activity
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/ledger/recent | jq .

# Check Cloud Run logs for errors
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=sardis-api-staging AND severity>=ERROR" \
  --limit=20 \
  --format="table(timestamp, textPayload)"
```

### Step 3: Identify Scope

Determine:
- **What wallets are affected?** Check wallet balances and recent transactions.
- **What time window?** Use ledger entries with timestamps.
- **Is the issue on-chain or off-chain?** Cross-reference ledger with BaseScan.
- **Is it an agent issue or platform issue?** Check if the kill switch status shows agent-level activations.

```bash
# Check kill switch status for any automated activations
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/kill-switch/status | jq .

# Check a specific wallet
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/balance | jq .
```

### Step 4: Notify Stakeholders

- Post in `#alerts-p0` or `#alerts-p1` Slack channel
- If funds are at risk, notify CEO and CTO immediately
- If customer data is involved, notify compliance team
- Document the incident timeline in the thread

### Step 5: Remediate

Depending on the root cause:

| Root Cause | Action |
|------------|--------|
| Compromised API key | Rotate the key, check affected transactions |
| Runaway agent | Freeze wallet, deactivate agent, review policy |
| Smart contract bug | Activate kill switch on affected chain, prepare patch |
| Chain congestion | Activate chain kill switch, wait for conditions to improve |
| Database issue | Check Neon dashboard, consider failover |
| Bad deployment | Rollback Cloud Run revision (see Section 3) |

### Step 6: Post-Mortem

After resolution:
1. Deactivate any kill switches that were activated
2. Unfreeze any wallets that were frozen
3. Write a post-mortem within 48 hours (P0) or 5 days (P1)
4. File follow-up tickets for preventive measures
5. Update this runbook if the incident revealed gaps

---

## 8. Common Issues

### Error Reference Table

| Error / Symptom | Likely Cause | Fix |
|-----------------|-------------|-----|
| `401 Unauthorized` on API calls | Invalid or expired API key | Verify `SARDIS_API_KEY` is correct. Keys are SHA-256 hashed; ensure you are using the raw key, not the hash. |
| `403 Forbidden` | API key lacks permission for the endpoint | Check the key's scopes in the dashboard or via `GET /api/v2/api-keys`. |
| `429 Too Many Requests` | Rate limit exceeded | Back off and retry. Check `Retry-After` header. Agent payment rate limits are per-agent. |
| `503 Service Unavailable` from `/health` | Critical component down (database, Turnkey in live mode) | Check `critical_failures` array in health response. Likely database or MPC provider. |
| `503 Service Unavailable` from `/ready` | Service is in graceful shutdown | Wait for the new revision to become ready. If rollback is needed, route traffic manually. |
| `KillSwitchError` in logs | Kill switch is active | Check `GET /api/v2/kill-switch/status` to find which scope is active and whether it was manual or automated. |
| Transaction stuck at `pending` | Chain congestion or low gas | Check the transaction on BaseScan. If using Circle Paymaster, gas is sponsored. Check RPC health in `/health`. |
| Transaction `failed` / `reverted` | Insufficient balance, policy rejection, or contract revert | Check the revert reason with `cast receipt {tx_hash}`. Check spending policy with `GET /api/v2/policies`. |
| `SARDIS.HEALTH.DATABASE_UNAVAILABLE` | PostgreSQL connection failed | Check Neon dashboard. Verify `DATABASE_URL` env var. Try `psql` manually. |
| `SARDIS.HEALTH.REDIS_PING_FAILED` | Redis connection failed | Check Upstash dashboard. Verify `UPSTASH_REDIS_URL` env var. Non-critical for API but critical for kill switch in production. |
| `SARDIS.HEALTH.TURNKEY_UNREACHABLE` | Turnkey MPC service unreachable | Check Turnkey status page. Critical in live execution mode. Payments will fail. |
| `SARDIS.HEALTH.RPC_UNCONFIGURED` | No RPC endpoint set for the target chain | Set `SARDIS_BASE_RPC_URL` (or appropriate chain env var). Alchemy is the primary provider. |
| `SARDIS.HEALTH.CONTRACTS_UNCONFIGURED` | Policy module address not set for target chain | Deploy contracts or set the policy module address in chain config. |
| Wallet balance shows `0` but funds were sent | Querying wrong chain, or deposit not yet indexed | Check `GET /api/v2/wallets/{id}/balances` for all chains. Verify the deposit tx on BaseScan. |
| `CRITICAL: Redis is required for production kill switch` | Starting in production without Redis | Set `SARDIS_REDIS_URL`, `REDIS_URL`, or `UPSTASH_REDIS_URL`. Redis is mandatory for multi-instance kill switch consistency. |

### API Key Troubleshooting

```bash
# List your API keys (redacted)
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/api-keys | jq .

# Test authentication
curl -s -o /dev/null -w "%{http_code}" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets
# 200 = valid, 401 = invalid key, 403 = insufficient permissions
```

### Chain Congestion

When Base (or another chain) is congested:

1. Check current gas prices:
   ```bash
   cast gas-price --rpc-url "$SARDIS_BASE_RPC_URL"
   ```

2. Check block number to verify RPC is synced:
   ```bash
   cast block-number --rpc-url "$SARDIS_BASE_RPC_URL"
   ```

3. If transactions are failing, activate the chain kill switch temporarily:
   ```bash
   curl -s -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"chain": "base", "reason": "manual", "notes": "Chain congestion", "auto_reactivate": 1800}' \
     https://api.sardis.sh/api/v2/kill-switch/chains/activate | jq .
   ```

### Insufficient Balance

```bash
# Check wallet balance
curl -s -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/wallets/{wallet_id}/balance | jq .

# Check on-chain balance directly
cast call {USDC_CONTRACT} \
  "balanceOf(address)(uint256)" {WALLET_ADDRESS} \
  --rpc-url "$SARDIS_BASE_RPC_URL"
```

USDC on Base mainnet: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

---

## Appendix: Quick Reference

### Key URLs

| Resource | URL |
|----------|-----|
| API | `https://api.sardis.sh` |
| API Docs (OpenAPI) | `https://api.sardis.sh/api/v2/docs` |
| Health (deep) | `https://api.sardis.sh/health` |
| Health (lightweight) | `https://api.sardis.sh/api/v2/health` |
| BaseScan | `https://basescan.org` |
| Neon Dashboard | `https://console.neon.tech` |
| Upstash Dashboard | `https://console.upstash.com` |
| Turnkey Dashboard | `https://app.turnkey.com` |
| Cloud Run Console | `https://console.cloud.google.com/run` |

### Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `SARDIS_API_KEY` | API authentication |
| `DATABASE_URL` | Neon PostgreSQL connection string |
| `UPSTASH_REDIS_URL` | Redis (kill switch, caching) |
| `SARDIS_BASE_RPC_URL` | Alchemy RPC for Base |
| `TURNKEY_API_KEY` | MPC signing provider |
| `TURNKEY_ORGANIZATION_ID` | Turnkey org |
| `STRIPE_SECRET_KEY` | Stripe Issuing |
| `SARDIS_ENVIRONMENT` | `dev`, `staging`, `production` |
| `SARDIS_MPC__NAME` | MPC provider: `turnkey`, `fireblocks`, `local`, `simulated` |

### Related Runbooks

- `docs/runbooks/incident-response.md` -- Full incident lifecycle and SLA timers
- `docs/runbooks/key-compromise.md` -- Key rotation and compromise response
- `docs/runbooks/rollback.md` -- Deployment rollback procedures
- `docs/on-call.md` -- On-call schedule and escalation
- `docs/slo.md` -- Service level objectives
