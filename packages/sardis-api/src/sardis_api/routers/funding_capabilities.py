"""Funding capability matrix endpoints."""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from fastapi import APIRouter, Depends

from sardis_api.authz import Principal, require_principal
from sardis_cards.providers.issuer_readiness import evaluate_issuer_readiness
from sardis_v2_core.config import load_settings

router = APIRouter(prefix="/funding", tags=["funding"])


@dataclass
class FundingCapabilitiesDeps:
    settings: Any = None


def get_deps() -> FundingCapabilitiesDeps:
    raise NotImplementedError("Dependency override required")


def _resolve_settings(deps: FundingCapabilitiesDeps):
    if deps.settings is not None:
        return deps.settings
    return load_settings()


@router.get("/capabilities")
async def get_funding_capability_matrix(
    deps: FundingCapabilitiesDeps = Depends(get_deps),
    _: Principal = Depends(require_principal),
):
    settings = _resolve_settings(deps)
    issuer_rows = {row.name: row for row in evaluate_issuer_readiness()}

    stripe_financial_account_id = (
        getattr(settings.stripe, "treasury_financial_account_id", "")
        or os.getenv("STRIPE_TREASURY_FINANCIAL_ACCOUNT_ID", "")
    ).strip()
    stripe_connected_account = (
        getattr(settings.stripe, "connected_account_id", "")
        or os.getenv("STRIPE_CONNECTED_ACCOUNT_ID", "")
    ).strip()

    providers: list[dict[str, Any]] = []
    for provider_name in ("stripe_issuing", "lithic", "rain", "bridge_cards"):
        row = issuer_rows.get(provider_name)
        if row is None:
            continue

        missing_env = list(row.missing_env)
        fiat_ready = False
        if provider_name == "stripe_issuing":
            fiat_ready = row.configured and bool(stripe_financial_account_id)
            if row.configured and not stripe_financial_account_id:
                missing_env.append("STRIPE_TREASURY_FINANCIAL_ACCOUNT_ID")
        elif provider_name == "lithic":
            fiat_ready = row.configured

        providers.append(
            {
                "provider": provider_name,
                "configured": bool(row.configured),
                "card_issuing_ready": bool(row.card_issuing and row.configured),
                "funding_fiat_ready": bool(fiat_ready),
                "funding_stablecoin_ready": bool(row.stablecoin_native and row.configured),
                "onchain_rail_ready": False,
                "stablecoin_native": bool(row.stablecoin_native),
                "required_env": list(row.required_env),
                "missing_env": missing_env,
                "notes": row.notes,
            }
        )

    coinbase_key_name = (
        getattr(settings.coinbase, "api_key_name", "")
        or os.getenv("COINBASE_CDP_API_KEY_NAME", "")
    ).strip()
    coinbase_key_private = (
        getattr(settings.coinbase, "api_key_private_key", "")
        or os.getenv("COINBASE_CDP_API_KEY_PRIVATE_KEY", "")
    ).strip()
    coinbase_ready = bool(coinbase_key_name and coinbase_key_private)
    coinbase_missing = []
    if not coinbase_key_name:
        coinbase_missing.append("COINBASE_CDP_API_KEY_NAME")
    if not coinbase_key_private:
        coinbase_missing.append("COINBASE_CDP_API_KEY_PRIVATE_KEY")

    providers.append(
        {
            "provider": "coinbase_cdp",
            "configured": coinbase_ready,
            "card_issuing_ready": False,
            "funding_fiat_ready": False,
            "funding_stablecoin_ready": coinbase_ready,
            "onchain_rail_ready": coinbase_ready,
            "stablecoin_native": True,
            "required_env": [
                "COINBASE_CDP_API_KEY_NAME",
                "COINBASE_CDP_API_KEY_PRIVATE_KEY",
            ],
            "missing_env": coinbase_missing,
            "notes": "On-chain stablecoin rail and x402 execution path.",
        }
    )

    fiat_ready_providers = sorted(
        [entry["provider"] for entry in providers if entry["funding_fiat_ready"]]
    )
    stablecoin_ready_providers = sorted(
        [entry["provider"] for entry in providers if entry["funding_stablecoin_ready"]]
    )

    return {
        "primary_provider": getattr(settings.cards, "primary_provider", None),
        "fallback_provider": getattr(settings.cards, "fallback_provider", None),
        "on_chain_provider": getattr(settings.cards, "on_chain_provider", None),
        "default_fiat_connected_account": stripe_connected_account or None,
        "providers": providers,
        "rails": {
            "fiat_ready_providers": fiat_ready_providers,
            "stablecoin_ready_providers": stablecoin_ready_providers,
        },
    }
