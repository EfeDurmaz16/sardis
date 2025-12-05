"""Tests for webhook system."""

import pytest
import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

from sardis_core.webhooks import (
    WebhookEvent,
    EventType,
    WebhookManager,
    WebhookSubscription,
)
from sardis_core.webhooks.events import (
    create_payment_completed_event,
    create_payment_failed_event,
    create_wallet_created_event,
    create_limit_exceeded_event,
    create_risk_alert_event,
)


class TestWebhookEvent:
    """Tests for WebhookEvent class."""
    
    def test_event_creation(self):
        """Test creating a basic event."""
        event = WebhookEvent(
            event_type=EventType.PAYMENT_COMPLETED,
            data={"test": "data"}
        )
        
        assert event.event_id.startswith("evt_")
        assert event.event_type == EventType.PAYMENT_COMPLETED
        assert event.data == {"test": "data"}
        assert event.api_version == "2024-01"
    
    def test_event_to_dict(self):
        """Test converting event to dictionary."""
        event = WebhookEvent(
            event_type=EventType.WALLET_CREATED,
            data={"wallet_id": "wallet_123"}
        )
        
        d = event.to_dict()
        
        assert d["id"] == event.event_id
        assert d["type"] == "wallet.created"
        assert d["data"]["wallet_id"] == "wallet_123"
        assert "created_at" in d
    
    def test_event_to_json(self):
        """Test converting event to JSON string."""
        event = WebhookEvent(
            event_type=EventType.PAYMENT_FAILED,
            data={"error": "Insufficient balance"}
        )
        
        json_str = event.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["type"] == "payment.failed"
        assert parsed["data"]["error"] == "Insufficient balance"
    
    def test_event_serializes_decimal(self):
        """Test Decimal values are serialized correctly."""
        event = WebhookEvent(
            event_type=EventType.PAYMENT_COMPLETED,
            data={"amount": Decimal("123.45")}
        )
        
        d = event.to_dict()
        
        assert d["data"]["amount"] == "123.45"
    
    def test_event_serializes_datetime(self):
        """Test datetime values are serialized correctly."""
        now = datetime.now(timezone.utc)
        event = WebhookEvent(
            event_type=EventType.PAYMENT_COMPLETED,
            data={"timestamp": now}
        )
        
        d = event.to_dict()
        
        assert d["data"]["timestamp"] == now.isoformat()


class TestEventFactories:
    """Tests for event factory functions."""
    
    def test_create_payment_completed_event(self):
        """Test creating payment completed event."""
        event = create_payment_completed_event(
            tx_id="tx_123",
            from_wallet="wallet_a",
            to_wallet="wallet_b",
            amount=Decimal("50.00"),
            fee=Decimal("0.10"),
            currency="USDC",
            purpose="Test payment"
        )
        
        assert event.event_type == EventType.PAYMENT_COMPLETED
        assert event.data["transaction"]["id"] == "tx_123"
        assert event.data["transaction"]["amount"] == Decimal("50.00")
        assert event.data["transaction"]["fee"] == Decimal("0.10")
        assert event.data["transaction"]["total"] == Decimal("50.10")
    
    def test_create_payment_failed_event(self):
        """Test creating payment failed event."""
        event = create_payment_failed_event(
            tx_id="tx_456",
            from_wallet="wallet_a",
            to_wallet="wallet_b",
            amount=Decimal("100.00"),
            currency="USDC",
            error="Insufficient balance"
        )
        
        assert event.event_type == EventType.PAYMENT_FAILED
        assert event.data["transaction"]["error"] == "Insufficient balance"
        assert event.data["transaction"]["status"] == "failed"
    
    def test_create_wallet_created_event(self):
        """Test creating wallet created event."""
        event = create_wallet_created_event(
            wallet_id="wallet_new",
            agent_id="agent_123",
            initial_balance=Decimal("100.00"),
            currency="USDC"
        )
        
        assert event.event_type == EventType.WALLET_CREATED
        assert event.data["wallet"]["id"] == "wallet_new"
        assert event.data["wallet"]["agent_id"] == "agent_123"
    
    def test_create_limit_exceeded_event(self):
        """Test creating limit exceeded event."""
        event = create_limit_exceeded_event(
            wallet_id="wallet_xyz",
            agent_id="agent_abc",
            limit_type="per_tx",
            limit_value=Decimal("50.00"),
            attempted_amount=Decimal("75.00"),
            currency="USDC"
        )
        
        assert event.event_type == EventType.LIMIT_EXCEEDED
        assert event.data["limit_type"] == "per_tx"
        assert event.data["limit_value"] == Decimal("50.00")
        assert event.data["attempted_amount"] == Decimal("75.00")
    
    def test_create_risk_alert_event(self):
        """Test creating risk alert event."""
        event = create_risk_alert_event(
            wallet_id="wallet_risky",
            agent_id="agent_risky",
            risk_score=85.0,
            risk_factors=["high_velocity", "large_amount"],
            recommended_action="block"
        )
        
        assert event.event_type == EventType.RISK_ALERT
        assert event.data["risk_score"] == 85.0
        assert "high_velocity" in event.data["risk_factors"]


