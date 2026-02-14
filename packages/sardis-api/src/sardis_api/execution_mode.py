"""Execution mode and pilot-lane guards for payment execution endpoints."""
from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Optional

from fastapi import HTTPException, status

from .authz import Principal


SIMULATED_MODE = "simulated"
STAGING_LIVE_MODE = "staging_live"
PRODUCTION_LIVE_MODE = "production_live"


@dataclass(frozen=True)
class PilotExecutionPolicy:
    """Resolved execution policy for request-time gating."""

    mode: str
    allowed_orgs: set[str]
    allowed_merchants: set[str]
    max_amount: Optional[Decimal]


def resolve_execution_mode(settings: Any | None = None) -> str:
    """
    Resolve execution mode from environment + settings.

    Supported modes:
    - simulated
    - staging_live (controlled pilot lane)
    - production_live
    """
    env = str(getattr(settings, "environment", os.getenv("SARDIS_ENVIRONMENT", "dev"))).strip().lower()
    chain_mode = str(getattr(settings, "chain_mode", os.getenv("SARDIS_CHAIN_MODE", "simulated"))).strip().lower()
    explicit = os.getenv("SARDIS_EXECUTION_MODE", "").strip().lower()

    if explicit:
        if explicit in {"sim", "simulate", SIMULATED_MODE}:
            return SIMULATED_MODE
        if explicit in {"live", "testnet", STAGING_LIVE_MODE}:
            return PRODUCTION_LIVE_MODE if env in {"prod", "production"} else STAGING_LIVE_MODE
        if explicit in {"mainnet", PRODUCTION_LIVE_MODE}:
            return PRODUCTION_LIVE_MODE
        # Unknown explicit mode: fail closed into simulated.
        return SIMULATED_MODE

    if chain_mode != "live":
        return SIMULATED_MODE
    return PRODUCTION_LIVE_MODE if env in {"prod", "production"} else STAGING_LIVE_MODE


def get_pilot_execution_policy(settings: Any | None = None) -> PilotExecutionPolicy:
    """Read pilot policy from environment variables."""
    mode = resolve_execution_mode(settings)

    allowed_orgs = _parse_csv_env("SARDIS_PILOT_ALLOWLIST_ORGS")
    allowed_merchants = _parse_csv_env("SARDIS_PILOT_ALLOWLIST_MERCHANTS")

    raw_max = os.getenv("SARDIS_PILOT_MAX_AMOUNT", "100.00").strip()
    max_amount: Optional[Decimal] = None
    if raw_max:
        try:
            parsed = Decimal(raw_max)
            if parsed > 0:
                max_amount = parsed
        except (InvalidOperation, ValueError):
            max_amount = None

    return PilotExecutionPolicy(
        mode=mode,
        allowed_orgs=allowed_orgs,
        allowed_merchants=allowed_merchants,
        max_amount=max_amount,
    )


def enforce_staging_live_guard(
    *,
    policy: PilotExecutionPolicy,
    principal: Principal,
    merchant_domain: str | None,
    amount: Optional[Decimal],
    operation: str,
) -> None:
    """
    Enforce a strict pilot lane in staging_live mode.

    Fail-closed semantics:
    - Pilot org allowlist MUST be configured.
    - Organization must be in allowlist.
    - If merchant allowlist is configured, merchant must match.
    - If max amount is configured and provided, amount must be below threshold.
    """
    if policy.mode != STAGING_LIVE_MODE:
        return

    if not policy.allowed_orgs:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "pilot allowlist not configured",
                "reason_code": "SARDIS.EXECUTION.PILOT_ALLOWLIST_UNCONFIGURED",
                "operation": operation,
            },
        )

    org = (principal.organization_id or "").strip().lower()
    if org not in policy.allowed_orgs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "organization not allowed in staging live lane",
                "reason_code": "SARDIS.EXECUTION.PILOT_ORG_NOT_ALLOWED",
                "organization_id": principal.organization_id,
                "operation": operation,
            },
        )

    if merchant_domain and policy.allowed_merchants:
        merchant = merchant_domain.strip().lower()
        if not _merchant_allowed(merchant, policy.allowed_merchants):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "merchant/domain not allowed in staging live lane",
                    "reason_code": "SARDIS.EXECUTION.PILOT_MERCHANT_NOT_ALLOWED",
                    "merchant_domain": merchant_domain,
                    "operation": operation,
                },
            )

    if amount is not None and policy.max_amount is not None and amount > policy.max_amount:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "amount exceeds pilot max amount",
                "reason_code": "SARDIS.EXECUTION.PILOT_AMOUNT_EXCEEDED",
                "max_amount": str(policy.max_amount),
                "operation": operation,
            },
        )


def _parse_csv_env(name: str) -> set[str]:
    raw = os.getenv(name, "")
    if not raw.strip():
        return set()
    values = [v.strip().lower() for v in raw.split(",")]
    return {v for v in values if v}


def _merchant_allowed(merchant: str, rules: set[str]) -> bool:
    if merchant in rules:
        return True
    return any(merchant.endswith(f".{rule}") for rule in rules)

