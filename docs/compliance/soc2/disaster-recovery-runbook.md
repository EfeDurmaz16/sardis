# Disaster Recovery Runbook

**Document ID:** SARDIS-SOC2-DRR-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Engineering / Infrastructure
**Classification:** Internal — Restricted

---

## 1. Purpose

This runbook provides step-by-step procedures for recovering Sardis platform services following a disaster, infrastructure failure, or catastrophic data loss. It satisfies SOC 2 Trust Service Criteria A1.2 (recovery objectives) and A1.3 (recovery plan testing).

## 2. Recovery Objectives

| Metric | Target | Notes |
|--------|--------|-------|
| **RTO (Recovery Time Objective)** | 4 hours | Full service restoration from disaster declaration |
| **RPO (Recovery Point Objective)** | 1 hour | Maximum acceptable data loss |
| **MTTR (Mean Time to Repair)** | 2 hours | Target for component-level recovery |

These targets apply to the production environment. Staging recovery targets are relaxed to 24 hours for both RTO and RPO.

## 3. Service Dependencies and Priority

### Recovery Priority Order

Services are recovered in the following order, based on dependency relationships:

| Priority | Service | Dependency | Recovery Method |
|----------|---------|------------|-----------------|
| 1 | PostgreSQL (Neon) | None (foundational) | Neon point-in-time restore |
| 2 | Redis (Upstash) | None | Upstash automatic recovery / reprovision |
| 3 | Sardis API (Cloud Run) | Database, Redis | Cloud Run redeployment |
| 4 | Dashboard (Vercel) | API | Vercel redeployment |
| 5 | Landing page (Vercel) | None | Vercel redeployment |
| 6 | Blockchain RPC (Alchemy) | External | Failover to backup RPC |
| 7 | MPC Custody (Turnkey) | External | Turnkey recovery procedures |
| 8 | Virtual Cards (Stripe) | External | Stripe service restoration |

### External Service Dependencies

| Service | Purpose | SLA | Fallback |
|---------|---------|-----|----------|
| Neon | PostgreSQL database | 99.95% | Point-in-time restore, branch restore |
| Upstash | Redis cache | 99.99% | In-memory fallback (graceful degradation) |
| Turnkey | MPC wallet custody | 99.9% | Operations queued until restoration |
| Stripe | Virtual card issuing | 99.99% | Card operations queued |
| Alchemy | Blockchain RPC | 99.9% | Public RPC fallback endpoints |
| Vercel | Frontend hosting | 99.99% | Static fallback page |
| iDenfy | KYC verification | 99.9% | KYC operations queued |
| Elliptic | Sanctions screening | 99.9% | Fail-closed (block transactions) |

## 4. Disaster Scenarios and Recovery Procedures

### 4.1 Database Recovery (Neon PostgreSQL)

#### Scenario: Database Corruption or Data Loss

**Detection:** Health check reports `database` component as `unhealthy`. API returns 503 on readiness probe.

**RPO:** Neon provides continuous WAL streaming, enabling point-in-time recovery to within seconds of the failure.

**Procedure:**

1. **Assess the situation:**
   - Check Neon status page: `https://neon.tech/status`
   - Verify from health check:
     ```bash
     curl -s https://api.sardis.sh/health | jq '.components.database'
     ```
   - Determine the timestamp of the last known good state

2. **Activate emergency freeze** (prevent writes with corrupted state):
   ```
   POST /api/v2/admin/emergency/freeze-all
   {"reason": "database_recovery", "notes": "Point-in-time restore in progress"}
   ```

3. **Point-in-time restore via Neon console:**
   - Log in to Neon console (`https://console.neon.tech`)
   - Navigate to the production project
   - Go to "Branches" > "Restore"
   - Select the target timestamp (last known good state)
   - Choose "Restore to current branch" (overwrites current data) or "Restore to new branch" (preserves current data for investigation)
   - Confirm the restore operation

4. **If restoring to a new branch:**
   - Update `DATABASE_URL` to point to the new branch endpoint:
     ```bash
     gcloud run services update sardis-api-staging \
       --update-env-vars "DATABASE_URL=postgresql://<user>:<pass>@<new-branch-endpoint>.neon.tech/sardis"
     ```
   - Test connectivity and data integrity

