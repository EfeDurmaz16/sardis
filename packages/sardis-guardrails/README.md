# Sardis Guardrails

Runtime safety guardrails for the Sardis agent payment platform. Provides circuit breakers, kill switches, rate limiting, input validation, and behavioral monitoring to ensure safe and reliable agent payment execution.

## Features

- **Circuit Breaker**: Automatic failure detection and service protection
- **Kill Switch**: Emergency stop mechanisms (global, per-org, per-agent)
- **Rate Limiting**: Token bucket algorithm with sliding windows
- **Input Validation**: Comprehensive validation and sanitization
- **Behavioral Monitoring**: Anomaly detection based on spending patterns

## Installation

```bash
uv pip install sardis-guardrails
```

## Quick Start

### Circuit Breaker

Protect payment operations from cascading failures:

```python
from decimal import Decimal
from sardis_guardrails import CircuitBreaker, CircuitBreakerError

# Create circuit breaker for an agent
breaker = CircuitBreaker(agent_id="agent-123")

# Protect a payment function
@breaker.protected
async def make_payment(amount: Decimal) -> str:
    # Payment logic here
    return transaction_hash

# Use it
try:
    tx_hash = await make_payment(Decimal("100.00"))
except CircuitBreakerError:
    # Circuit is open, reject request
    print("Service temporarily unavailable")
```

### Kill Switch

Emergency stop for critical situations:

```python
from sardis_guardrails import get_kill_switch, ActivationReason, KillSwitchError

# Get global kill switch instance
kill_switch = get_kill_switch()

# Activate for an agent
await kill_switch.activate_agent(
    agent_id="agent-123",
    reason=ActivationReason.FRAUD,
    activated_by="security-team",
    notes="Suspicious activity detected"
)

# Check before payment execution
try:
    await kill_switch.check(agent_id="agent-123", org_id="org-456")
    # Proceed with payment
except KillSwitchError as e:
    # Kill switch active, block payment
    print(f"Payment blocked: {e}")
```

### Rate Limiting

Prevent excessive transaction volume:

```python
from decimal import Decimal
from sardis_guardrails import RateLimiter, RateLimitError

# Create rate limiter for an agent
limiter = RateLimiter(agent_id="agent-123")

# Configure limits
limiter.add_limit(
    name="per_minute",
    max_transactions=10,
    window_seconds=60.0,
    max_amount=Decimal("1000.00")
)

limiter.add_limit(
    name="per_hour",
    max_transactions=100,
    window_seconds=3600.0,
    max_amount=Decimal("10000.00")
)

# Check before transaction
try:
    await limiter.check_all_limits(amount=Decimal("50.00"))
    # Proceed with payment
except RateLimitError as e:
    print(f"Rate limit exceeded: {e}")
```

### Input Validation

Validate and sanitize payment inputs:

```python
from decimal import Decimal
from sardis_guardrails import (
    PaymentInputValidator,
    ValidationError,
    WalletAddressValidator,
    AmountValidator
)

# Comprehensive validation
try:
    validator = PaymentInputValidator(
        recipient_address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
        amount=Decimal("100.00"),
        token="USDC",
        chain="BASE",
        merchant_name="Example Corp",
        purpose="Payment for services"
    )
    validator.validate_full()
except ValidationError as e:
    print(f"Invalid input: {e}")

# Validate individual components
try:
    address = WalletAddressValidator.validate_ethereum_address(
        "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb"
    )
    amount = AmountValidator.validate_amount(
        amount=Decimal("100.00"),
        token="USDC",
        min_amount=Decimal("0.01"),
        max_amount=Decimal("1000000.00")
    )
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### Behavioral Monitoring

Detect anomalous spending patterns:

```python
from decimal import Decimal
from sardis_guardrails import (
    BehavioralMonitor,
    TransactionData,
    SensitivityLevel,
    AlertSeverity
)

