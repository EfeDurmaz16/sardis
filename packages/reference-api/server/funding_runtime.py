"""Funding runtime configuration helpers."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
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


def configure_recurring_autofund_handler(
    recurring_billing_service: Any,
    ordered_funding_adapters: list[Any],
    *,
    chain_mode: str,
    funding_request_cls: Any = _DEFAULT_PROVIDER,
    execute_funding_with_failover_func: Any = _DEFAULT_PROVIDER,
    token_type_cls: Any = _DEFAULT_PROVIDER,
    normalize_token_amount_func: Any = _DEFAULT_PROVIDER,
) -> bool:
    """Wire recurring billing auto-fund execution for configured adapters."""
    if ordered_funding_adapters:
        if funding_request_cls is _DEFAULT_PROVIDER:
            from sardis_v2_core.funding import FundingRequest

            funding_request_cls = FundingRequest
        if execute_funding_with_failover_func is _DEFAULT_PROVIDER:
            from sardis_v2_core.funding import execute_funding_with_failover

            execute_funding_with_failover_func = execute_funding_with_failover
        if token_type_cls is _DEFAULT_PROVIDER:
            from sardis_v2_core.tokens import TokenType

            token_type_cls = TokenType
        if normalize_token_amount_func is _DEFAULT_PROVIDER:
            from sardis_v2_core.tokens import normalize_token_amount

            normalize_token_amount_func = normalize_token_amount

        async def recurring_autofund_handler(
            subscription: dict[str, object],
            amount_minor: int,
        ) -> str:
            token_raw = str(subscription.get("token") or "USDC").upper()
            try:
                token_type = token_type_cls(token_raw)
            except ValueError as exc:
                raise ValueError(f"unsupported_autofund_token:{token_raw}") from exc
            amount = normalize_token_amount_func(token_type, max(int(amount_minor), 0))
            if amount <= 0:
                raise ValueError("autofund_amount_must_be_positive")
            request = funding_request_cls(
                amount=amount,
                currency="USD",
                description=f"Recurring auto-fund for subscription {subscription.get('id', 'unknown')}",
                metadata={
                    "source": "recurring_billing",
                    "subscription_id": str(subscription.get("id", "")),
                    "wallet_id": str(subscription.get("wallet_id", "")),
                    "chain": str(subscription.get("chain", "")),
                    "token": token_raw,
                },
            )
            transfer, attempts = await execute_funding_with_failover_func(
                ordered_funding_adapters,
                request,
            )
            logger.info(
                "Recurring auto-fund routed provider=%s transfer_id=%s attempts=%d",
                transfer.provider,
                transfer.transfer_id,
                len(attempts),
            )
            return transfer.transfer_id

        recurring_billing_service.configure_autofund_handler(
            recurring_autofund_handler,
            allow_simulated_fallback=False,
        )
        return True

    if chain_mode == "live":
        recurring_billing_service.configure_autofund_handler(
            None,
            allow_simulated_fallback=False,
        )
        logger.warning(
            "Live recurring auto-fund is enabled but no funding adapters are configured; "
            "autofund requests will fail closed."
        )

    return False


def configure_stripe_webhook_issuing_provider(
    *,
    stripe_api_key: str,
    stripe_webhook_secret: str,
    policy_store: Any,
    wallet_repository: Any,
    issuing_provider_cls: Any = _DEFAULT_PROVIDER,
    mcc_info_resolver: Any = _DEFAULT_PROVIDER,
) -> Any:
    """Create the Stripe Issuing webhook provider with payment policy evaluation."""
    if issuing_provider_cls is _DEFAULT_PROVIDER:
        from sardis_cards.providers.stripe_issuing import StripeIssuingProvider

        issuing_provider_cls = StripeIssuingProvider
    if mcc_info_resolver is _DEFAULT_PROVIDER:
        from sardis_v2_core.mcc_service import get_mcc_info

        mcc_info_resolver = get_mcc_info

    async def stripe_webhooks_policy_evaluator(
        wallet_id: str,
        amount: Any,
        mcc_code: str,
        merchant_name: str,
    ) -> tuple[bool, str]:
        normalized_amount = Decimal(str(amount))
        if not policy_store or not wallet_repository:
            return True, "OK"
        wallet = await wallet_repository.get(wallet_id)
        if not wallet:
            return True, "OK"
        policy = await policy_store.fetch_policy(wallet.agent_id)
        if not policy:
            return True, "OK"

        merchant_category = None
        if mcc_code:
            mcc_info = mcc_info_resolver(mcc_code)
            if mcc_info:
                merchant_category = mcc_info.category

        return policy.validate_payment(
            amount=normalized_amount,
            fee=Decimal("0"),
            mcc_code=mcc_code,
            merchant_category=merchant_category,
        )

    return issuing_provider_cls(
        api_key=stripe_api_key,
        webhook_secret=stripe_webhook_secret,
        policy_evaluator=stripe_webhooks_policy_evaluator,
    )
