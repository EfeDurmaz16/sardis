# Payment Hardening SLO Alerts

Date: 2026-02-25
Owner: Sardis Platform

## Scope

This alert set covers:
- Funding provider reliability and failover behavior
- Policy-denial bursts (goal drift/jailbreak pressure signal)
- Approval response latency

## Metrics Used

- `sardis_funding_provider_attempts_total`
- `sardis_funding_failover_events_total`
- `sardis_provider_errors_total`
- `sardis_policy_denial_spikes_total`
- `sardis_approval_response_time_seconds`

## Suggested Alert Rules (PromQL)

### 1) Funding provider error spike

```promql
sum by (provider) (rate(sardis_provider_errors_total{operation="funding"}[5m])) > 0.1
```

Severity: `warning`
Action: Check provider health dashboard; consider temporary routing override.

### 2) Funding all-provider failures

```promql
increase(sardis_funding_failover_events_total{result="all_failed"}[10m]) > 0
```

Severity: `critical`
Action: Freeze new funding attempts for affected orgs and trigger incident channel.

### 3) Excessive failover rate

```promql
(
  increase(sardis_funding_failover_events_total{result="success_after_failover"}[15m])
/
  clamp_min(sum(increase(sardis_funding_provider_attempts_total{status="success"}[15m])), 1)
) > 0.3
```

Severity: `warning`
Action: Provider degradation likely; validate primary route and fallback ordering.

### 4) Policy denial burst

```promql
increase(sardis_policy_denial_spikes_total[5m]) > 0
```

Severity: `critical`
Action: Review recent prompt traces and block suspicious merchant/session patterns.

### 5) Approval latency SLO breach (p95)

```promql
histogram_quantile(
  0.95,
  sum(rate(sardis_approval_response_time_seconds_bucket[30m])) by (le, action)
) > 3600
```

Severity: `warning`
Action: Page approval on-call and evaluate escalation automation.

## Runbook Hooks

- Funding criticals:
  - Temporarily switch primary funding route to fallback provider.
  - Enable stricter funding limits for impacted organizations.
- Policy-denial bursts:
  - Enable emergency approval mode for high-risk rails.
  - Review latest agent prompts and deny-list malicious domains.
- Approval latency:
  - Activate secondary approver pool.
  - Escalate all `high` urgency approvals to dedicated channel.

## Notes

- Thresholds above are starter values and should be calibrated with 7-day traffic baseline.
- Keep alert ownership in `docs/alerts/README.md` on-call rotation section.
