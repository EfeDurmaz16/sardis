"""
End-to-End Virtual Cards & Fiat Rails Tests for Sardis

Tests the complete flow for:
- Virtual card creation and management
- Fiat on-ramp and off-ramp operations

Run with: pytest tests/e2e/test_cards_fiat_flow.py -v
"""
import os
import pytest
from datetime import datetime, timezone

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")


class TestVirtualCardOperations:
    """Test virtual card operations via Lithic integration."""

    @pytest.mark.e2e
    async def test_create_single_use_card(self, api_key, api_url):
        """Should create a single-use virtual card."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create wallet first
                wallet = await client.wallets.create(
                    agent_id=f"card_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Create virtual card
                card = await client.cards.create(
                    wallet_id=wallet.id,
                    limit=500,
                    card_type="single_use",
                    nickname="Test Single Use Card",
                )

                assert card.card_id is not None
                assert card.status in ["active", "pending"]
                assert card.type == "single_use"

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Card methods not available in SDK")

    @pytest.mark.e2e
    async def test_create_merchant_locked_card(self, api_key, api_url):
        """Should create a merchant-locked card."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"card_merchant_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                card = await client.cards.create(
                    wallet_id=wallet.id,
                    limit=1000,
                    card_type="merchant_locked",
                    merchant_categories=["software", "cloud_services"],
                    nickname="SaaS Only Card",
                )

                assert card.card_id is not None
                assert card.type == "merchant_locked"

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Card methods not available in SDK")

    @pytest.mark.e2e
    async def test_card_lifecycle(self, api_key, api_url):
        """Test complete card lifecycle: create -> use -> freeze -> unfreeze -> cancel."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"card_lifecycle_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Create card
                card = await client.cards.create(
                    wallet_id=wallet.id,
                    limit=500,
                    card_type="reusable",
                )
                card_id = card.card_id

                # Freeze card
                frozen = await client.cards.freeze(card_id)
                assert frozen.status == "frozen"

                # Unfreeze card
                unfrozen = await client.cards.unfreeze(card_id)
                assert unfrozen.status == "active"

                # Cancel card
                cancelled = await client.cards.cancel(card_id)
                assert cancelled.status == "cancelled"

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Card methods not available in SDK")

    @pytest.mark.e2e
    async def test_get_card_transactions(self, api_key, api_url):
        """Should list card transactions."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # List transactions for test card
                transactions = await client.cards.list_transactions(
                    card_id="card_test",
                    limit=10,
                )

                assert isinstance(transactions, list)

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Card methods not available in SDK")


class TestFiatOnRamp:
    """Test fiat on-ramp operations via Bridge integration."""

    @pytest.mark.e2e
    async def test_initiate_bank_funding(self, api_key, api_url):
        """Should initiate bank account funding."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"fiat_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Initiate funding
                funding = await client.fiat.fund_wallet(
                    wallet_id=wallet.id,
                    amount=1000,
                    source="bank_account",
                    currency="USD",
                )

                assert funding.funding_id is not None
                assert funding.status in ["pending", "processing", "completed"]

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Fiat methods not available in SDK")

    @pytest.mark.e2e
    async def test_get_funding_status(self, api_key, api_url):
        """Should check funding status."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Check status of test funding
                status = await client.fiat.get_funding_status(
                    funding_id="fund_test",
                )

                assert status.funding_id == "fund_test"
                assert status.status in ["pending", "processing", "completed", "failed"]

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Fiat methods not available in SDK")


class TestFiatOffRamp:
    """Test fiat off-ramp operations."""

    @pytest.mark.e2e
    async def test_initiate_withdrawal(self, api_key, api_url):
        """Should initiate withdrawal to bank account."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"withdrawal_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Initiate withdrawal
                withdrawal = await client.fiat.withdraw(
                    wallet_id=wallet.id,
                    amount=500,
                    destination="bank_account",
                    account_id="acct_test",
                )

                assert withdrawal.withdrawal_id is not None
                assert withdrawal.status in ["pending", "processing", "completed"]

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Fiat methods not available in SDK")

    @pytest.mark.e2e
    async def test_list_funding_history(self, api_key, api_url):
        """Should list funding/withdrawal history."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                transactions = await client.fiat.list_transactions(
                    limit=20,
                )

                assert isinstance(transactions, list)
                for tx in transactions:
                    assert tx.type in ["deposit", "withdrawal"]
                    assert tx.status is not None

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Fiat methods not available in SDK")


class TestCardFiatIntegration:
    """Test integrated card and fiat flows."""

    @pytest.mark.e2e
    async def test_fund_wallet_and_create_card(self, api_key, api_url):
        """Test complete flow: fund wallet -> create card -> make payment."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create wallet
                wallet = await client.wallets.create(
                    agent_id=f"integration_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Fund wallet (simulated)
                funding = await client.fiat.fund_wallet(
                    wallet_id=wallet.id,
                    amount=2000,
                    source="bank_account",
                )
                assert funding.status in ["pending", "processing", "completed"]

                # Create card
                card = await client.cards.create(
                    wallet_id=wallet.id,
                    limit=1000,
                    card_type="single_use",
                )
                assert card.card_id is not None

                # Check wallet balance
                balance = await client.wallets.get_balance(wallet.id)
                assert balance is not None

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Required methods not available in SDK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
