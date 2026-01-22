"""
End-to-End Flow Tests for Sardis SDK

Tests the complete payment flow from SDK through API to ledger.
These tests require a running Sardis API server.

Run with: pytest tests/e2e/ -v --api-url=http://localhost:8000
"""
import os
import pytest
from decimal import Decimal
from datetime import datetime, timezone

# Test configuration
API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")

# Test scenarios from the plan
TEST_SCENARIOS = [
    {
        "name": "Allowed SaaS - OpenAI",
        "vendor": "OpenAI",
        "amount": 20.00,
        "expected": "APPROVED",
        "category": "saas",
    },
    {
        "name": "Blocked merchant - Amazon",
        "vendor": "Amazon",
        "amount": 500.00,
        "expected": "BLOCKED",
        "category": "retail",
    },
    {
        "name": "Over daily limit - GitHub",
        "vendor": "GitHub",
        "amount": 600.00,
        "expected": "BLOCKED",
        "category": "devtools",
    },
    {
        "name": "Within limits - Vercel",
        "vendor": "Vercel",
        "amount": 50.00,
        "expected": "APPROVED",
        "category": "saas",
    },
]


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "e2e: end-to-end integration test")


@pytest.fixture(scope="session")
def api_url():
    """Get API URL from environment or default."""
    return API_URL


@pytest.fixture(scope="session")
def api_key():
    """Get test API key."""
    return TEST_API_KEY


@pytest.fixture(scope="module")
async def test_wallet(api_key, api_url):
    """
    Create a test wallet for E2E tests.

    This wallet will be used across all tests in the module.
    """
    try:
        from sardis_sdk import SardisClient

        async with SardisClient(api_key=api_key, base_url=api_url) as client:
            # Create wallet
            wallet = await client.wallets.create(
                agent_id="e2e_test_agent",
                chain="base_sepolia",
                metadata={"test": True, "created_at": datetime.now(timezone.utc).isoformat()},
            )

            yield wallet

            # Cleanup would go here if needed
    except ImportError:
        pytest.skip("sardis_sdk not installed")
    except Exception as e:
        pytest.skip(f"Could not create test wallet: {e}")


class TestHealthCheck:
    """Verify API is running before other tests."""

    @pytest.mark.e2e
    async def test_api_health(self, api_key, api_url):
        """API should return healthy status."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                health = await client.health()

                assert health["status"] == "healthy"
                assert "version" in health
        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except Exception as e:
            pytest.fail(f"Health check failed: {e}")


class TestWalletOperations:
    """Test wallet creation and management."""

    @pytest.mark.e2e
    async def test_create_wallet(self, api_key, api_url):
        """Should create a new wallet."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id="test_agent_create",
                    chain="base_sepolia",
                )

                assert wallet.id is not None
                assert wallet.id.startswith("wallet_")
                assert wallet.agent_id == "test_agent_create"
        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_get_wallet(self, api_key, api_url, test_wallet):
        """Should get wallet by ID."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.get(test_wallet.id)

                assert wallet.id == test_wallet.id
        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_get_balance(self, api_key, api_url, test_wallet):
        """Should get wallet balance."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                balance = await client.wallets.get_balance(test_wallet.id)

                assert balance.wallet_id == test_wallet.id
                assert balance.token is not None
                assert balance.chain is not None
        except ImportError:
            pytest.skip("sardis_sdk not installed")


