# Runbook: Incident Response
> Owner: Engineering | Last updated: 2026-03-03

---

## 1. Incident Lifecycle

```
Detect → Acknowledge → Triage → Mitigate → Resolve → Post-mortem
```

### Timers
| Phase | P0 Target | P1 Target |
|---|---|---|
| Acknowledge | 15 min | 30 min |
| Triage (severity confirmed) | 30 min | 1 hour |
| Mitigation (service partially restored) | 2 hours | 4 hours |
| Full resolution | 4 hours | 24 hours |
| Post-mortem published | 48 hours | 5 days |

---

## 2. Step-by-Step Response

### Step 1: Acknowledge
1. Respond in `#alerts-p0` or `#alerts-p1` within SLA
2. Announce: `"[NAME] is on this. Investigating."`
3. Start incident timer (note UTC time)

### Step 2: Triage
Determine:
- **What is broken?** (specific endpoint, service, data)
- **Who is affected?** (all users, specific org, specific wallet)
- **Is data at risk?** (funds, PII, credentials)
- **What changed recently?** (`git log --since="2 hours ago"`)

Quick diagnostics:
```bash
# Check API health
curl https://api.sardis.sh/health

# Check Vercel deploy status
vercel inspect --scope sardis

# Check Neon DB
psql $DATABASE_URL -c "SELECT 1"

# Check recent errors in logs
# (Vercel Dashboard → Functions → Logs → Filter by ERROR)
```

### Step 3: Escalate if needed
If not mitigated within 30 minutes → escalate per `docs/on-call.md`.

### Step 4: Mitigate
Choose the fastest path to service restoration:
- **Rollback** → see `docs/runbooks/rollback.md`
- **Feature disable** → set env var to disable broken feature
- **Database fix** → see database section below
- **External provider fallback** → see provider fallback section

### Step 5: Communicate
- Post status update in `#alerts-p0` every 30 minutes
- If user-facing: update status page (status.sardis.sh)
- If partner-facing: email partner contact within 1 hour of P0

### Step 6: Resolve
1. Confirm service fully restored
2. Announce: `"[NAME] Resolved at [TIME UTC]. Root cause: [BRIEF]. Full post-mortem by [DATE]."`
3. Start post-mortem within 48 hours

---

## 3. Database Incidents

### Connection lost / DB unavailable
```bash
# Check Neon status: console.neon.tech
# Try connecting manually:
psql $DATABASE_URL -c "SELECT now()"

# If DB is truly down: Neon has automatic failover (< 30s typically)
# If > 5 minutes down: Contact Neon support + escalate to P0
```

### Corrupted data / accidental deletion
```bash
# Neon supports point-in-time recovery
# Go to: console.neon.tech → your project → Restore
# Or via API:
# curl -X POST https://console.neon.tech/api/v2/projects/{id}/restore ...

# DO NOT run manual UPDATE/DELETE in production without second pair of eyes
```

---

## 4. Payment System Incidents

### Payments failing (on-chain tx reverting)
```bash
# Check Base mainnet status: status.base.org
# Check Alchemy RPC status: status.alchemy.com

# Test policy check manually:
curl -X POST https://api.sardis.sh/api/v2/policies/check \
  -H "X-API-Key: $SARDIS_API_KEY" \
  -d '{"amount": 1.0, "token": "USDC", "destination": "test.com"}'

# If policy engine is broken:
# → Set SARDIS_POLICY_BYPASS_MODE=monitoring (denies no payments but logs all)
# → Use ONLY as last resort; creates compliance risk
```

### Wallet frozen accidentally
```bash
# Unfreeze via API:
curl -X POST https://api.sardis.sh/api/v2/wallets/{wallet_id}/unfreeze \
  -H "X-API-Key: $SARDIS_API_KEY"
```

---

## 5. Security Incidents
See `docs/runbooks/key-compromise.md` for credential/key incidents.

For unauthorized access:
1. **Immediately** freeze affected wallets
2. Rotate all API keys (Vercel env → SARDIS_API_KEY)
3. Revoke affected user sessions in DB:
   ```sql
   UPDATE api_keys SET revoked_at = now(), revoked_reason = 'security_incident'
   WHERE org_id = '<affected_org>';
   ```
4. Escalate to founder + legal immediately
5. Assess if breach notification required (GDPR 72h window)

---

## 6. Post-Mortem Template

File in `docs/post-mortems/YYYY-MM-DD-<title>.md`:

```markdown
## Incident Summary
- **Date/Time:** (UTC)
- **Duration:**
- **Severity:**
- **Impact:** (# users affected, $ volume impacted)

## Timeline
- HH:MM - Alert fired
- HH:MM - Acknowledged by [NAME]
- HH:MM - Root cause identified
- HH:MM - Mitigation applied
- HH:MM - Fully resolved

## Root Cause
(What actually went wrong)

## Contributing Factors
(What made this possible / worse)

## What We Did Well

## What We Could Improve

## Action Items
| Action | Owner | Due |
|---|---|---|
| ... | ... | ... |
```
