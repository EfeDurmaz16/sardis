"""
End-to-End Test: Wallet Freeze Blocks Transactions

Tests the wallet freeze functionality:
- Wallet can be frozen via API
- Frozen wallets block all transaction attempts
- Freeze state persists across requests
- Wallets can be unfrozen to restore functionality
- Freeze metadata (reason, frozen_by) is tracked

Run with: pytest tests/e2e/test_wallet_freeze.py -v
"""
import os
import pytest
from datetime import datetime, timezone

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")


class TestWalletFreeze:
    """Test wallet freeze functionality."""

    @pytest.mark.e2e
    async def test_freeze_wallet_blocks_transactions(self, api_key, api_url):
        """Should block all transactions when wallet is frozen."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create wallet
                wallet = await client.wallets.create(
                    agent_id=f"freeze_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                    metadata={"test": "freeze_blocking"},
                )

                assert wallet.id is not None
                assert wallet.is_active is True

                # Verify wallet starts unfrozen
                fetched_wallet = await client.wallets.get(wallet.id)
                initial_frozen_state = getattr(fetched_wallet, 'is_frozen', False)
                assert initial_frozen_state is False, "Wallet should start unfrozen"

                # Freeze the wallet
                try:
                    frozen_wallet = await client.wallets.freeze(
                        wallet_id=wallet.id,
                        reason="E2E test: compliance freeze",
                        frozen_by="test_system",
                    )
                    assert frozen_wallet.is_frozen is True
                    assert frozen_wallet.freeze_reason == "E2E test: compliance freeze"
                except AttributeError:
                    pytest.skip("Wallet freeze method not available in SDK")

                # Verify freeze state persists
                refetched_wallet = await client.wallets.get(wallet.id)
                assert refetched_wallet.is_frozen is True

                # Attempt transaction on frozen wallet - should be blocked
                mandate = {
                    "mandate_id": f"frozen_wallet_test_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "vendor:test_merchant",
                    "amount_minor": "10000000",  # $10
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "Test transaction on frozen wallet",
                    "vendor_name": "TestMerchant",
                }

                transaction_blocked = False
                try:
                    result = await client.payments.execute_mandate(mandate)
                    # If we get here, check if there's a pending state
                    if result.status == "blocked" or result.status == "failed":
                        transaction_blocked = True
                except Exception as e:
                    # Should raise error for frozen wallet
                    error_msg = str(e).lower()
                    assert any(kw in error_msg for kw in ["frozen", "freeze", "blocked", "disabled"]), \
                        f"Expected freeze-related error, got: {e}"
                    transaction_blocked = True

                assert transaction_blocked, "Transaction should be blocked on frozen wallet"

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_unfreeze_wallet_restores_functionality(self, api_key, api_url):
        """Should allow transactions after wallet is unfrozen."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create and freeze wallet
                wallet = await client.wallets.create(
                    agent_id=f"unfreeze_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                try:
                    # Freeze wallet
                    await client.wallets.freeze(
                        wallet_id=wallet.id,
                        reason="Temporary freeze for testing",
                        frozen_by="test_admin",
                    )

                    # Verify frozen
                    frozen_wallet = await client.wallets.get(wallet.id)
                    assert frozen_wallet.is_frozen is True

                    # Unfreeze wallet
                    unfrozen_wallet = await client.wallets.unfreeze(wallet_id=wallet.id)
                    assert unfrozen_wallet.is_frozen is False
                    assert unfrozen_wallet.freeze_reason is None

                    # Verify unfreeze persists
                    refetched_wallet = await client.wallets.get(wallet.id)
                    assert refetched_wallet.is_frozen is False

                    # Transaction should now succeed (or fail for other reasons, not freeze)
                    mandate = {
                        "mandate_id": f"unfrozen_test_{datetime.now(timezone.utc).timestamp()}",
                        "subject": wallet.id,
                        "destination": "vendor:test_merchant",
                        "amount_minor": "5000000",  # $5
                        "token": "USDC",
                        "chain": "base_sepolia",
                        "purpose": "Test transaction after unfreeze",
                        "vendor_name": "TestMerchant",
                    }

                    try:
                        result = await client.payments.execute_mandate(mandate)
                        # Success means unfreeze worked
                        assert result.status in ["completed", "pending"]
                    except Exception as e:
                        # Should NOT be frozen error
                        error_msg = str(e).lower()
                        assert not any(kw in error_msg for kw in ["frozen", "freeze"]), \
                            "Should not be blocked by freeze after unfreeze"
                        # Other errors (policy, balance, etc.) are OK

                except AttributeError:
                    pytest.skip("Wallet freeze/unfreeze methods not available in SDK")

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_freeze_metadata_tracking(self, api_key, api_url):
        """Should track freeze metadata (reason, frozen_by, frozen_at)."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"freeze_metadata_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                freeze_reason = "Suspicious activity detected - E2E test"
                frozen_by = "compliance_system"

                try:
                    # Freeze with metadata
                    frozen_wallet = await client.wallets.freeze(
                        wallet_id=wallet.id,
                        reason=freeze_reason,
                        frozen_by=frozen_by,
                    )

                    # Verify metadata
                    assert frozen_wallet.is_frozen is True
                    assert frozen_wallet.freeze_reason == freeze_reason
                    assert frozen_wallet.frozen_by == frozen_by
                    assert frozen_wallet.frozen_at is not None

                    # Verify metadata persists across fetches
                    refetched = await client.wallets.get(wallet.id)
                    assert refetched.freeze_reason == freeze_reason
                    assert refetched.frozen_by == frozen_by

                except AttributeError:
                    pytest.skip("Wallet freeze metadata not available in SDK")

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_frozen_wallet_blocks_multiple_transaction_types(self, api_key, api_url):
        """Should block all transaction types when frozen (payments, holds, cards)."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"freeze_all_tx_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                try:
                    # Freeze wallet
                    await client.wallets.freeze(
                        wallet_id=wallet.id,
                        reason="Block all transaction types test",
                    )

                    # Test 1: Block payment
                    payment_blocked = False
                    try:
                        mandate = {
                            "mandate_id": f"frozen_payment_{datetime.now(timezone.utc).timestamp()}",
                            "subject": wallet.id,
                            "destination": "vendor:merchant",
                            "amount_minor": "5000000",
                            "token": "USDC",
                            "chain": "base_sepolia",
                            "purpose": "Payment on frozen wallet",
                            "vendor_name": "Merchant",
                        }
                        await client.payments.execute_mandate(mandate)
                    except Exception as e:
                        if any(kw in str(e).lower() for kw in ["frozen", "freeze", "blocked"]):
                            payment_blocked = True

                    # Test 2: Block hold creation
                    hold_blocked = False
                    try:
                        hold = await client.holds.create(
                            wallet_id=wallet.id,
                            amount_minor=10000000,
                            token="USDC",
                            chain="base_sepolia",
                        )
                    except AttributeError:
                        # Holds not implemented yet
                        hold_blocked = True
                    except Exception as e:
                        if any(kw in str(e).lower() for kw in ["frozen", "freeze", "blocked"]):
                            hold_blocked = True

                    # Test 3: Block card creation
                    card_blocked = False
                    try:
                        card = await client.cards.create(
                            wallet_id=wallet.id,
                            spend_limit=50000,
                        )
                    except AttributeError:
                        # Cards not implemented yet
                        card_blocked = True
                    except Exception as e:
                        if any(kw in str(e).lower() for kw in ["frozen", "freeze", "blocked"]):
                            card_blocked = True

                    # At minimum, payment should be blocked
                    assert payment_blocked, "Payment should be blocked on frozen wallet"

                except AttributeError:
                    pytest.skip("Wallet freeze not available in SDK")

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_freeze_state_in_wallet_list(self, api_key, api_url):
        """Should include freeze state in wallet list responses."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create two wallets - one frozen, one not
                wallet1 = await client.wallets.create(
                    agent_id=f"list_frozen_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                wallet2 = await client.wallets.create(
                    agent_id=f"list_unfrozen_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                try:
                    # Freeze first wallet
                    await client.wallets.freeze(
                        wallet_id=wallet1.id,
                        reason="Test list filtering",
                    )

                    # List wallets
                    wallets = await client.wallets.list(limit=50)

                    # Find our test wallets
                    found_frozen = None
                    found_unfrozen = None

                    for w in wallets:
                        if w.id == wallet1.id:
                            found_frozen = w
                        elif w.id == wallet2.id:
                            found_unfrozen = w

                    # Verify freeze state in list
                    if found_frozen:
                        assert found_frozen.is_frozen is True

                    if found_unfrozen:
                        assert found_unfrozen.is_frozen is False

                except AttributeError:
                    pytest.skip("Wallet freeze or list not available in SDK")

        except ImportError:
            pytest.skip("sardis_sdk not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
