# Sardis Operational Runbook

This runbook provides step-by-step procedures for common operational tasks and incident response scenarios for Sardis operators.

## Table of Contents

1. [System Health Checks](#system-health-checks)
2. [Common Operations](#common-operations)
3. [Incident Response](#incident-response)
4. [Database Operations](#database-operations)
5. [External Service Issues](#external-service-issues)
6. [Monitoring and Alerts](#monitoring-and-alerts)

---

## System Health Checks

### Daily Health Check

```bash
# 1. Check API health endpoint
curl https://api.sardis.sh/health

# Expected response:
# {
#   "status": "healthy",
#   "database": "connected",
#   "redis": "connected",
#   "version": "2.0.0"
# }

# 2. Check database connections
psql $DATABASE_URL -c "SELECT COUNT(*) FROM pg_stat_activity;"

# 3. Check Redis connectivity
redis-cli -u $REDIS_URL ping
# Expected: PONG

# 4. Verify recent transactions
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/transactions?limit=10
```

### Weekly Health Check

```bash
# 1. Review error logs in Sentry
# Visit: https://sentry.io/sardis/errors

# 2. Check disk usage on Neon
# Visit Neon dashboard: https://console.neon.tech

# 3. Review webhook delivery success rates
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/webhooks/deliveries?status=failed

# 4. Verify Turnkey MPC connectivity
# This should be monitored via health checks
curl https://api.sardis.sh/health | jq '.turnkey'
```

---

## Common Operations

### Rotate API Keys

**When:** Quarterly, or immediately after suspected compromise

```bash
# 1. Generate new API key
python -c "import secrets; print('sk_live_' + secrets.token_hex(32))"

# 2. Update in Vercel
vercel env add SARDIS_API_KEY production
# Paste the new key when prompted

# 3. Redeploy API
vercel --prod

# 4. Notify API consumers
# Send migration notice with 7-day transition period

# 5. After transition, revoke old key
# Old keys become invalid automatically via hash comparison
```

### Rotate Database Credentials

**When:** Quarterly, or after security incident

```bash
# 1. Create new role in Neon console
# Visit: https://console.neon.tech -> Settings -> Roles

# 2. Generate new connection string
# Copy from Neon dashboard

# 3. Update Vercel env
vercel env add DATABASE_URL production
# Paste new connection string

# 4. Redeploy
vercel --prod

# 5. Wait 5 minutes for connection pool to drain

# 6. Revoke old role in Neon console
```

### Rotate Turnkey API Keys

**When:** Quarterly

```bash
# 1. Generate new API key pair in Turnkey dashboard
# Visit: https://app.turnkey.com -> Settings -> API Keys

# 2. Update both keys in Vercel
vercel env add TURNKEY_API_PUBLIC_KEY production
vercel env add TURNKEY_API_PRIVATE_KEY production

# 3. Update organization ID if changed
vercel env add TURNKEY_ORGANIZATION_ID production

# 4. Redeploy
vercel --prod

# 5. Verify MPC signing works
curl https://api.sardis.sh/health | jq '.mpc'

# 6. Revoke old API key pair in Turnkey dashboard
```

### Manual Approval Request Review

**When:** High-value or high-risk approval pending

```bash
# 1. List pending approvals
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/approvals?status=pending

# 2. Get approval details
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/approvals/{approval_id}

# 3. Review agent history
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/agents/{agent_id}/transactions

# 4. Approve or deny
# Approve:
curl -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/approvals/{approval_id}/approve \
  -d '{"reviewed_by": "operator@sardis.dev"}'

# Deny:
curl -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/approvals/{approval_id}/deny \
  -d '{"reviewed_by": "operator@sardis.dev", "reason": "Risk assessment failed"}'
```

### Deploy Smart Contract Updates

**When:** Contract upgrade needed (rare)

```bash
# 1. Test on testnet first
cd contracts
forge script script/DeployMainnet.s.sol --rpc-url $BASE_SEPOLIA_RPC_URL --broadcast

# 2. Verify contracts
forge verify-contract $CONTRACT_ADDRESS SardisWalletFactory \
  --chain-id 84532 --watch

# 3. After successful testnet deploy, deploy to mainnet
forge script script/DeployMainnet.s.sol --rpc-url $BASE_RPC_URL --broadcast

# 4. Verify mainnet contracts
forge verify-contract $CONTRACT_ADDRESS SardisWalletFactory \
  --chain-id 8453 --watch

# 5. Update contract addresses in Vercel
vercel env add SARDIS_BASE_WALLET_FACTORY_ADDRESS production
vercel env add SARDIS_BASE_ESCROW_ADDRESS production

# 6. Redeploy API
vercel --prod
```

### Emergency Circuit Breaker Activation

**When:** System under attack or experiencing critical failures

```bash
# 1. Enable circuit breaker via environment variable
vercel env add SARDIS_CIRCUIT_BREAKER_ENABLED true production

# 2. Redeploy immediately
vercel --prod

# 3. All new transactions will return 503 Service Unavailable
# Existing transactions in flight will complete

# 4. To restore service:
vercel env add SARDIS_CIRCUIT_BREAKER_ENABLED false production
vercel --prod
```

---

## Incident Response

### Transaction Stuck or Failed

**Symptoms:** User reports transaction not completing

```bash
# 1. Find transaction by ID
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/transactions/{tx_id}

# 2. Check blockchain status
# Visit block explorer: https://basescan.org/tx/{on_chain_tx_hash}

# 3. Check ledger for audit trail
psql $DATABASE_URL -c \
  "SELECT * FROM ledger WHERE transaction_id = '{tx_id}' ORDER BY created_at DESC;"

# 4. If transaction failed on-chain:
# - Review revert reason in block explorer
# - Check gas settings
# - Verify contract addresses

# 5. If transaction never submitted:
# - Check Turnkey MPC service status
# - Review application logs in Vercel

# 6. Resolutions:
# a) Retry transaction (if safe to do so)
# b) Issue refund to user wallet
# c) Escalate to engineering if smart contract issue
```

### KYC Verification Stuck

**Symptoms:** User completed KYC but status not updating

```bash
# 1. Check Persona inquiry status
curl -H "Authorization: Bearer persona_$ENV_$KEY" \
  https://withpersona.com/api/v1/inquiries/{inquiry_id}

# 2. Check webhook deliveries
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/webhooks/deliveries?event=persona.completed

# 3. If webhook failed:
# - Check Persona webhook endpoint health
# - Verify webhook secret matches
# - Retry webhook manually from Persona dashboard

# 4. If inquiry is still pending in Persona:
# - User may need to resubmit documents
# - Contact Persona support

# 5. Manual override (use sparingly):
psql $DATABASE_URL -c \
  "UPDATE agents SET kyc_status = 'approved' WHERE id = '{agent_id}';"
```

### Rate Limit Exceeded

**Symptoms:** 429 Too Many Requests errors

```bash
# 1. Identify the client
# Check application logs for IP address or API key

# 2. Review recent requests
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/metrics/rate-limit?api_key={key}

# 3. If legitimate traffic spike:
# - Temporarily increase rate limits
vercel env add SARDIS_RATE_LIMIT_PER_MINUTE 120 production
vercel --prod

# 4. If suspected abuse:
# - Block API key
psql $DATABASE_URL -c \
  "UPDATE api_keys SET status = 'revoked' WHERE key_hash = sha256('{key}');"

# 5. Monitor for continued issues
```

### Database Connection Pool Exhausted

**Symptoms:** `Too many connections` errors

```bash
# 1. Check active connections
psql $DATABASE_URL -c \
  "SELECT COUNT(*), state FROM pg_stat_activity GROUP BY state;"

# 2. Identify long-running queries
psql $DATABASE_URL -c \
  "SELECT pid, now() - pg_stat_activity.query_start AS duration, query
   FROM pg_stat_activity
   WHERE state = 'active'
   ORDER BY duration DESC;"

# 3. Kill problematic queries (use with caution)
psql $DATABASE_URL -c "SELECT pg_terminate_backend({pid});"

# 4. Increase connection pool size in Neon dashboard
# Visit: https://console.neon.tech -> Settings -> Connection Pooling

# 5. Restart API to reset connections
vercel --prod
```

---

## Database Operations

### Run Database Migration

```bash
# 1. Backup database first (Neon auto-backups, but verify)
# Visit: https://console.neon.tech -> Backups

# 2. Apply migration
psql $DATABASE_URL -f migrations/001_add_approvals.sql

# 3. Verify migration
psql $DATABASE_URL -c "\dt"  # List tables
psql $DATABASE_URL -c "SELECT * FROM schema_migrations ORDER BY version DESC LIMIT 5;"

# 4. If migration fails, rollback
psql $DATABASE_URL -f migrations/001_add_approvals_rollback.sql
```

### Database Performance Optimization

```bash
# 1. Analyze slow queries
psql $DATABASE_URL -c \
  "SELECT query, calls, total_time, mean_time
   FROM pg_stat_statements
   ORDER BY mean_time DESC
   LIMIT 10;"

# 2. Add missing indexes
psql $DATABASE_URL -c \
  "CREATE INDEX CONCURRENTLY idx_transactions_created_at
   ON transactions(created_at DESC);"

# 3. Update table statistics
psql $DATABASE_URL -c "VACUUM ANALYZE transactions;"

# 4. Review Neon performance insights
# Visit: https://console.neon.tech -> Monitoring
```

---

## External Service Issues

### Turnkey MPC Service Outage

**Detection:** Health check shows `turnkey: disconnected`

```bash
# 1. Check Turnkey status page
# Visit: https://status.turnkey.com

# 2. Verify API credentials
curl -H "X-Stamp-Organizationid: $TURNKEY_ORGANIZATION_ID" \
  https://api.turnkey.com/public/v1/query/whoami

# 3. If Turnkey is down:
# - Enable maintenance mode
vercel env add SARDIS_MAINTENANCE_MODE true production
vercel --prod

# 4. Notify users via status page
# Post to https://status.sardis.sh

# 5. When Turnkey recovers:
vercel env add SARDIS_MAINTENANCE_MODE false production
vercel --prod
```

### Persona KYC Service Issues

```bash
# 1. Check Persona status
# Visit: https://status.withpersona.com

# 2. If Persona is down:
# - Queue KYC requests for later processing
# - Notify users of delay

# 3. Alternative: Manual KYC review
# Review documents directly in Persona dashboard
```

### RPC Provider Rate Limits

```bash
# 1. Detected via transaction failures with rate limit errors

# 2. Switch to backup RPC provider
vercel env add SARDIS_BASE_RPC_URL $BACKUP_RPC_URL production
vercel --prod

# 3. If using Alchemy, check usage dashboard
# Visit: https://dashboard.alchemy.com

# 4. Upgrade RPC plan if needed
```

---

## Monitoring and Alerts

### Configure Sentry Alerts

```bash
# 1. Log in to Sentry
# Visit: https://sentry.io/sardis

# 2. Set up alert rules:
# - Error rate > 10 errors/min → Page on-call engineer
# - Critical errors (500s) → Immediate notification
# - Transaction failures > 5% → Email team

# 3. Configure integrations:
# - PagerDuty for critical alerts
# - Slack for warnings
```

### Review Metrics Dashboard

```bash
# Key metrics to monitor:

# 1. Transaction success rate
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/metrics/transactions?period=1h

# 2. API latency (p95, p99)
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/metrics/latency

# 3. Approval queue depth
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/approvals?status=pending | jq 'length'

# 4. Webhook delivery success rate
curl -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/webhooks/stats
```

### Set Up Custom Alerts

```bash
# 1. Create alert webhook in your monitoring system
# (e.g., PagerDuty, Opsgenie)

# 2. Subscribe to Sardis system events
curl -X POST -H "Authorization: Bearer $SARDIS_API_KEY" \
  https://api.sardis.sh/api/v2/webhooks/subscriptions \
  -d '{
    "url": "https://your-monitoring-system.com/webhook",
    "events": ["system.health_check_failed", "system.high_error_rate"]
  }'
```

---

## Emergency Contacts

- **Engineering Lead:** engineering@sardis.sh
- **Security Team:** security@sardis.sh
- **On-Call Rotation:** PagerDuty escalation policy
- **External Support:**
  - Turnkey Support: support@turnkey.com
  - Persona Support: support@withpersona.com
  - Neon Support: https://neon.tech/docs/introduction/support

---

## Additional Resources

- [Approval Flow Documentation](./APPROVAL_FLOW.md)
- [Secret Management Guide](./secret-management.md)
- [Production Deployment Guide](./PRODUCTION_DEPLOYMENT.md)
- [Mainnet Deployment Checklist](./mainnet-deployment-checklist.md)
- [Security Audit Checklist](./security-audit-checklist.md)
