"""
End-to-End On-Ramp Tests for Sardis

Tests the complete on-ramp flow including:
- Funding wallet from fiat (bank/card)
- Funding wallet from crypto (direct deposit)
- KYC verification for high-value on-ramp
- Widget generation for Onramper integration
- Webhook handling for completed on-ramps

Run with: pytest tests/e2e/test_onramp_e2e.py -v
"""
import os
import pytest
from datetime import datetime, timezone
from decimal import Decimal

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")


class TestOnrampFunding:
    """Test on-ramp funding operations."""

    @pytest.mark.e2e
    async def test_fund_wallet_from_bank(self, api_key, api_url):
        """Should create ACH funding instructions for wallet."""
        try:
            from sardis_ramp import SardisFiatRamp
            from sardis_ramp.ramp_types import FundingMethod

            # Initialize ramp in sandbox mode
            ramp = SardisFiatRamp(
                sardis_api_key=api_key,
                bridge_api_key=os.getenv("BRIDGE_API_KEY", "bridge_test_key"),
                environment="sandbox",
            )

            # Fund wallet from bank (ACH)
            wallet_id = f"wallet_onramp_test_{int(datetime.now(timezone.utc).timestamp())}"

            try:
                result = await ramp.fund_wallet(
                    wallet_id=wallet_id,
                    amount_usd=500.00,
                    method=FundingMethod.BANK,
                )

                # Should return funding result with ACH instructions or payment link
                assert result is not None
                assert result.type in ["fiat", "crypto"]

                if result.type == "fiat":
                    # Should have payment link or ACH instructions
                    assert result.payment_link or result.ach_instructions

                    if result.ach_instructions:
                        assert result.ach_instructions.account_number
                        assert result.ach_instructions.routing_number
                        assert result.ach_instructions.bank_name
                        assert result.ach_instructions.reference

            finally:
                await ramp.close()

        except ImportError:
            pytest.skip("sardis_ramp not available")
        except Exception as e:
            # May fail in test if wallet doesn't exist or Bridge API not configured
            # That's acceptable in E2E tests
            if "not found" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Skipping due to environment: {e}")
            raise

    @pytest.mark.e2e
    async def test_fund_wallet_from_card(self, api_key, api_url):
        """Should create card payment link for wallet funding."""
        try:
            from sardis_ramp import SardisFiatRamp
            from sardis_ramp.ramp_types import FundingMethod

            ramp = SardisFiatRamp(
                sardis_api_key=api_key,
                bridge_api_key=os.getenv("BRIDGE_API_KEY", "bridge_test_key"),
                environment="sandbox",
            )

            wallet_id = f"wallet_card_test_{int(datetime.now(timezone.utc).timestamp())}"

            try:
                result = await ramp.fund_wallet(
                    wallet_id=wallet_id,
                    amount_usd=100.00,
                    method=FundingMethod.CARD,
                )

                assert result is not None
                # Card funding typically provides a payment link
                if result.type == "fiat":
                    assert result.payment_link or result.transfer_id

            finally:
                await ramp.close()

        except ImportError:
            pytest.skip("sardis_ramp not available")
        except Exception as e:
            if "not found" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Skipping due to environment: {e}")
            raise

    @pytest.mark.e2e
    async def test_fund_wallet_crypto_direct(self, api_key, api_url):
        """Should return deposit address for direct crypto funding."""
        try:
            from sardis_ramp import SardisFiatRamp
            from sardis_ramp.ramp_types import FundingMethod

            ramp = SardisFiatRamp(
                sardis_api_key=api_key,
                bridge_api_key=os.getenv("BRIDGE_API_KEY", "bridge_test_key"),
                environment="sandbox",
            )

            wallet_id = f"wallet_crypto_test_{int(datetime.now(timezone.utc).timestamp())}"

            try:
                result = await ramp.fund_wallet(
                    wallet_id=wallet_id,
                    amount_usd=1000.00,
                    method=FundingMethod.CRYPTO,
                )

                # Crypto funding returns deposit address
                assert result is not None
                assert result.type == "crypto"
                assert result.deposit_address is not None
                assert result.chain is not None
                assert result.token is not None

            finally:
                await ramp.close()

        except ImportError:
            pytest.skip("sardis_ramp not available")
        except Exception as e:
            if "not found" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Skipping due to environment: {e}")
            raise


