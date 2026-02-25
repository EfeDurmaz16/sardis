from __future__ import annotations

from types import SimpleNamespace

import pytest

from sardis_api.routers.ap2 import Dependencies, _compliance_checks_impl, perform_compliance_checks


class _KYAService:
    def __init__(self, allowed: bool, reason: str = "kya_denied"):
        self._allowed = allowed
        self._reason = reason

    async def check_agent(self, request):
        return SimpleNamespace(allowed=self._allowed, reason=self._reason)


class _SanctionsService:
    def __init__(self, *, should_block: bool = False, risk_level: str = "low", provider: str = "elliptic"):
        self._should_block = should_block
        self._risk_level = risk_level
        self._provider = provider

    async def screen_address(self, address: str, chain: str = ""):
        return SimpleNamespace(
            should_block=self._should_block,
            risk_level=SimpleNamespace(value=self._risk_level),
            provider=self._provider,
            reason=f"risk_{self._risk_level}",
        )


class _KYCService:
    def __init__(self, *, verified: bool = True, raise_error: bool = False):
        self._verified = verified
        self._raise_error = raise_error

    async def check_verification(self, agent_id: str):
        if self._raise_error:
            raise RuntimeError("kyc_down")
        return SimpleNamespace(is_verified=self._verified, status="approved" if self._verified else "pending")


def _deps(**kwargs) -> Dependencies:
    return Dependencies(
        verifier=SimpleNamespace(),
        orchestrator=SimpleNamespace(),
        wallet_repo=SimpleNamespace(),
        agent_repo=SimpleNamespace(),
        **kwargs,
    )


@pytest.mark.asyncio
async def test_kya_denied_when_enforcement_enabled(monkeypatch):
    monkeypatch.setenv("SARDIS_KYA_ENFORCEMENT_ENABLED", "true")

    result = await perform_compliance_checks(
        deps=_deps(kya_service=_KYAService(allowed=False)),
        agent_id="agent_1",
        destination="0xmerchant",
        chain="base",
        amount_minor=10_000,
    )

    assert result.passed is False
    assert result.reason == "kya_denied"
    assert result.provider == "sardis_kya"


@pytest.mark.asyncio
async def test_kyt_high_risk_triggers_manual_review():
    result = await perform_compliance_checks(
        deps=_deps(sanctions_service=_SanctionsService(risk_level="high")),
        agent_id="agent_1",
        destination="0xmerchant",
        chain="base",
        amount_minor=10_000,
    )

    assert result.passed is True
    assert result.kyt_review_required is True
    assert result.kyt_risk_level == "high"


@pytest.mark.asyncio
async def test_kyt_blocks_on_sanctions_hit():
    result = await perform_compliance_checks(
        deps=_deps(sanctions_service=_SanctionsService(should_block=True, risk_level="blocked")),
        agent_id="agent_1",
        destination="0xblocked",
        chain="base",
        amount_minor=10_000,
    )

    assert result.passed is False
    assert result.reason == "sanctions_hit"


@pytest.mark.asyncio
async def test_source_address_is_screened_for_kyt():
    result = await _compliance_checks_impl(
        deps=_deps(sanctions_service=_SanctionsService(risk_level="severe")),
        agent_id="agent_1",
        destination="0xmerchant",
        chain="base",
        amount_minor=10_000,
        source_address="0xsource",
        token="USDC",
    )

    assert result.passed is True
    assert result.kyt_review_required is True
    assert result.kyt_risk_level == "severe"


@pytest.mark.asyncio
async def test_kyc_service_error_fails_closed():
    result = await perform_compliance_checks(
        deps=_deps(kyc_service=_KYCService(raise_error=True)),
        agent_id="agent_1",
        destination="0xmerchant",
        chain="base",
        amount_minor=200_000,
    )

    assert result.passed is False
    assert result.reason == "kyc_service_error"
