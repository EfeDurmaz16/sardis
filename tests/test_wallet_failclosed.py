"""
Tests that wallet security features are fail-closed.

Verifies that dangerous operations raise explicit errors rather than
silently succeeding with insecure fallback behavior.

Defects addressed:
1. Circle entity secret sent unencrypted (now requires RSA key or raises)
2. Social recovery used insecure HMAC shares (now disabled entirely)
3. Key rotation tracked in-memory without Turnkey API call (now raises)
4. Health check returned mock-healthy when no MPC checker configured (now UNKNOWN)
"""
from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock

import pytest

# ---------------------------------------------------------------------------
# DEFECT 1: Circle entity secret must not be sent unencrypted
# ---------------------------------------------------------------------------

class TestCircleEntitySecretEncryption:
    """Circle client must refuse to build ciphertext without RSA key."""

    def test_build_cipher_raises_without_rsa_key(self, monkeypatch):
        """Without SARDIS_CIRCLE_ENTITY_SECRET_CIPHER_KEY, must raise."""
        monkeypatch.delenv("SARDIS_CIRCLE_ENTITY_SECRET_CIPHER_KEY", raising=False)

        from sardis.wallet.circle_client import CircleWalletClient

        client = CircleWalletClient(
            api_key="test-api-key",
            entity_secret="a" * 64,  # 32-byte hex
        )

        with pytest.raises(NotImplementedError, match="Circle entity secret RSA encryption required"):
            client._build_entity_secret_cipher()

    def test_build_cipher_raises_with_empty_rsa_key(self, monkeypatch):
        """Empty env var should still raise."""
        monkeypatch.setenv("SARDIS_CIRCLE_ENTITY_SECRET_CIPHER_KEY", "")

        from sardis.wallet.circle_client import CircleWalletClient

        client = CircleWalletClient(
            api_key="test-api-key",
            entity_secret="a" * 64,
        )

        with pytest.raises(NotImplementedError, match="Circle entity secret RSA encryption required"):
            client._build_entity_secret_cipher()

    def test_build_cipher_succeeds_with_valid_rsa_key(self, monkeypatch):
        """With a valid RSA public key, encryption should succeed."""
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
        except ImportError:
            pytest.skip("cryptography package not installed")

        # Generate a test RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        public_key_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

        monkeypatch.setenv("SARDIS_CIRCLE_ENTITY_SECRET_CIPHER_KEY", public_key_pem)

        from sardis.wallet.circle_client import CircleWalletClient

        client = CircleWalletClient(
            api_key="test-api-key",
            entity_secret="a" * 64,
        )

        # Should not raise
        result = client._build_entity_secret_cipher()
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_create_wallet_set_fails_without_cipher(self, monkeypatch):
        """Wallet set creation must fail when cipher is not configured."""
        monkeypatch.delenv("SARDIS_CIRCLE_ENTITY_SECRET_CIPHER_KEY", raising=False)

        from sardis.wallet.circle_client import CircleWalletClient

        client = CircleWalletClient(
            api_key="test-api-key",
            entity_secret="a" * 64,
        )

        with pytest.raises(NotImplementedError, match="Circle entity secret RSA encryption required"):
            await client.create_wallet_set("test-set")


# ---------------------------------------------------------------------------
# DEFECT 2: Social recovery must be fully disabled (insecure HMAC shares)
# ---------------------------------------------------------------------------

class TestSocialRecoveryDisabled:
    """All social recovery operations must raise RuntimeError."""

    def _get_manager(self):
        from sardis.wallet.social_recovery import SocialRecoveryManager
        return SocialRecoveryManager()

    def test_generate_sss_shares_raises(self):
        """SSS share generation must be disabled."""
        manager = self._get_manager()
        with pytest.raises(RuntimeError, match="Social recovery is disabled"):
            manager._generate_sss_shares(b"secret", 5, 3)

    def test_reconstruct_secret_raises(self):
        """SSS secret reconstruction must be disabled."""
        manager = self._get_manager()
        with pytest.raises(RuntimeError, match="Social recovery is disabled"):
            manager._reconstruct_secret([(1, b"share1"), (2, b"share2")], 2)

    @pytest.mark.asyncio
    async def test_setup_recovery_raises(self):
        """Setting up social recovery must be disabled."""
        manager = self._get_manager()
        guardians = [
            {"identifier": f"guardian{i}@example.com", "type": "email"}
            for i in range(3)
        ]
        with pytest.raises(RuntimeError, match="Social recovery is disabled"):
            await manager.setup_recovery(
                wallet_id="wal_test",
                recovery_secret=b"secret",
                guardians=guardians,
            )

    @pytest.mark.asyncio
    async def test_initiate_recovery_raises(self):
        """Initiating recovery must be disabled."""
        manager = self._get_manager()
        with pytest.raises(RuntimeError, match="Social recovery is disabled"):
            await manager.initiate_recovery(
                wallet_id="wal_test",
                requester_proof="proof",
            )

    @pytest.mark.asyncio
    async def test_execute_recovery_raises(self):
        """Executing recovery must be disabled."""
        manager = self._get_manager()
        with pytest.raises(RuntimeError, match="Social recovery is disabled"):
            await manager.execute_recovery(recovery_id="recovery_test")

    def test_error_message_mentions_shamir(self):
        """Error message must mention Shamir's Secret Sharing as the fix."""
        manager = self._get_manager()
        with pytest.raises(RuntimeError) as exc_info:
            manager._generate_sss_shares(b"secret", 5, 3)
        assert "Shamir" in str(exc_info.value)


