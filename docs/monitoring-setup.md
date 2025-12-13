# Sardis Monitoring Setup

## Overview

Sardis uses Datadog for comprehensive monitoring, logging, and alerting.

## Prerequisites

1. **Datadog Account**: Sign up at https://www.datadoghq.com/
2. **API Keys**: Generate from Organization Settings > API Keys
3. **Agent Installation**: For server-side metrics

## Environment Variables

```bash
# Datadog Configuration
DD_API_KEY=your_datadog_api_key
DD_APP_KEY=your_datadog_app_key
DD_SITE=datadoghq.com  # or datadoghq.eu for EU

# Enable Datadog
DD_ENABLED=true
DD_SERVICE=sardis-api
DD_ENV=production
DD_VERSION=1.0.0

# Log Level
DD_LOG_LEVEL=INFO
```

## Python Integration

### Install Dependencies

```bash
pip install ddtrace datadog
```

### Application Setup

```python
# sardis_api/main.py

import os
from ddtrace import patch_all, tracer

# Auto-instrument all supported libraries
patch_all()

# Configure tracer
tracer.configure(
    hostname=os.getenv("DD_AGENT_HOST", "localhost"),
    port=int(os.getenv("DD_TRACE_AGENT_PORT", 8126)),
)
```

### Uvicorn Startup

```bash
DD_SERVICE=sardis-api \
DD_ENV=production \
ddtrace-run uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port 8000
```

## Key Metrics

### API Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `sardis.api.requests` | Total requests | N/A |
| `sardis.api.latency.p99` | 99th percentile latency | > 500ms |
| `sardis.api.errors` | Error count | > 10/min |
| `sardis.api.rate_limit_hits` | Rate limit triggers | > 100/min |

### Payment Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `sardis.payments.total` | Total payments | N/A |
| `sardis.payments.amount` | Payment volume (USD) | N/A |
| `sardis.payments.failed` | Failed payments | > 5% |
| `sardis.payments.latency` | Payment processing time | > 10s |

### Chain Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `sardis.chain.gas_price` | Current gas price (gwei) | > 100 |
| `sardis.chain.tx_pending` | Pending transactions | > 50 |
| `sardis.chain.tx_confirmed` | Confirmed transactions | N/A |
| `sardis.chain.tx_failed` | Failed transactions | > 1% |

### Compliance Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `sardis.compliance.checks` | Total compliance checks | N/A |
| `sardis.compliance.blocked` | Blocked transactions | Any |
| `sardis.compliance.kyc_pending` | Pending KYC verifications | > 100 |

## Dashboard Configuration

### Main Dashboard

```yaml
# datadog/dashboards/sardis-main.json
{
  "title": "Sardis - Main Dashboard",
  "description": "Overview of Sardis payment platform",
  "widgets": [
    {
      "definition": {
        "type": "timeseries",
        "title": "API Request Rate",
        "requests": [
          {
            "q": "sum:sardis.api.requests{*}.as_rate()"
          }
        ]
      }
    },
    {
      "definition": {
        "type": "query_value",
        "title": "P99 Latency",
        "requests": [
          {
            "q": "p99:sardis.api.latency{*}"
          }
        ],
        "precision": 0,
        "custom_unit": "ms"
      }
    },
    {
      "definition": {
        "type": "timeseries",
        "title": "Payment Volume",
        "requests": [
          {
            "q": "sum:sardis.payments.amount{*}.as_count()"
          }
        ]
      }
    }
  ]
}
```

## Alert Rules

### Critical Alerts (PagerDuty)

