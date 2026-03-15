# Incident Response Runbook

**Version:** 1.0
**Last updated:** March 2026
**Owner:** Efe Baran Durmaz (Founder)

## Severity Definitions

| Severity | Description | Examples | Response Time |
|----------|-------------|----------|---------------|
| P0 — Critical | Complete service outage, data breach, financial loss | API down, key compromise, unauthorized transactions | < 30 minutes |
| P1 — High | Major feature unavailable, payments blocked | Chain executor down, Turnkey unreachable, kill switch triggered | < 2 hours |
| P2 — Medium | Degraded performance, non-critical feature down | High latency, dashboard errors, webhook delays | < 8 hours |
| P3 — Low | Minor issue, workaround available | UI bugs, documentation errors, non-blocking warnings | < 24 hours |

## Detection

### Automated Detection
- **Health checks:** `/health` endpoint checks 10+ components every 30 seconds
- **Cloud Run alerts:** Error rate > 5%, latency P95 > 2s, memory > 80%
- **Gitleaks:** Blocks commits containing secrets
- **Kill switch:** Automatically triggered by anomaly detection, compliance violations, fraud signals

### Manual Detection
- Customer reports via support@sardis.sh
- Internal monitoring of dashboard and transaction flows
- Regular review of structured logs (JSON format, correlation IDs)

## Response Procedures

### P0 — Critical Incident

1. **Acknowledge** (< 30 min)
   - Confirm the incident via health check and logs
   - Activate kill switch if financial risk: `POST /admin/kill-switch/rail/{rail}`
   - Post initial status update

2. **Contain** (< 1 hour)
   - Identify blast radius (which users/orgs affected)
   - If credential compromise: rotate JWT_SECRET_KEY, invalidate all sessions
   - If data breach: preserve evidence, begin forensic timeline
   - If chain issue: halt affected chain via kill switch

3. **Remediate** (ongoing)
   - Deploy fix or rollback: `gcloud run services update-traffic --to-revisions=PREVIOUS`
   - Verify fix via health check and smoke tests
   - Re-enable services gradually (remove kill switch)

4. **Communicate**
   - Notify affected users via email
   - Update status page
   - Post-incident report within 48 hours

### P1 — High Priority

1. **Acknowledge** (< 2 hours)
   - Verify via health check and logs
   - Assess user impact

2. **Investigate**
   - Check component health: database, Redis, Turnkey, RPC, Stripe
   - Review recent deployments (git log, Cloud Run revisions)
   - Check for upstream outages (Turnkey status, Alchemy status, Neon status)

3. **Remediate**
   - Apply fix or workaround
   - If deployment-related: rollback to previous revision
   - If third-party: activate fallback/degraded mode if available

### P2/P3 — Medium/Low Priority

1. Track in issue tracker
2. Investigate during business hours
3. Deploy fix in next release cycle
4. No emergency procedures needed

## Communication Templates

### Status Page Update (P0/P1)
```
[Investigating] We are aware of an issue affecting [service/feature].
Our team is actively investigating. We will provide an update within [time].

[Identified] The issue has been identified as [brief description].
We are working on a fix. Estimated resolution: [time].

[Resolved] The issue affecting [service/feature] has been resolved.
All services are operating normally. A post-incident report will follow.
```

### Customer Email (Data Breach)
```
Subject: Security Notice — Sardis Account

Dear [Customer],

We are writing to inform you of a security incident that may have affected
your Sardis account. [Description of what happened, what data was affected,
and what we are doing about it.]

Actions we have taken: [List]
Actions you should take: [List]

We take the security of your data seriously and apologize for any concern
this may cause. Please contact security@sardis.sh with any questions.

Regards,
Sardis Security Team
```

## Post-Incident Review

After every P0/P1 incident, conduct a blameless post-mortem within 72 hours:

1. **Timeline:** What happened, when, in what order
2. **Impact:** Users affected, duration, financial impact
3. **Root cause:** Why it happened (5 Whys analysis)
4. **Detection:** How was it detected? Could it have been detected sooner?
5. **Response:** Was the response effective? What could be improved?
6. **Action items:** Specific, assigned, time-bound improvements
7. **Lessons learned:** What should change in procedures, monitoring, or code

## Key Contacts

| Role | Contact | Escalation |
|------|---------|------------|
| Founder / Primary Oncall | Efe Baran Durmaz | security@sardis.sh |
| Cloud Infrastructure | GCP Cloud Run | console.cloud.google.com |
| Database | Neon PostgreSQL | console.neon.tech |
| MPC Custody | Turnkey | turnkey.com/support |
| Payments | Stripe | dashboard.stripe.com |

## Recovery Procedures

### JWT Secret Rotation
```bash
# Generate new secret
NEW_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# Update Cloud Run (preserves other env vars)
gcloud run services update sardis-api-staging \
  --update-env-vars JWT_SECRET_KEY=$NEW_SECRET

# Note: This invalidates ALL existing JWT tokens.
# Users will need to re-login.
```

### Database Point-in-Time Recovery
```
1. Log into Neon console (console.neon.tech)
2. Select the sardis-production branch
3. Use "Restore" to create a branch from a specific timestamp
4. Verify data in the restored branch
5. Promote the restored branch if correct
```

### Kill Switch Operations
```bash
# Activate global kill switch
curl -X POST https://api.sardis.sh/admin/kill-switch/global \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"reason": "P0 incident", "scope": "global"}'

# Deactivate after resolution
curl -X DELETE https://api.sardis.sh/admin/kill-switch/global \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```
