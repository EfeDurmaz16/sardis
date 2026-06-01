#!/usr/bin/env python3
"""
Sardis EventBus + Webhook Example
==================================

This example demonstrates the centralized event system with:
  1. EventBus subscription with wildcard patterns
  2. Custom event handlers for policy violations
  3. Webhook-backed event forwarding

The EventBus is the in-process pub/sub that fires before webhooks
go out to external services. Use it for real-time monitoring, logging,
and internal orchestration.

Prerequisites:
    pip install sardis

Run:
    python examples/event_webhooks.py
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime

from sardis.core.event_bus import get_default_bus
from sardis.core.webhooks import EventType, WebhookEvent

# --- Setup ------------------------------------------------------------------

bus = get_default_bus()

# Track events for the summary
event_log: list[dict] = []


# --- Handlers ---------------------------------------------------------------

def on_policy_event(event: WebhookEvent) -> None:
    """Handle all policy-related events."""
    data = event.data
    print(f"  [POLICY] {event.event_type.value}")
    print(f"    Agent: {data.get('agent_id', 'n/a')}")
    print(f"    Amount: ${data.get('amount', 'n/a')}")

    if event.event_type == EventType.POLICY_VIOLATED:
        print(f"    VIOLATION: {data.get('reason', 'Unknown')}")
        print(f"    Checks failed: {data.get('checks_failed', [])}")

    event_log.append({
        "type": event.event_type.value,
        "time": datetime.now(UTC).isoformat(),
        "data": data,
    })


def on_spend_event(event: WebhookEvent) -> None:
    """Handle spending events for budget tracking."""
    data = event.data
    print(f"  [SPEND] {event.event_type.value}")
    print(f"    Amount: ${data.get('amount', 0)} {data.get('token', 'USDC')}")
    print(f"    Running total: ${data.get('running_total', 'n/a')}")

    event_log.append({
        "type": event.event_type.value,
        "time": datetime.now(UTC).isoformat(),
        "data": data,
    })


def on_any_event(event: WebhookEvent) -> None:
    """Catch-all handler for logging."""
    event_log.append({
        "type": event.event_type.value,
        "time": datetime.now(UTC).isoformat(),
    })


async def on_approval_needed(event: WebhookEvent) -> None:
    """Async handler for approval routing events."""
    data = event.data
    print("  [APPROVAL] Human approval needed!")
    print(f"    Agent: {data.get('agent_id', 'n/a')}")
    print(f"    Amount: ${data.get('amount', 'n/a')}")
    print(f"    Reason: {data.get('reason', 'Threshold exceeded')}")
    # In production, this would notify a Slack channel or email
    await asyncio.sleep(0.01)  # simulate async notification


# --- Subscribe to events ---------------------------------------------------

def setup_subscriptions():
    """Register event handlers with the bus."""
    # Wildcard: all policy events (policy.*)
    bus.subscribe("policy.*", on_policy_event)

    # Wildcard: all spend events (spend.*)
    bus.subscribe("spend.*", on_spend_event)

    # Specific: approval needed
    bus.subscribe(EventType.APPROVAL_REQUESTED.value, on_approval_needed)

    # Catch-all: log everything
    bus.subscribe("*", on_any_event)

    print("Subscriptions registered:")
    print("  - policy.* -> on_policy_event")
    print("  - spend.* -> on_spend_event")
    print(f"  - {EventType.APPROVAL_REQUESTED.value} -> on_approval_needed")
    print("  - * -> on_any_event (catch-all)")
    print()


# --- Simulate events --------------------------------------------------------

async def simulate_payment_flow():
    """Simulate a sequence of payment events.

    ``EventBus.emit`` is async and takes ``(event_type, data)`` — it builds the
    ``WebhookEvent`` internally and routes it to matching subscribers. We await
    each emit (``fire_and_forget=False``) so the handlers run before the summary.
    """
    print("=" * 60)
    print("Simulating Payment Flow")
    print("=" * 60)
    print()

    # 1. Policy check passed
    print("1. Agent requests payment - policy check passes")
    await bus.emit(
        EventType.POLICY_CHECK_PASSED,
        data={
            "agent_id": "agent-001",
            "amount": 25.00,
            "token": "USDC",
            "destination": "openai.com",
            "checks_passed": ["amount_limit", "token_allowed", "destination_not_blocked"],
        },
        fire_and_forget=False,
    )
    print()

    # 2. Payment executed
    print("2. Payment executed")
    await bus.emit(
        EventType.PAYMENT_COMPLETED,
        data={
            "agent_id": "agent-001",
            "amount": 25.00,
            "token": "USDC",
            "running_total": 125.00,
            "tx_id": "tx_abc123",
        },
        fire_and_forget=False,
    )
    print()

    # 3. Policy violation
    print("3. Agent tries blocked payment - policy violation")
    await bus.emit(
        EventType.POLICY_VIOLATED,
        data={
            "agent_id": "agent-001",
            "amount": 500.00,
            "token": "USDC",
            "destination": "gambling.com",
            "reason": "Destination gambling.com is blocked",
            "checks_failed": ["destination_blocked"],
        },
        fire_and_forget=False,
    )
    print()

    # 4. Spend threshold warning
    print("4. Spend approaches limit - threshold warning")
    await bus.emit(
        EventType.SPEND_THRESHOLD_WARNING,
        data={
            "agent_id": "agent-001",
            "running_total": 900.00,
            "limit_total": 1000.00,
            "percent_used": 90,
        },
        fire_and_forget=False,
    )
    print()

    # 5. Approval needed
    print("5. Large payment requires human approval")
    await bus.emit(
        EventType.APPROVAL_REQUESTED,
        data={
            "agent_id": "agent-001",
            "amount": 250.00,
            "token": "USDC",
            "destination": "aws.amazon.com",
            "reason": "Amount exceeds approval threshold of $200",
        },
        fire_and_forget=False,
    )
    print()


# --- Summary ----------------------------------------------------------------

def print_summary():
    """Print a summary of all events captured."""
    print("=" * 60)
    print("Event Summary")
    print("=" * 60)
    print(f"Total events captured: {len(event_log)}")
    print()

    # Count by type
    type_counts: dict[str, int] = {}
    for entry in event_log:
        t = entry["type"]
        type_counts[t] = type_counts.get(t, 0) + 1

    for event_type, count in sorted(type_counts.items()):
        print(f"  {event_type}: {count}")

    print()
    print("Full event log (JSON):")
    print(json.dumps(event_log, indent=2, default=str))


# --- Main -------------------------------------------------------------------

if __name__ == "__main__":
    print()
    print("Sardis EventBus + Webhook Example")
    print("=" * 60)
    print()

    setup_subscriptions()
    asyncio.run(simulate_payment_flow())
    print_summary()
