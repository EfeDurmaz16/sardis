---
name: sardis-guardrails
description: Real-time security monitoring and circuit breaker controls for Sardis agent wallets
version: 1.0.0
metadata:
  openclaw:
    requires:
      env:
        - SARDIS_API_KEY
      bins:
        - curl
        - jq
    primaryEnv: SARDIS_API_KEY
    emoji: "🛡️"
    homepage: https://sardis.sh
    install:
      npm:
        - "@sardis/sdk"
    user-invocable: true
    disable-model-invocation: false
---

# Sardis Guardrails - Real-Time Security Controls

Comprehensive security monitoring and emergency controls for agent wallets. Protect against runaway spending, anomalous behavior, and security threats with circuit breakers and kill switches.

## Capabilities

- **Circuit Breaker Status**: Check if automatic spending halts are active
- **Kill Switch Control**: Emergency stop all transactions wallet-wide
- **Rate Limit Monitoring**: Track transaction velocity and spending patterns
- **Behavioral Alerts**: Get warnings for anomalous agent behavior
- **Emergency Controls**: Immediate response to security threats

## Security Model

**CRITICAL CONTROLS**: This skill can activate emergency stops that halt all wallet transactions. Use with caution.

## Quick Setup

```bash
export SARDIS_API_KEY=sk_your_key_here
```

## API Endpoint Patterns

Base URL: `https://api.sardis.sh/v2`

### Check Circuit Breaker Status

```bash
# Get current circuit breaker and kill switch status
curl -X GET https://api.sardis.sh/v2/guardrails/status \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: wallet_abc123"

# Example response:
# {
#   "wallet_id": "wallet_abc123",
#   "circuit_breaker": {
#     "active": false,
#     "reason": null,
#     "triggered_at": null
#   },
#   "kill_switch": {
#     "active": false,
#     "activated_by": null,
#     "activated_at": null
#   },
#   "rate_limits": {
#     "tx_per_minute": 5,
#     "current_rate": 2.3,
#     "threshold_breached": false
#   },
#   "status": "operational"
# }
```

### Activate Kill Switch

```bash
# Emergency stop all transactions for a wallet
curl -X POST https://api.sardis.sh/v2/guardrails/kill-switch/activate \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wallet_abc123",
    "reason": "Suspected unauthorized activity detected"
  }'

# Response:
# {
#   "wallet_id": "wallet_abc123",
#   "kill_switch_active": true,
#   "activated_at": "2026-02-21T10:30:00Z",
#   "reason": "Suspected unauthorized activity detected",
#   "message": "All transactions halted. Contact support to reactivate."
# }
```

### Deactivate Kill Switch

```bash
# Resume normal operations after investigation
curl -X POST https://api.sardis.sh/v2/guardrails/kill-switch/deactivate \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_id": "wallet_abc123"
  }'

# Response:
# {
#   "wallet_id": "wallet_abc123",
#   "kill_switch_active": false,
#   "deactivated_at": "2026-02-21T11:00:00Z",
#   "message": "Wallet operational. Transactions resumed."
# }
```

### Check Rate Limits

```bash
# Monitor transaction velocity and spending rate
curl -X GET https://api.sardis.sh/v2/guardrails/rate-limits \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: wallet_abc123"

# Example response:
# {
#   "wallet_id": "wallet_abc123",
#   "limits": {
#     "tx_per_minute": {
#       "limit": 5,
#       "current": 2.3,
#       "percentage_used": 46.0,
#       "breached": false
#     },
#     "tx_per_hour": {
#       "limit": 100,
#       "current": 45,
#       "percentage_used": 45.0,
#       "breached": false
#     },
#     "spend_per_hour_usd": {
#       "limit": "1000.00",
#       "current": "325.50",
#       "percentage_used": 32.55,
#       "breached": false
#     }
#   },
#   "status": "healthy"
# }
```

### Get Behavioral Alerts

```bash
# Retrieve anomaly detection alerts
curl -X GET https://api.sardis.sh/v2/guardrails/alerts \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: wallet_abc123"

# Filters:
# - severity: low, medium, high, critical
# - limit: Number of alerts (default 20, max 100)
# - since: ISO 8601 timestamp for alerts after this time

# Example with filters:
curl -X GET "https://api.sardis.sh/v2/guardrails/alerts?severity=high&limit=10" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: wallet_abc123"
```

## Example Commands

### Emergency Stop Workflow

```bash
# 1. Check current status
WALLET_ID=wallet_abc123
STATUS=$(curl -s -X GET https://api.sardis.sh/v2/guardrails/status \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: $WALLET_ID")

echo "Current Status:"
echo "$STATUS" | jq '.'

# 2. Activate kill switch if needed
if [[ $(echo "$STATUS" | jq -r '.circuit_breaker.active') == "true" ]]; then
  echo "Circuit breaker already active!"

  curl -X POST https://api.sardis.sh/v2/guardrails/kill-switch/activate \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "Content-Type: application/json" \
    -d "{\"wallet_id\": \"$WALLET_ID\", \"reason\": \"Manual emergency stop\"}"
fi
```

### Rate Limit Monitor

