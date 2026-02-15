# 24/7 Alerting And Incident Response Drill

Owner: Sardis incident commander rotation  
Scope: Treasury and stablecoin payment incidents

## Severity Model
1. `SEV-1`: live payment execution degraded or data-integrity risk
2. `SEV-2`: partial degradation with available fallback
3. `SEV-3`: isolated failures with manual workaround

## Trigger Conditions
1. Health endpoint failures (`/api/v2/health`) over threshold.
2. Spike in webhook replay/signature errors.
3. Reconciliation drift break growth above normal baseline.
4. Manual review queue growth above alert threshold.

## Drill Procedure (Monthly)
1. Start drill ticket and assign:
   - incident commander
   - API responder
   - infra responder
   - comms owner
2. Inject one synthetic failure:
   - webhook signature mismatch burst, or
   - delayed ACH return handling, or
   - canonical state ingestion lag
3. Verify paging path:
   - monitoring workflow alert
   - Slack/incident channel ack in under 5 minutes
4. Execute containment:
   - freeze risky rail if needed
   - route to manual review queue
   - apply rollback if SLA breach persists
5. Close drill with postmortem:
   - root cause
   - containment time
   - recovery time
   - action items

## Service Objectives For Drill
1. Ack time: under 5 minutes
2. Mitigation start: under 10 minutes
3. Recovery: under 30 minutes
4. Postmortem published: under 24 hours

