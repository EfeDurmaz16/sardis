"""Funding runtime configuration helpers."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_DEFAULT_PROVIDER = object()


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


@dataclass(frozen=True)
class FundingAdapterRuntimeConfig:
    """Resolved primary, fallback, and ordered funding adapters."""

    primary_adapter: Any | None
    fallback_adapter: Any | None
    ordered_adapters: list[Any]


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


def configure_funding_adapters(
    settings: Any,
    *,
    treasury_provider: Any | None,
    stripe_funding_runtime: StripeFundingRuntimeConfig,
    environ: Mapping[str, str] | None = None,
    stripe_issuing_funding_adapter_cls: Any = _DEFAULT_PROVIDER,
    http_topup_funding_adapter_cls: Any = _DEFAULT_PROVIDER,
    circle_cpn_funding_adapter_cls: Any = _DEFAULT_PROVIDER,
) -> FundingAdapterRuntimeConfig:
    """Create primary and fallback stablecoin/treasury funding adapters."""
    env = environ if environ is not None else os.environ

    if stripe_issuing_funding_adapter_cls is _DEFAULT_PROVIDER:
        from sardis_v2_core.funding import StripeIssuingFundingAdapter

        stripe_issuing_funding_adapter_cls = StripeIssuingFundingAdapter
    if http_topup_funding_adapter_cls is _DEFAULT_PROVIDER:
        from sardis_v2_core.funding import HttpTopupFundingAdapter

        http_topup_funding_adapter_cls = HttpTopupFundingAdapter
    if circle_cpn_funding_adapter_cls is _DEFAULT_PROVIDER:
        from sardis_v2_core.cpn_funding_adapter import CircleCPNFundingAdapter

        circle_cpn_funding_adapter_cls = CircleCPNFundingAdapter

    def build_funding_adapter(adapter_name: str) -> Any | None:
        normalized = (adapter_name or "").strip().lower()
        if not normalized:
            return None
        if normalized == "stripe":
            if treasury_provider is None:
                logger.warning(
                    "Stripe treasury provider unavailable; cannot initialize Stripe funding adapter"
                )
                return None
            return stripe_issuing_funding_adapter_cls(treasury_provider)
        if normalized == "rain":
            rain_api_key = settings.rain.api_key or env.get("RAIN_API_KEY", "")
            if not rain_api_key:
                logger.warning("RAIN_API_KEY missing; cannot initialize Rain funding adapter")
                return None
            return http_topup_funding_adapter_cls(
                provider="rain",
                rail="stablecoin",
                base_url=settings.rain.base_url or "https://api.rain.xyz",
                api_key=rain_api_key,
                topup_path=settings.rain.funding_topup_path or "/v1/funding/topups",
                auth_style="bearer",
                program_id=settings.rain.program_id or env.get("RAIN_PROGRAM_ID", ""),
            )
        if normalized == "bridge":
            bridge_api_key = settings.bridge_cards.api_key or env.get("BRIDGE_API_KEY", "")
            if not bridge_api_key:
                logger.warning("BRIDGE_API_KEY missing; cannot initialize Bridge funding adapter")
                return None
            return http_topup_funding_adapter_cls(
                provider="bridge",
                rail="stablecoin",
                base_url=settings.bridge_cards.cards_base_url or "https://api.bridge.xyz",
                api_key=bridge_api_key,
                api_secret=settings.bridge_cards.api_secret or env.get("BRIDGE_API_SECRET", ""),
                topup_path=settings.bridge_cards.funding_topup_path or "/v1/funding/topups",
                auth_style="x_api_key",
                program_id=settings.bridge_cards.program_id or env.get("BRIDGE_PROGRAM_ID", ""),
            )
        if normalized == "coinbase_cdp":
            coinbase_topup_api_key = (
                settings.coinbase.topup_api_key
                or env.get("COINBASE_CDP_TOPUP_API_KEY", "")
            )
            if not coinbase_topup_api_key:
                logger.warning(
                    "COINBASE_CDP_TOPUP_API_KEY missing; cannot initialize Coinbase funding adapter"
                )
                return None
            return http_topup_funding_adapter_cls(
                provider="coinbase_cdp",
                rail="stablecoin",
                base_url=settings.coinbase.topup_base_url or "https://api.coinbase.com",
                api_key=coinbase_topup_api_key,
                topup_path=settings.coinbase.topup_path or "/v1/funding/topups",
                auth_style="bearer",
            )
        if normalized == "circle_cpn":
            if not stripe_funding_runtime.circle_cpn_api_key:
                logger.warning("CIRCLE_CPN_API_KEY missing; cannot initialize Circle CPN funding adapter")
                return None
            return circle_cpn_funding_adapter_cls(
                api_key=stripe_funding_runtime.circle_cpn_api_key,
                base_url=settings.circle_cpn.base_url or "https://api.circle.com",
                payout_path=settings.circle_cpn.payout_path or "/v1/cpn/payments",
                status_path=settings.circle_cpn.status_path or "/v1/cpn/payments/{payment_id}",
                auth_style=settings.circle_cpn.auth_style or "bearer",
                timeout_seconds=float(settings.circle_cpn.timeout_seconds),
                program_id=(
                    settings.circle_cpn.program_id
                    or env.get("SARDIS_CIRCLE_CPN__PROGRAM_ID", "")
                    or env.get("CIRCLE_CPN_PROGRAM_ID", "")
                ),
            )
        logger.warning(
            "Funding adapter '%s' requested but not wired in this deployment",
            normalized,
        )
        return None

    primary_adapter = build_funding_adapter(settings.funding.primary_adapter)
    fallback_adapter = build_funding_adapter(settings.funding.fallback_adapter or "")
    ordered_adapters = [
        adapter for adapter in (primary_adapter, fallback_adapter) if adapter is not None
    ]

    return FundingAdapterRuntimeConfig(
        primary_adapter=primary_adapter,
        fallback_adapter=fallback_adapter,
        ordered_adapters=ordered_adapters,
    )
