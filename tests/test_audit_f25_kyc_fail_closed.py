"""Test F25: KYC service errors must fail closed (reject payment)."""

from __future__ import annotations

import pytest

from sardis_api.routers.ap2 import (
    KYC_THRESHOLD_MINOR,
    perform_compliance_checks,
)


class _KYCServiceError:
    """Mock KYC service that raises exceptions."""

    async def check_verification(self, agent_id: str) -> None:  # noqa: ARG002
        raise RuntimeError("KYC service unavailable")


@pytest.mark.asyncio
async def test_kyc_service_error_fails_closed_low_value():
    """KYC service errors must fail closed even for low-value transactions."""
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": _KYCServiceError(),
            "sanctions_service": None,
        },
    )()

    # Test with low-value transaction ($1000 - just at KYC threshold)
    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_test",
        destination="0xRecipient",
        chain="base",
        amount_minor=KYC_THRESHOLD_MINOR,
    )

    assert res.passed is False, "KYC service error should reject payment"
    assert res.reason == "kyc_service_error"
    assert res.provider == "persona"
    assert res.rule == "kyc_service_error"


@pytest.mark.asyncio
async def test_kyc_service_error_fails_closed_mid_value():
    """KYC service errors must fail closed for mid-value transactions."""
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": _KYCServiceError(),
            "sanctions_service": None,
        },
    )()

    # Test with mid-value transaction ($5000)
    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_test",
        destination="0xRecipient",
        chain="base",
        amount_minor=500000,
    )

    assert res.passed is False, "KYC service error should reject payment"
    assert res.reason == "kyc_service_error"
    assert res.provider == "persona"
    assert res.rule == "kyc_service_error"


@pytest.mark.asyncio
async def test_kyc_service_error_fails_closed_high_value():
    """KYC service errors must fail closed for high-value transactions."""
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": _KYCServiceError(),
            "sanctions_service": None,
        },
    )()

    # Test with high-value transaction ($10,000)
    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_test",
        destination="0xRecipient",
        chain="base",
        amount_minor=1000000,
    )

    assert res.passed is False, "KYC service error should reject payment"
    assert res.reason == "kyc_service_error"
    assert res.provider == "persona"
    assert res.rule == "kyc_service_error"


@pytest.mark.asyncio
async def test_kyc_service_error_below_threshold():
    """Transactions below KYC threshold should not trigger KYC checks."""
    deps = type(
        "Deps",
        (),
        {
            "kyc_service": _KYCServiceError(),
            "sanctions_service": None,
        },
    )()

    # Test with transaction below KYC threshold ($999)
    res = await perform_compliance_checks(
        deps=deps,
        agent_id="agent_test",
        destination="0xRecipient",
        chain="base",
        amount_minor=KYC_THRESHOLD_MINOR - 1,
    )

    # Below threshold, KYC check should not run, payment should pass
    assert res.passed is True, "Below KYC threshold should skip KYC check"