class TestEventTypes:
    """Tests for all event types."""
    
    def test_all_payment_events(self):
        """Test all payment-related event types exist."""
        assert EventType.PAYMENT_INITIATED.value == "payment.initiated"
        assert EventType.PAYMENT_COMPLETED.value == "payment.completed"
        assert EventType.PAYMENT_FAILED.value == "payment.failed"
        assert EventType.PAYMENT_REFUNDED.value == "payment.refunded"
    
    def test_all_wallet_events(self):
        """Test all wallet-related event types exist."""
        assert EventType.WALLET_CREATED.value == "wallet.created"
        assert EventType.WALLET_FUNDED.value == "wallet.funded"
        assert EventType.WALLET_UPDATED.value == "wallet.updated"
        assert EventType.WALLET_DEACTIVATED.value == "wallet.deactivated"
    
    def test_all_limit_events(self):
        """Test all limit-related event types exist."""
        assert EventType.LIMIT_EXCEEDED.value == "limit.exceeded"
        assert EventType.LIMIT_WARNING.value == "limit.warning"
        assert EventType.LIMIT_UPDATED.value == "limit.updated"
    
    def test_all_risk_events(self):
        """Test all risk-related event types exist."""
        assert EventType.RISK_ALERT.value == "risk.alert"
        assert EventType.FRAUD_DETECTED.value == "fraud.detected"


class TestWebhookSubscription:
    """Tests for WebhookSubscription class."""
    
    def test_subscription_creation(self):
        """Test creating a subscription."""
        sub = WebhookSubscription(
            url="https://example.com/webhook",
            owner_id="owner_123",
            events=[EventType.PAYMENT_COMPLETED]
        )
        
        assert sub.subscription_id.startswith("whsub_")
        assert sub.url == "https://example.com/webhook"
        assert sub.secret.startswith("whsec_")
        assert sub.is_active is True
    
    def test_subscribes_to_specific_events(self):
        """Test subscription filters events correctly."""
        sub = WebhookSubscription(
            url="https://example.com",
            owner_id="owner",
            events=[EventType.PAYMENT_COMPLETED, EventType.PAYMENT_FAILED]
        )
        
        assert sub.subscribes_to(EventType.PAYMENT_COMPLETED) is True
        assert sub.subscribes_to(EventType.PAYMENT_FAILED) is True
        assert sub.subscribes_to(EventType.WALLET_CREATED) is False
    
    def test_subscribes_to_all_when_empty(self):
        """Test empty events list means all events."""
        sub = WebhookSubscription(
            url="https://example.com",
            owner_id="owner",
            events=[]
        )
        
        assert sub.subscribes_to(EventType.PAYMENT_COMPLETED) is True
        assert sub.subscribes_to(EventType.WALLET_CREATED) is True
        assert sub.subscribes_to(EventType.RISK_ALERT) is True


