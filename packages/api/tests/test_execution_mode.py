"""Execution-mode and pilot-lane guard tests."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import pytest
from fastapi import HTTPException

from sardis_api.authz import Principal
from sardis_api.execution_mode import (
    STAGING_LIVE_MODE,
    enforce_staging_live_guard,
    get_pilot_execution_policy,
    resolve_execution_mode,
)


@dataclass
class _Settings:
    environment: str = "sandbox"
    chain_mode: str = "simulated"


def _principal(org_id: str = "org_demo") -> Principal:
    return Principal(kind="api_key", organization_id=org_id, scopes=["*"])


def test_resolve_execution_mode_defaults_to_simulated():
    settings = _Settings(environment="sandbox", chain_mode="simulated")
    assert resolve_execution_mode(settings) == "simulated"


def test_resolve_execution_mode_explicit_live_maps_to_staging(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SARDIS_EXECUTION_MODE", "live")
    settings = _Settings(environment="sandbox", chain_mode="live")
    assert resolve_execution_mode(settings) == STAGING_LIVE_MODE


def test_staging_live_requires_org_allowlist():
    policy = get_pilot_execution_policy(_Settings(environment="sandbox", chain_mode="live"))
    assert policy.mode == STAGING_LIVE_MODE
    with pytest.raises(HTTPException) as exc:
        enforce_staging_live_guard(
            policy=policy,
            principal=_principal("org_a"),
            merchant_domain="amazon.com",
            amount=Decimal("10"),
            operation="wallets.transfer",
        )
    assert exc.value.status_code == 503
    assert exc.value.detail["reason_code"] == "SARDIS.EXECUTION.PILOT_ALLOWLIST_UNCONFIGURED"


def test_staging_live_allows_matching_org_and_merchant(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SARDIS_PILOT_ALLOWLIST_ORGS", "org_a")
    monkeypatch.setenv("SARDIS_PILOT_ALLOWLIST_MERCHANTS", "amazon.com")
    policy = get_pilot_execution_policy(_Settings(environment="sandbox", chain_mode="live"))
    enforce_staging_live_guard(
        policy=policy,
        principal=_principal("org_a"),
        merchant_domain="checkout.amazon.com",
        amount=Decimal("25"),
        operation="wallets.transfer",
    )


def test_staging_live_blocks_merchant_not_allowlisted(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SARDIS_PILOT_ALLOWLIST_ORGS", "org_a")
    monkeypatch.setenv("SARDIS_PILOT_ALLOWLIST_MERCHANTS", "amazon.com")
    policy = get_pilot_execution_policy(_Settings(environment="sandbox", chain_mode="live"))
    with pytest.raises(HTTPException) as exc:
        enforce_staging_live_guard(
            policy=policy,
            principal=_principal("org_a"),
            merchant_domain="evil-shop.example",
            amount=Decimal("25"),
            operation="wallets.transfer",
        )
    assert exc.value.status_code == 403
    assert exc.value.detail["reason_code"] == "SARDIS.EXECUTION.PILOT_MERCHANT_NOT_ALLOWED"