```bash
# Monitor and alert on high transaction rates
WALLET_ID=wallet_abc123

while true; do
  LIMITS=$(curl -s -X GET https://api.sardis.sh/v2/guardrails/rate-limits \
    -H "Authorization: Bearer $SARDIS_API_KEY" \
    -H "X-Wallet-ID: $WALLET_ID")

  TX_RATE=$(echo "$LIMITS" | jq -r '.limits.tx_per_minute.current')
  THRESHOLD=80

  USAGE=$(echo "$LIMITS" | jq -r '.limits.tx_per_minute.percentage_used')

  if (( $(echo "$USAGE > $THRESHOLD" | bc -l) )); then
    echo "WARNING: Transaction rate at ${USAGE}% of limit"
    echo "Current: $TX_RATE tx/min"
  fi

  sleep 30
done
```

### Behavioral Alert Dashboard

```bash
# Get critical alerts and display summary
WALLET_ID=wallet_abc123

echo "=== Critical Security Alerts ==="
curl -s -X GET "https://api.sardis.sh/v2/guardrails/alerts?severity=critical&limit=5" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: $WALLET_ID" | jq '.alerts[] | "\(.timestamp) - \(.type): \(.message)"'

echo -e "\n=== High Priority Alerts ==="
curl -s -X GET "https://api.sardis.sh/v2/guardrails/alerts?severity=high&limit=5" \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: $WALLET_ID" | jq '.alerts[] | "\(.timestamp) - \(.type): \(.message)"'
```

### Automated Circuit Breaker Response

```bash
# Check for circuit breaker activation and notify
WALLET_ID=wallet_abc123

STATUS=$(curl -s -X GET https://api.sardis.sh/v2/guardrails/status \
  -H "Authorization: Bearer $SARDIS_API_KEY" \
  -H "X-Wallet-ID: $WALLET_ID")

if [[ $(echo "$STATUS" | jq -r '.circuit_breaker.active') == "true" ]]; then
  REASON=$(echo "$STATUS" | jq -r '.circuit_breaker.reason')
  echo "ALERT: Circuit breaker triggered!"
  echo "Reason: $REASON"

  # Send notification (integrate with your alerting system)
  # curl -X POST https://your-webhook.com/alert -d "Circuit breaker active: $REASON"
fi
```

## Response Examples

### Guardrails Status Response

```json
{
  "wallet_id": "wallet_abc123",
  "circuit_breaker": {
    "active": false,
    "reason": null,
    "triggered_at": null,
    "auto_recovery": true,
    "recovery_threshold": "10 minutes below threshold"
  },
  "kill_switch": {
    "active": false,
    "activated_by": null,
    "activated_at": null,
    "requires_manual_reset": true
  },
  "rate_limits": {
    "tx_per_minute": {
      "limit": 5,
      "current": 2.3,
      "breached": false
    },
    "tx_per_hour": {
      "limit": 100,
      "current": 45,
      "breached": false
    },
    "spend_per_hour_usd": {
      "limit": "1000.00",
      "current": "325.50",
      "breached": false
    }
  },
  "status": "operational",
  "last_checked": "2026-02-21T10:30:00Z"
}
```

### Behavioral Alerts Response

```json
{
  "wallet_id": "wallet_abc123",
  "alerts": [
    {
      "alert_id": "alert_xyz789",
      "severity": "high",
      "type": "unusual_recipient",
      "message": "Transaction to new recipient with no prior history",
      "details": {
        "recipient": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        "amount": "500.00",
        "token": "USDC",
        "deviation": "high"
      },
      "timestamp": "2026-02-21T09:45:00Z",
      "auto_blocked": false,
      "requires_review": true
    },
    {
      "alert_id": "alert_abc456",
      "severity": "medium",
      "type": "velocity_spike",
      "message": "Transaction rate 3x higher than normal baseline",
      "details": {
        "normal_rate": "2.5 tx/min",
        "current_rate": "7.8 tx/min",
        "duration": "5 minutes"
      },
      "timestamp": "2026-02-21T09:30:00Z",
      "auto_blocked": false,
      "requires_review": false
    }
  ],
  "total": 2,
  "has_critical": false
}
```

### Kill Switch Activation Response

```json
{
  "wallet_id": "wallet_abc123",
  "kill_switch_active": true,
  "activated_by": "api_key_sk_xyz",
  "activated_at": "2026-02-21T10:30:00Z",
  "reason": "Suspected unauthorized activity detected",
  "affected_transactions": {
    "pending_count": 3,
    "pending_total_usd": "125.50",
    "all_blocked": true
  },
  "message": "All transactions halted. Contact support@sardis.sh to reactivate.",
  "reactivation_requires": ["manual_approval", "security_review"]
}
```

## Error Handling

- `401 Unauthorized` - Invalid or missing API key
- `403 Forbidden` - No access to this wallet or insufficient permissions
- `404 Not Found` - Wallet does not exist
- `409 Conflict` - Kill switch already in requested state
- `429 Too Many Requests` - Rate limit exceeded

## Use Cases

- **Security Incident Response**: Emergency stop during security threats
- **Anomaly Detection**: Catch unusual spending patterns early
- **Compliance Monitoring**: Track transaction velocity for regulatory compliance
- **Automated Safety**: Circuit breakers prevent runaway spending
- **Alert Automation**: Integrate with monitoring systems for real-time alerts

## Related Skills

- `sardis-balance` - Monitor wallet balances and spending
- `sardis-policy` - Define spending rules and limits
- `sardis-payment` - Execute controlled payments

## Links

- Website: https://sardis.sh
- Documentation: https://sardis.sh/docs/guardrails
- API Reference: https://api.sardis.sh/v2/docs
- Security: https://sardis.sh/security
- Support: support@sardis.sh
