"""Test F07: Spend recording should log CRITICAL on failure."""
import logging
import time
import pytest
from unittest.mock import AsyncMock, MagicMock
from sardis_wallet.manager import EnhancedWalletManager
from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import PaymentMandate, VCProof


def _proof():
    return VCProof(
        verification_method="did:key:test",
        created=str(int(time.time())),
        proof_value="dGVzdA==",
    )


@pytest.mark.asyncio
async def test_spend_recording_logs_critical_on_failure(caplog):
    """async_record_spend should log CRITICAL if persistence fails."""
    settings = SardisSettings()

    mock_store = MagicMock()
    mock_store.record_spend = AsyncMock(side_effect=RuntimeError("Database unavailable"))

    manager = EnhancedWalletManager(
        settings=settings,
        async_policy_store=mock_store,
    )

    mandate = PaymentMandate(
        mandate_id="test_mandate",
        mandate_type="payment",
        issuer="agent_123",
        subject="agent_123",
        expires_at=int(time.time()) + 3600,
        nonce="test-nonce",
        proof=_proof(),
        domain="example.com",
        purpose="checkout",
        amount_minor=1000,
        token="USDC",
        destination="0xdest",
        chain="base",
        audit_hash="test-hash",
    )

    with caplog.at_level(logging.CRITICAL, logger="sardis_wallet.manager"):
        with pytest.raises(RuntimeError, match="Database unavailable"):
            await manager.async_record_spend(mandate)

    critical_logs = [r for r in caplog.records if r.levelno == logging.CRITICAL]
    assert len(critical_logs) > 0, "Expected CRITICAL log on spend recording failure"
    assert "Failed to record spend" in critical_logs[0].message or "mandate" in critical_logs[0].message.lower()
