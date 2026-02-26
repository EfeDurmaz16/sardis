from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest

from sardis_compliance.kyc import (
    FailoverKYCProvider,
    InquirySession,
    KYCProvider,
    KYCResult,
    KYCStatus,
    VerificationRequest,
)
from sardis_compliance.sanctions import (
    EntityType,
    FailoverSanctionsProvider,
    SanctionsProvider,
    SanctionsRisk,
    ScreeningResult,
    TransactionScreeningRequest,
    WalletScreeningRequest,
)


class _RaisingKYCProvider(KYCProvider):
    async def create_inquiry(self, request: VerificationRequest) -> InquirySession:  # noqa: ARG002
        raise RuntimeError("primary create failure")

    async def get_inquiry_status(self, inquiry_id: str) -> KYCResult:  # noqa: ARG002
        raise RuntimeError("primary status failure")

    async def cancel_inquiry(self, inquiry_id: str) -> bool:  # noqa: ARG002
        raise RuntimeError("primary cancel failure")

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:  # noqa: ARG002
        raise RuntimeError("primary verify failure")


@dataclass
class _SuccessKYCProvider(KYCProvider):
    inquiry_id: str = "inq_fallback"
    verify_result: bool = True

    async def create_inquiry(self, request: VerificationRequest) -> InquirySession:
        return InquirySession(
            inquiry_id=self.inquiry_id,
            session_token="token",
            template_id="tpl",
            status=KYCStatus.PENDING,
            redirect_url=None,
            expires_at=None,
        )

    async def get_inquiry_status(self, inquiry_id: str) -> KYCResult:  # noqa: ARG002
        return KYCResult(status=KYCStatus.APPROVED, verification_id=self.inquiry_id, provider="fallback")

    async def cancel_inquiry(self, inquiry_id: str) -> bool:  # noqa: ARG002
        return True

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:  # noqa: ARG002
        return self.verify_result


class _RaisingSanctionsProvider(SanctionsProvider):
    async def screen_wallet(self, request: WalletScreeningRequest) -> ScreeningResult:  # noqa: ARG002
        raise RuntimeError("primary wallet failure")

    async def screen_transaction(
        self,
        request: TransactionScreeningRequest,  # noqa: ARG002
    ) -> ScreeningResult:
        raise RuntimeError("primary tx failure")

    async def add_to_blocklist(self, address: str, reason: str) -> bool:  # noqa: ARG002
        return True

    async def remove_from_blocklist(self, address: str) -> bool:  # noqa: ARG002
        return True


class _StaticSanctionsProvider(SanctionsProvider):
    def __init__(self, result: ScreeningResult):
        self._result = result

    async def screen_wallet(self, request: WalletScreeningRequest) -> ScreeningResult:  # noqa: ARG002
        return self._result

    async def screen_transaction(self, request: TransactionScreeningRequest) -> ScreeningResult:  # noqa: ARG002
        return self._result

    async def add_to_blocklist(self, address: str, reason: str) -> bool:  # noqa: ARG002
        return True

    async def remove_from_blocklist(self, address: str) -> bool:  # noqa: ARG002
        return True


@pytest.mark.asyncio
async def test_failover_kyc_provider_uses_fallback_on_primary_error():
    provider = FailoverKYCProvider(
        primary=_RaisingKYCProvider(),
        fallback=_SuccessKYCProvider(),
    )

    session = await provider.create_inquiry(VerificationRequest(reference_id="agent_1"))
    assert session.inquiry_id == "inq_fallback"

    result = await provider.get_inquiry_status("inq_fallback")
    assert result.status == KYCStatus.APPROVED
    assert await provider.cancel_inquiry("inq_fallback") is True
    assert await provider.verify_webhook(b"{}", "sig") is True


@pytest.mark.asyncio
async def test_failover_sanctions_provider_uses_fallback_on_primary_exception():
    fallback_result = ScreeningResult(
        risk_level=SanctionsRisk.LOW,
        is_sanctioned=False,
        entity_id="0xabc",
        entity_type=EntityType.WALLET,
        provider="fallback",
    )
    provider = FailoverSanctionsProvider(
        primary=_RaisingSanctionsProvider(),
        fallback=_StaticSanctionsProvider(fallback_result),
    )

    wallet_result = await provider.screen_wallet(WalletScreeningRequest(address="0xabc", chain="base"))
    tx_result = await provider.screen_transaction(
        TransactionScreeningRequest(
            tx_hash="0xtx",
            chain="base",
            from_address="0xfrom",
            to_address="0xto",
            amount=Decimal("1.0"),
            token="USDC",
        )
    )
    assert wallet_result.provider == "fallback"
    assert tx_result.provider == "fallback"


@pytest.mark.asyncio
async def test_failover_sanctions_provider_retries_provider_error_block():
    primary_error_result = ScreeningResult(
        risk_level=SanctionsRisk.BLOCKED,
        is_sanctioned=False,
        entity_id="0xabc",
        entity_type=EntityType.WALLET,
        provider="primary",
        reason="API error: HTTP 503",
    )
    fallback_ok_result = ScreeningResult(
        risk_level=SanctionsRisk.LOW,
        is_sanctioned=False,
        entity_id="0xabc",
        entity_type=EntityType.WALLET,
        provider="fallback",
    )
    provider = FailoverSanctionsProvider(
        primary=_StaticSanctionsProvider(primary_error_result),
        fallback=_StaticSanctionsProvider(fallback_ok_result),
    )

    result = await provider.screen_wallet(WalletScreeningRequest(address="0xabc", chain="base"))
    assert result.provider == "fallback"
    assert result.risk_level == SanctionsRisk.LOW
