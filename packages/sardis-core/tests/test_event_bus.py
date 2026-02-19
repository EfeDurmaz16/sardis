"""Tests for the EventBus system."""
import asyncio
import pytest
from sardis_v2_core import (
    EventBus,
    EventType,
    WebhookEvent,
    get_default_bus,
    emit_policy_event,
    emit_spend_event,
    emit_approval_event,
)


@pytest.mark.asyncio
async def test_event_bus_subscribe_and_emit():
    """Test basic subscribe and emit functionality."""
    bus = EventBus()
    received_events = []

    async def handler(event: WebhookEvent):
        received_events.append(event)

    bus.subscribe("policy.*", handler)

    await bus.emit(
        EventType.POLICY_VIOLATED,
        data={"policy_id": "pol_123", "reason": "Limit exceeded"},
        agent_id="agent_456",
        fire_and_forget=False,
    )

    # Give async tasks time to complete
    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.POLICY_VIOLATED
    assert received_events[0].data["policy_id"] == "pol_123"
    assert received_events[0].data["agent_id"] == "agent_456"


@pytest.mark.asyncio
async def test_wildcard_pattern_matching():
    """Test wildcard pattern matching."""
    bus = EventBus()
    policy_events = []
    all_events = []

    async def policy_handler(event: WebhookEvent):
        policy_events.append(event)

    async def all_handler(event: WebhookEvent):
        all_events.append(event)

    bus.subscribe("policy.*", policy_handler)
    bus.subscribe("*", all_handler)

    await bus.emit(
        EventType.POLICY_CREATED,
        data={"policy_id": "pol_123"},
        fire_and_forget=False,
    )

    await bus.emit(
        EventType.PAYMENT_COMPLETED,
        data={"tx_id": "tx_456"},
        fire_and_forget=False,
    )

    await asyncio.sleep(0.1)

    assert len(policy_events) == 1
    assert len(all_events) == 2
    assert policy_events[0].event_type == EventType.POLICY_CREATED


@pytest.mark.asyncio
async def test_unsubscribe():
    """Test unsubscribe functionality."""
    bus = EventBus()
    received_events = []

    async def handler(event: WebhookEvent):
        received_events.append(event)

    bus.subscribe("policy.*", handler)

    await bus.emit(
        EventType.POLICY_VIOLATED,
        data={"test": "1"},
        fire_and_forget=False,
    )

    bus.unsubscribe("policy.*", handler)

    await bus.emit(
        EventType.POLICY_VIOLATED,
        data={"test": "2"},
        fire_and_forget=False,
    )

    await asyncio.sleep(0.1)

    assert len(received_events) == 1


@pytest.mark.asyncio
async def test_emit_policy_event():
    """Test emit_policy_event helper."""
    bus = get_default_bus()
    bus.clear_subscribers()
    received_events = []

    async def handler(event: WebhookEvent):
        received_events.append(event)

    bus.subscribe("policy.*", handler)

    await emit_policy_event(
        EventType.POLICY_VIOLATED,
        policy_id="pol_123",
        agent_id="agent_456",
        reason="Daily limit exceeded",
        details={"limit": "1000.00", "attempted": "1200.00"},
    )

    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    event = received_events[0]
    assert event.event_type == EventType.POLICY_VIOLATED
    assert event.data["policy_id"] == "pol_123"
    assert event.data["agent_id"] == "agent_456"
    assert event.data["reason"] == "Daily limit exceeded"
    assert event.data["limit"] == "1000.00"


@pytest.mark.asyncio
async def test_emit_spend_event():
    """Test emit_spend_event helper."""
    bus = get_default_bus()
    bus.clear_subscribers()
    received_events = []

    async def handler(event: WebhookEvent):
        received_events.append(event)

    bus.subscribe("spend.*", handler)

    await emit_spend_event(
        EventType.SPEND_THRESHOLD_WARNING,
        agent_id="agent_123",
        amount="800.00",
        limit="1000.00",
        period="daily",
        percentage=80.0,
    )

    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    event = received_events[0]
    assert event.event_type == EventType.SPEND_THRESHOLD_WARNING
    assert event.data["amount"] == "800.00"
    assert event.data["percentage"] == 80.0


@pytest.mark.asyncio
async def test_emit_approval_event():
    """Test emit_approval_event helper."""
    bus = get_default_bus()
    bus.clear_subscribers()
    received_events = []

    async def handler(event: WebhookEvent):
        received_events.append(event)

    bus.subscribe("approval.*", handler)

    await emit_approval_event(
        EventType.APPROVAL_GRANTED,
        approval_id="appr_789",
        agent_id="agent_123",
        transaction_id="tx_456",
        approver_id="user_999",
    )

    await asyncio.sleep(0.1)

    assert len(received_events) == 1
    event = received_events[0]
    assert event.event_type == EventType.APPROVAL_GRANTED
    assert event.data["approval_id"] == "appr_789"
    assert event.data["transaction_id"] == "tx_456"


def test_new_event_types_exist():
    """Test that all new event types were added."""
    expected_new_types = [
        "policy.created",
        "policy.updated",
        "policy.violated",
        "policy.check.passed",
        "spend.threshold.warning",
        "spend.threshold.reached",
        "spend.daily.summary",
        "approval.requested",
        "approval.granted",
        "approval.denied",
        "approval.expired",
        "card.created",
        "card.activated",
        "card.transaction",
        "card.declined",
        "card.frozen",
        "compliance.check.passed",
        "compliance.check.failed",
        "compliance.alert",
        "group.budget.warning",
        "group.budget.exceeded",
    ]

    all_event_values = [e.value for e in EventType]

    for expected in expected_new_types:
        assert expected in all_event_values, f"Missing event type: {expected}"


@pytest.mark.asyncio
async def test_sync_handler():
    """Test that sync handlers work alongside async handlers."""
    bus = EventBus()
    received_events = []

    def sync_handler(event: WebhookEvent):
        received_events.append(("sync", event))

    async def async_handler(event: WebhookEvent):
        received_events.append(("async", event))

    bus.subscribe("policy.*", sync_handler)
    bus.subscribe("policy.*", async_handler)

    await bus.emit(
        EventType.POLICY_CREATED,
        data={"test": "data"},
        fire_and_forget=False,
    )

    await asyncio.sleep(0.1)

    assert len(received_events) == 2
    assert any(handler_type == "sync" for handler_type, _ in received_events)
    assert any(handler_type == "async" for handler_type, _ in received_events)
