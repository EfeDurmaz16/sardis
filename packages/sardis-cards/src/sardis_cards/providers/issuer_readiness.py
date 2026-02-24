"""Readiness helpers for evaluating external card issuers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class IssuerReadiness:
    name: str
    configured: bool
    stablecoin_native: bool
    card_issuing: bool
    required_env: tuple[str, ...]
    missing_env: tuple[str, ...]
    notes: Optional[str] = None


def _readiness(name: str, stablecoin_native: bool, card_issuing: bool, required_env: tuple[str, ...], notes: str | None = None) -> IssuerReadiness:
    missing = tuple(k for k in required_env if not os.getenv(k))
    return IssuerReadiness(
        name=name,
        configured=len(missing) == 0,
        stablecoin_native=stablecoin_native,
        card_issuing=card_issuing,
        required_env=required_env,
        missing_env=missing,
        notes=notes,
    )


def evaluate_issuer_readiness() -> list[IssuerReadiness]:
    """
    Evaluate candidate issuer readiness from local environment.

    This is intentionally lightweight: it does not call remote APIs.
    """
    stripe_api_key = os.getenv("STRIPE_API_KEY") or os.getenv("STRIPE_SECRET_KEY")
    stripe_missing: tuple[str, ...] = tuple() if stripe_api_key else ("STRIPE_API_KEY|STRIPE_SECRET_KEY",)
    rows = [
        IssuerReadiness(
            name="stripe_issuing",
            configured=bool(stripe_api_key),
            stablecoin_native=False,
            card_issuing=True,
            required_env=("STRIPE_API_KEY", "STRIPE_SECRET_KEY"),
            missing_env=stripe_missing,
            notes="Either STRIPE_API_KEY or STRIPE_SECRET_KEY must be configured.",
        ),
        _readiness(
            name="lithic",
            stablecoin_native=False,
            card_issuing=True,
            required_env=("LITHIC_API_KEY",),
            notes="Card funding typically needs fiat settlement path.",
        ),
        _readiness(
            name="rain",
            stablecoin_native=True,
            card_issuing=True,
            required_env=("RAIN_API_KEY", "RAIN_PROGRAM_ID"),
            notes="Partner onboarding details vary by region/program.",
        ),
        _readiness(
            name="bridge_cards",
            stablecoin_native=True,
            card_issuing=True,
            required_env=("BRIDGE_API_KEY",),
            notes="Bridge cards API access is feature-gated by account.",
        ),
    ]
    return rows