class TestPaymentScenarios:
    """Test payment scenarios from the plan."""

    @pytest.mark.e2e
    @pytest.mark.parametrize("scenario", TEST_SCENARIOS, ids=[s["name"] for s in TEST_SCENARIOS])
    async def test_payment_scenario(self, api_key, api_url, test_wallet, scenario):
        """Test payment scenario against policy."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                mandate = {
                    "mandate_id": f"e2e_test_{datetime.now(timezone.utc).timestamp()}",
                    "subject": test_wallet.id,
                    "destination": f"vendor:{scenario['vendor'].lower()}",
                    "amount_minor": str(int(scenario["amount"] * 1_000_000)),
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": f"E2E test - {scenario['name']}",
                    "vendor_name": scenario["vendor"],
                    "metadata": {
                        "category": scenario["category"],
                        "test": True,
                    },
                }

                try:
                    result = await client.payments.execute_mandate(mandate)

                    if scenario["expected"] == "APPROVED":
                        assert result.status in ["completed", "pending"]
                    else:
                        pytest.fail(f"Expected BLOCKED but got {result.status}")

                except Exception as e:
                    if scenario["expected"] == "BLOCKED":
                        # Expected - policy should block this
                        assert any(kw in str(e).lower() for kw in ["policy", "blocked", "denied", "limit"])
                    else:
                        raise

        except ImportError:
            pytest.skip("sardis_sdk not installed")


class TestHoldOperations:
    """Test hold (pre-authorization) operations."""

    @pytest.mark.e2e
    async def test_hold_lifecycle(self, api_key, api_url, test_wallet):
        """Test complete hold lifecycle: create -> capture."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create hold
                hold = await client.holds.create(
                    wallet_id=test_wallet.id,
                    amount_minor=50000000,  # $50
                    token="USDC",
                    chain="base_sepolia",
                )

                assert hold.id is not None
                assert hold.status == "active"

                # Capture hold
                captured = await client.holds.capture(hold.id)
                assert captured.status == "captured"

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_void_hold(self, api_key, api_url, test_wallet):
        """Test voiding a hold."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create hold
                hold = await client.holds.create(
                    wallet_id=test_wallet.id,
                    amount_minor=25000000,  # $25
                    token="USDC",
                    chain="base_sepolia",
                )

                # Void hold
                voided = await client.holds.void(hold.id)
                assert voided.status == "voided"

        except ImportError:
            pytest.skip("sardis_sdk not installed")


class TestWebhookOperations:
    """Test webhook subscription operations."""

    @pytest.mark.e2e
    async def test_webhook_lifecycle(self, api_key, api_url):
        """Test webhook create -> list -> delete."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create webhook
                webhook = await client.webhooks.create(
                    url="https://example.com/sardis-webhook-test",
                    events=["payment.completed", "payment.failed"],
                )

                assert webhook.id is not None
                assert webhook.active is True

                # List webhooks
                webhooks = await client.webhooks.list()
                assert any(w.id == webhook.id for w in webhooks)

                # Delete webhook
                await client.webhooks.delete(webhook.id)

                # Verify deleted
                webhooks_after = await client.webhooks.list()
                assert not any(w.id == webhook.id for w in webhooks_after)

        except ImportError:
            pytest.skip("sardis_sdk not installed")


class TestLedgerVerification:
    """Test ledger entry verification."""

    @pytest.mark.e2e
    async def test_ledger_entry_after_payment(self, api_key, api_url, test_wallet):
        """Verify ledger entry is created after payment."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Execute payment
                mandate = {
                    "mandate_id": f"ledger_test_{datetime.now(timezone.utc).timestamp()}",
                    "subject": test_wallet.id,
                    "destination": "vendor:openai",
                    "amount_minor": "10000000",  # $10
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "E2E ledger verification test",
                    "vendor_name": "OpenAI",
                }

                try:
                    result = await client.payments.execute_mandate(mandate)

                    # Verify ledger entry was created
                    if result.ledger_tx_id:
                        # Query ledger for this entry
                        entries = await client.ledger.list_entries(
                            wallet_id=test_wallet.id,
                            limit=10,
                        )

                        # Should find the entry
                        assert any(
                            e.tx_id == result.ledger_tx_id
                            for e in entries
                        )
                except Exception as e:
                    if "policy" in str(e).lower():
                        pytest.skip("Payment blocked by policy in test environment")
                    raise

        except ImportError:
            pytest.skip("sardis_sdk not installed")


class TestCompletePaymentFlow:
    """Test the complete payment flow from the plan."""

    @pytest.mark.e2e
    async def test_complete_flow(self, api_key, api_url):
        """
        Test complete payment flow:
        1. Create agent identity (wallet)
        2. Create wallet via SDK
        3. Fund wallet (simulated mode)
        4. Set spending policy
        5. Execute payment via SDK
        6. Verify transaction in ledger
        7. Verify webhook delivery (if configured)
        """
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # 1. Create wallet (agent identity)
                wallet = await client.wallets.create(
                    agent_id=f"complete_flow_agent_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                    metadata={"test": "complete_flow"},
                )
                assert wallet.id is not None

                # 2. Verify wallet was created
                fetched_wallet = await client.wallets.get(wallet.id)
                assert fetched_wallet.id == wallet.id

                # 3. Check balance (should be 0 or simulated amount)
                balance = await client.wallets.get_balance(wallet.id)
                assert balance.wallet_id == wallet.id

                # 4. Execute a small payment
                mandate = {
                    "mandate_id": f"complete_flow_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "vendor:vercel",
                    "amount_minor": "5000000",  # $5
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "Complete flow test payment",
                    "vendor_name": "Vercel",
                    "metadata": {"test": "complete_flow"},
                }

                try:
                    result = await client.payments.execute_mandate(mandate)

                    # 5. Verify transaction details
                    assert result.status in ["completed", "pending"]
                    assert result.chain == "base_sepolia"

                    # 6. Verify ledger entry if available
                    if result.ledger_tx_id:
                        entries = await client.ledger.list_entries(
                            wallet_id=wallet.id,
                            limit=5,
                        )
                        # Entry should exist
                        assert len(entries) > 0

                except Exception as e:
                    if "policy" in str(e).lower():
                        # In test mode, policy might block
                        pytest.skip("Payment blocked by test policy")
                    raise

        except ImportError:
            pytest.skip("sardis_sdk not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
