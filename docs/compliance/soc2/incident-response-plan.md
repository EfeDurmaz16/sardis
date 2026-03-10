# Incident Response Plan

**Document ID:** SARDIS-SOC2-IRP-001
**Version:** 1.0
**Effective Date:** 2026-03-10
**Last Reviewed:** 2026-03-10
**Owner:** Engineering / Security
**Classification:** Internal

---

## 1. Purpose

This document defines the incident response procedures for the Sardis platform. It covers detection, classification, containment, eradication, recovery, and post-incident review processes. It satisfies SOC 2 Trust Service Criteria CC7.3 (evaluation of security events), CC7.4 (response to security incidents), and CC7.5 (communication of incidents).

## 2. Scope

This plan covers security incidents, service outages, data breaches, and operational failures affecting:

- Sardis API and backend services
- PostgreSQL databases (Neon)
- MPC wallet operations (Turnkey)
- Virtual card operations (Stripe Issuing)
- Blockchain transaction execution
- Customer data and PII
- Third-party integrations (iDenfy, Elliptic, Alchemy)

## 3. Severity Levels

### P0 — Critical

**Definition:** Complete service outage, active data breach, unauthorized fund movement, or compromise of MPC signing infrastructure.

| Attribute | Value |
|-----------|-------|
| **Response Time** | 15 minutes |
| **Update Frequency** | Every 30 minutes until resolved |
| **Resolution Target** | 4 hours |
| **Escalation** | Immediate to CTO and all on-call engineers |
| **Customer Communication** | Within 1 hour of detection |
| **Regulatory Notification** | As required by jurisdiction (see Section 10) |

**Examples:**

- All payments failing across all chains
- Unauthorized wallet transactions detected
- Database breach with PII exposure
- Turnkey MPC infrastructure compromise
- Kill switch or emergency freeze failure
- Global API authentication bypass

### P1 — High

**Definition:** Partial service degradation affecting a significant number of customers, single-chain outage, or potential security vulnerability being actively exploited.

| Attribute | Value |
|-----------|-------|
| **Response Time** | 30 minutes |
| **Update Frequency** | Every 1 hour until resolved |
| **Resolution Target** | 8 hours |
| **Escalation** | On-call engineer + engineering lead |
| **Customer Communication** | Within 2 hours if customer-facing |

**Examples:**

- Single blockchain chain executor failure (e.g., Base down, Polygon operational)
- Elevated error rates (>5% of requests failing)
- Stripe Issuing API outage affecting card operations
- Webhook delivery failures at scale
- Rate limiting bypass discovered
- Single organization's wallets compromised

### P2 — Medium

**Definition:** Minor service degradation, non-critical component failure, or security vulnerability discovered but not actively exploited.

| Attribute | Value |
|-----------|-------|
| **Response Time** | 2 hours |
| **Update Frequency** | Every 4 hours during business hours |
| **Resolution Target** | 24 hours |
| **Escalation** | On-call engineer |
| **Customer Communication** | As needed |

**Examples:**

- Redis cache unavailable (graceful degradation to in-memory)
- Non-critical health check component reporting degraded
- Elevated latency on non-payment endpoints
- TAP JWKS endpoint intermittently unavailable
- Single merchant webhook delivery failure
- Dependency vulnerability with no known exploit

### P3 — Low

**Definition:** Cosmetic issues, informational security findings, or minor operational anomalies with no customer impact.

| Attribute | Value |
|-----------|-------|
| **Response Time** | Next business day |
| **Update Frequency** | N/A |
| **Resolution Target** | 1 week |
| **Escalation** | Assigned engineer |
| **Customer Communication** | Not required |

**Examples:**

- Dashboard UI rendering issues
- Documentation inaccuracies
- Log format inconsistencies
- Non-exploitable code quality findings
- Test environment failures

## 4. Recovery Objectives

| Metric | Target | Scope |
|--------|--------|-------|
| **RTO (Recovery Time Objective)** | 4 hours | Full service restoration |
| **RPO (Recovery Point Objective)** | 1 hour | Maximum acceptable data loss |
| **MTTR (Mean Time to Repair)** | 2 hours | Average across all incidents |

These objectives apply to production services. Staging environments have relaxed targets (RTO: 24 hours, RPO: 24 hours).

## 5. Incident Response Team

### Roles