# ---------------------------------------------------------------------------
# DEFECT 3: Key rotation must raise (no Turnkey integration)
# ---------------------------------------------------------------------------

class TestKeyRotationDisabled:
    """Key rotation must raise NotImplementedError (not implemented with Turnkey)."""

    def _get_manager(self):
        from sardis.wallet.manager import EnhancedWalletManager

        settings = MagicMock()
        settings.circle_wallet_api_key = None
        settings.circle_entity_secret = None
        settings.circle_wallet_set_id = None
        settings.circle_account_type = None

        return EnhancedWalletManager(settings=settings)

    @pytest.mark.asyncio
    async def test_rotate_wallet_key_raises(self):
        """rotate_wallet_key must raise NotImplementedError."""
        manager = self._get_manager()
        with pytest.raises(NotImplementedError, match="Key rotation requires Turnkey API integration"):
            await manager.rotate_wallet_key(wallet_id="wal_test")

    @pytest.mark.asyncio
    async def test_emergency_key_rotation_raises(self):
        """emergency_key_rotation must raise NotImplementedError."""
        manager = self._get_manager()
        with pytest.raises(NotImplementedError, match="Emergency key rotation requires Turnkey API integration"):
            await manager.emergency_key_rotation(
                wallet_id="wal_test",
                reason="test",
                initiated_by="test",
            )

    @pytest.mark.asyncio
    async def test_rotate_key_error_mentions_turnkey_dashboard(self):
        """Error message must mention Turnkey dashboard as the workaround."""
        manager = self._get_manager()
        with pytest.raises(NotImplementedError) as exc_info:
            await manager.rotate_wallet_key(wallet_id="wal_test")
        assert "Turnkey dashboard" in str(exc_info.value)


# ---------------------------------------------------------------------------
# DEFECT 4: Health check must report honest status without MPC checker
# ---------------------------------------------------------------------------

class TestHealthCheckHonestStatus:
    """Health check must return UNKNOWN when no MPC checker is configured."""

    @pytest.mark.asyncio
    async def test_mpc_check_returns_unknown_without_checker(self):
        """Without MPCProviderChecker, status must be UNKNOWN, not HEALTHY."""
        from sardis.wallet.health_check import (
            HealthChecker,
            HealthStatus,
        )

        checker = HealthChecker()  # No mpc_checker provided
        result = await checker._check_mpc_connectivity(
            wallet_id="wal_test1234567890",
            wallet_data={},
        )

        assert result.status == HealthStatus.UNKNOWN
        assert "not configured" in result.message.lower()
        assert result.details.get("configured") is False

    @pytest.mark.asyncio
    async def test_mpc_check_returns_healthy_with_checker(self):
        """With a real MPCProviderChecker that returns success, status is HEALTHY."""
        from sardis.wallet.health_check import (
            HealthChecker,
            HealthStatus,
        )

        mock_checker = AsyncMock()
        mock_checker.check_connectivity = AsyncMock(return_value=(True, 50.0))

        checker = HealthChecker(mpc_checker=mock_checker)
        result = await checker._check_mpc_connectivity(
            wallet_id="wal_test1234567890",
            wallet_data={},
        )

        assert result.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_full_health_report_reflects_unknown_mpc(self):
        """Full wallet health check should reflect unknown MPC status."""
        from sardis.wallet.health_check import (
            HealthCheckConfig,
            HealthChecker,
            HealthStatus,
        )

        config = HealthCheckConfig(
            check_mpc_connectivity=True,
            check_chain_connectivity=False,
            check_key_validity=False,
            check_balance=False,
            check_security=False,
            check_compliance=False,
        )

        checker = HealthChecker(config=config)  # No mpc_checker
        report = await checker.check_wallet_health(
            wallet_id="wal_test1234567890",
            wallet_data={},
        )

        # Should have at least one check result
        assert len(report.check_results) >= 1
        mpc_result = report.check_results[0]
        assert mpc_result.status == HealthStatus.UNKNOWN
