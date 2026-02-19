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
from datetime import datetime, timezone

from sardis_v2_core.event_bus import EventBus, get_default_bus
from sardis_v2_core.webhooks import EventType, WebhookEvent

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

    if event.event_type == EventType.POLICY_VIOLATION:
        print(f"    VIOLATION: {data.get('reason', 'Unknown')}")
        print(f"    Checks failed: {data.get('checks_failed', [])}")

    event_log.append({
        "type": event.event_type.value,
        "time": datetime.now(timezone.utc).isoformat(),
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
        "time": datetime.now(timezone.utc).isoformat(),
        "data": data,
    })


def on_any_event(event: WebhookEvent) -> None:
    """Catch-all handler for logging."""
    event_log.append({
        "type": event.event_type.value,
        "time": datetime.now(timezone.utc).isoformat(),
    })


async def on_approval_needed(event: WebhookEvent) -> None:
    """Async handler for approval routing events."""
    data = event.data
    print(f"  [APPROVAL] Human approval needed!")
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

def simulate_payment_flow():
    """Simulate a sequence of payment events."""
    print("=" * 60)
    print("Simulating Payment Flow")
    print("=" * 60)
    print()

    # 1. Policy check passed
    print("1. Agent requests payment - policy check passes")
    bus.emit(WebhookEvent(
        event_type=EventType.POLICY_CHECK_PASSED,
        data={
            "agent_id": "agent-001",
            "amount": 25.00,
            "token": "USDC",
            "destination": "openai.com",
            "checks_passed": ["amount_limit", "token_allowed", "destination_not_blocked"],
        },
    ))
    print()

    # 2. Spend recorded
    print("2. Payment executed - spend recorded")
    bus.emit(WebhookEvent(
        event_type=EventType.SPEND_RECORDED,
        data={
            "agent_id": "agent-001",
            "amount": 25.00,
            "token": "USDC",
            "running_total": 125.00,
            "tx_id": "tx_abc123",
        },
    ))
    print()

    # 3. Policy violation
    print("3. Agent tries blocked payment - policy violation")
    bus.emit(WebhookEvent(
        event_type=EventType.POLICY_VIOLATION,
        data={
            "agent_id": "agent-001",
            "amount": 500.00,
            "token": "USDC",
            "destination": "gambling.com",
            "reason": "Destination gambling.com is blocked",
            "checks_failed": ["destination_blocked"],
        },
    ))
    print()

    # 4. Spend threshold warning
    print("4. Spend approaches limit - threshold warning")
    bus.emit(WebhookEvent(
        event_type=EventType.SPEND_THRESHOLD_WARNING,
        data={
            "agent_id": "agent-001",
            "running_total": 900.00,
            "limit_total": 1000.00,
            "percent_used": 90,
        },
    ))
    print()

    # 5. Approval needed
    print("5. Large payment requires human approval")
    bus.emit(WebhookEvent(
        event_type=EventType.APPROVAL_REQUESTED,
        data={
            "agent_id": "agent-001",
            "amount": 250.00,
            "token": "USDC",
            "destination": "aws.amazon.com",
            "reason": "Amount exceeds approval threshold of $200",
        },
    ))
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
    simulate_payment_flow()
    print_summary()