| Role | Responsibility | Assigned To |
|------|---------------|-------------|
| **Incident Commander (IC)** | Owns the incident; coordinates all response activities; makes containment decisions | On-call senior engineer |
| **Technical Lead** | Diagnoses root cause; implements fix | On-call engineer or subject matter expert |
| **Communications Lead** | Manages internal and external communications | Engineering lead or CTO |
| **Scribe** | Documents timeline, actions, and decisions in real-time | Any available engineer |

### Escalation Matrix

```
Detection → On-Call Engineer (15 min)
                ↓ (if P0 or P1)
           Engineering Lead (30 min)
                ↓ (if P0)
           CTO (30 min)
                ↓ (if data breach or regulatory impact)
           Legal Counsel (1 hour)
                ↓ (if customer PII compromised)
           Affected Customers (per Section 9)
```

## 6. Incident Response Phases

### Phase 1: Detection

**Sources of Detection:**

| Source | Mechanism | File/System |
|--------|-----------|-------------|
| Health checks | Deep health probe (`GET /health`) checks database, Redis, Turnkey, Stripe, RPC, contracts, TAP JWKS | `packages/sardis-api/src/sardis_api/health.py` |
| Liveness/readiness probes | Kubernetes-style probes (`GET /health/live`, `GET /ready`) | `packages/sardis-api/src/sardis_api/health.py` |
| Kill switch monitoring | Global and per-scope kill switch status | `packages/sardis-api/src/sardis_api/kill_switch_dep.py` |
| Cloud Run metrics | Error rates, latency, request volume | Google Cloud Monitoring |
| Gitleaks | Secret exposure in commits | `.github/workflows/secret-scan.yml` |
| Customer reports | Support channels, dashboard alerts | Support system |
| Audit log anomalies | Unexpected admin actions, unusual patterns | `packages/sardis-api/src/sardis_api/audit_log.py` |
| Blockchain monitoring | Failed transactions, unexpected contract events | Alchemy webhooks, on-chain monitoring |

**Automated Alerting Thresholds:**

- API error rate > 5% over 5-minute window
- P99 latency > 5 seconds
- Health check returning non-200 for > 2 consecutive checks
- Database connection pool exhaustion
- Kill switch activation (any scope)
- Emergency freeze event

### Phase 2: Classification

Upon detection, the Incident Commander:

1. Assigns a severity level (P0-P3) per Section 3
2. Creates an incident record with:
   - Incident ID (format: `INC-YYYY-MM-DD-NNN`)
   - Detection timestamp
   - Initial severity
   - Affected components
   - Initial description
3. Notifies the appropriate personnel per the escalation matrix
4. Opens a dedicated incident communication channel

### Phase 3: Containment

**Immediate containment actions by severity:**

#### P0 Containment

1. **Activate emergency freeze** (if payment operations are compromised):
   ```
   POST /api/v2/admin/emergency/freeze-all
   {
     "reason": "incident_response",
     "notes": "INC-YYYY-MM-DD-NNN: <brief description>"
   }
   ```
   This endpoint (`packages/sardis-api/src/sardis_api/routers/emergency.py`):
   - Freezes ALL active wallets (`UPDATE wallets SET frozen = TRUE`)
   - Activates the global kill switch via `sardis_guardrails.kill_switch`
   - Records the event in `emergency_freeze_events` table
   - Logs via `log_admin_action` for audit trail
   - Requires admin principal + MFA
   - Rate-limited at 5 req/min (sensitive admin action)

2. **Activate kill switch** for specific scope (if targeted containment is appropriate):
   - Global: Blocks all payment operations
   - Organization: Blocks payments for a specific org
   - Agent: Blocks payments for a specific agent
   - Rail: Blocks a specific payment rail (a2a, ap2, checkout)
   - Chain: Blocks payments on a specific blockchain

   The kill switch system (`packages/sardis-api/src/sardis_api/kill_switch_dep.py`) returns HTTP 503 with scope information when active.

3. **Revoke compromised credentials** — see Secrets Rotation Runbook

4. **Isolate affected systems** — scale down, remove from load balancer, or block traffic

#### P1 Containment

1. Activate relevant scoped kill switch (chain, rail, or organization level)
2. Increase monitoring frequency
3. Prepare rollback if the issue is deployment-related

#### P2/P3 Containment

1. Standard triage and assignment
2. No emergency containment typically required

### Phase 4: Eradication

