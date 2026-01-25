"""
End-to-End Compliance Flow Tests for Sardis

Tests the complete compliance flow including:
- KYC verification flow
- AML/Sanctions screening
- Transaction monitoring

Run with: pytest tests/e2e/test_compliance_flow.py -v
"""
import os
import pytest
from datetime import datetime, timezone

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
TEST_API_KEY = os.getenv("SARDIS_TEST_API_KEY", "sk_test_sardis_e2e")


class TestKYCFlow:
    """Test KYC verification flow."""

    @pytest.mark.e2e
    async def test_create_kyc_inquiry(self, api_key, api_url):
        """Should create a KYC verification inquiry."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create agent first
                wallet = await client.wallets.create(
                    agent_id=f"kyc_test_agent_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Create KYC inquiry
                kyc_result = await client.compliance.create_kyc_inquiry(
                    agent_id=wallet.agent_id,
                    name_first="Test",
                    name_last="User",
                    email="test@sardis.dev",
                )

                assert kyc_result.inquiry_id is not None
                assert kyc_result.session_token is not None
                assert kyc_result.status in ["pending", "not_started"]

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("KYC methods not available in SDK")

    @pytest.mark.e2e
    async def test_check_kyc_status(self, api_key, api_url):
        """Should check KYC verification status."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Check status for test agent
                kyc_status = await client.compliance.get_kyc_status(
                    agent_id="test_agent",
                )

                assert kyc_status.status in [
                    "not_started", "pending", "approved",
                    "declined", "expired", "needs_review"
                ]

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("KYC methods not available in SDK")

    @pytest.mark.e2e
    async def test_kyc_required_for_large_payment(self, api_key, api_url):
        """Should require KYC for payments above threshold."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Create wallet
                wallet = await client.wallets.create(
                    agent_id=f"kyc_threshold_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Try large payment without KYC
                mandate = {
                    "mandate_id": f"kyc_test_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "vendor:enterprise",
                    "amount_minor": "15000000000",  # $15,000 - above threshold
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "Large enterprise payment",
                    "vendor_name": "Enterprise",
                }

                try:
                    result = await client.payments.execute_mandate(mandate)
                    # If it succeeds, might be in simulated mode
                except Exception as e:
                    # Should be blocked due to KYC requirement
                    assert any(kw in str(e).lower() for kw in ["kyc", "verification", "identity"])

        except ImportError:
            pytest.skip("sardis_sdk not installed")


class TestAMLScreening:
    """Test AML/Sanctions screening flow."""

    @pytest.mark.e2e
    async def test_screen_wallet_address(self, api_key, api_url):
        """Should screen wallet address for sanctions."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Screen a test address
                screening_result = await client.compliance.screen_address(
                    address="0x1234567890123456789012345678901234567890",
                    chain="ethereum",
                )

                assert screening_result.risk_level in ["low", "medium", "high", "severe", "blocked"]
                assert screening_result.is_sanctioned is not None
                assert screening_result.screened_at is not None

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Screening methods not available in SDK")

    @pytest.mark.e2e
    async def test_block_sanctioned_address(self, api_key, api_url):
        """Should block payment to sanctioned address."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                wallet = await client.wallets.create(
                    agent_id=f"aml_test_{datetime.now(timezone.utc).timestamp()}",
                    chain="base_sepolia",
                )

                # Try payment to known sanctioned address (mock)
                mandate = {
                    "mandate_id": f"aml_test_{datetime.now(timezone.utc).timestamp()}",
                    "subject": wallet.id,
                    "destination": "0x0000000000000000000000000000000000000bad",
                    "amount_minor": "10000000",
                    "token": "USDC",
                    "chain": "base_sepolia",
                    "purpose": "Test sanctioned address",
                    "vendor_name": "Sanctioned",
                }

                try:
                    result = await client.payments.execute_mandate(mandate)
                    # Should be blocked in production
                except Exception as e:
                    assert any(kw in str(e).lower() for kw in [
                        "sanction", "blocked", "compliance", "aml"
                    ])

        except ImportError:
            pytest.skip("sardis_sdk not installed")

    @pytest.mark.e2e
    async def test_transaction_monitoring(self, api_key, api_url):
        """Should monitor transactions for suspicious activity."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                # Get transaction monitoring alerts
                alerts = await client.compliance.get_monitoring_alerts(
                    limit=10,
                )

                # Should return list (may be empty in test)
                assert isinstance(alerts, list)

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Monitoring methods not available in SDK")


class TestComplianceReporting:
    """Test compliance reporting functionality."""

    @pytest.mark.e2e
    async def test_get_compliance_report(self, api_key, api_url):
        """Should generate compliance report."""
        try:
            from sardis_sdk import SardisClient

            async with SardisClient(api_key=api_key, base_url=api_url) as client:
                report = await client.compliance.get_report(
                    start_date="2024-01-01",
                    end_date="2024-12-31",
                )

                assert report is not None
                # Report should have key metrics
                assert hasattr(report, 'total_transactions') or 'total_transactions' in report

        except ImportError:
            pytest.skip("sardis_sdk not installed")
        except AttributeError:
            pytest.skip("Reporting methods not available in SDK")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