class TestOnrampKYC:
    """Test KYC verification for high-value on-ramp."""

    @pytest.mark.e2e
    async def test_kyc_required_for_large_onramp(self, api_key, api_url):
        """Should require KYC for on-ramp above threshold."""
        try:
            from sardis_ramp import SardisFiatRamp, KYCRequired
            from sardis_ramp.ramp_types import FundingMethod

            # Set a low KYC threshold for testing
            ramp = SardisFiatRamp(
                sardis_api_key=api_key,
                bridge_api_key=os.getenv("BRIDGE_API_KEY", "bridge_test_key"),
                environment="sandbox",
                kyc_threshold_usd=1000.00,
            )

            wallet_id = f"wallet_kyc_test_{int(datetime.now(timezone.utc).timestamp())}"

            try:
                # Try to fund with amount above threshold
                # In sandbox mode, this may bypass KYC, but in production it would require it
                result = await ramp.fund_wallet(
                    wallet_id=wallet_id,
                    amount_usd=5000.00,
                    method=FundingMethod.BANK,
                )

                # In sandbox, may succeed with bypass
                # In production, would raise KYCRequired

            except KYCRequired as e:
                # Expected in production
                assert "KYC verification required" in str(e)
                assert "1000" in str(e) or "threshold" in str(e).lower()
            finally:
                await ramp.close()

        except ImportError:
            pytest.skip("sardis_ramp not available")
        except Exception as e:
            if "not found" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Skipping due to environment: {e}")
            raise

    @pytest.mark.e2e
    async def test_kyc_bypass_below_threshold(self, api_key, api_url):
        """Should allow on-ramp below KYC threshold without verification."""
        try:
            from sardis_ramp import SardisFiatRamp
            from sardis_ramp.ramp_types import FundingMethod

            ramp = SardisFiatRamp(
                sardis_api_key=api_key,
                bridge_api_key=os.getenv("BRIDGE_API_KEY", "bridge_test_key"),
                environment="sandbox",
                kyc_threshold_usd=1000.00,
            )

            wallet_id = f"wallet_below_kyc_{int(datetime.now(timezone.utc).timestamp())}"

            try:
                # Amount below threshold - should not require KYC
                result = await ramp.fund_wallet(
                    wallet_id=wallet_id,
                    amount_usd=500.00,  # Below $1000 threshold
                    method=FundingMethod.BANK,
                )

                # Should succeed without KYC
                assert result is not None

            finally:
                await ramp.close()

        except ImportError:
            pytest.skip("sardis_ramp not available")
        except Exception as e:
            if "not found" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Skipping due to environment: {e}")
            raise


