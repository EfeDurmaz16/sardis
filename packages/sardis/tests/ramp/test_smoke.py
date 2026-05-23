"""Credential-free smoke tests for the Sardis ramp package."""

from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sardis.ramp import (
    BankAccount,
    BridgeProvider,
    CoinbaseOnrampProvider,
    FundingMethod,
    RampProvider,
    RampQuote,
    RampRouter,
    RampSession,
    RampStatus,
    SardisFiatRamp,
)


class FakeProvider(RampProvider):
    def __init__(
        self,
        name: str,
        *,
        supports_onramp: bool = True,
        supports_offramp: bool = False,
        fee_percent: Decimal = Decimal("1.0"),
    ) -> None:
        self._name = name
        self._supports_onramp = supports_onramp
        self._supports_offramp = supports_offramp
        self._fee_percent = fee_percent
        self.created_sessions: list[RampSession] = []

    @property
    def provider_name(self) -> str:
        return self._name

    @property
    def supports_onramp(self) -> bool:
        return self._supports_onramp

    @property
    def supports_offramp(self) -> bool:
        return self._supports_offramp

    async def get_quote(
        self,
        amount: Decimal,
        source_currency: str,
        destination_currency: str,
        chain: str,
        direction: str,
    ) -> RampQuote:
        return RampQuote(
            provider=self.provider_name,
            amount_fiat=amount,
            amount_crypto=amount,
            fiat_currency=source_currency,
            crypto_currency=destination_currency,
            chain=chain,
            fee_amount=amount * self._fee_percent / Decimal("100"),
            fee_percent=self._fee_percent,
            exchange_rate=Decimal("1"),
            expires_at=datetime.utcnow() + timedelta(minutes=5),
        )

    async def create_onramp(
        self,
        amount_fiat: Decimal,
        fiat_currency: str,
        crypto_currency: str,
        chain: str,
        destination_address: str,
        wallet_id: str | None = None,
        metadata: dict | None = None,
    ) -> RampSession:
        session = RampSession(
            session_id=f"{self.provider_name}_session",
            provider=self.provider_name,
            direction="onramp",
            status=RampStatus.PENDING,
            amount_fiat=amount_fiat,
            amount_crypto=amount_fiat,
            fiat_currency=fiat_currency,
            crypto_currency=crypto_currency,
            chain=chain,
            destination_address=destination_address,
            metadata=metadata or {},
        )
        self.created_sessions.append(session)
        return session

    async def create_offramp(
        self,
        amount_crypto: Decimal,
        crypto_currency: str,
        chain: str,
        fiat_currency: str,
        bank_account: dict,
        wallet_id: str | None = None,
        metadata: dict | None = None,
    ) -> RampSession:
        return RampSession(
            session_id=f"{self.provider_name}_offramp",
            provider=self.provider_name,
            direction="offramp",
            status=RampStatus.PENDING,
            amount_fiat=amount_crypto,
            amount_crypto=amount_crypto,
            fiat_currency=fiat_currency,
            crypto_currency=crypto_currency,
            chain=chain,
            destination_address=bank_account["account_number"],
            metadata=metadata or {},
        )

    async def get_status(self, session_id: str) -> RampSession:
        return RampSession(
            session_id=session_id,
            provider=self.provider_name,
            direction="onramp",
            status=RampStatus.COMPLETED,
            amount_fiat=Decimal("10"),
            amount_crypto=Decimal("10"),
            fiat_currency="USD",
            crypto_currency="USDC",
            chain="base",
            destination_address="0xabc",
        )

    async def handle_webhook(self, payload: bytes, headers: dict) -> dict:
        return {"provider": self.provider_name, "payload": payload.decode(), "headers": headers}


def test_public_import_surface_is_credential_free() -> None:
    bank_account = BankAccount(
        account_holder_name="Sardis Test",
        account_number="123456789",
        routing_number="021000021",
    )

    assert FundingMethod.BANK.value == "bank"
    assert RampStatus.PENDING.value == "pending"
    assert bank_account.account_type == "checking"
    assert SardisFiatRamp.__name__ == "SardisFiatRamp"


def test_providers_fail_closed_without_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SARDIS_API_KEY", raising=False)
    monkeypatch.delenv("BRIDGE_API_KEY", raising=False)
    monkeypatch.delenv("COINBASE_ONRAMP_API_KEY", raising=False)

    with pytest.raises(ValueError, match="Sardis API key required"):
        SardisFiatRamp()

    with pytest.raises(ValueError, match="Sardis API key required"):
        BridgeProvider()

    with pytest.raises(ValueError, match="Coinbase API key required"):
        CoinbaseOnrampProvider()


@pytest.mark.asyncio
async def test_router_prefers_coinbase_for_usdc_onramp() -> None:
    bridge = FakeProvider("bridge")
    coinbase = FakeProvider("coinbase", fee_percent=Decimal("0"))
    router = RampRouter([bridge, coinbase])

    session = await router.get_best_onramp(
        amount_fiat=Decimal("25"),
        fiat_currency="USD",
        crypto_currency="USDC",
        chain="base",
        destination_address="0xabc",
        wallet_id="wallet_123",
    )

    assert session.provider == "coinbase"
    assert coinbase.created_sessions
    assert not bridge.created_sessions


@pytest.mark.asyncio
async def test_router_rejects_empty_provider_list() -> None:
    with pytest.raises(ValueError, match="At least one provider required"):
        RampRouter([])
