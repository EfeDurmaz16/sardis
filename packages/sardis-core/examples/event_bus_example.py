"""Example usage of the Sardis EventBus system.

This demonstrates how to:
1. Subscribe to events with wildcard patterns
2. Emit events using helper functions
3. Integrate with the webhook service
"""
import asyncio
from sardis_v2_core import (
    EventBus,
    EventType,
    WebhookEvent,
    get_default_bus,
    emit_policy_event,
    emit_spend_event,
    emit_approval_event,
    emit_card_event,
    emit_compliance_event,
)


async def policy_monitor(event: WebhookEvent):
    """Monitor all policy-related events."""
    print(f"[POLICY] {event.event_type.value}: {event.data.get('reason', 'N/A')}")


async def spending_monitor(event: WebhookEvent):
    """Monitor spending threshold events."""
    if event.event_type == EventType.SPEND_THRESHOLD_WARNING:
        percentage = event.data.get("percentage", 0)
        print(f"[WARNING] Spending at {percentage}% of limit")
    elif event.event_type == EventType.SPEND_THRESHOLD_REACHED:
        print(f"[ALERT] Spending limit reached!")


async def audit_logger(event: WebhookEvent):
    """Log all events for audit trail."""
    print(f"[AUDIT] {event.event_type.value} | Agent: {event.data.get('agent_id', 'N/A')}")


async def main():
    """Run example event bus scenarios."""
    print("=== Sardis EventBus Example ===\n")

    # Get the default event bus
    bus = get_default_bus()
    bus.clear_subscribers()  # Start fresh

    # Subscribe to different event patterns
    bus.subscribe("policy.*", policy_monitor)
    bus.subscribe("spend.*", spending_monitor)
    bus.subscribe("*", audit_logger)  # Catch all events

    print("1. Policy Violation Event")
    print("-" * 40)
    await emit_policy_event(
        EventType.POLICY_VIOLATED,
        policy_id="pol_123",
        agent_id="agent_456",
        reason="Daily spending limit exceeded",
        details={"limit": "1000.00", "attempted": "1200.00"},
    )
    await asyncio.sleep(0.1)  # Let handlers run

    print("\n2. Spending Warning Event")
    print("-" * 40)
    await emit_spend_event(
        EventType.SPEND_THRESHOLD_WARNING,
        agent_id="agent_789",
        amount="800.00",
        limit="1000.00",
        period="daily",
        percentage=80.0,
    )
    await asyncio.sleep(0.1)

    print("\n3. Approval Request Event")
    print("-" * 40)
    await emit_approval_event(
        EventType.APPROVAL_REQUESTED,
        approval_id="appr_001",
        agent_id="agent_999",
        transaction_id="tx_555",
        reason="Transaction exceeds auto-approval threshold",
    )
    await asyncio.sleep(0.1)

    print("\n4. Card Transaction Event")
    print("-" * 40)
    await emit_card_event(
        EventType.CARD_TRANSACTION,
        card_id="card_123",
        agent_id="agent_456",
        transaction_id="tx_777",
        amount="45.99",
        merchant="Amazon",
    )
    await asyncio.sleep(0.1)

    print("\n5. Compliance Check Event")
    print("-" * 40)
    await emit_compliance_event(
        EventType.COMPLIANCE_CHECK_PASSED,
        agent_id="agent_111",
        check_type="kyc",
        result="pass",
        details={"verification_level": "basic"},
    )
    await asyncio.sleep(0.1)

    print("\n=== Example Complete ===")


if __name__ == "__main__":
    asyncio.run(main())
