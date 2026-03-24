# Sardis Mainnet Deployment Checklist

**Date:** 2026-03-24
**Target:** Base mainnet (chain ID 8453) + Tempo mainnet (chain ID 4217)
**Deployment:** Cloud Run (`sardis-api` service) + Neon PostgreSQL

---

## Phase 1: Pre-Deploy Checks

### 1.1 Environment Variables & Secrets

Verify all required secrets are set in GCP Secret Manager (`sardis-staging-01`):

```bash
# Check secrets exist
gcloud secrets list --project=sardis-staging-01 --format="value(name)" | sort
```

**Required secrets (must be non-empty):**

| Secret | GCP Secret Name | How to verify |
|--------|----------------|---------------|
| `DATABASE_URL` | `database-url` | `psql "$DATABASE_URL" -c "SELECT 1"` |
| `SARDIS_SECRET_KEY` | `sardis-secret-key` | Non-empty, 32+ chars |
| `JWT_SECRET_KEY` | `jwt-secret-key` | Non-empty, 64 hex chars |
| `SARDIS_ADMIN_PASSWORD` | `sardis-admin-password` | Non-empty, not default |
| `SARDIS_REDIS_URL` | `sardis-redis-url` | `redis-cli -u "$SARDIS_REDIS_URL" ping` |
| `TURNKEY_API_PUBLIC_KEY` | `turnkey-api-public-key` | Non-empty |
| `TURNKEY_API_PRIVATE_KEY` | `turnkey-api-private-key` | Non-empty |
| `TURNKEY_ORGANIZATION_ID` | `turnkey-organization-id` | Non-empty |

**Required env vars (set on Cloud Run service):**

| Variable | Value | Notes |
|----------|-------|-------|
| `SARDIS_ENVIRONMENT` | `prod` | Enables strict checks |
| `SARDIS_CHAIN_MODE` | `live` | Enables on-chain execution |
| `SARDIS_EXECUTION_MODE` | `production_live` | Full production path |
| `SARDIS_MPC__NAME` | `turnkey` | MPC signing via Turnkey |
| `SARDIS_BASE_RPC_URL` | Alchemy Base mainnet URL | Dedicated RPC, not public |
| `SARDIS_TEMPO_RPC_URL` | `https://rpc.tempo.xyz` | Tempo mainnet RPC |
| `SARDIS_PAYMASTER_PROVIDER` | `circle` | Circle Paymaster for gas |
| `SARDIS_DEFAULT_CHAIN` | `base` | Default chain for API calls |
| `SARDIS_HEALTH_CHAIN` | `base` | Health check chain target |

**Contract addresses (set after Base deploy, already set for Tempo):**

| Variable | Source |
|----------|--------|
| `SARDIS_BASE_LEDGER_ANCHOR_ADDRESS` | `contracts/deployments/base.json` → ledgerAnchor.address |
| `SARDIS_BASE_REFUND_PROTOCOL_ADDRESS` | `contracts/deployments/base.json` → refundProtocol.address |
| `SARDIS_ERC8183_ENABLED` | `true` |
| `SARDIS_ERC8183_CONTRACT_ADDRESS` | `contracts/deployments/base.json` → jobManager.address |
| `SARDIS_BASE_JOB_REGISTRY_ADDRESS` | `contracts/deployments/base.json` → jobRegistry.address |
| `SARDIS_BASE_JOB_MANAGER_ADDRESS` | `contracts/deployments/base.json` → jobManager.address |

**Tempo contract addresses (already deployed):**

| Contract | Address |
|----------|---------|
| LedgerAnchor | `0x9a5D2a6c81414FD1E6a2c9b55306c6D0b954b98B` |
| RefundProtocol | `0x801ea29ca523ea16475e3def938002d6be985e9d` |
| IdentityRegistry | `0xc5a3eb812bef4b883a2e890865de9d51818ac90a` |
| JobRegistry | `0x19eeeb6b349cfd4025cc75fa99bb36f6b8bec62d` |
| JobManager | `0x758114d2229d3da2a8629b96b0394a3e8319fbb0` |
| ReputationRegistry | `0x127ac64f6ddf7292e8dee43e39f4e66af859e704` |
| ValidationRegistry | `0xc95e58f9e1df9c3df4593632846eb2a02cf73d6b` |

### 1.2 Contract Deployment (Base Mainnet)

Base contracts are still `pending_deploy` (see `contracts/deployments/base.json`). Deploy before API goes live:

```bash
# Fund deployer wallet with ~0.001 ETH on Base
export PRIVATE_KEY=<deployer-private-key>
export SARDIS_ADDRESS=<sardis-platform-address>
export BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<key>
export BASESCAN_API_KEY=<key>

./scripts/deploy-mainnet-contracts.sh
```

After deployment:
1. Copy addresses from `/tmp/sardis-mainnet-deploy.log`
2. Update `contracts/deployments/base.json` with deployed addresses and `lifecycle: "canonical_live"`
3. Set env vars on Cloud Run (see Phase 3)

### 1.3 Pre-Deploy Validation

```bash
# Run smoke test against staging
./scripts/verify-mainnet.sh staging

# Run full test suite
uv run pytest tests/ -x -q

# Verify Docker builds
docker build -t sardis-api:pre-deploy .

# Check for secrets in code
./scripts/detect-secrets.sh
```

---

## Phase 2: Database Migrations

### 2.1 Migration Inventory

Total: 89 migrations (001-089). The run_migrations.sh script is idempotent -- it skips already-applied migrations.

**New migrations (078-089) added in this release:**

| Migration | Description | Risk |
|-----------|-------------|------|
| 078_payment_objects.sql | Payment object tables | Low -- new tables |
| 079_funding_cells.sql | Funding cell tables | Low -- new tables |
| 080_mandate_trees.sql | Mandate tree hierarchy | Low -- new tables |
| 081_state_transitions.sql | State transition log | Low -- new tables |
| 082_fx_quotes.sql | FX quote tables | Low -- new tables |
| 083_subscriptions.sql | Subscription enhancements | Low -- new tables |
| 084_disputes.sql | Dispute tables | Low -- new tables |
| 085_a2a_tables.sql | Agent-to-agent tables | Low -- new tables |
| 086_organizations_reconcile.sql | Org reconciliation | Medium -- alters existing |
| 087_missing_indexes.sql | Performance indexes | Low -- additive |
| 088_constraints_repair.sql | Constraint fixes | Medium -- alters constraints |
| 089_notification_configs.sql | Notification config | Low -- new tables |

### 2.2 Execute Migrations

```bash
# 1. Dry run first (see what will be applied)
DATABASE_URL="$PROD_DATABASE_URL" ./scripts/run_migrations.sh --dry-run

# 2. Take a Neon branch snapshot (point-in-time recovery)
#    Neon Console > Project > Branches > Create Branch (from main, current point)

# 3. Apply migrations
DATABASE_URL="$PROD_DATABASE_URL" ./scripts/run_migrations.sh

# 4. Verify
psql "$PROD_DATABASE_URL" -c "SELECT version, description, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 15;"
```

**Expected final state:** Migration 089 is the latest applied version.

### 2.3 Migration Rollback

If migrations fail partway through:
1. Check which migration failed: `SELECT MAX(version) FROM schema_migrations;`
2. Restore from the Neon branch snapshot taken in step 2.2.2
3. Fix the failing migration SQL
4. Re-run from the failed point

---

## Phase 3: Cloud Run Deployment

### 3.1 Build and Deploy

```bash
# Set project/region
export GOOGLE_CLOUD_PROJECT=sardis-staging-01
export CLOUD_RUN_REGION=us-east1

# Set any new env vars that need updating
export SARDIS_ENVIRONMENT=prod
export SARDIS_CHAIN_MODE=live
export SARDIS_EXECUTION_MODE=production_live
export SARDIS_MPC__NAME=turnkey
export SARDIS_DEFAULT_CHAIN=base
export SARDIS_HEALTH_CHAIN=base
export SARDIS_ERC8183_ENABLED=true
# ... set contract addresses from Phase 1.2

# Deploy (builds image via Cloud Build, deploys with --no-traffic first)
./scripts/deploy-cloudrun.sh production
```

### 3.2 Canary Verification

After deploy (traffic not yet routed):

```bash
# Get the new revision URL (no-traffic revision)
REVISION_URL=$(gcloud run revisions list \
  --service sardis-api \
  --project sardis-staging-01 \
  --region us-east1 \
  --format="value(status.url)" \
  --limit=1)

# Test health endpoint on new revision
curl -s "$REVISION_URL/health" | python3 -m json.tool

# Verify critical components
curl -s "$REVISION_URL/health" | python3 -c "
import json, sys
h = json.load(sys.stdin)
assert h['status'] in ('healthy', 'partial'), f'Unhealthy: {h[\"status\"]}'
assert h['execution_mode'] == 'production_live', f'Wrong mode: {h[\"execution_mode\"]}'
assert not h['critical_failures'], f'Critical failures: {h[\"critical_failures\"]}'
print('Canary health check PASSED')
"
```

