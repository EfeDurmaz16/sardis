# Runbook: Rollback & Failover
> Owner: Engineering | Last updated: 2026-03-03

---

## 1. Application Rollback (Vercel)

### Instant rollback to previous deploy
```bash
# List recent deployments
vercel ls

# Rollback to a specific deployment (< 30 seconds)
vercel rollback <deployment-url-or-id> --scope sardis

# Or via Vercel dashboard:
# vercel.com/sardis → Deployments → click previous deploy → Promote to Production
```

### Validate rollback
```bash
curl https://api.sardis.sh/health
curl https://api.sardis.sh/api/v2/health

# Check version info
curl https://api.sardis.sh/api/v2/ | jq '.version'
```

---

## 2. Database Rollback

### Revert a migration (Alembic)
```bash
# From the repo root:
cd packages/sardis-core

# Check current revision
uv run alembic current

# Downgrade one step
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade <revision_id>

# ⚠️ WARNING: Some downgrade migrations are destructive (DROP COLUMN).
# Always verify the migration file before running downgrade in production.
```

### Point-in-time recovery (Neon)
```bash
# Option A: Neon Console
# console.neon.tech → your project → Restore → choose point in time

# Option B: Neon API
curl -X POST https://console.neon.tech/api/v2/projects/<project_id>/restore \
  -H "Authorization: Bearer $NEON_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "source_branch_id": "<branch_id>",
    "source_timestamp": "2026-03-03T10:00:00Z"
  }'
```

---

## 3. Feature Disable via Environment Variables

If a specific feature is causing issues, disable it without a full rollback:

| Feature | Env Var to Disable | Effect |
|---|---|---|
| Cards | `SARDIS_ENABLE_CARDS=false` | Card endpoints return 503 |
| Off-ramp | Remove `BRIDGE_API_KEY` | Off-ramp returns 503 |
| KYC | `SARDIS_KYC_ENABLED=false` | Skips KYC gate (use only in emergency) |
| ERC-4337 | `SARDIS_ERC4337_ENABLED=false` | Falls back to EOA transactions |
| Webhooks | `SARDIS_WEBHOOKS_ENABLED=false` | Stops outbound webhook delivery |
| Compliance | `SARDIS_COMPLIANCE_STRICT=false` | Soft mode (logs but doesn't block) |

Update env vars in Vercel:
```bash
vercel env rm SARDIS_ENABLE_CARDS production
vercel env add SARDIS_ENABLE_CARDS production  # enter: false
vercel --prod  # trigger redeploy
```

---

## 4. Smart Contract Rollback

Smart contracts are **immutable** — there is no rollback. Mitigation options:

### Pause contract (if pause function exists)
```bash
# SardisPolicyModule has pause function
cast send $SARDIS_BASE_POLICY_MODULE_ADDRESS \
  "pause()" \
  --rpc-url $BASE_RPC_URL \
  --private-key $SARDIS_PRIVATE_KEY
```

### Deploy new contract version
```bash
cd contracts
forge script script/DeploySafeModules.s.sol \
  --rpc-url $BASE_RPC_URL \
  --broadcast \
  --verify

# Update SARDIS_CONTRACTS["base"] in executor.py with new addresses
# Deploy new API version pointing to new contracts
```

---

## 5. RPC Failover

If Alchemy RPC is unavailable:
```bash
# Switch to backup RPC in Vercel:
vercel env rm SARDIS_BASE_RPC_URL production
vercel env add SARDIS_BASE_RPC_URL production
# Enter backup: https://base.publicnode.com  (free, no auth)
# Or: https://base-mainnet.g.alchemy.com/v2/<backup-key>
```

Fallback RPC priority order:
1. Alchemy (primary) — `SARDIS_BASE_RPC_URL`
2. Coinbase Node — `https://mainnet.base.org` (free, no auth)
3. Public node — `https://base.publicnode.com`
4. Blast API — `https://base-mainnet.public.blastapi.io`

---

## 6. External Provider Failover

### Circle Paymaster unavailable
```bash
# Switch to Pimlico bundler in executor config:
# Set SARDIS_PAYMASTER_MODE=pimlico
# The executor falls back to Pimlico if Circle fails (already coded in paymaster_client.py)
```

### iDenfy KYC unavailable
```bash
# Option: Put KYC in deferred mode (approve with manual review flag)
# Set SARDIS_KYC_MODE=deferred
# New users get approved with kyc_status="pending_review"
# Manual review required before allowing transactions > $100
```

---

## 7. Post-Rollback Validation

Run after every rollback:
```bash
# 1. Health checks
curl https://api.sardis.sh/health
curl https://api.sardis.sh/api/v2/health

# 2. Policy check works
curl -X POST https://api.sardis.sh/api/v2/policies/check \
  -H "X-API-Key: $TEST_API_KEY" \
  -d '{"amount": 1.0, "token": "USDC"}'

# 3. No stuck transactions in DB
psql $DATABASE_URL -c "
  SELECT id, status, created_at FROM transactions
  WHERE status = 'processing' AND created_at < now() - interval '10 minutes';
"

# 4. Verify error rate dropped
# Check Vercel function logs for error rate returning to baseline
```