class TestWebhookManager:
    """Tests for WebhookManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a webhook manager."""
        return WebhookManager()
    
    def test_register_subscription(self, manager):
        """Test registering a webhook subscription."""
        sub = manager.register(
            url="https://example.com/hook",
            owner_id="dev_123",
            events=[EventType.PAYMENT_COMPLETED]
        )
        
        assert sub.url == "https://example.com/hook"
        assert sub.owner_id == "dev_123"
        assert sub.secret is not None
    
    def test_unregister_subscription(self, manager):
        """Test unregistering a subscription."""
        sub = manager.register(
            url="https://example.com",
            owner_id="owner"
        )
        
        result = manager.unregister(sub.subscription_id)
        assert result is True
        
        # Should be gone
        assert manager.get_subscription(sub.subscription_id) is None
    
    def test_unregister_nonexistent(self, manager):
        """Test unregistering non-existent subscription."""
        result = manager.unregister("nonexistent_id")
        assert result is False
    
    def test_get_subscription(self, manager):
        """Test getting a subscription by ID."""
        sub = manager.register(
            url="https://example.com",
            owner_id="owner"
        )
        
        retrieved = manager.get_subscription(sub.subscription_id)
        
        assert retrieved is not None
        assert retrieved.subscription_id == sub.subscription_id
    
    def test_list_subscriptions(self, manager):
        """Test listing all subscriptions."""
        manager.register(url="https://a.com", owner_id="owner1")
        manager.register(url="https://b.com", owner_id="owner2")
        manager.register(url="https://c.com", owner_id="owner1")
        
        all_subs = manager.list_subscriptions()
        assert len(all_subs) == 3
        
        owner1_subs = manager.list_subscriptions(owner_id="owner1")
        assert len(owner1_subs) == 2
    
    def test_update_subscription(self, manager):
        """Test updating a subscription."""
        sub = manager.register(
            url="https://old.com",
            owner_id="owner",
            events=[EventType.PAYMENT_COMPLETED]
        )
        
        updated = manager.update_subscription(
            subscription_id=sub.subscription_id,
            url="https://new.com",
            events=[EventType.PAYMENT_FAILED],
            is_active=False
        )
        
        assert updated.url == "https://new.com"
        assert updated.events == [EventType.PAYMENT_FAILED]
        assert updated.is_active is False
    
    def test_signature_generation(self, manager):
        """Test HMAC signature generation."""
        payload = '{"test": "data"}'
        secret = "test_secret"
        
        signature = manager._sign_payload(payload, secret)
        
        assert signature.startswith("sha256=")
        assert len(signature) > 10
    
    def test_signature_verification(self, manager):
        """Test signature verification."""
        payload = '{"test": "data"}'
        secret = "test_secret"
        
        signature = manager._sign_payload(payload, secret)
        
        # Should verify correctly
        assert manager.verify_signature(payload, signature, secret) is True
        
        # Should fail with wrong secret
        assert manager.verify_signature(payload, signature, "wrong_secret") is False
        
        # Should fail with modified payload
        assert manager.verify_signature('{"test": "modified"}', signature, secret) is False
    
    @pytest.mark.asyncio
    async def test_emit_to_matching_subscriptions(self, manager):
        """Test emitting events to matching subscriptions."""
        # Create subscriptions
        sub1 = manager.register(
            url="https://a.com",
            owner_id="owner",
            events=[EventType.PAYMENT_COMPLETED]
        )
        sub2 = manager.register(
            url="https://b.com",
            owner_id="owner",
            events=[EventType.WALLET_CREATED]
        )
        
        # Create event
        event = WebhookEvent(
            event_type=EventType.PAYMENT_COMPLETED,
            data={"test": True}
        )
        
        # Emit (just queues, doesn't deliver in this test)
        await manager.emit(event)
        
        # Check queue has the event for sub1 only
        assert manager._event_queue.qsize() == 1
    
    @pytest.mark.asyncio
    async def test_emit_and_wait(self, manager):
        """Test emitting event and waiting for delivery."""
        # Create a subscription with mocked delivery
        sub = manager.register(
            url="https://example.com",
            owner_id="owner",
            events=[EventType.PAYMENT_COMPLETED]
        )
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        
        async def mock_post(*args, **kwargs):
            return mock_response
        
        with patch.object(manager, '_get_client') as mock_client:
            mock_http = AsyncMock()
            mock_http.post = mock_post
            mock_client.return_value = mock_http
            
            event = WebhookEvent(
                event_type=EventType.PAYMENT_COMPLETED,
                data={"tx_id": "tx_123"}
            )
            
            results = await manager.emit_and_wait(event)
            
            assert sub.subscription_id in results
            # Note: actual delivery test requires real HTTP mocking
    
    def test_inactive_subscription_not_delivered(self, manager):
        """Test inactive subscriptions don't receive events."""
        sub = manager.register(
            url="https://example.com",
            owner_id="owner"
        )
        
        # Deactivate
        manager.update_subscription(sub.subscription_id, is_active=False)
        
        # Check it won't match
        active_subs = [
            s for s in manager.list_subscriptions()
            if s.is_active and s.subscribes_to(EventType.PAYMENT_COMPLETED)
        ]
        
        assert len(active_subs) == 0


class TestWebhookDelivery:
    """Tests for webhook delivery mechanics."""
    
    @pytest.fixture
    def manager(self):
        return WebhookManager()
    
    def test_delivery_result_success(self):
        """Test successful delivery result."""
        from sardis_core.webhooks.manager import DeliveryResult
        
        result = DeliveryResult(
            success=True,
            status_code=200,
            response_body="OK",
            duration_ms=50
        )
        
        assert result.success is True
        assert result.error is None
    
    def test_delivery_result_failure(self):
        """Test failed delivery result."""
        from sardis_core.webhooks.manager import DeliveryResult
        
        result = DeliveryResult(
            success=False,
            status_code=500,
            error="Internal server error",
            duration_ms=100
        )
        
        assert result.success is False
        assert result.error == "Internal server error"
    
    def test_subscription_delivery_stats(self, manager):
        """Test delivery stats are tracked."""
        sub = manager.register(
            url="https://example.com",
            owner_id="owner"
        )
        
        # Initial stats
        assert sub.total_deliveries == 0
        assert sub.successful_deliveries == 0
        assert sub.failed_deliveries == 0
        
        # Simulate successful delivery
        sub.total_deliveries += 1
        sub.successful_deliveries += 1
        
        assert sub.total_deliveries == 1
        assert sub.successful_deliveries == 1
    
    @pytest.mark.asyncio
    async def test_close_client(self, manager):
        """Test closing the HTTP client."""
        # Should not raise even if no client
        await manager.close()