1. **Root cause analysis:** Identify the underlying cause
2. **Develop fix:** Create a targeted fix (hotfix for P0/P1)
3. **Test:** Validate fix in staging
4. **Deploy:** Follow the emergency hotfix process (see Change Management Policy, Section 9)

### Phase 5: Recovery

1. **Restore services:**
   - Deploy the fix to production
   - Verify via health check: `GET /health`
   - All components must report healthy
2. **Lift containment:**
   - Unfreeze wallets (if frozen):
     ```
     POST /api/v2/admin/emergency/unfreeze-all
     {
       "reason": "incident_resolved",
       "notes": "INC-YYYY-MM-DD-NNN resolved"
     }
     ```
   - Deactivate kill switches
3. **Verify:**
   - Monitor error rates for 30 minutes post-recovery
   - Confirm payment operations are functional (test transaction)
   - Verify webhook delivery is operational
   - Check that all health components report healthy
4. **Customer notification:** Confirm resolution to affected customers

### Phase 6: Post-Incident Review

Required for all P0 and P1 incidents; recommended for P2. Conducted within 72 hours of resolution.

**Post-Incident Review Template:**

```
# Post-Incident Review: INC-YYYY-MM-DD-NNN

## Summary
- Severity: P0/P1/P2
- Duration: X hours Y minutes
- Impact: <description of customer/business impact>
- Detection: <how the incident was detected>

## Timeline
- HH:MM UTC — <event>
- HH:MM UTC — <event>
- ...

## Root Cause
<technical description of the root cause>

## Contributing Factors
- <factor 1>
- <factor 2>

## What Went Well
- <positive observation>

## What Could Be Improved
- <improvement opportunity>

## Action Items
- [ ] <action> — Owner: <name> — Due: <date>
- [ ] <action> — Owner: <name> — Due: <date>

## Preventive Measures
- <measure to prevent recurrence>
```

## 7. Freeze-All Procedure (Detailed)

The freeze-all procedure is the most critical containment action available. It is a full-stop on all wallet operations.

### When to Use

- Confirmed unauthorized fund movement
- Suspected MPC key compromise
- Active exploitation of a payment vulnerability
- Database integrity compromise affecting financial data

### Execution

**Endpoint:** `POST /api/v2/admin/emergency/freeze-all`

**Requirements:**
- Admin principal (`Principal.is_admin == True`)
- MFA verification (if enabled, via `require_mfa_if_enabled` dependency)
- Rate limit: 5 requests/minute (sensitive admin action via `@admin_rate_limit(is_sensitive=True)`)

**What It Does:**
1. Sets `frozen = TRUE` on ALL wallets where `frozen = FALSE`
2. Records the event in `emergency_freeze_events` table with: event_id, action, triggered_by, wallets_affected, reason, notes, timestamp
3. Activates the global kill switch (`sardis_guardrails.kill_switch`)
4. Logs at CRITICAL level: `"EMERGENCY FREEZE-ALL: N wallets frozen by <user>"`
5. Records an admin audit entry via `log_admin_action`

**Verification:**
```
GET /api/v2/admin/emergency/status
```
Returns:
```json
{
  "is_frozen": true,
  "last_event": {
    "event_id": "...",
    "action": "freeze_all",
    "wallets_affected": 142,
    "triggered_by": "admin@sardis.sh",
    "timestamp": "2026-03-10T14:30:00Z",
    "reason": "incident_response"
  }
}
```

### Reversal

**Endpoint:** `POST /api/v2/admin/emergency/unfreeze-all`

Only execute after the incident is fully resolved and verified. The unfreeze:
1. Sets `frozen = FALSE` on ALL frozen wallets
2. Deactivates the global kill switch
3. Records the unfreeze event in `emergency_freeze_events`

## 8. Kill Switch Scoping

The kill switch system provides granular payment suspension beyond the full freeze:

| Scope | Effect | Use Case |
|-------|--------|----------|
| Global | All payment operations return 503 | Total platform compromise |
| Organization (`org:<id>`) | Payments for a specific org return 503 | Single customer compromise |
| Agent (`agent:<id>`) | Payments for a specific agent return 503 | Rogue agent behavior |
| Rail (`a2a`, `ap2`, `checkout`) | Payments on a specific rail return 503 | Rail-specific vulnerability |
| Chain (`base`, `ethereum`, etc.) | Payments on a specific chain return 503 | Chain-specific issue (e.g., RPC outage) |

