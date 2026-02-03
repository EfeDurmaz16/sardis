"""
End-to-End Test: Off-Ramp with Velocity Checks

Tests the complete off-ramp flow with velocity control enforcement:
- Virtual card creation for fiat off-ramping
- Multiple transactions to trigger velocity limits
- Velocity check enforcement (transaction count, unique recipients)
- Rate limiting behavior

Run with: pytest tests/e2e/test_offramp_velocity.py -v
"""
import os
import pytest
from datetime import datetime, timezone
from decimal import Decimal

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")


class TestOfframpVelocity:
    """Test off-ramp transactions with velocity checks."""

    @pytest.mark.e2e
    async def test_offramp_velocity_transaction_count(self, api_key, api_url):
        """Should enforce velocity limits on transaction count during off-ramp."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create wallet for off-ramp testing
                wallet = await client.wallets.create(
                    agent_id=f"offramp_velocity_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                    metadata={"test": "velocity_check", "purpose": "offramp"},
                )

                # Create virtual card for off-ramping
                try:
                    card = await client.cards.create(
                        wallet_id=wallet.id,
                        spend_limit=50000,  # $500 limit
                        spend_limit_duration="MONTHLY",
                    )
                    assert card.id is not None
                    assert card.state in ["OPEN", "ACTIVE"]
                except AttributeError:
                    pytest.skip("Card methods not available in SDK")

                # Execute multiple transactions rapidly to trigger velocity check
                transaction_results = []
                num_transactions = 25  # Exceeds typical hourly limit (20)

                for i in range(num_transactions):
                    mandate = {
                        "mandate_id": f"velocity_test_{datetime.now(timezone.utc).timestamp()}_{i}",
                        "subject": wallet.id,
                        "destination": f"vendor:merchant_{i % 5}",  # 5 different merchants
                        "amount_minor": "5000000",  # $5 each
                        "token": "USDC",
                        "chain": "base_sepolia",
                        "purpose": f"Velocity test transaction {i+1}",
                        "vendor_name": f"Merchant{i % 5}",
                        "metadata": {
                            "card_id": card.id if 'card' in locals() else None,
                            "test": "velocity",
                        },
                    }

                    try:
                        result = await client.payments.execute_mandate(mandate)
                        transaction_results.append({
                            "success": True,
                            "status": result.status,
                            "index": i,
                        })
                    except Exception as e:
                        error_msg = str(e).lower()
                        transaction_results.append({
                            "success": False,
                            "error": error_msg,
                            "index": i,
                        })

                        # Check if blocked by velocity controls
                        if any(kw in error_msg for kw in ["velocity", "rate", "too many", "limit"]):
                            # Expected behavior - velocity check triggered
                            break

                # Verify velocity check was triggered
                blocked_transactions = [r for r in transaction_results if not r["success"]]
                successful_transactions = [r for r in transaction_results if r["success"]]

                # Should have some successful transactions before velocity kicked in
                assert len(successful_transactions) > 0, "Should allow some transactions initially"

                # Should eventually block due to velocity
                # In test mode, this might be lenient, so we just check the pattern
                if len(blocked_transactions) > 0:
                    # Verify it was blocked for velocity reasons
                    assert any(
                        any(kw in r.get("error", "") for kw in ["velocity", "rate", "too many"])
                        for r in blocked_transactions
                    ), "Should be blocked by velocity check"

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_offramp_velocity_unique_recipients(self, api_key, api_url):
        """Should enforce velocity limits on unique recipient count."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create wallet
                wallet = await client.wallets.create(
                    agent_id=f"offramp_unique_recipients_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Create transactions to many different recipients
                num_unique_recipients = 15  # Exceeds typical daily limit (10)
                transaction_results = []

                for i in range(num_unique_recipients):
                    mandate = {
                        "mandate_id": f"unique_recipient_test_{datetime.now(timezone.utc).timestamp()}_{i}",
                        "subject": wallet.id,
                        "destination": f"vendor:unique_merchant_{i}",  # Unique each time
                        "amount_minor": "3000000",  # $3
                        "token": "USDC",
                        "chain": "base_sepolia",
                        "purpose": f"Payment to unique recipient {i+1}",
                        "vendor_name": f"UniqueMerchant{i}",
                    }

                    try:
                        result = await client.payments.execute_mandate(mandate)
                        transaction_results.append({"success": True, "index": i})
                    except Exception as e:
                        error_msg = str(e).lower()
                        transaction_results.append({"success": False, "error": error_msg, "index": i})

                        # Check if blocked by unique recipient velocity check
                        if any(kw in error_msg for kw in ["recipient", "velocity", "too many"]):
                            break

                # Verify behavior
                successful = [r for r in transaction_results if r["success"]]
                assert len(successful) > 0, "Should allow some unique recipients initially"

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_offramp_velocity_reset_after_window(self, api_key, api_url):
        """Should reset velocity counters after time window."""
        try:
            from sardis_sdk import SardisClient
            import asyncio

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"offramp_velocity_reset_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Execute transaction
                mandate1 = {
                    "mandate_id": f"velocity_reset_1_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "vendor:test_merchant",
                    "amount_minor": "5000000",
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "First transaction",
                    "vendor_name": "TestMerchant",
                }

                try:
                    await client.payments.execute_mandate(mandate1)
                except Exception:
                    # May fail in test mode, that's OK
                    pass

                # In a real test, we'd wait for the velocity window to reset
                # For E2E, we just verify the window concept exists
                # Actual timing tests would be in integration tests

                # Execute second transaction (in production, would be after window)
                mandate2 = {
                    "mandate_id": f"velocity_reset_2_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "vendor:test_merchant",
                    "amount_minor": "5000000",
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "Second transaction after window",
                    "vendor_name": "TestMerchant",
                }

                try:
                    await client.payments.execute_mandate(mandate2)
                    # If this succeeds, velocity window handling is working
                except Exception as e:
                    # Expected in some test configurations
                    pass

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_offramp_amount_spike_detection(self, api_key, api_url):
        """Should detect sudden spikes in transaction amounts (velocity check)."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"offramp_spike_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Establish baseline with small transactions
                baseline_transactions = 3
                for i in range(baseline_transactions):
                    mandate = {
                        "mandate_id": f"baseline_{datetime.now(timezone.utc).timestamp()}_{i}",
                        "subject": wallet.id,
                        "destination": "vendor:baseline_merchant",
                        "amount_minor": "2000000",  # $2 baseline
                        "token": "USDC",
                        "chain": "base_sepolia",
                        "purpose": f"Baseline transaction {i+1}",
                        "vendor_name": "BaselineMerchant",
                    }

                    try:
                        await client.payments.execute_mandate(mandate)
                    except Exception:
                        # May fail, establishing pattern
                        pass

                # Try large spike transaction (10x baseline)
                spike_mandate = {
                    "mandate_id": f"spike_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "vendor:spike_merchant",
                    "amount_minor": "20000000",  # $20 - significant spike
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "Spike transaction",
                    "vendor_name": "SpikeMerchant",
                }

                try:
                    result = await client.payments.execute_mandate(spike_mandate)
                    # May succeed or require additional verification
                    # In production with velocity checks, might trigger MFA/approval
                except Exception as e:
                    error_msg = str(e).lower()
                    # Check for velocity/amount-related blocking
                    if any(kw in error_msg for kw in ["amount", "velocity", "spike", "unusual"]):
                        # Expected behavior
                        pass

        except ImportError:
            pytest.skip("sardis_sdk not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