5. **Verify database integrity:**
   - Check table counts for critical tables: `wallets`, `transactions`, `api_keys`, `audit_log`
   - Verify the latest ledger entries match expected state
   - Confirm `emergency_freeze_events` table is intact
   - Run a test query against the `payment_executions` table

6. **Restart API services:**
   - Force Cloud Run to pick up the new connection:
     ```bash
     gcloud run services update sardis-api --no-traffic
     gcloud run services update sardis-api --update-traffic latest=100
     ```
   - Wait for health check to report healthy

7. **Unfreeze wallets:**
   ```
   POST /api/v2/admin/emergency/unfreeze-all
   {"reason": "database_recovered", "notes": "PITR restore complete, integrity verified"}
   ```

8. **Post-recovery validation:**
   - Process a test payment end-to-end
   - Verify webhook delivery
   - Check audit log continuity

#### Scenario: Neon Regional Outage

If Neon is completely unavailable:

1. Activate emergency freeze
2. Monitor Neon status page for restoration ETA
3. If ETA exceeds RTO (4 hours), initiate failover to backup:
   - Restore from the most recent Neon backup to a new Neon project in a different region
   - Update `DATABASE_URL` across all services
4. Post-restoration: reconcile any transactions that occurred during the outage window

### 4.2 Turnkey MPC Key Recovery

#### Scenario: Turnkey API Unavailable

**Detection:** Health check reports `turnkey` component as `unhealthy`.

**Impact:** Wallet creation and transaction signing are blocked. Existing wallet balances are safe (on-chain, non-custodial).

**Procedure:**

1. **Assess scope:**
   ```bash
   curl -s https://api.sardis.sh/health | jq '.components.turnkey'
   ```
2. **Activate scoped containment:**
   - If Turnkey is fully down, payments cannot be signed. The kill switch should be activated:
     ```
     POST /api/v2/admin/kill-switch/activate
     {"scope": "global", "reason": "turnkey_outage"}
     ```
3. **Monitor Turnkey status:**
   - Check Turnkey status page
   - Contact Turnkey support for ETA
4. **Queue pending operations:**
   - Payment requests received during the outage are queued in the `pending_payments` table
   - They will be processed when Turnkey is restored
5. **Upon restoration:**
   - Verify Turnkey connectivity via health check
   - Process queued payments in order
   - Deactivate kill switch
6. **Post-recovery:** Reconcile all transactions and verify wallet balances

#### Scenario: Turnkey Organization Recovery

If the Turnkey organization needs to be recovered (e.g., credential loss):

1. Contact Turnkey support with organization ID (`TURNKEY_ORGANIZATION_ID`)
2. Follow Turnkey's organization recovery procedure (requires admin authenticator)
3. Generate new API credentials
4. Update environment variables per the Secrets Rotation Runbook
5. Verify all wallet operations

**Critical Note:** Sardis never holds private keys. MPC key shares are managed entirely by Turnkey. Wallet addresses and on-chain funds remain accessible as long as Turnkey's recovery process succeeds.

### 4.3 Cloud Run Service Recovery

#### Scenario: API Service Failure

**Detection:** Health check returns non-200, Cloud Run metrics show elevated error rates.

**Procedure:**

1. **Check Cloud Run status:**
   ```bash
   gcloud run services describe sardis-api --region=us-central1 --format='get(status.conditions)'
   ```

2. **If the latest revision is unhealthy — rollback to previous revision:**
   ```bash
   # List recent revisions
   gcloud run revisions list --service=sardis-api --region=us-central1 --limit=5

   # Route traffic to the previous known-good revision
   gcloud run services update-traffic sardis-api \
     --region=us-central1 \
     --to-revisions=sardis-api-<previous-revision>=100
   ```

3. **If the service needs full redeployment:**
   ```bash
   # Use the deploy script
   bash scripts/deploy-cloudrun.sh
   ```
   Or via GitHub Actions: trigger the Deploy workflow with the last known good version.

4. **Verify:**
   ```bash
   curl -f https://api.sardis.sh/health
   curl -f https://api.sardis.sh/ready
   ```

