"""End-to-end integration tests for Sardis."""

import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport

from sardis_core.api.main import app
from sardis_core.api.dependencies import get_container


class TestAgentRegistrationFlow:
    """Test complete agent registration flow."""
    
    @pytest.fixture
    def container(self):
        """Get fresh container for each test."""
        # Get new container
        return get_container()
    
    @pytest.mark.asyncio
    async def test_register_agent_creates_wallet(self):
        """Test that registering an agent creates a wallet with correct limits."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "test_shopping_agent",
                    "owner_id": "developer_1",
                    "description": "Test agent for integration",
                    "initial_balance": "100.00",
                    "limit_per_tx": "20.00",
                    "limit_total": "100.00"
                }
            )
            
            assert response.status_code == 201
            data = response.json()
            
            # Agent created
            assert "agent" in data
            assert data["agent"]["name"] == "test_shopping_agent"
            assert data["agent"]["owner_id"] == "developer_1"
            
            # Wallet created with correct values
            assert "wallet" in data
            assert data["wallet"]["balance"] == "100.00"
            assert data["wallet"]["limit_per_tx"] == "20.00"
            assert data["wallet"]["limit_total"] == "100.00"
            assert data["wallet"]["spent_total"] == "0.00"
            
            # Virtual card assigned
            assert data["wallet"]["virtual_card"] is not None
            assert "masked_number" in data["wallet"]["virtual_card"]


class TestPaymentFlow:
    """Test complete payment flow from agent to merchant."""
    
    @pytest.mark.asyncio
    async def test_full_payment_flow(self):
        """Test complete payment: register -> pay -> check balance."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register agent
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "payment_test_agent",
                    "owner_id": "dev_payment",
                    "initial_balance": "100.00",
                    "limit_per_tx": "50.00",
                    "limit_total": "100.00"
                }
            )
            assert agent_response.status_code == 201
            agent_data = agent_response.json()
            agent_id = agent_data["agent"]["agent_id"]
            
            # 2. Register merchant
            merchant_response = await client.post(
                "/api/v1/merchants",
                json={
                    "name": "Test Merchant",
                    "description": "For integration testing",
                    "category": "testing"
                }
            )
            assert merchant_response.status_code == 201
            merchant_data = merchant_response.json()
            merchant_id = merchant_data["merchant_id"]
            
            # 3. Make payment
            payment_response = await client.post(
                "/api/v1/payments",
                json={
                    "agent_id": agent_id,
                    "merchant_id": merchant_id,
                    "amount": "25.00",
                    "currency": "USDC",
                    "purpose": "Integration test purchase"
                }
            )
            assert payment_response.status_code == 200
            payment_data = payment_response.json()
            
            assert payment_data["success"] is True
            assert payment_data["transaction"]["amount"] == "25.00"
            assert payment_data["transaction"]["status"] == "completed"
            
            # 4. Verify wallet balance updated
            wallet_response = await client.get(f"/api/v1/agents/{agent_id}/wallet")
            assert wallet_response.status_code == 200
            wallet_data = wallet_response.json()
            
            # Balance should be 100 - 25 - 0.10 (fee) = 74.90
            assert Decimal(wallet_data["balance"]) == Decimal("74.90")
            assert Decimal(wallet_data["spent_total"]) == Decimal("25.10")
    
    @pytest.mark.asyncio
    async def test_payment_exceeds_limit_rejected(self):
        """Test payment exceeding limit is rejected."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register agent with low limit
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "limited_agent",
                    "owner_id": "dev_limit",
                    "initial_balance": "100.00",
                    "limit_per_tx": "10.00",  # Low limit
                    "limit_total": "100.00"
                }
            )
            agent_id = agent_response.json()["agent"]["agent_id"]
            
            # Register merchant
            merchant_response = await client.post(
                "/api/v1/merchants",
                json={"name": "Limit Test Merchant", "category": "test"}
            )
            merchant_id = merchant_response.json()["merchant_id"]
            
            # Try to pay more than limit
            payment_response = await client.post(
                "/api/v1/payments",
                json={
                    "agent_id": agent_id,
                    "merchant_id": merchant_id,
                    "amount": "25.00",  # Exceeds $10 limit
                    "currency": "USDC"
                }
            )
            
            # Should be rejected
            assert payment_response.status_code == 400
            error_data = payment_response.json()
            assert "limit" in error_data["detail"].lower()
    
    @pytest.mark.asyncio
    async def test_payment_insufficient_balance_rejected(self):
        """Test payment with insufficient balance is rejected."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Register agent with low balance
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "poor_agent",
                    "owner_id": "dev_poor",
                    "initial_balance": "5.00",  # Low balance
                    "limit_per_tx": "100.00",
                    "limit_total": "100.00"
                }
            )
            agent_id = agent_response.json()["agent"]["agent_id"]
            
            merchant_response = await client.post(
                "/api/v1/merchants",
                json={"name": "Balance Test Merchant", "category": "test"}
            )
            merchant_id = merchant_response.json()["merchant_id"]
            
            # Try to pay more than balance
            payment_response = await client.post(
                "/api/v1/payments",
                json={
                    "agent_id": agent_id,
                    "merchant_id": merchant_id,
                    "amount": "20.00",  # More than $5 balance
                    "currency": "USDC"
                }
            )
            
            assert payment_response.status_code == 400
            assert "balance" in payment_response.json()["detail"].lower()