The kill switch dependency (`require_kill_switch_clear` in `packages/sardis-api/src/sardis_api/kill_switch_dep.py`) checks all applicable scopes before allowing a payment to proceed.

## 9. Communication Templates

### 9.1 Internal Notification (P0/P1)

```
INCIDENT ALERT — [P0/P1] — INC-YYYY-MM-DD-NNN

Status: ACTIVE
Severity: P0/P1
Detected: YYYY-MM-DD HH:MM UTC
Incident Commander: <name>

Summary: <1-2 sentence description>

Impact: <description of customer/business impact>

Current Actions:
- <action being taken>

Next Update: HH:MM UTC
```

### 9.2 Customer Communication (P0)

```
Subject: Sardis Service Disruption — [Date]

We are currently experiencing a service disruption affecting [payment operations / card operations / specific functionality].

Status: We are actively investigating and working to resolve the issue.

Impact: [Description of what customers may experience]

What you need to do: [Any customer actions required, or "No action required at this time"]

We will provide updates every [30 minutes / 1 hour] until the issue is resolved.

If you have questions, contact support at support@sardis.sh.
```

### 9.3 Customer Resolution Notification

```
Subject: Sardis Service Disruption Resolved — [Date]

The service disruption reported on [date] has been resolved as of [time] UTC.

Root cause: [Brief, non-technical description]

Duration: [X hours Y minutes]

Impact: [Summary of what was affected]

Preventive measures: [What we are doing to prevent recurrence]

We apologize for the inconvenience. If you continue to experience issues, contact support@sardis.sh.
```

### 9.4 Regulatory Notification (Data Breach)

Used when PII is confirmed to be compromised. Notification timing is jurisdiction-dependent:

| Jurisdiction | Notification Deadline | Authority |
|-------------|----------------------|-----------|
| GDPR (EU) | 72 hours | Relevant supervisory authority |
| CCPA (California) | Without unreasonable delay | California AG (if >500 residents) |
| NY DFS | 72 hours | NY Department of Financial Services |

Template:

```
Subject: Data Breach Notification — Sardis, Inc.

Date of Discovery: [date]
Date of Incident: [date or date range]

Nature of Breach: [Description of what data was compromised]

Data Categories Affected: [e.g., names, email addresses, transaction history]

Number of Individuals Affected: [count or estimate]

Measures Taken: [Containment and remediation actions]

Contact: [Name, title, email, phone]
```

## 10. Regulatory Considerations

### Financial Data Incidents

For incidents involving financial transaction data:

- Preserve all audit logs and ledger entries (append-only ledger ensures no data loss)
- Do not modify or delete any transaction records
- Engage legal counsel for reporting obligations under BSA/AML
- Coordinate with Turnkey if MPC infrastructure is involved

### Blockchain-Specific Incidents

For incidents involving on-chain transactions:

- On-chain transactions are immutable and public — containment focuses on preventing additional unauthorized transactions
- Freeze-all is the primary containment mechanism
- Work with chain-specific teams (e.g., Circle for USDC freeze requests) if unauthorized transfers are confirmed
- Preserve all transaction hashes and block references for investigation

## 11. Training and Testing

- **Tabletop exercises:** Conducted quarterly, simulating P0 scenarios
- **Freeze-all drill:** Tested in staging monthly to ensure the procedure works as expected
- **On-call rotation:** All engineers participate; onboarding includes incident response training
- **This plan is reviewed:** After every P0/P1 incident and annually as part of SOC 2 audit

## 12. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-03-10 | Engineering | Initial version |

---

**Appendix A: Related Documents**

- Disaster Recovery Runbook (`docs/compliance/soc2/disaster-recovery-runbook.md`)
- Change Management Policy (`docs/compliance/soc2/change-management-policy.md`)
- Secrets Rotation Runbook (`docs/compliance/soc2/secrets-rotation-runbook.md`)
- Access Control Policy (`docs/compliance/soc2/access-control-policy.md`)

**Appendix B: Key System References**

- Emergency freeze endpoint: `packages/sardis-api/src/sardis_api/routers/emergency.py`
- Kill switch dependency: `packages/sardis-api/src/sardis_api/kill_switch_dep.py`
- Health checks: `packages/sardis-api/src/sardis_api/health.py`
- Audit logging: `packages/sardis-api/src/sardis_api/audit_log.py`
- Ledger engine: `packages/sardis-ledger/src/sardis_ledger/engine.py`