5. **If Cloud Run region is unavailable:**
   - Deploy to an alternate region:
     ```bash
     gcloud run deploy sardis-api \
       --region=us-east1 \
       --image=<container-image> \
       --update-env-vars "DATABASE_URL=..."
     ```
   - Update DNS to point to the new region (see Section 4.6)

### 4.4 Redis Recovery (Upstash)

#### Scenario: Redis Unavailable

**Detection:** Health check reports `cache` component as `unhealthy`.

**Impact:** Sardis is designed for graceful degradation when Redis is unavailable:
- Rate limiting falls back to in-memory counters (less precise but functional)
- Kill switch state may be stale (fail-closed behavior ensures safety)
- Session data lost (users need to re-authenticate)

**Procedure:**

1. **Check Upstash status:** `https://status.upstash.com`
2. **If temporary outage:** No action needed — services degrade gracefully
3. **If extended outage (>1 hour):**
   - Provision a new Upstash database:
     - Create new database in Upstash console
     - Select the same region for low latency
   - Update environment variables:
     ```bash
     gcloud run services update sardis-api \
       --update-env-vars "SARDIS_REDIS_URL=rediss://default:<pass>@<host>:6379,UPSTASH_REDIS_URL=rediss://default:<pass>@<host>:6379"
     ```
4. **Post-recovery:**
   - Rate limiter counters reset (acceptable — they rebuild automatically)
   - Kill switch state reloaded from database
   - Sessions invalidated (users re-authenticate)

### 4.5 Blockchain RPC Failover

#### Scenario: Primary RPC Provider (Alchemy) Unavailable

**Detection:** Health check reports `rpc` component as `unhealthy`. Chain executor fails to submit transactions.

**Procedure:**

1. **Activate chain-level kill switch** for affected chains:
   ```
   POST /api/v2/admin/kill-switch/activate
   {"scope": "chain:base", "reason": "rpc_outage"}
   ```

2. **Switch to backup RPC:**
   - Update the RPC URL environment variable:
     ```bash
     gcloud run services update sardis-api \
       --update-env-vars "SARDIS_BASE_RPC_URL=https://mainnet.base.org"
     ```
   - Note: Public RPCs have lower rate limits and should be used temporarily only

3. **Monitor with backup RPC:**
   ```bash
   curl -s https://api.sardis.sh/health | jq '.components.rpc'
   ```

4. **When Alchemy is restored:**
   - Switch back to Alchemy RPC:
     ```bash
     gcloud run services update sardis-api \
       --update-env-vars "SARDIS_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/<key>"
     ```
   - Deactivate chain-level kill switch
   - Process any queued transactions

### 4.6 DNS Failover

#### Scenario: DNS Resolution Failure

**Procedure:**

1. **Verify DNS resolution:**
   ```bash
   dig api.sardis.sh
   dig app.sardis.sh
   ```

2. **If Vercel DNS is down:**
   - Vercel manages DNS for `sardis.sh` — check Vercel status page
   - If prolonged, update DNS records to point directly to Cloud Run URL:
     ```
     api.sardis.sh → CNAME → sardis-api-<hash>.run.app
     ```
   - Update via domain registrar if Vercel DNS management is unavailable

3. **If domain registrar issue:**
   - Contact registrar support
   - Use backup domain if configured
   - Communicate alternate access URLs to customers

### 4.7 Full Platform Recovery (Worst Case)

For a complete platform recovery from scratch:

1. **Database (Priority 1):**
   - Neon point-in-time restore (or provision new project + restore from backup)
   - Verify all 50+ tables are intact
   - Run migration verification: `alembic current`

2. **Redis (Priority 2):**
   - Provision new Upstash database
   - No data migration needed (ephemeral data)

3. **API (Priority 3):**
   ```bash
   # Deploy API to Cloud Run
   bash scripts/deploy-cloudrun.sh
   ```
   Or trigger GitHub Actions Deploy workflow.

4. **Frontend (Priority 4):**
   - Dashboard: trigger Vercel deployment or `cd dashboard && pnpm build && vercel --prod`
   - Landing: trigger Vercel deployment or `cd landing && pnpm build && vercel --prod`

5. **Verify all components:**
   ```bash
   curl -s https://api.sardis.sh/health | jq '.'
   ```
   All components must report healthy before lifting any containment measures.

