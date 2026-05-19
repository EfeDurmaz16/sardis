"""Funding runtime configuration helpers."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StripeFundingRuntimeConfig:
    """Resolved Stripe/funding bootstrap settings used by provider routes."""

    stripe_api_key: str
    stripe_webhook_secret: str
    stripe_financial_account_id: str
    stripe_connected_account_default: str
    connected_account_map: dict[str, str]
    circle_cpn_api_key: str
    should_configure_funding_runtime: bool


def resolve_stripe_funding_runtime_config(
    settings: Any,
    *,
    environ: Mapping[str, str] | None = None,
) -> StripeFundingRuntimeConfig:
    """Resolve Stripe treasury and stablecoin funding configuration."""
    env = environ if environ is not None else os.environ
    stripe_settings = settings.stripe
    circle_cpn_settings = settings.circle_cpn
    rain_settings = settings.rain
    bridge_cards_settings = settings.bridge_cards
    coinbase_settings = settings.coinbase

    stripe_api_key = (
        getattr(stripe_settings, "api_key", "")
        or env.get("STRIPE_API_KEY", "")
        or env.get("STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret = getattr(stripe_settings, "webhook_secret", "") or env.get(
        "STRIPE_WEBHOOK_SECRET",
        "",
    )
    stripe_financial_account_id = getattr(
        stripe_settings,
        "treasury_financial_account_id",
        "",
    ) or env.get("STRIPE_TREASURY_FINANCIAL_ACCOUNT_ID", "")
    stripe_connected_account_default = getattr(
        stripe_settings,
        "connected_account_id",
        "",
    ) or env.get("STRIPE_CONNECTED_ACCOUNT_ID", "")
    connected_account_map_raw = getattr(
        stripe_settings,
        "connected_account_map_json",
        "",
    ) or env.get("STRIPE_CONNECTED_ACCOUNT_MAP_JSON", "")
    connected_account_map: dict[str, str] = {}
    if connected_account_map_raw:
        try:
            parsed = json.loads(connected_account_map_raw)
            if isinstance(parsed, dict):
                connected_account_map = {
                    str(org_id): str(acct_id)
                    for org_id, acct_id in parsed.items()
                    if str(acct_id).strip()
                }
            else:
                logger.warning("STRIPE_CONNECTED_ACCOUNT_MAP_JSON must be a JSON object")
        except json.JSONDecodeError:
            logger.warning("Invalid STRIPE_CONNECTED_ACCOUNT_MAP_JSON; ignoring")

    circle_cpn_api_key = (
        getattr(circle_cpn_settings, "api_key", "")
        or env.get("SARDIS_CIRCLE_CPN__API_KEY", "")
        or env.get("CIRCLE_CPN_API_KEY", "")
    )
    should_configure_funding_runtime = bool(
        stripe_api_key
        or circle_cpn_api_key
        or getattr(rain_settings, "api_key", "")
        or env.get("RAIN_API_KEY", "")
        or getattr(bridge_cards_settings, "api_key", "")
        or env.get("BRIDGE_API_KEY", "")
        or getattr(coinbase_settings, "topup_api_key", "")
        or env.get("COINBASE_CDP_TOPUP_API_KEY", "")
        or getattr(settings, "chain_mode", "") == "live"
    )

    return StripeFundingRuntimeConfig(
        stripe_api_key=stripe_api_key,
        stripe_webhook_secret=stripe_webhook_secret,
        stripe_financial_account_id=stripe_financial_account_id,
        stripe_connected_account_default=stripe_connected_account_default,
        connected_account_map=connected_account_map,
        circle_cpn_api_key=circle_cpn_api_key,
        should_configure_funding_runtime=should_configure_funding_runtime,
    )
