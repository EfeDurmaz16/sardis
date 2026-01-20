"""Integration tests for checkout surface (Pivot D)."""
from __future__ import annotations

from decimal import Decimal
import pytest
from unittest.mock import AsyncMock, MagicMock

from sardis_checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus
from sardis_checkout.orchestrator import CheckoutOrchestrator
from sardis_checkout.connectors.stripe import StripeConnector
from sardis_v2_core.wallets import Wallet


class TestCheckoutOrchestrator:
    """Tests for CheckoutOrchestrator."""

    @pytest.mark.asyncio
    async def test_create_checkout_with_stripe(self):
        """Test creating checkout session with Stripe connector."""
        # Mock Stripe connector
        from sardis_checkout.connectors.base import PSPConnector
        
        from sardis_checkout.models import PSPType
        
        class MockStripeConnector(PSPConnector):
            @property
            def psp_type(self) -> PSPType:
                return PSPType.STRIPE
            
            async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutResponse:
                return CheckoutResponse(
                    checkout_id="cs_test_123",
                    redirect_url="https://checkout.stripe.com/test",
                    status=PaymentStatus.PENDING,
                    psp_name="stripe",
                    amount=Decimal("100.00"),
                    currency="USD",
                    agent_id="agent_001",
                    mandate_id="mandate_001",
                )
            
            async def verify_webhook(self, payload: bytes, signature: str) -> bool:
                return True
            
            async def get_payment_status(self, checkout_id: str) -> PaymentStatus:
                return PaymentStatus.PENDING
            
            async def handle_webhook(self, payload: dict, headers: dict) -> dict:
                return {"status": "success"}
        
        mock_stripe = MockStripeConnector()
        
        orchestrator = CheckoutOrchestrator()
        orchestrator.register_connector("stripe", mock_stripe)
        
        request = CheckoutRequest(
            agent_id="agent_001",
            wallet_id="wallet_001",
            mandate_id="mandate_001",
            amount=Decimal("100.00"),
            currency="USD",
            description="Test payment",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        
        response = await orchestrator.create_checkout(request, psp_preference="stripe")
        
        assert response.checkout_id == "cs_test_123"
        assert response.psp_name == "stripe"
        assert response.status == PaymentStatus.PENDING
        assert response.amount == Decimal("100.00")

    @pytest.mark.asyncio
    async def test_get_payment_status(self):
        """Test getting payment status from PSP."""
        from sardis_checkout.connectors.base import PSPConnector
        from sardis_checkout.models import PSPType
        
        class MockStripeConnector(PSPConnector):
            @property
            def psp_type(self) -> PSPType:
                return PSPType.STRIPE
            
            async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutResponse:
                return CheckoutResponse(
                    checkout_id="cs_test_123",
                    redirect_url="https://checkout.stripe.com/test",
                    status=PaymentStatus.PENDING,
                    psp_name="stripe",
                    amount=Decimal("100.00"),
                    currency="USD",
                    agent_id="agent_001",
                    mandate_id="mandate_001",
                )
            
            async def verify_webhook(self, payload: bytes, signature: str) -> bool:
                return True
            
            async def get_payment_status(self, checkout_id: str) -> PaymentStatus:
                return PaymentStatus.COMPLETED
            
            async def handle_webhook(self, payload: dict, headers: dict) -> dict:
                return {"status": "success"}
        
        mock_stripe = MockStripeConnector()
        
        orchestrator = CheckoutOrchestrator()
        orchestrator.register_connector("stripe", mock_stripe)
        
        status = await orchestrator.get_payment_status("cs_test_123", "stripe")
        
        assert status == PaymentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_handle_webhook(self):
        """Test handling PSP webhook."""
        from sardis_checkout.connectors.base import PSPConnector
        from sardis_checkout.models import PSPType
        
        class MockStripeConnector(PSPConnector):
            @property
            def psp_type(self) -> PSPType:
                return PSPType.STRIPE
            
            async def create_checkout_session(self, request: CheckoutRequest) -> CheckoutResponse:
                return CheckoutResponse(
                    checkout_id="cs_test_123",
                    redirect_url="https://checkout.stripe.com/test",
                    status=PaymentStatus.PENDING,
                    psp_name="stripe",
                    amount=Decimal("100.00"),
                    currency="USD",
                    agent_id="agent_001",
                    mandate_id="mandate_001",
                )
            
            async def verify_webhook(self, payload: bytes, signature: str) -> bool:
                return True
            
            async def get_payment_status(self, checkout_id: str) -> PaymentStatus:
                return PaymentStatus.PENDING
            
            async def handle_webhook(self, payload: dict, headers: dict) -> dict:
                return {
                    "event_type": "checkout.session.completed",
                    "session_id": "cs_test_123",
                    "payment_status": "paid",
                }
        
        mock_stripe = MockStripeConnector()
        
        orchestrator = CheckoutOrchestrator()
        orchestrator.register_connector("stripe", mock_stripe)
        
        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_123",
                    "payment_status": "paid",
                }
            }
        }
        headers = {"stripe-signature": "test_signature"}
        
        result = await orchestrator.handle_webhook("stripe", payload, headers)
        
        assert result["event_type"] == "checkout.session.completed"


class TestStripeConnector:
    """Tests for Stripe connector."""

    @pytest.mark.asyncio
    async def test_create_checkout_session(self):
        """Test creating Stripe checkout session."""
        # Note: This would require actual Stripe API key in integration tests
        # For unit tests, we mock the HTTP client
        connector = StripeConnector(
            api_key="sk_test_mock",
            webhook_secret="whsec_mock",
        )
        
        # Mock the HTTP client
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "cs_test_123",
            "url": "https://checkout.stripe.com/test",
            "payment_status": "unpaid",
        }
        mock_response.raise_for_status = MagicMock()
        
        connector._client = AsyncMock()
        connector._client.post = AsyncMock(return_value=mock_response)
        
        request = CheckoutRequest(
            agent_id="agent_001",
            wallet_id="wallet_001",
            mandate_id="mandate_001",
            amount=Decimal("100.00"),
            currency="USD",
            description="Test payment",
            success_url="https://example.com/success",
            cancel_url="https://example.com/cancel",
        )
        
        response = await connector.create_checkout_session(request)
        
        assert response.checkout_id == "cs_test_123"
        assert response.psp_name == "stripe"
        assert response.amount == Decimal("100.00")