6. **Unfreeze and resume:**
   ```
   POST /api/v2/admin/emergency/unfreeze-all
   {"reason": "full_recovery_complete"}
   ```

## 5. Backup Strategy

### 5.1 Database Backups

| Attribute | Value |
|-----------|-------|
| **Provider** | Neon (automated) |
| **Frequency** | Continuous (WAL streaming) |
| **Retention** | 30 days |
| **Type** | Point-in-time recovery |
| **Encryption** | Encrypted at rest by Neon |
| **Testing** | Monthly restore test to staging |

### 5.2 Code and Configuration

| Attribute | Value |
|-----------|-------|
| **Provider** | GitHub |
| **Frequency** | Every commit |
| **Retention** | Permanent (git history) |
| **Includes** | All source code, CI/CD configs, migration files |
| **Excludes** | Secrets (managed via GitHub Actions secrets and Cloud Run env vars) |

### 5.3 Smart Contracts

| Attribute | Value |
|-----------|-------|
| **Source** | `contracts/` directory in git |
| **Deployed Addresses** | Recorded in deployment logs and `packages/sardis-chain/` config |
| **On-chain State** | Immutable, always available via blockchain |
| **ABI/Artifacts** | Stored in git after `forge build` |

### 5.4 Secrets

| Attribute | Value |
|-----------|-------|
| **Provider** | GitHub Actions secrets, Cloud Run environment variables |
| **Backup** | Encrypted secrets vault (offline) |
| **Recovery** | Regenerate from provider dashboards (Neon, Turnkey, Stripe, etc.) |

## 6. Testing Schedule

| Test Type | Frequency | Scope |
|-----------|-----------|-------|
| Database restore drill | Monthly | Restore staging from Neon PITR |
| API failover test | Quarterly | Cloud Run revision rollback |
| DNS failover test | Annually | Alternate DNS resolution |
| Full recovery simulation | Annually | End-to-end recovery from backups |
| Kill switch drill | Monthly | Activate/deactivate in staging |
| Freeze-all drill | Monthly | Execute freeze/unfreeze cycle in staging |

Each test is documented with:
- Date and participants
- Actual recovery time vs. target
- Issues encountered
- Corrective actions

## 7. Communication During Disaster Recovery

| Audience | Channel | Frequency |
|----------|---------|-----------|
| Engineering team | Internal chat + incident channel | Every 30 minutes |
| Customers | Status page + email | Every 1 hour (P0), every 2 hours (P1) |
| Management | Direct message + email | Every 1 hour |

Status page URL: `https://status.sardis.sh` (if configured) or direct customer email.

## 8. Post-Recovery Checklist

After any disaster recovery:

- [ ] All health check components reporting healthy
- [ ] Database integrity verified (row counts, latest records)
- [ ] Audit log continuity confirmed (no gaps)
- [ ] Ledger integrity verified (append-only property intact)
- [ ] Test payment processed successfully end-to-end
- [ ] Webhook delivery confirmed functional
- [ ] All kill switches and emergency freezes lifted
- [ ] Customer communication sent confirming resolution
- [ ] Incident report filed (see Incident Response Plan)
- [ ] Recovery time documented and compared against RTO/RPO targets
- [ ] Action items created for any procedural gaps identified

## 9. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-10 | Engineering | Initial version |

---

**Appendix A: Related Documents**

- Incident Response Plan (`docs/compliance/soc2/incident-response-plan.md`)
- Secrets Rotation Runbook (`docs/compliance/soc2/secrets-rotation-runbook.md`)
- Data Retention Policy (`docs/compliance/soc2/data-retention-policy.md`)

**Appendix B: Key Infrastructure Endpoints**

- Neon Console: `https://console.neon.tech`
- Upstash Console: `https://console.upstash.com`
- Turnkey Dashboard: `https://dashboard.turnkey.com`
- Stripe Dashboard: `https://dashboard.stripe.com`
- Google Cloud Console: `https://console.cloud.google.com`
- Vercel Dashboard: `https://vercel.com/dashboard`
- Alchemy Dashboard: `https://dashboard.alchemy.com`
- GitHub Repository: `https://github.com/<org>/sardis`