```yaml
# datadog/monitors/critical.yml

# API Down
- name: "Sardis API - Health Check Failed"
  type: service check
  query: "\"sardis.api.health\".over(\"*\").by(\"host\").last(3).count_by_status()"
  message: |
    API health check failed!
    @pagerduty-sardis-critical
  thresholds:
    critical: 3

# High Error Rate
- name: "Sardis API - High Error Rate"
  type: metric alert
  query: "sum(last_5m):sum:sardis.api.errors{*}.as_count() / sum:sardis.api.requests{*}.as_count() * 100 > 5"
  message: |
    Error rate above 5%!
    Current: {{value}}%
    @pagerduty-sardis-critical
  thresholds:
    critical: 5
    warning: 2

# Payment Failures
- name: "Sardis - Payment Failure Spike"
  type: metric alert
  query: "sum(last_5m):sum:sardis.payments.failed{*}.as_count() > 10"
  message: |
    High payment failure rate detected!
    @pagerduty-sardis-critical
  thresholds:
    critical: 10
    warning: 5
```

### Warning Alerts (Slack)

```yaml
# datadog/monitors/warnings.yml

# High Latency
- name: "Sardis API - High Latency"
  type: metric alert
  query: "avg(last_5m):p99:sardis.api.latency{*} > 500"
  message: |
    P99 latency above 500ms!
    @slack-sardis-alerts
  thresholds:
    critical: 1000
    warning: 500

# Rate Limiting
- name: "Sardis - High Rate Limiting"
  type: metric alert
  query: "sum(last_5m):sum:sardis.api.rate_limit_hits{*}.as_count() > 100"
  message: |
    High rate limit hits detected.
    @slack-sardis-alerts
  thresholds:
    warning: 100
```

## Log Management

### Structured Logging

```python
import structlog

logger = structlog.get_logger()

# Log payment
logger.info(
    "payment_executed",
    mandate_id=mandate.mandate_id,
    amount=mandate.amount_minor,
    token=mandate.token,
    chain=mandate.chain,
    tx_hash=receipt.tx_hash,
)
```

### Log Facets

Configure in Datadog:
- `@mandate_id` - Payment mandate ID
- `@tx_hash` - Blockchain transaction hash
- `@agent_id` - Agent identifier
- `@wallet_id` - Wallet identifier
- `@chain` - Blockchain network
- `@status` - Operation status

## APM Traces

### Custom Spans

```python
from ddtrace import tracer

@tracer.wrap("payment.execute")
async def execute_payment(mandate):
    with tracer.trace("compliance.check") as span:
        result = await compliance_engine.preflight(mandate)
        span.set_tag("compliance.provider", result.provider)
    
    with tracer.trace("chain.dispatch") as span:
        receipt = await chain_executor.dispatch_payment(mandate)
        span.set_tag("chain", mandate.chain)
        span.set_tag("tx_hash", receipt.tx_hash)
    
    return receipt
```

## SLOs

### Availability SLO

```yaml
name: "Sardis API Availability"
type: metric
query: |
  100 * (
    sum:sardis.api.requests{status:2*}.as_count() /
    sum:sardis.api.requests{*}.as_count()
  )
thresholds:
  - target: 99.9
    timeframe: 30d
  - target: 99.5
    timeframe: 7d
```

### Latency SLO

```yaml
name: "Sardis API Latency"
type: metric
query: |
  100 * (
    sum:sardis.api.requests{latency:<200}.as_count() /
    sum:sardis.api.requests{*}.as_count()
  )
thresholds:
  - target: 95
    timeframe: 30d
```

## Deployment

### Kubernetes

```yaml
# k8s/datadog-agent.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: datadog-agent-config
data:
  DD_API_KEY: "${DD_API_KEY}"
  DD_SITE: "datadoghq.com"
  DD_APM_ENABLED: "true"
  DD_LOGS_ENABLED: "true"
```

### Vercel

Add to `vercel.json`:

```json
{
  "env": {
    "DD_API_KEY": "@dd-api-key",
    "DD_SITE": "datadoghq.com"
  }
}
```

## Runbook Integration

See `RUNBOOK.md` for:
- Alert response procedures
- Escalation paths
- Common issues and resolutions