### 3.3 Route Traffic

```bash
# Route 100% traffic to latest revision
gcloud run services update-traffic sardis-api \
  --project sardis-staging-01 \
  --region us-east1 \
  --to-latest

# Verify public URL
API_URL=$(gcloud run services describe sardis-api \
  --project sardis-staging-01 \
  --region us-east1 \
  --format="value(status.url)")

curl -s "$API_URL/health" | python3 -m json.tool
```

### 3.4 Run Post-Deploy Smoke Test

```bash
./scripts/verify-mainnet.sh production
```

---

## Phase 4: Post-Deploy Verification

### 4.1 Health Check Matrix

| Endpoint | Expected | Command |
|----------|----------|---------|
| `GET /` | 200, `status: healthy` | `curl -s $API_URL/` |
| `GET /health` | 200, `status: healthy` | `curl -s $API_URL/health` |
| `GET /health/live` | 200, `status: alive` | `curl -s $API_URL/health/live` |
| `GET /ready` | 200, `status: ready` | `curl -s $API_URL/ready` |
| `GET /api/v2/health` | 200, `status: ok` | `curl -s $API_URL/api/v2/health` |

### 4.2 Component Health

From `/health` response, verify:
- `components.database.status` = `healthy`
- `components.cache.status` = `healthy` (Redis)
- `components.rpc.status` = `healthy`
- `components.turnkey.status` = `healthy`
- `components.contracts.status` = `healthy`
- `components.custody.non_custodial` = `true`
- `critical_failures` = `[]` (empty)

### 4.3 Functional Smoke Test

```bash
# 1. Create an API key (via admin)
# 2. Create an agent
curl -s -X POST "$API_URL/api/v2/agents" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"name": "smoke-test-agent"}'

# 3. Create a wallet for the agent
curl -s -X POST "$API_URL/api/v2/wallets" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"agent_id": "<agent_id>", "chain": "base"}'

# 4. Check wallet balance
curl -s "$API_URL/api/v2/wallets/<wallet_id>/balance" \
  -H "Authorization: Bearer $API_KEY"
```

---

## Phase 5: Rollback Procedure

### 5.1 Instant Rollback (Traffic Routing)

Route traffic back to the previous revision (zero downtime):

```bash
# List recent revisions
gcloud run revisions list \
  --service sardis-api \
  --project sardis-staging-01 \
  --region us-east1 \
  --limit=5

# Route 100% to previous revision
gcloud run services update-traffic sardis-api \
  --project sardis-staging-01 \
  --region us-east1 \
  --to-revisions=<previous-revision-name>=100
```

### 5.2 Database Rollback

If migrations caused issues:

1. **Neon branch restore:** Restore the branch snapshot created before migrations
2. **Manual rollback:** If only specific migrations need reverting, check for `*_rollback.sql` files
   - Only migration 001 has a rollback file (`001_initial_schema_rollback.sql`)
   - For others, manually reverse using the migration SQL as reference

### 5.3 Contract Rollback

Smart contracts are immutable once deployed. If a contract has a critical bug:
1. Pause the contract (if it has a pause function)
2. Deploy a new version
3. Update env vars to point to the new address
4. Redeploy Cloud Run

### 5.4 Full Rollback Sequence

1. Route Cloud Run traffic to previous revision (immediate)
2. Restore Neon DB branch if migrations are incompatible
3. Verify health on rollback revision
4. Investigate root cause before re-attempting

---

## Appendix: Pre-Deployed Infrastructure

These contracts are already live and do NOT need deployment:

| Component | Address | Chain |
|-----------|---------|-------|
| Zodiac Roles (policy) | `0x9646fDAD06d3e24444381f44362a3B0eB343D337` | Base |
| Circle Paymaster | `0x0578cFB241215b77442a541325d6A4E6dFE700Ec` | Base |
| Safe ProxyFactory | `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` | Base |
| CCTP TokenMessenger V2 | `0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d` | All EVM |
| CCTP MessageTransmitter V2 | `0x81D40F21F12A8F0E3252Bccb954D722d4c464B64` | All EVM |
| Base USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Base |
