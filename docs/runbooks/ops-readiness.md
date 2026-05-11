# Ops Readiness Runbook

This public runbook defines the minimum operational evidence required for a non-strict Sardis release gate. Private partner-specific drill notes and customer timelines live outside the public repository.

## SLOs

| Surface | SLO | Alert threshold |
| --- | --- | --- |
| API health | 99.9% monthly availability for `/api/v2/health` | Two consecutive failed GitHub Actions health checks |
| Payment execution | 99% of accepted payment executions reach terminal state within 5 minutes | `transaction_stuck` or queue-depth alert |
| Approval queue | P95 approval queue age below 10 minutes | `approval_queue_backlog` alert |
| Reconciliation | 99.9% of ledger projections reconcile within 15 minutes | projection drift or duplicate suppression failure |

## Alert Routing

The public repo keeps alert routing configurable through environment variables:

- `SARDIS_ALERT_SEVERITY_CHANNELS_JSON` maps severities to channels.
- `SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON` sets per-channel cooldowns.
- `PAGERDUTY_ROUTING_KEY` enables PagerDuty escalation for critical incidents.
- `SLACK_WEBHOOK_URL` is used by the scheduled GitHub Actions health monitor.

Default critical routing should include Slack, email, and PagerDuty. In strict release mode, missing PagerDuty routing fails the gate.

## Rollback

API rollback uses Cloud Run revision traffic shifting or redeployment from the last known-good image. Frontend rollback uses Vercel deployment promotion. Detailed commands live in `docs/production-runbook.md` and `docs/runbooks/rollback.md`.

## Reconciliation Chaos

Reconciliation checks must cover:

- out-of-order event delivery
- duplicate event suppression
- projection drift between ledger and payment state
- provider outage during settlement or webhook delivery

The expected recovery path is replay, compare, and append corrective evidence without mutating prior audit records.
