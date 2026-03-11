# KYA (Know Your Agent)

Trust scoring and behavioral anomaly detection for AI agents. KYA is Sardis's answer to the question: "How do we know this agent is behaving correctly?"

## What is KYA?

**KYA (Know Your Agent)** is a trust framework that monitors agent behavior, detects anomalies, and assigns risk scores. It's the AI equivalent of Know Your Customer (KYC), but for autonomous agents instead of humans.

Unlike KYC, which verifies human identity, KYA verifies:
- Agent behavioral patterns
- Transaction consistency
- Policy compliance history
- Reputation signals

## Why KYA Matters

AI agents can:
- Be compromised (prompt injection, jailbreaking)
- Malfunction (hallucinate invalid payments)
- Drift over time (model updates, fine-tuning)
- Make mistakes (misunderstand user intent)

**KYA detects these issues before they become financial losses.**

## Trust Score

Every agent wallet has a **trust score** (0-100):

- **90-100:** Excellent - Low friction, high limits
- **70-89:** Good - Standard policies apply
- **50-69:** Moderate - Additional verification required
- **Below 50:** Poor - Restricted or suspended

Trust scores are calculated from:

1. **Transaction History** (40%)
   - Successful payments
   - Policy compliance rate
   - Refund/dispute frequency

2. **Behavioral Consistency** (30%)
   - Spending patterns stable over time
   - No sudden spikes or anomalies

3. **Identity Attestation** (20%)
   - TAP (Trust Anchor Protocol) verification
   - Creator reputation
   - Code signing

4. **External Signals** (10%)
   - GitHub stars (for open source agents)
   - Community reputation
   - Security audits

## Checking Trust Score

```python
wallet = client.wallets.get(wallet_id)

print(wallet.trust_score)        # 85
print(wallet.trust_level)        # "good"
print(wallet.anomaly_alerts)     # []
```

## Anomaly Detection

Sardis monitors for suspicious patterns:

### Spending Anomalies

```python
# Normal: Agent spends $50-100/day on APIs
# Anomaly: Agent suddenly attempts $5000 payment

# KYA Response:
{
  "anomaly_type": "spending_spike",
  "severity": "high",
  "baseline": "$75/day (30-day average)",
  "detected": "$5000 single transaction",
  "action": "require_confirmation"
}
```

### Merchant Anomalies

```python
# Normal: Agent only pays openai.com, aws.amazon.com
# Anomaly: Agent attempts payment to unknown domain

# KYA Response:
{
  "anomaly_type": "new_merchant",
  "severity": "medium",
  "merchant": "random-site.com",
  "action": "require_confirmation"
}
```

### Time Pattern Anomalies

```python
# Normal: Agent makes payments 9am-5pm weekdays
# Anomaly: Payment attempt at 3am on Sunday

# KYA Response:
{
  "anomaly_type": "unusual_time",
  "severity": "medium",
  "pattern": "Weekday business hours",
  "detected": "Sunday 03:14 AM",
  "action": "flag_for_review"
}
```

### Velocity Anomalies

```python
# Normal: Agent makes 5-10 payments per day
# Anomaly: 100 payments in 10 minutes

# KYA Response:
{
  "anomaly_type": "transaction_velocity",
  "severity": "critical",
  "baseline": "8 tx/day (30-day average)",
  "detected": "100 tx in 10 minutes",
  "action": "temporary_suspension"
}
```

## Automated Responses

Based on anomaly severity, KYA can:

1. **Allow with logging** (Low severity)
   - Transaction proceeds
   - Flagged for manual review

2. **Require confirmation** (Medium severity)
   - Send email/SMS to owner
   - Transaction waits for approval

3. **Temporary hold** (High severity)
   - Block transaction
   - Notify owner immediately
   - Require 2FA to resume

4. **Wallet suspension** (Critical severity)
   - All transactions blocked
   - Manual investigation required

## TAP Protocol Integration

Sardis supports **TAP (Trust Anchor Protocol)** for agent identity verification:

