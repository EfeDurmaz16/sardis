# Incident Response Playbook

## Overview

This playbook provides step-by-step procedures for responding to security incidents, service outages, and other operational emergencies in the Sardis platform.

**Version:** 1.0
**Last Updated:** 2024-02-03
**Owner:** Security & Operations Team

---

## Table of Contents

1. [Incident Classification](#incident-classification)
2. [Incident Response Team](#incident-response-team)
3. [Response Procedures](#response-procedures)
4. [Specific Incident Types](#specific-incident-types)
5. [Post-Incident Activities](#post-incident-activities)
6. [Communication Templates](#communication-templates)

---

## Incident Classification

### Severity Levels

| Severity | Definition | Response Time | Examples |
|----------|------------|---------------|----------|
| **P0 - Critical** | Complete service outage, data breach, or security compromise | 15 minutes | API down, database breach, unauthorized transactions |
| **P1 - High** | Significant feature degradation, potential security issue | 1 hour | Payment failures, authentication issues, sanctions bypass |
| **P2 - Medium** | Partial service degradation, minor security concern | 4 hours | Slow response times, non-critical feature down |
| **P3 - Low** | Minor issues, cosmetic bugs | Next business day | UI glitches, logging errors |

### Incident Categories

- **Security Incidents**: Unauthorized access, data breaches, malware
- **Service Outages**: API downtime, database failures, network issues
- **Compliance Incidents**: AML/KYC failures, regulatory violations
- **Financial Incidents**: Transaction errors, wallet discrepancies, fund locks
- **Data Incidents**: Data loss, corruption, or integrity issues

---

## Incident Response Team

### Roles and Responsibilities

#### Incident Commander (IC)
- **Primary:** On-call Engineering Lead
- **Backup:** CTO
- **Responsibilities:**
  - Declare incident severity
  - Coordinate response activities
  - Make critical decisions
  - Own communication to stakeholders

#### Technical Lead
- **Primary:** Senior Backend Engineer
- **Responsibilities:**
  - Diagnose technical issues
  - Implement fixes
  - Coordinate with infrastructure team

#### Communications Lead
- **Primary:** Product Manager
- **Responsibilities:**
  - Draft status updates
  - Communicate with customers
  - Update status page
  - Coordinate with legal/PR if needed

#### Compliance Officer
- **Primary:** Head of Compliance
- **Responsibilities:**
  - Assess regulatory impact
  - Coordinate with regulators if required
  - Document compliance-related issues

### On-Call Rotation

- **Primary On-Call:** Monitors alerts 24/7, first responder
- **Secondary On-Call:** Backup if primary doesn't respond within 15 minutes
- **Escalation:** CTO if incident not acknowledged within 30 minutes

---

## Response Procedures

### Phase 1: Detection and Triage (0-15 minutes)

1. **Alert Received**
   - Via: PagerDuty, Sentry, monitoring dashboard, customer report
   - On-call acknowledges alert within 5 minutes

2. **Initial Assessment**
   ```bash
   # Quick health checks
   curl https://api.sardis.sh/health
   curl https://api.sardis.sh/api/v2/status

   # Check Sentry for recent errors
   # Check CloudWatch/monitoring dashboards
   # Check customer reports in support channel
   ```

3. **Severity Classification**
   - Use severity matrix above
   - When in doubt, escalate to higher severity
   - Document initial classification in incident ticket

4. **Notify Response Team**
   - P0: Page IC, Technical Lead, Communications Lead immediately
   - P1: Page IC and Technical Lead
   - P2: Notify via Slack, no page
   - P3: Create ticket, handle during business hours

### Phase 2: Containment (15-60 minutes)

1. **Create Incident Channel**
   ```
   Slack: #incident-YYYYMMDD-HHmm
   Zoom: incident-war-room (standing link)
   Jira: INC-XXXX
   ```

2. **Immediate Containment Actions**

   **For Security Incidents:**
   - Isolate affected systems
   - Revoke compromised credentials
   - Enable additional logging
   - Block suspicious IPs/addresses

   **For Service Outages:**
   - Enable maintenance mode if needed
   - Scale up resources
   - Rollback recent deployments
   - Switch to backup services

   **For Financial Incidents:**
   - Freeze affected wallets
   - Halt automated transactions
   - Lock withdrawal functions
   - Preserve transaction logs

3. **Evidence Preservation**
   ```bash
   # Capture logs
   kubectl logs -n production deployment/sardis-api --since=1h > incident-logs.txt

   # Database snapshot
   pg_dump -h $DB_HOST -U $DB_USER sardis > incident-snapshot.sql

   # Metrics snapshot
   # Export Sentry events, CloudWatch metrics
   ```

### Phase 3: Investigation (Parallel with Containment)

1. **Root Cause Analysis**
   - Check recent deployments (last 24h)
   - Review database migrations
   - Examine infrastructure changes
   - Analyze application logs
   - Review security logs

2. **Investigation Commands**
   ```bash
   # Recent deployments
   kubectl rollout history deployment/sardis-api -n production

   # Database queries
   psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT * FROM audit_logs WHERE created_at > NOW() - INTERVAL '1 hour';"

   # Check transactions
   psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT * FROM ledger_entries WHERE created_at > NOW() - INTERVAL '1 hour' AND status = 'failed';"

   # Sentry errors
   # Navigate to Sentry dashboard, filter by time range
   ```

3. **Document Findings**
   - Update incident ticket with timeline
   - Record all hypotheses and tests
   - Note all actions taken

### Phase 4: Resolution

1. **Implement Fix**
   - Deploy hotfix if needed
   - Run database migrations
   - Restart services
   - Clear caches

2. **Verification**
   ```bash
   # Health check
   curl https://api.sardis.sh/health

   # Smoke test critical paths
   curl -X POST https://api.sardis.sh/api/v2/payments/create \
     -H "Authorization: Bearer $API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"test": "smoke_test"}'

   # Check error rates in Sentry
   # Verify metrics returned to normal
   ```

3. **Gradual Rollout**
   - Re-enable features incrementally
   - Monitor closely for 30 minutes
   - Unfreeze wallets gradually if applicable

### Phase 5: Recovery

1. **Service Restoration**
   - Disable maintenance mode
   - Resume normal operations
   - Clear status page incident

2. **Customer Communication**
   - Email affected customers
   - Post on status page
   - Update social media if needed

3. **Internal Notification**
   - All-hands Slack message
   - Update stakeholders
   - Schedule post-mortem

---

## Specific Incident Types

### 1. API Outage

**Symptoms:** 500 errors, timeouts, health check failures

**Immediate Actions:**
1. Check AWS/infrastructure status
2. Check database connectivity
3. Review recent deployments
4. Check resource utilization (CPU, memory, connections)

**Containment:**
```bash
# Scale up
kubectl scale deployment sardis-api --replicas=10 -n production

# Rollback if recent deployment
kubectl rollout undo deployment/sardis-api -n production

# Check database connections
psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT count(*) FROM pg_stat_activity;"
```

**Recovery:**
- Monitor error rates
- Verify all endpoints
- Check transaction processing

---

### 2. Data Breach / Unauthorized Access

**Symptoms:** Suspicious logins, unauthorized transactions, data exfiltration alerts

**CRITICAL - IMMEDIATE ACTIONS:**
1. **DO NOT** alert the attacker (no public communication yet)
2. Isolate affected systems
3. Preserve forensic evidence
4. Contact legal counsel immediately

**Containment:**
```bash
# Revoke all API keys
psql -h $DB_HOST -U $DB_USER -d sardis -c "UPDATE api_keys SET is_active = FALSE WHERE created_at < NOW();"

# Force password reset
psql -h $DB_HOST -U $DB_USER -d sardis -c "UPDATE users SET force_password_reset = TRUE;"

# Block suspicious IPs (example)
# Add to WAF rules or security groups
```

**Regulatory Obligations:**
- Notify FinCEN within 72 hours if customer data compromised
- Notify affected customers per GDPR/CCPA requirements
- File SAR if financial crime suspected
- Preserve all logs for investigation

**Investigation:**
- Engage forensics team
- Review access logs
- Check for lateral movement
- Identify scope of compromise

---

### 3. Payment Processing Failure

**Symptoms:** Transactions stuck in pending, failed payments, blockchain errors

**Immediate Actions:**
1. Check blockchain node connectivity
2. Verify gas prices
3. Check wallet balances
4. Review recent smart contract changes

**Diagnosis:**
```bash
# Check pending transactions
psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT * FROM ledger_entries WHERE status = 'pending' AND created_at < NOW() - INTERVAL '10 minutes';"

# Check blockchain node
curl -X POST $ETH_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check gas prices
curl -X POST $ETH_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_gasPrice","params":[],"id":1}'
```

**Resolution:**
- Retry failed transactions
- Update gas price settings
- Switch to backup RPC if needed

---

### 4. Compliance Alert (KYC/Sanctions)

**Symptoms:** Sanctions screening match, KYC verification failure, suspicious activity detected

**Immediate Actions:**
1. Freeze affected wallet
2. Halt all transactions for subject
3. Notify Compliance Officer
4. Preserve all transaction history

**Compliance Actions:**
```bash
# Freeze wallet
psql -h $DB_HOST -U $DB_USER -d sardis -c "UPDATE wallets SET is_frozen = TRUE, frozen_reason = 'Compliance hold - INC-XXX' WHERE wallet_id = '$WALLET_ID';"

# Export transaction history
psql -h $DB_HOST -U $DB_USER -d sardis -c "COPY (SELECT * FROM ledger_entries WHERE from_wallet = '$WALLET_ID' OR to_wallet = '$WALLET_ID') TO STDOUT CSV HEADER;" > compliance-export.csv
```

**Follow-up:**
- File SAR if required (within 30 days)
- Coordinate with legal
- Document all actions in compliance system
- Do NOT disclose SAR filing to customer

---

### 5. Database Issues

**Symptoms:** Slow queries, connection pool exhaustion, replication lag

**Immediate Actions:**
1. Check database metrics (connections, CPU, disk)
2. Identify long-running queries
3. Check replication status

**Diagnosis:**
```bash
# Active connections
psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;"

# Long-running queries
psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT pid, now() - query_start as duration, query FROM pg_stat_activity WHERE state != 'idle' ORDER BY duration DESC LIMIT 10;"

# Kill problematic query (if needed)
psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT pg_terminate_backend(PID);"

# Replication lag
psql -h $DB_HOST -U $DB_USER -d sardis -c "SELECT now() - pg_last_xact_replay_timestamp() AS replication_lag;"
```

**Resolution:**
- Scale database if needed
- Optimize slow queries
- Increase connection pool size
- Add read replicas

---

## Post-Incident Activities

### Incident Closure (Within 24 hours)

1. **Verify Resolution**
   - All systems operational
   - Metrics returned to baseline
   - No recurring errors

2. **Update Documentation**
   - Close incident ticket
   - Update status page
   - Send final customer communication

3. **Schedule Post-Mortem**
   - Within 48 hours for P0/P1
   - Within 1 week for P2

### Post-Mortem Process

**Attendees:** IC, Technical Lead, affected team members, stakeholders

**Agenda:**
1. Timeline review
2. Root cause analysis
3. What went well
4. What went wrong
5. Action items

**Post-Mortem Template:**
```markdown
# Incident Post-Mortem: [INC-XXX]

## Summary
- **Date:** YYYY-MM-DD
- **Duration:** X hours
- **Severity:** PX
- **Impact:** [users affected, transactions impacted, revenue impact]

## Timeline
- HH:MM - Alert triggered
- HH:MM - Incident declared
- HH:MM - Root cause identified
- HH:MM - Fix deployed
- HH:MM - Incident resolved

## Root Cause
[Detailed explanation]

## Resolution
[What fixed it]

## Impact
- Users affected: X
- Transactions failed: X
- Revenue impact: $X
- Compliance impact: [any regulatory implications]

## What Went Well
- Quick detection
- Fast response time
- Good communication

## What Went Wrong
- Lack of monitoring
- Manual process
- Insufficient testing

## Action Items
- [ ] Add monitoring for X (Owner: @person, Due: YYYY-MM-DD)
- [ ] Automate Y process (Owner: @person, Due: YYYY-MM-DD)
- [ ] Update runbook (Owner: @person, Due: YYYY-MM-DD)
```

### Follow-up Actions

1. **Implement Preventive Measures**
   - Add monitoring/alerts
   - Update runbooks
   - Improve testing
   - Conduct training

2. **Regulatory Reporting (if applicable)**
   - File SAR if suspicious activity
   - Notify regulators if required
   - Document in compliance system

3. **Customer Compensation (if applicable)**
   - Service credits
   - Fee waivers
   - Goodwill gestures

---

## Communication Templates

### Internal Status Update (Slack)

```
🚨 **INCIDENT UPDATE - INC-XXX** 🚨

**Severity:** P0 - Critical
**Status:** Investigating
**Impact:** Payment processing down for all users
**Started:** 2024-02-03 14:30 UTC

**Current Status:**
We are investigating an issue causing payment failures. The team is actively working on resolution.

**Next Update:** 15 minutes

**Incident Channel:** #incident-20240203-1430
**IC:** @john.doe
```

### Customer Communication (Status Page)

```
**Investigating** - We are investigating an issue with payment processing.
New payments may fail during this time. We will provide an update within 15 minutes.

Posted: Feb 3, 14:30 UTC
```

```
**Identified** - We have identified the root cause and are implementing a fix.
Expected resolution: Feb 3, 15:00 UTC

Updated: Feb 3, 14:45 UTC
```

```
**Resolved** - The issue has been resolved. All systems are operational.
Failed payments will be automatically retried.

We apologize for the inconvenience.

Resolved: Feb 3, 15:00 UTC
```

### Customer Email (Post-Incident)

```
Subject: Service Disruption - Payment Processing

Dear Sardis Customer,

We experienced a service disruption affecting payment processing on February 3, 2024,
from 14:30 to 15:00 UTC (30 minutes).

What happened:
[Brief, non-technical explanation]

Impact:
- X% of payments were affected
- All failed transactions have been automatically retried
- No funds were lost

What we're doing:
- Root cause has been identified and fixed
- Additional monitoring has been implemented
- Preventive measures are in place

We sincerely apologize for any inconvenience this may have caused.

If you have questions, please contact support@sardis.sh.

Best regards,
The Sardis Team
```

---

## Emergency Contacts

### Internal Team
- **CTO:** [phone] [email]
- **Head of Engineering:** [phone] [email]
- **Head of Compliance:** [phone] [email]
- **Legal Counsel:** [phone] [email]

### External Partners
- **AWS Support:** Priority case line
- **Turnkey (MPC):** [emergency contact]
- **Lithic (Cards):** [emergency contact]
- **Elliptic (Sanctions):** [support contact]

### Regulatory
- **FinCEN:** (800) 949-2732
- **State Regulator:** [contact info]

---

## Tools and Access

### Monitoring & Alerts
- **PagerDuty:** https://sardis.pagerduty.com
- **Sentry:** https://sentry.io/sardis
- **CloudWatch:** AWS Console
- **Status Page:** https://status.sardis.sh

### Infrastructure
- **AWS Console:** https://console.aws.amazon.com
- **Kubernetes Dashboard:** [internal URL]
- **Database:** [connection info in 1Password]

### Communication
- **Slack:** #incidents channel
- **Zoom:** incident-war-room (standing link)
- **Status Page Admin:** [admin URL]

---

## Appendix

### Incident Log Template

Track all actions during incident response:

| Time | Action | Owner | Result |
|------|--------|-------|--------|
| 14:30 | Alert triggered | System | - |
| 14:32 | On-call acknowledged | @john | - |
| 14:35 | Severity declared P0 | @john | Team paged |
| 14:40 | Root cause identified | @jane | Database lock |
| 14:45 | Fix deployed | @jane | - |
| 15:00 | Verified resolution | @john | All clear |

### Decision Log

Document all critical decisions:

| Time | Decision | Made By | Rationale |
|------|----------|---------|-----------|
| 14:35 | Declared P0 | IC | Complete service outage |
| 14:50 | Deployed hotfix | Tech Lead | Low risk, high impact |

---

**Document Control:**
- Version: 1.0
- Last Review: 2024-02-03
- Next Review: 2024-05-03 (quarterly)
- Owner: Security & Operations Team