# Create monitor for an agent
monitor = BehavioralMonitor(
    agent_id="agent-123",
    sensitivity=SensitivityLevel.NORMAL
)

# Record normal transactions to build baseline
for _ in range(20):
    await monitor.record_transaction(
        TransactionData(
            amount=Decimal("100.00"),
            merchant="Example Corp",
            token="USDC",
            chain="BASE"
        )
    )

# Check suspicious transaction
alerts = await monitor.check_transaction(
    TransactionData(
        amount=Decimal("10000.00"),  # Unusually large
        merchant="Example Corp",
        token="USDC",
        chain="BASE"
    )
)

for alert in alerts:
    print(f"[{alert.severity}] {alert.description}")
    if alert.severity == AlertSeverity.CRITICAL:
        # Take action (e.g., activate kill switch)
        pass
```

## Integration Example

Combining all guardrails in a payment flow:

```python
from decimal import Decimal
from sardis_guardrails import (
    CircuitBreaker,
    get_kill_switch,
    RateLimiter,
    PaymentInputValidator,
    BehavioralMonitor,
    TransactionData,
    ActivationReason,
    AlertSeverity
)

async def execute_payment(
    agent_id: str,
    org_id: str,
    recipient: str,
    amount: Decimal,
    token: str,
    chain: str,
    merchant: str,
    purpose: str
):
    # 1. Input validation
    validator = PaymentInputValidator(
        recipient_address=recipient,
        amount=amount,
        token=token,
        chain=chain,
        merchant_name=merchant,
        purpose=purpose
    )
    validator.validate_full()

    # 2. Kill switch check
    kill_switch = get_kill_switch()
    await kill_switch.check(agent_id=agent_id, org_id=org_id)

    # 3. Rate limiting
    limiter = RateLimiter(agent_id=agent_id)
    limiter.add_limit("per_minute", 10, 60.0, Decimal("1000.00"))
    await limiter.check_all_limits(amount)

    # 4. Behavioral check
    monitor = BehavioralMonitor(agent_id=agent_id)
    tx_data = TransactionData(
        amount=amount,
        merchant=merchant,
        token=token,
        chain=chain
    )

    alerts = await monitor.check_transaction(tx_data)
    for alert in alerts:
        if alert.severity == AlertSeverity.CRITICAL:
            # Auto-activate kill switch on critical anomaly
            await kill_switch.activate_agent(
                agent_id=agent_id,
                reason=ActivationReason.ANOMALY,
                notes=alert.description
            )
            raise Exception(f"Payment blocked: {alert.description}")

    # 5. Execute with circuit breaker
    breaker = CircuitBreaker(agent_id=agent_id)

    @breaker.protected
    async def _execute():
        # Actual payment logic here
        tx_hash = await execute_blockchain_transaction(...)

        # Record successful transaction
        await monitor.record_transaction(tx_data)

        return tx_hash

    return await _execute()
```

## Configuration

### Circuit Breaker

```python
from sardis_guardrails import CircuitBreakerConfig

config = CircuitBreakerConfig(
    failure_threshold=5,        # Failures before tripping
    reset_timeout=60.0,         # Seconds before retry
    half_open_max_calls=3,      # Test calls in half-open
    success_threshold=2         # Successes to close
)

breaker = CircuitBreaker(agent_id="agent-123", config=config)
```

### Sensitivity Levels

- **RELAXED**: 3.0 sigma threshold (fewer alerts)
- **NORMAL**: 2.5 sigma threshold (recommended)
- **STRICT**: 2.0 sigma threshold (more alerts)
- **PARANOID**: 1.5 sigma threshold (maximum alerts)

## License

MIT License - see LICENSE file for details.

## Links

- [Sardis Documentation](https://sardis.sh/docs)
- [GitHub Repository](https://github.com/EfeDurmaz16/sardis)
- [Bug Reports](https://github.com/EfeDurmaz16/sardis/issues)
