# Sardis Grafana Dashboards

Importable Grafana dashboard templates for all Sardis Prometheus metrics (`sardis_*` prefix).

## Dashboards

| File | UID | What it covers |
|------|-----|----------------|
| `api-overview.json` | `sardis-api-overview` | Request rate, latency (p50/p95/p99), error rate %, uptime, top error/volume by endpoint |
| `payments.json` | `sardis-payments` | Payment volume, success/failure ratio, execution latency, breakdown by chain and token |
| `policy-engine.json` | `sardis-policy-engine` | Policy check rate, denial rate, denial reasons, spike alerts, approval queue depth |
| `cards.json` | `sardis-cards` | Card transaction volume, decline rate by provider, decline reasons, provider breakdown |
| `infrastructure.json` | `sardis-infrastructure` | DB query latency, active connections, cache hit rate, RPC call rates, MPC signing duration |

## Import Instructions

### Grafana Cloud

1. Open your Grafana Cloud instance.
2. Go to **Dashboards → Import** (or click the `+` icon → Import).
3. Click **Upload JSON file** and select one of the `.json` files from this directory.
4. In the **Prometheus** datasource dropdown, select your configured Prometheus datasource.
5. Click **Import**.

Repeat for each dashboard file.

### Self-Hosted Grafana

Same steps as above, or use the Grafana HTTP API:

```bash
GRAFANA_URL=http://localhost:3000
GRAFANA_TOKEN=<your-service-account-token>

for f in ops/grafana/*.json; do
  curl -s -X POST "$GRAFANA_URL/api/dashboards/import" \
    -H "Authorization: Bearer $GRAFANA_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"dashboard\": $(cat $f), \"overwrite\": true, \"folderId\": 0}"
  echo "Imported $f"
done
```

## Prometheus Data Source Configuration

All dashboards use the variable `${DS_PROMETHEUS}`. Grafana resolves this automatically on import when you select the datasource.

To configure Prometheus in Grafana:

1. Go to **Configuration → Data Sources → Add data source**.
2. Select **Prometheus**.
3. Set the URL (e.g. `http://prometheus:9090` or your remote-write endpoint).
4. Click **Save & Test**.

For Grafana Cloud managed Prometheus, the datasource is pre-configured — just select it during import.

### Prometheus scrape config

Add the Sardis API to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: sardis-api
    static_configs:
      - targets: ["sardis-api:8000"]
    metrics_path: /metrics
    scheme: http
```

## Alert Rule Examples

Paste these into Grafana **Alerting → Alert Rules** (or into your `prometheus/rules.yml`):

```yaml
groups:
  - name: sardis
    rules:

      - alert: HighErrorRate
        expr: |
          100 * sum(rate(sardis_errors_total[5m]))
            / sum(rate(sardis_http_requests_total[5m])) > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Sardis API error rate > 5%"

      - alert: PaymentSuccessRateLow
        expr: |
          100 * sum(sardis_payments_total{status="success"})
            / sum(sardis_payments_total) < 95
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Sardis payment success rate < 95%"

      - alert: PolicyDenialSpike
        expr: rate(sardis_policy_denial_spikes_total[5m]) > 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Policy denial spike detected"

      - alert: DBConnectionsHigh
        expr: sardis_db_connections_active > 85
        for: 3m
        labels:
          severity: warning
        annotations:
          summary: "DB connection pool > 85%"

      - alert: CacheHitRateLow
        expr: sardis_cache_hit_rate < 0.7
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Cache hit rate < 70%"
```
