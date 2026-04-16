# Alerting Infrastructure Status

Date: 2026-04-11
Scope: Read-only audit of Sardis alerting stack. No changes deployed.

## TL;DR

The repo ships a 19-rule alert file (`monitoring/alerts.yml`) that is **not wired
to any running alert engine**. The only live alert path in production today is a
single GitHub Actions cron that pings `/api/v2/health` every 10 minutes and posts
to Slack on failure. Sentry captures exceptions but has no repo-managed alert
rules. Grafana dashboards exist as JSON templates but import is manual.

This is a launch blocker for anything beyond "is the API reachable" — stuck
transactions, policy-denial spikes, Turnkey outage, approval backlog, and
compliance-service failures all go undetected until a human notices.

## Deployed components

| Component | State | Notes |
|---|---|---|
| Prometheus metrics endpoint | LIVE | `packages/sardis-api/src/sardis_api/routers/metrics.py` exposes `sardis_*` metrics via `prometheus_client`. |
| Sentry SDK | LIVE | Initialised in `packages/sardis-api/src/sardis_api/main.py:245` and `packages/sardis-api/src/sardis_api/monitoring.py`. `SENTRY_DSN` is passed to Cloud Run in `scripts/deploy-cloudrun.sh:74`. Exception capture works; no alert rules defined in repo. |
| Health endpoint | LIVE | `packages/sardis-api/src/sardis_api/health.py` — `/health`, `/health/live`, `/api/v2/health`. |
| GitHub Actions health monitor | LIVE | `.github/workflows/monitoring.yml`, `*/10 * * * *`, curls `/api/v2/health`, posts to `SLACK_WEBHOOK_URL` on failure. Only real-time alert path currently running. |
| Grafana dashboard JSON | PRESENT, NOT IMPORTED | `ops/grafana/{api-overview,payments,policy-engine,cards,infrastructure}.json`. README describes manual import to a Grafana Cloud instance. No evidence the instance exists or is provisioned. |

## Missing components

| Component | Gap |
|---|---|
| Prometheus server / scrape config | Nothing scrapes `/metrics`. No `prometheus.yml`, no scrape job, no Cloud Run sidecar, no Grafana Cloud agent config in the repo. |
| Alertmanager (or equivalent) | `monitoring/alerts.yml` uses a custom schema (`source:`, `condition:` as free-text, `channels:` list) — it is **not** valid Prometheus `alerting_rules.yml`, Grafana unified-alerting JSON, or Alertmanager config. It is not consumed by any code in the repo (grep `alerts.yml` returns zero non-self references). It is effectively a design doc. |
| Sentry alert rules | Sentry captures errors but the 19 rules in `monitoring/alerts.yml` (stuck tx, turnkey down, policy denial spike, approval backlog, 5xx rate, etc.) have no Sentry equivalent configured from the repo. |
| PagerDuty routing | `alerts.yml` references `${PAGERDUTY_KEY}` for critical alerts — no routing in place. |
| Slack `slack-ops` webhook | Only the GitHub Actions health check uses a Slack webhook (`SLACK_WEBHOOK_URL`). The named channel `slack-ops` referenced in `alerts.yml` is not wired. |

## Risk assessment for launch

Alerts for the following conditions — all declared in `alerts.yml` — will NOT
fire in production today:

- `transaction_stuck` (tx pending > 5min) — silent
- `turnkey_unhealthy` (signing service down) — silent
- `api_error_rate` (5xx > 1%) — silent unless health endpoint itself 5xxs
- `compliance_service_down` (Persona / Elliptic) — silent
- `daily_spend_limit_exceeded` — silent
- `policy_denial_spike_detected` — silent
- `approval_queue_backlog` — silent

The only failure mode that currently pages anyone is: `/api/v2/health` returns
non-200 for the duration of a 10-minute cron tick.

## Recommendation (cheapest path to real alerts)

Short form — two tracks, pick at least one before launch:

1. **Sentry Alerts (fastest, no new infra).** Define 5-7 alert rules inside
   Sentry directly against the exception stream + custom events. Wire existing
   `SENTRY_DSN`. Covers: unhandled 5xx spikes, webhook signature failures,
   Turnkey / asyncpg integration errors. Cost: $0 (existing plan). Time: ~2h of
   clicking in the Sentry UI plus one doc page listing the rules. Does NOT cover
   business-logic alerts like stuck-tx or approval backlog — those need option 2.

2. **Grafana Cloud free tier + Prometheus remote-write.** Provision a Grafana
   Cloud stack, add a `prometheus_remote_write` config to the API process (the
   metrics are already exposed), import the 5 dashboards from `ops/grafana/`,
   and rewrite `monitoring/alerts.yml` into Grafana unified-alerting rules
   (valid YAML this time). Free tier is sufficient for current volume. Time:
   ~1 day. Covers business-logic alerts (`sardis_payment_*`, `sardis_policy_*`,
   `sardis_approval_queue_depth` etc.).

For a launch window, option 1 alone is the minimum acceptable state. Option 2
should follow within the first two weeks post-launch.

A third follow-up: rewrite `monitoring/alerts.yml` into whichever format the
chosen backend consumes, or delete it — the current file looks authoritative but
is inert, which is worse than having nothing.
