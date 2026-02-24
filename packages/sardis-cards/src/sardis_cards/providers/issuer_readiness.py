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
    return [
        _readiness(
            name="stripe_issuing",
            stablecoin_native=False,
            card_issuing=True,
            required_env=("STRIPE_API_KEY",),
            notes="Use STRIPE_SECRET_KEY as fallback in legacy envs.",
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
