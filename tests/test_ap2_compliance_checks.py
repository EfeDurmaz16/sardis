"""Unit tests for AP2 compliance checks wiring (KYC + sanctions)."""

from __future__ import annotations

import pytest

from sardis_api.routers.ap2 import (
    HIGH_VALUE_THRESHOLD_MINOR,
    KYC_THRESHOLD_MINOR,
    perform_compliance_checks,
)
from sardis_compliance.kyc import KYCResult, KYCStatus
from sardis_compliance.sanctions import EntityType, SanctionsRisk, ScreeningResult


class _FakeKYCService:
    def __init__(self, status: KYCStatus):
        self._result = KYCResult(status=status, verification_id="verif_1")

    async def check_verification(self, agent_id: str) -> KYCResult:  # noqa: ARG002
        return self._result


class _FakeSanctionsService:
    def __init__(self, result: ScreeningResult):
        self._result = result

    async def screen_address(self, address: str, chain: str = "ethereum", force_refresh: bool = False) -> ScreeningResult:  # noqa: ARG002
        return self._result


@pytest.mark.asyncio
async def test_high_value_requires_kyc():
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": _FakeKYCService(KYCStatus.NOT_STARTED),
            "sanctions_service": None,
        },
    )()

    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_1",
        destination="0x0",
        chain="base_sepolia",
        amount_minor=HIGH_VALUE_THRESHOLD_MINOR,
    )

    assert res.passed is False
    assert res.reason == "kyc_required_high_value"


@pytest.mark.asyncio
async def test_low_value_allows_without_kyc():
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": _FakeKYCService(KYCStatus.NOT_STARTED),
            "sanctions_service": None,
        },
    )()

    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_1",
        destination="0x0",
        chain="base_sepolia",
        amount_minor=KYC_THRESHOLD_MINOR,
    )

    assert res.passed is True
    assert res.kyc_verified is False


@pytest.mark.asyncio
async def test_sanctions_hit_blocks():
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": None,
            "sanctions_service": _FakeSanctionsService(
                ScreeningResult(
                    risk_level=SanctionsRisk.BLOCKED,
                    is_sanctioned=True,
                    entity_id="0x0",
                    entity_type=EntityType.WALLET,
                    reason="ofac",
                )
            ),
        },
    )()

    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_1",
        destination="0x0",
        chain="base_sepolia",
        amount_minor=1,
    )

    assert res.passed is False
    assert res.reason == "sanctions_hit"


@pytest.mark.asyncio
async def test_sanctions_service_error_fails_closed():
    class _Boom:
        async def screen_address(self, address: str, chain: str = "ethereum", force_refresh: bool = False):  # noqa: ARG002
            raise RuntimeError("down")

    deps = type(
        "Deps",
        (),
        {
            "kyc_service": None,
            "sanctions_service": _Boom(),
        },
    )()

    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_1",
        destination="0x0",
        chain="base_sepolia",
        amount_minor=1,
    )

    assert res.passed is False
    assert res.reason == "sanctions_service_error"

