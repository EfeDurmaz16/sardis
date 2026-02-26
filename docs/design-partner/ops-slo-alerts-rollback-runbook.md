# Ops SLO / Alerts / Rollback Runbook

## Service Targets (SLO)

### API (`api.sardis.sh`)
- Availability SLO: `>= 99.9%` monthly (HTTP 200 on `/api/v2/health`)
- Latency SLO: p95 `< 2.0s` on `/api/v2/health`
- Error budget burn trigger: if availability drops below 99.9% projection

### Frontends (`www.sardis.sh`, `app.sardis.sh`)
- Availability SLO: `>= 99.9%` monthly
- Core path availability: docs load, dashboard login route load

## Alerting

### Production routing/tuning knobs
- `SARDIS_ALERT_SEVERITY_CHANNELS_JSON`:
```json
{
  "info": ["websocket"],
  "warning": ["websocket", "slack"],
  "critical": ["websocket", "slack", "email", "pagerduty"]
}
```
- `SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON`:
```json
{
  "slack": 180,
  "email": 300,
  "pagerduty": 120
}
```
- `PAGERDUTY_ROUTING_KEY`: enables PagerDuty Events API v2 channel for human paging.
- Optional: `PAGERDUTY_SOURCE` (default: `sardis.api`).
- Pager route convention:
  - `critical` alerts must include at least one human-paged destination (`pagerduty`, `slack`, or `email`).
  - keep `websocket` on for dashboard visibility, but do not rely on it as sole critical route.

### Automated checks
- GitHub workflow: `.github/workflows/monitoring.yml`
  - Runs on schedule and manual dispatch
  - Checks `/api/v2/health` HTTP + payload status
  - Warns on latency threshold breach
  - Sends Slack notification on failure (`SLACK_WEBHOOK_URL`)

### Local on-demand monitor
- `scripts/health_monitor.sh`

```bash
HEALTH_URL=https://api.sardis.sh/health \
WEBHOOK_URL=https://hooks.slack.com/services/... \
bash scripts/health_monitor.sh
```

## Rollback Procedures

### 1) API rollback (Google Cloud Run)
1. List revisions:
```bash
gcloud run revisions list --service sardis-api-staging --region us-east1
```
2. Route traffic back to previous good revision:
```bash
gcloud run services update-traffic sardis-api-staging \
  --region us-east1 \
  --to-revisions <GOOD_REVISION>=100
```
3. Validate:
```bash
curl -fsS https://api.sardis.sh/api/v2/health
curl -fsS https://api.sardis.sh/health
```

### 2) API proxy rollback (Vercel `api.sardis.sh`)
1. Open Vercel project `api-proxy`, pick previous deployment.
2. Promote/rollback alias to known-good deployment.
3. Validate:
```bash
curl -fsS https://api.sardis.sh/api
curl -fsS https://api.sardis.sh/api/v2
```

### 3) Landing / Dashboard rollback (Vercel)
1. In Vercel project (`landing` or `dashboard`), promote previous stable deployment.
2. Validate:
```bash
curl -I https://www.sardis.sh
curl -I https://app.sardis.sh
```

## Incident Checklist
1. Acknowledge incident and assign owner.
2. Freeze risky deploys.
3. Roll back using the fastest safe path above.
4. Confirm health and core user flows.
5. Post incident summary with root cause + preventive action.