```python
wallet = client.wallets.create(
    name="my-agent",
    chain="base",
    tap_attestation={
        "public_key": "...",      # Ed25519 or ECDSA-P256
        "signature": "...",         # Signed by creator
        "creator_did": "did:key:..." # Decentralized identifier
    }
)
```

**Benefits:**
- Higher trust score
- Lower transaction fees
- Access to premium features
- Cryptographic proof of origin

## Trust Score Decay

Trust scores can decrease if:

- Policy violations increase
- Anomalies detected
- Long periods of inactivity
- Negative community reports

```python
# Check trust score history
history = client.wallets.trust_history(wallet_id)

for event in history:
    print(f"{event.date}: {event.score} ({event.reason})")

# Output:
# 2026-02-01: 95 (Initial score)
# 2026-02-10: 92 (Policy violation: merchant not on allowlist)
# 2026-02-15: 88 (Anomaly detected: spending spike)
# 2026-02-20: 90 (Recovered: 5 days clean behavior)
```

## Improving Trust Score

To increase your agent's trust score:

1. **Maintain consistent behavior**
   - Stable spending patterns
   - Predictable transaction frequency

2. **High policy compliance**
   - No violations for 30+ days → +5 points
   - Zero violations for 90+ days → +10 points

3. **Add TAP attestation**
   - Cryptographic identity → +10 points

4. **Build transaction history**
   - 100+ successful payments → +5 points
   - 1000+ successful payments → +10 points

5. **Community reputation**
   - Open source with 100+ stars → +5 points
   - Security audit passed → +10 points

## KYA API

```python
# Get detailed trust analysis
analysis = client.kya.analyze(wallet_id)

print(analysis.trust_score)           # 85
print(analysis.risk_factors)          # ["new_merchant_frequency"]
print(analysis.recommendations)       # ["Add merchant allowlist"]

# Report suspicious behavior
client.kya.report_anomaly(
    wallet_id=wallet_id,
    type="suspected_compromise",
    evidence="Agent making unusual API calls"
)

# Freeze wallet (emergency)
client.wallets.freeze(wallet_id, reason="Suspected compromise")

# Unfreeze after investigation
client.wallets.unfreeze(wallet_id)
```

## KYA vs KYC

| Feature | KYA (Agents) | KYC (Humans) |
|---------|--------------|--------------|
| **Verification** | Behavioral patterns | Identity documents |
| **Trust Signal** | Transaction history | Government ID |
| **Changes Over Time** | Model updates, drift | Rarely |
| **Compromise Risk** | Prompt injection | Account takeover |
| **Remediation** | Retrain, rollback | Password reset |

## Real-World Example

```python
# Production procurement agent
wallet = client.wallets.create(
    name="procurement-agent-v2",
    chain="base",
    policy="Max $5000/day, SaaS vendors only",
    tap_attestation=tap_cert
)

# Initial trust score: 75 (new agent, TAP verified)

# After 30 days of normal operation:
# - 250 successful payments
# - Zero policy violations
# - No anomalies detected
# New trust score: 92

# Owner increases daily limit to $10k (high trust → higher limits)
client.wallets.update_policy(
    wallet_id=wallet.id,
    policy="Max $10000/day, SaaS vendors only"
)
```

## Monitoring Dashboard

Sardis provides real-time KYA monitoring:

```python
# Get KYA dashboard data
dashboard = client.kya.dashboard()

print(dashboard.total_agents)         # 12
print(dashboard.average_trust_score)  # 87
print(dashboard.active_anomalies)     # 2
print(dashboard.flagged_agents)       # ["agent_xyz"]
```

## Best Practices

1. **Monitor trust scores weekly** - Catch degradation early
2. **Investigate anomalies immediately** - Don't ignore alerts
3. **Use TAP attestation for production** - Higher trust = lower friction
4. **Set up anomaly webhooks** - Real-time notifications
5. **Review KYA logs monthly** - Identify patterns
6. **Test agents in simulation mode** - Build trust history safely

## Next Steps

- [Spending Policies](policies.md) - Define guardrails
- [Audit Ledger](ledger.md) - Transaction history
- [Webhooks](../api/webhooks.md) - Real-time KYA alerts