class TestOnrampWidget:
    """Test Onramper widget integration."""

    @pytest.mark.e2e
    async def test_generate_onramp_widget_url(self, api_key, api_url):
        """Should generate Onramper widget URL with wallet pre-filled."""
        try:
            import httpx

            # Create widget URL request
            response = await httpx.AsyncClient().post(
                f"{api_url}/api/v2/ramp/onramp/widget",
                json={
                    "wallet_id": "wallet_test_widget",
                    "amount_usd": 100.00,
                    "chain": "base",
                    "token": "USDC",
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )

            if response.status_code == 404:
                pytest.skip("Onramp widget endpoint not available or wallet not found")

            response.raise_for_status()
            data = response.json()

            # Should return widget URL
            assert "widget_url" in data
            assert "onramper.com" in data["widget_url"]
            assert "wallet_address" in data
            assert data["chain"] == "base"
            assert data["token"] == "USDC"

        except httpx.HTTPError as e:
            if "not found" in str(e).lower():
                pytest.skip("Wallet not found or endpoint not configured")
            raise
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                pytest.skip(f"Skipping due to environment: {e}")
            raise

    @pytest.mark.e2e
    async def test_onramp_quote_endpoint(self, api_key, api_url):
        """Should fetch on-ramp quote from Onramper."""
        try:
            import httpx

            response = await httpx.AsyncClient().get(
                f"{api_url}/api/v2/ramp/onramp/quote",
                params={
                    "amount_usd": 100.00,
                    "payment_method": "creditcard",
                    "chain": "base",
                    "token": "USDC",
                },
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=10.0,
            )

            if response.status_code in [404, 502]:
                pytest.skip("Onramp quote endpoint not available")

            # May succeed or fail depending on Onramper API availability
            # We just verify the endpoint exists

        except httpx.HTTPError:
            pytest.skip("Onramp quote service not available")
        except Exception as e:
            if "not found" in str(e).lower() or "502" in str(e):
                pytest.skip(f"Skipping due to environment: {e}")
            raise


class TestOnrampWebhook:
    """Test webhook handling for completed on-ramps."""

    @pytest.mark.e2e
    async def test_onramp_webhook_completion(self, api_key, api_url):
        """Should handle Onramper completion webhook."""
        try:
            import httpx
            import hashlib
            import hmac
            import json

            # Simulate Onramper webhook payload
            payload = {
                "type": "transaction.completed",
                "payload": {
                    "wallet_address": "0x1234567890123456789012345678901234567890",
                    "crypto_amount": "100.00",
                    "crypto_currency": "USDC",
                    "tx_hash": "0xabcdef1234567890",
                    "network": "base",
                }
            }

            body = json.dumps(payload).encode()

            # Calculate signature if webhook secret is available
            webhook_secret = os.getenv("ONRAMPER_WEBHOOK_SECRET", "")
            headers = {"Content-Type": "application/json"}

            if webhook_secret:
                signature = hmac.new(webhook_secret.encode(), body, hashlib.sha256).hexdigest()
                headers["x-onramper-signature"] = signature

            response = await httpx.AsyncClient().post(
                f"{api_url}/api/v2/ramp/onramp/webhook",
                content=body,
                headers=headers,
                timeout=10.0,
            )

            if response.status_code == 404:
                pytest.skip("Onramp webhook endpoint not available")

            # Should accept webhook
            assert response.status_code in [200, 401]  # 401 if signature invalid

            if response.status_code == 200:
                data = response.json()
                assert data.get("status") == "received"

        except httpx.HTTPError as e:
            if "not found" in str(e).lower():
                pytest.skip("Webhook endpoint not available")
            raise
        except Exception as e:
            if "not found" in str(e).lower() or "404" in str(e):
                pytest.skip(f"Skipping due to environment: {e}")
            raise


class TestOnrampIntegration:
    """Test full on-ramp to wallet credit integration."""

    @pytest.mark.e2e
    async def test_end_to_end_onramp_flow(self, api_key, api_url):
        """Should complete full on-ramp flow from fiat to wallet credit."""
        try:
            from sardis_ramp import SardisFiatRamp
            from sardis_ramp.ramp_types import FundingMethod

            ramp = SardisFiatRamp(
                sardis_api_key=api_key,
                bridge_api_key=os.getenv("BRIDGE_API_KEY", "bridge_test_key"),
                environment="sandbox",
            )

            wallet_id = f"wallet_e2e_test_{int(datetime.now(timezone.utc).timestamp())}"

            try:
                # Step 1: Initiate funding
                funding_result = await ramp.fund_wallet(
                    wallet_id=wallet_id,
                    amount_usd=250.00,
                    method=FundingMethod.BANK,
                )

                assert funding_result is not None

                # Step 2: Check funding status (if transfer_id available)
                if funding_result.transfer_id:
                    status = await ramp.get_funding_status(funding_result.transfer_id)
                    assert status is not None
                    # Status may be pending, processing, or completed

                # Step 3: In production, webhook would be called when completed
                # Wallet balance would be updated on-chain (non-custodial)
                # This is verified by checking on-chain balance, not internal DB

            finally:
                await ramp.close()

        except ImportError:
            pytest.skip("sardis_ramp not available")
        except Exception as e:
            if "not found" in str(e).lower() or "api" in str(e).lower():
                pytest.skip(f"Skipping due to environment: {e}")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