class TestTransactionHistory:
    """Test transaction history functionality."""
    
    @pytest.mark.asyncio
    async def test_transaction_history_after_payments(self):
        """Test transaction history shows completed payments."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Setup
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "history_agent",
                    "owner_id": "dev_history",
                    "initial_balance": "200.00",
                    "limit_per_tx": "50.00",
                    "limit_total": "200.00"
                }
            )
            agent_id = agent_response.json()["agent"]["agent_id"]
            
            merchant_response = await client.post(
                "/api/v1/merchants",
                json={"name": "History Merchant", "category": "test"}
            )
            merchant_id = merchant_response.json()["merchant_id"]
            
            # Make multiple payments
            for i in range(3):
                await client.post(
                    "/api/v1/payments",
                    json={
                        "agent_id": agent_id,
                        "merchant_id": merchant_id,
                        "amount": "10.00",
                        "currency": "USDC",
                        "purpose": f"Payment {i+1}"
                    }
                )
            
            # Get transaction history
            history_response = await client.get(
                f"/api/v1/payments/agent/{agent_id}?limit=10"
            )
            
            assert history_response.status_code == 200
            transactions = history_response.json()
            
            # Should be 4 transactions (1 funding + 3 payments)
            assert len(transactions) == 4
            
            # Verify the 3 payments are there
            payments = [tx for tx in transactions if tx["purpose"].startswith("Payment")]
            assert len(payments) == 3
            for tx in payments:
                assert tx["amount"] == "10.00"
                assert tx["status"] == "completed"


class TestWebhookIntegration:
    """Test webhook subscription and event flow."""
    
    @pytest.mark.asyncio
    async def test_webhook_subscription_crud(self):
        """Test webhook CRUD operations."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create webhook
            create_response = await client.post(
                "/api/v1/webhooks",
                json={
                    "url": "https://example.com/webhook",
                    "events": ["payment.completed", "payment.failed"]
                }
            )
            
            assert create_response.status_code == 201
            webhook_data = create_response.json()
            assert webhook_data["url"] == "https://example.com/webhook"
            assert "secret" in webhook_data
            
            subscription_id = webhook_data["subscription_id"]
            
            # Get webhook
            get_response = await client.get(f"/api/v1/webhooks/{subscription_id}")
            assert get_response.status_code == 200
            assert get_response.json()["subscription_id"] == subscription_id
            
            # Update webhook
            update_response = await client.patch(
                f"/api/v1/webhooks/{subscription_id}",
                json={"is_active": False}
            )
            assert update_response.status_code == 200
            assert update_response.json()["is_active"] is False
            
            # Delete webhook
            delete_response = await client.delete(f"/api/v1/webhooks/{subscription_id}")
            assert delete_response.status_code == 204
            
            # Verify deleted
            get_after_delete = await client.get(f"/api/v1/webhooks/{subscription_id}")
            assert get_after_delete.status_code == 404


