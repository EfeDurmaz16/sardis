# Sardis Load Testing

This directory contains load testing scripts for the Sardis Payment OS API.

## Tools

### Locust (Python)

Best for: Python developers, quick setup, real-time web UI.

```bash
# Install
pip install locust

# Run with web UI
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Headless mode (100 users, 10 users/sec spawn rate, 5 minutes)
locust -f tests/load/locustfile.py --host=http://localhost:8000 \
    --headless -u 100 -r 10 -t 5m

# With custom API key
SARDIS_API_KEY=your_key locust -f tests/load/locustfile.py --host=http://localhost:8000
```

### k6 (Go)

Best for: High performance, CI/CD integration, detailed metrics.

```bash
# Install k6
# macOS: brew install k6
# Ubuntu: sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
#         echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
#         sudo apt-get update && sudo apt-get install k6

# Basic run
k6 run tests/load/k6_load_test.js --env API_URL=http://localhost:8000

# Custom settings
k6 run tests/load/k6_load_test.js \
    --vus 100 \
    --duration 5m \
    --env API_URL=http://localhost:8000 \
    --env API_KEY=your_key

# Output to JSON
k6 run tests/load/k6_load_test.js --out json=results.json
```

## Test Scenarios

### Standard Load Test

Simulates normal API usage with balanced operations:
- 40% Balance checks
- 20% Policy checks
- 15% Payment executions
- 10% Hold operations
- 10% Transaction listing
- 5% Wallet info queries

### High Volume Payments

Focuses on payment throughput:
- Rapid payment execution
- Minimal delays between requests
- Tests payment processing capacity

### Hold Lifecycle

Tests the complete hold flow:
- Create hold
- Capture or void
- Verify state transitions

## Performance Targets

| Metric | Target | Critical |
|--------|--------|----------|
| Response Time (p95) | < 500ms | < 1000ms |
| Response Time (p99) | < 1000ms | < 2000ms |
| Error Rate | < 1% | < 5% |
| Throughput | > 1000 req/s | > 500 req/s |
| Payment Processing | < 300ms | < 500ms |
| Policy Check | < 100ms | < 200ms |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SARDIS_API_URL` | API base URL | `http://localhost:8000` |
| `SARDIS_API_KEY` | API authentication key | `sk_test_load_test` |
| `SARDIS_TEST_WALLET_ID` | Wallet ID for tests | `wallet_load_test` |

## Pre-Test Setup

Before running load tests:

1. **Start the API server**
   ```bash
   cd packages/sardis-api
   python -m uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Create a test wallet**
   ```bash
   curl -X POST http://localhost:8000/api/v2/wallets \
     -H "Authorization: Bearer sk_test" \
     -H "Content-Type: application/json" \
     -d '{"agent_id": "load_test_agent", "chain": "base_sepolia"}'
   ```

3. **Verify API health**
   ```bash
   curl http://localhost:8000/health
   ```

## Interpreting Results

### Locust

- **RPS**: Requests per second
- **Response Time**: Average, min, max response times
- **Failures**: Failed request count and percentage

### k6

- **http_req_duration**: Request latency distribution
- **sardis_payment_ms**: Payment-specific latency
- **sardis_error_rate**: Percentage of failed requests
- **iterations**: Total test iterations completed

## CI/CD Integration

### GitHub Actions

```yaml
- name: Run Load Tests
  run: |
    k6 run tests/load/k6_load_test.js \
      --out json=load_results.json \
      --env API_URL=${{ secrets.API_URL }}

- name: Check Thresholds
  run: |
    # Parse results and fail if thresholds exceeded
    python scripts/check_load_results.py load_results.json
```

## Troubleshooting

### High Error Rates

1. Check API logs for errors
2. Verify database connections
3. Check rate limiting settings
4. Review Redis connection pool

### Slow Response Times

1. Check database query performance
2. Review policy evaluation complexity
3. Check external API latencies (Turnkey, Bridge)
4. Monitor CPU/memory usage

### Connection Errors

1. Verify API is running
2. Check firewall/security groups
3. Review connection pool limits
4. Check socket timeouts
