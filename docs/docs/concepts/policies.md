# Spending Policies

Natural language spending rules that prevent financial hallucinations and enforce guardrails on AI agent payments.

## Overview

Sardis spending policies are **natural language rules** that define what an AI agent can and cannot do with money. Think of them as a firewall between agent decisions and actual transactions.

**Key principle:** An agent cannot override, disable, or bypass its spending policy. The policy is enforced server-side before any transaction executes.

## Policy Components

Every policy can include:

1. **Amount Limits** - Per-transaction, daily, weekly, monthly caps
2. **Merchant Allowlist** - Domains or addresses the agent can pay
3. **Category Restrictions** - Types of purchases allowed (SaaS, cloud, APIs)
4. **Time Windows** - Business hours, specific days
5. **Approval Flows** - Require human confirmation above threshold

## Examples

### Simple Amount Limit

```python
wallet = client.wallets.create(
    name="gpt4-agent",
    chain="base",
    policy="Max $100 per transaction, $500 per day"
)
```

**What this allows:**
- Single payment of $99 ✅
- Five payments of $100 each in one day ❌ (daily limit)
- Single payment of $501 ❌ (per-tx limit)

### Merchant Allowlist

```python
policy = """
Max $1000/day
Only allow:
- openai.com
- anthropic.com
- replicate.com
"""

wallet = client.wallets.create(name="claude-agent", policy=policy)
```

**What this allows:**
- $500 to openai.com ✅
- $200 to random-site.com ❌ (not on allowlist)

### Category + Time Restrictions

```python
policy = """
Max $50/tx, $200/day
Only SaaS and cloud services
Only Monday-Friday 9am-5pm EST
"""
```

**What this allows:**
- $50 to AWS on Tuesday at 2pm ✅
- $50 to AWS on Saturday ❌ (time window)
- $50 to gambling site on Tuesday ❌ (category)

### Approval Threshold

```python
policy = """
Max $10,000/day
Amounts under $100: auto-approve
Amounts $100-$1000: require email confirmation
Amounts over $1000: require 2FA confirmation
"""
```

## Policy Enforcement Flow

```
Agent Request
     ↓
Policy Parser (NLP)
     ↓
Rule Evaluation
     ↓
├─ PASS → Execute Transaction
└─ FAIL → Return PolicyViolationError
```

**Critical:** Policies are evaluated **before** MPC signing. A rejected transaction never touches the blockchain.

## Policy Language

Sardis uses NLP to parse policies. Supported syntax:

### Amount Limits

```
"Max $100 per transaction"
"Maximum $500/day"
"No more than $1000 per week"
"Daily limit: $2000"
```

### Merchant Rules

```
"Only openai.com and anthropic.com"
"Allow domains: aws.amazon.com, cloud.google.com"
"Allowlist: 0x1234... (Ethereum address)"
"Block: gambling, adult content"
```

### Categories

```
"Only SaaS and API services"
"No gambling or high-risk merchants"
"Enterprise software only"
```

### Time Windows

```
"Only business hours (9am-5pm EST)"
"Monday through Friday"
"No weekends"
"Between 8am-6pm Pacific Time"
```

### Approval Flows

```
"Require confirmation for amounts over $500"
"Auto-approve under $50, else require 2FA"
"Human approval for new merchants"
```

## Policy Violations

When a transaction violates a policy, Sardis returns a detailed error:

```python
try:
    result = client.payments.execute(
        wallet_id=wallet.id,
        to="0x...",
        amount=5000,  # Exceeds daily limit
        token="USDC"
    )
except PolicyViolationError as e:
    print(e.violation_type)  # "daily_limit_exceeded"
    print(e.limit)           # "$500"
    print(e.attempted)       # "$5000"
    print(e.message)         # "Daily limit of $500 exceeded. Attempted: $5000"
```

Violation types:
- `amount_limit_exceeded` - Per-transaction cap
- `daily_limit_exceeded` - Daily spending cap
- `merchant_not_allowed` - Not on allowlist
- `category_blocked` - Prohibited category
- `time_window_violation` - Outside allowed hours
- `requires_approval` - Needs human confirmation

## Dynamic Policies

Policies can be updated at any time:

```python
client.wallets.update_policy(
    wallet_id=wallet.id,
    policy="Max $1000/day, only AWS and GCP"
)
```

**Important:** Policy updates take effect immediately for all future transactions. In-flight transactions use the policy active when initiated.

## Policy Templates

Sardis provides pre-built templates for common use cases:

```python
from sardis import PolicyTemplates

# Conservative: $100/day, major SaaS only
policy = PolicyTemplates.conservative(daily_limit=100)

# Standard: $1000/day, SaaS + cloud
policy = PolicyTemplates.standard(daily_limit=1000)

# Permissive: $10k/day, broad categories
policy = PolicyTemplates.permissive(daily_limit=10000)
```

## Multi-Agent Policies

For agent teams, apply different policies per agent:

```python
# Research agent: read-only data APIs
research_wallet = client.wallets.create(
    name="research-agent",
    policy="Max $10/day, only data APIs"
)

# Procurement agent: higher limits
procurement_wallet = client.wallets.create(
    name="procurement-agent",
    policy="Max $5000/day, SaaS + hardware vendors"
)

# Executive agent: approval required
exec_wallet = client.wallets.create(
    name="executive-agent",
    policy="Max $50k/day, require 2FA for amounts over $10k"
)
```

## Testing Policies

Use simulation mode to test policies without real transactions:

```python
client = SardisClient(api_key="sk_test_...", simulation=True)

wallet = client.wallets.create(
    name="test-agent",
    policy="Max $100/day"
)

# This will validate the policy but not execute
result = client.payments.simulate(
    wallet_id=wallet.id,
    to="0x...",
    amount=150,
    token="USDC"
)

print(result.would_succeed)  # False
print(result.violation)      # "daily_limit_exceeded"
```

## Best Practices

1. **Start restrictive, expand later** - Begin with tight limits, loosen as trust builds
2. **Use allowlists for production** - Don't rely on category blocking alone
3. **Layer controls** - Combine amount limits + merchant allowlists + time windows
4. **Monitor violations** - High violation rates may indicate agent misconfiguration
5. **Separate dev/prod policies** - Use different limits for testing vs production
6. **Set approval thresholds** - Require human review for high-value transactions

## Next Steps

- [KYA (Know Your Agent)](kya.md) - Trust scoring and anomaly detection
- [Audit Ledger](ledger.md) - Transaction history and compliance
- [API Reference](../api/rest.md) - Policy management endpoints