class TestRiskIntegration:
    """Test risk scoring API integration."""
    
    @pytest.mark.asyncio
    async def test_risk_score_for_agent(self):
        """Test getting risk score for an agent."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create agent
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "risk_test_agent",
                    "owner_id": "dev_risk",
                    "initial_balance": "100.00",
                    "limit_per_tx": "50.00",
                    "limit_total": "100.00"
                }
            )
            agent_id = agent_response.json()["agent"]["agent_id"]
            
            # Get risk score
            risk_response = await client.get(f"/api/v1/risk/agents/{agent_id}/score")
            
            assert risk_response.status_code == 200
            risk_data = risk_response.json()
            
            assert "score" in risk_data
            assert "level" in risk_data
            assert "is_acceptable" in risk_data
    
    @pytest.mark.asyncio
    async def test_service_authorization(self):
        """Test authorizing and revoking services."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Create agent
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "auth_test_agent",
                    "owner_id": "dev_auth",
                    "initial_balance": "100.00"
                }
            )
            agent_id = agent_response.json()["agent"]["agent_id"]
            
            # Authorize a service
            auth_response = await client.post(
                f"/api/v1/risk/agents/{agent_id}/authorize",
                json={"service_id": "trusted_merchant_1"}
            )
            
            assert auth_response.status_code == 200
            assert "trusted_merchant_1" in auth_response.json()["services"]
            
            # List authorized services
            list_response = await client.get(
                f"/api/v1/risk/agents/{agent_id}/authorized-services"
            )
            assert "trusted_merchant_1" in list_response.json()["services"]
            
            # Revoke service
            revoke_response = await client.delete(
                f"/api/v1/risk/agents/{agent_id}/authorize/trusted_merchant_1"
            )
            assert revoke_response.status_code == 200
            assert "trusted_merchant_1" not in revoke_response.json()["services"]


class TestCatalogAndPurchase:
    """Test browsing catalog and making purchases."""
    
    @pytest.mark.asyncio
    async def test_browse_and_purchase_product(self):
        """Test browsing catalog and purchasing a product."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create agent
            agent_response = await client.post(
                "/api/v1/agents",
                json={
                    "name": "shopper_agent",
                    "owner_id": "dev_shop",
                    "initial_balance": "100.00",
                    "limit_per_tx": "50.00",
                    "limit_total": "100.00"
                }
            )
            agent_id = agent_response.json()["agent"]["agent_id"]
            
            # 1.5 Register a merchant for the catalog to find
            await client.post(
                "/api/v1/merchants",
                json={
                    "name": "Catalog Merchant",
                    "description": "For catalog testing",
                    "category": "electronics"
                }
            )
            
            # 2. Browse products
            catalog_response = await client.get(
                "/api/v1/catalog/products?max_price=50&in_stock_only=true"
            )
            
            assert catalog_response.status_code == 200
            products = catalog_response.json()
            assert len(products) > 0
            
            # 3. Get a specific product
            product = products[0]
            product_id = product["product_id"]
            merchant_id = product["merchant_id"]
            price = Decimal(product["price"])
            
            # 4. Purchase the product
            payment_response = await client.post(
                "/api/v1/payments",
                json={
                    "agent_id": agent_id,
                    "merchant_id": merchant_id,
                    "amount": str(price),
                    "currency": "USDC",
                    "purpose": f"Purchase: {product['name']}"
                }
            )
            
            assert payment_response.status_code == 200, f"Payment failed: {payment_response.json()}"
            payment_data = payment_response.json()
            assert payment_data["success"] is True
            
            # 5. Verify balance reduced
            merchant_wallet_response = await client.get(f"/api/v1/merchants/{merchant_id}/wallet")
            merchant_wallet = merchant_wallet_response.json()
            assert Decimal(merchant_wallet["balance"]) == Decimal("25.10") # Assuming merchant starts at 0 and receives full price
            
            wallet_response = await client.get(f"/api/v1/agents/{agent_id}/wallet")
            new_balance = Decimal(wallet_response.json()["balance"])
            expected = Decimal("100.00") - price - Decimal("0.10")  # Including fee
            assert new_balance == expected


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_health(self):
        """Test root endpoint returns health status."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "Sardis" in data["service"]
    
    @pytest.mark.asyncio
    async def test_detailed_health(self):
        """Test detailed health endpoint."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "components" in data
            assert data["components"]["api"] == "up"


class TestPaymentEstimation:
    """Test payment estimation functionality."""
    
    @pytest.mark.asyncio
    async def test_estimate_payment(self):
        """Test payment cost estimation."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/payments/estimate?amount=50.00&currency=USDC"
            )
            
            assert response.status_code == 200
            data = response.json()
            
            assert Decimal(data["amount"]) == Decimal("50.00")
            assert Decimal(data["fee"]) == Decimal("0.10")
            assert Decimal(data["total"]) == Decimal("50.10")
            assert data["currency"] == "USDC"

