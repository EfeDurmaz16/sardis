"""Virtual card runtime bootstrap helpers."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Mapping

logger = logging.getLogger(__name__)

_DEFAULT_PROVIDER = object()


@dataclass(frozen=True)
class CardRuntimeConfig:
    """Resolved virtual-card repository, provider adapter, and webhook handlers."""

    cards_enabled: bool
    card_repository: Any | None
    card_provider: Any | None
    webhook_secret: str | None
    asa_handler: Any | None
    rain_webhook_secret: str
    bridge_webhook_secret: str


def configure_card_runtime(
    settings: Any,
    *,
    database_url: str,
    use_postgres: bool,
    policy_store: Any,
    wallet_repository: Any,
    agent_repository: Any,
    environ: Mapping[str, str] | None = None,
    card_repository_cls: Any = _DEFAULT_PROVIDER,
    card_provider_adapter_cls: Any = _DEFAULT_PROVIDER,
    mock_provider_cls: Any = _DEFAULT_PROVIDER,
    lithic_provider_cls: Any = _DEFAULT_PROVIDER,
    stripe_issuing_provider_cls: Any = _DEFAULT_PROVIDER,
    rain_cards_provider_cls: Any = _DEFAULT_PROVIDER,
    bridge_cards_provider_cls: Any = _DEFAULT_PROVIDER,
    card_provider_router_cls: Any = _DEFAULT_PROVIDER,
    organization_card_provider_router_cls: Any = _DEFAULT_PROVIDER,
    asa_handler_cls: Any = _DEFAULT_PROVIDER,
    card_webhook_handler_cls: Any = _DEFAULT_PROVIDER,
) -> CardRuntimeConfig:
    """Create optional virtual-card route dependencies outside the app factory."""
    env = environ if environ is not None else os.environ
    cards_enabled = env.get("SARDIS_ENABLE_CARDS", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if not cards_enabled:
        return CardRuntimeConfig(
            cards_enabled=False,
            card_repository=None,
            card_provider=None,
            webhook_secret=None,
            asa_handler=None,
            rain_webhook_secret="",
            bridge_webhook_secret="",
        )

    cards_settings = settings.cards
    lithic_settings = settings.lithic
    stripe_settings = settings.stripe
    rain_settings = settings.rain
    bridge_cards_settings = settings.bridge_cards

    if card_repository_cls is _DEFAULT_PROVIDER:
        from .repositories.card_repository import CardRepository

        card_repository_cls = CardRepository
    if card_provider_adapter_cls is _DEFAULT_PROVIDER:
        from .card_adapter import CardProviderCompatAdapter

        card_provider_adapter_cls = CardProviderCompatAdapter
    if mock_provider_cls is _DEFAULT_PROVIDER:
        from sardis_cards.providers.mock import MockProvider

        mock_provider_cls = MockProvider

    card_repository = card_repository_cls(dsn=database_url if use_postgres else None)
    configured_primary = (
        getattr(cards_settings, "primary_provider", "") or "mock"
    ).strip().lower()
    configured_fallback = (
        getattr(cards_settings, "fallback_provider", "") or ""
    ).strip().lower()
    lithic_api_key = getattr(lithic_settings, "api_key", "") or env.get(
        "LITHIC_API_KEY",
        "",
    )
    stripe_api_key = (
        getattr(stripe_settings, "api_key", "")
        or env.get("STRIPE_API_KEY", "")
        or env.get("STRIPE_SECRET_KEY", "")
    )
    stripe_webhook_secret = getattr(stripe_settings, "webhook_secret", "") or env.get(
        "STRIPE_WEBHOOK_SECRET",
        "",
    )
    provider_cache: dict[str, object] = {}

    def build_provider(provider_name: str) -> Any | None:
        cached = provider_cache.get(provider_name)
        if cached is not None:
            return cached
        if provider_name == "lithic":
            if not lithic_api_key:
                logger.warning("LITHIC_API_KEY missing; cannot initialize Lithic provider")
                return None
            try:
                provider_cls = lithic_provider_cls
                if provider_cls is _DEFAULT_PROVIDER:
                    from sardis_cards.providers.lithic import LithicProvider

                    provider_cls = LithicProvider
                provider = provider_cls(
                    api_key=lithic_api_key,
                    environment=getattr(lithic_settings, "environment", ""),
                )
                provider_cache[provider_name] = provider
                return provider
            except Exception as exc:
                logger.warning("Lithic provider init failed: %s", exc)
                return None
        if provider_name == "stripe_issuing":
            if not stripe_api_key:
                logger.warning(
                    "STRIPE_API_KEY/STRIPE_SECRET_KEY missing; cannot initialize Stripe Issuing provider"
                )
                return None
            try:
                provider_cls = stripe_issuing_provider_cls
                if provider_cls is _DEFAULT_PROVIDER:
                    from sardis_cards.providers.stripe_issuing import (
                        StripeIssuingProvider,
                    )

                    provider_cls = StripeIssuingProvider

                async def stripe_policy_evaluator(
                    wallet_id: str,
                    amount,
                    mcc_code: str,
                    merchant_name: str,
                ) -> tuple[bool, str]:
                    from decimal import Decimal

                    del merchant_name
                    amount_decimal = Decimal(str(amount))
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
                        from sardis.core.mcc_service import get_mcc_info

                        mcc_info = get_mcc_info(mcc_code)
                        if mcc_info:
                            merchant_category = mcc_info.category
                    return policy.validate_payment(
                        amount=amount_decimal,
                        fee=Decimal("0"),
                        mcc_code=mcc_code,
                        merchant_category=merchant_category,
                    )

                provider = provider_cls(
                    api_key=stripe_api_key,
                    webhook_secret=stripe_webhook_secret or None,
                    policy_evaluator=stripe_policy_evaluator,
                )
                provider_cache[provider_name] = provider
                return provider
            except Exception as exc:
                logger.warning("Stripe Issuing provider init failed: %s", exc)
                return None
        if provider_name == "mock":
            provider = mock_provider_cls()
            provider_cache[provider_name] = provider
            return provider
        if provider_name == "rain":
            rain_api_key = getattr(rain_settings, "api_key", "") or env.get(
                "RAIN_API_KEY",
                "",
            )
            if not rain_api_key:
                logger.warning("RAIN_API_KEY missing; cannot initialize Rain provider")
                return None
            try:
                provider_cls = rain_cards_provider_cls
                if provider_cls is _DEFAULT_PROVIDER:
                    from sardis_cards.providers.partner_issuers import RainCardsProvider

                    provider_cls = RainCardsProvider
                provider = provider_cls(
                    api_key=rain_api_key,
                    base_url=getattr(rain_settings, "base_url", "")
                    or env.get("RAIN_BASE_URL", "https://api.rain.xyz"),
                    program_id=getattr(rain_settings, "program_id", "")
                    or env.get("RAIN_PROGRAM_ID", ""),
                    path_map=getattr(rain_settings, "cards_path_map_json", "")
                    or env.get("RAIN_CARDS_PATH_MAP_JSON", ""),
                    method_map=getattr(rain_settings, "cards_method_map_json", "")
                    or env.get("RAIN_CARDS_METHOD_MAP_JSON", ""),
                )
                provider_cache[provider_name] = provider
                return provider
            except Exception as exc:
                logger.warning("Rain provider init failed: %s", exc)
                return None
        if provider_name == "bridge_cards":
            bridge_api_key = getattr(bridge_cards_settings, "api_key", "") or env.get(
                "BRIDGE_API_KEY",
                "",
            )
            if not bridge_api_key:
                logger.warning("BRIDGE_API_KEY missing; cannot initialize Bridge cards provider")
                return None
            try:
                provider_cls = bridge_cards_provider_cls
                if provider_cls is _DEFAULT_PROVIDER:
                    from sardis_cards.providers.partner_issuers import BridgeCardsProvider

                    provider_cls = BridgeCardsProvider
                provider = provider_cls(
                    api_key=bridge_api_key,
                    api_secret=getattr(bridge_cards_settings, "api_secret", "")
                    or env.get("BRIDGE_API_SECRET", ""),
                    base_url=getattr(bridge_cards_settings, "cards_base_url", "")
                    or env.get("BRIDGE_CARDS_BASE_URL", "https://api.bridge.xyz"),
                    program_id=getattr(bridge_cards_settings, "program_id", "")
                    or env.get("BRIDGE_PROGRAM_ID", ""),
                    path_map=getattr(
                        bridge_cards_settings,
                        "cards_path_map_json",
                        "",
                    )
                    or env.get("BRIDGE_CARDS_PATH_MAP_JSON", ""),
                    method_map=getattr(
                        bridge_cards_settings,
                        "cards_method_map_json",
                        "",
                    )
                    or env.get("BRIDGE_CARDS_METHOD_MAP_JSON", ""),
                )
                provider_cache[provider_name] = provider
                return provider
            except Exception as exc:
                logger.warning("Bridge cards provider init failed: %s", exc)
                return None
        logger.warning("Unknown card provider configured: %s", provider_name)
        return None

    primary_provider = build_provider(configured_primary)
    fallback_provider = None
    if configured_fallback and configured_fallback != configured_primary:
        fallback_provider = build_provider(configured_fallback)

    if primary_provider is None and fallback_provider is not None:
        provider_impl = fallback_provider
        logger.info(
            "Primary card provider unavailable; using fallback provider=%s",
            configured_fallback,
        )
    elif primary_provider is None:
        provider_impl = mock_provider_cls()
        logger.warning("No card provider could be initialized; using MockProvider")
    elif fallback_provider is not None:
        provider_router_cls = card_provider_router_cls
        if provider_router_cls is _DEFAULT_PROVIDER:
            from sardis_cards.providers.router import CardProviderRouter

            provider_router_cls = CardProviderRouter
        provider_impl = provider_router_cls(primary=primary_provider, fallback=fallback_provider)
        logger.info(
            "Cards enabled with routed providers primary=%s fallback=%s",
            configured_primary,
            configured_fallback,
        )
    else:
        provider_impl = primary_provider
        logger.info("Cards enabled with provider=%s", configured_primary)

    org_overrides_raw = getattr(cards_settings, "org_provider_overrides_json", "") or env.get(
        "SARDIS_CARDS_ORG_PROVIDER_OVERRIDES_JSON",
        "",
    )
    if org_overrides_raw and wallet_repository and agent_repository:
        try:
            parsed = json.loads(org_overrides_raw)
        except json.JSONDecodeError:
            parsed = {}
            logger.warning("Invalid SARDIS_CARDS_ORG_PROVIDER_OVERRIDES_JSON; ignoring")
        if isinstance(parsed, dict) and parsed:
            org_provider_map: dict[str, object] = {}
            for org_id, provider_name in parsed.items():
                provider_name_str = str(provider_name).strip().lower()
                provider_candidate = build_provider(provider_name_str)
                if provider_candidate is None:
                    logger.warning(
                        "Could not initialize org-specific provider '%s' for org=%s",
                        provider_name_str,
                        org_id,
                    )
                    continue
                org_provider_map[str(org_id)] = provider_candidate
            if org_provider_map:
                org_router_cls = organization_card_provider_router_cls
                if org_router_cls is _DEFAULT_PROVIDER:
                    from sardis_cards.providers.org_router import (
                        OrganizationCardProviderRouter,
                    )

                    org_router_cls = OrganizationCardProviderRouter

                async def resolve_wallet_org(wallet_id: str) -> str | None:
                    wallet = await wallet_repository.get(wallet_id)
                    if not wallet:
                        return None
                    agent = await agent_repository.get(wallet.agent_id)
                    if not agent or not getattr(agent, "owner_id", None):
                        return None
                    return str(agent.owner_id)

                provider_impl = org_router_cls(
                    default_provider=provider_impl,
                    providers_by_org=org_provider_map,
                    wallet_org_resolver=resolve_wallet_org,
                )
                logger.info(
                    "Cards org provider overrides enabled for %d org(s)",
                    len(org_provider_map),
                )

    card_provider = card_provider_adapter_cls(provider_impl, card_repository)
    webhook_secret = getattr(lithic_settings, "webhook_secret", "") or env.get(
        "LITHIC_WEBHOOK_SECRET",
    )
    asa_handler = None
    asa_secret = (
        getattr(lithic_settings, "asa_webhook_secret", "")
        or env.get("LITHIC_ASA_WEBHOOK_SECRET", "")
        or getattr(lithic_settings, "webhook_secret", "")
        or env.get("LITHIC_WEBHOOK_SECRET", "")
    )
    lithic_present = configured_primary == "lithic" or configured_fallback == "lithic"
    if lithic_present and getattr(lithic_settings, "asa_enabled", False):
        if not asa_secret:
            logger.warning("LITHIC_ASA is enabled but no ASA webhook secret is configured")
        else:
            handler_cls = asa_handler_cls
            webhook_handler_cls = card_webhook_handler_cls
            if handler_cls is _DEFAULT_PROVIDER or webhook_handler_cls is _DEFAULT_PROVIDER:
                from sardis_cards.webhooks import ASAHandler, CardWebhookHandler

                handler_cls = ASAHandler if handler_cls is _DEFAULT_PROVIDER else handler_cls
                webhook_handler_cls = (
                    CardWebhookHandler
                    if webhook_handler_cls is _DEFAULT_PROVIDER
                    else webhook_handler_cls
                )

            async def lookup_provider_card(card_token: str):
                if hasattr(provider_impl, "get_card"):
                    return await provider_impl.get_card(card_token)
                return None

            asa_handler = handler_cls(
                webhook_handler=webhook_handler_cls(secret=asa_secret, provider="lithic"),
                card_lookup=lookup_provider_card,
            )
            logger.info("Lithic ASA handler enabled")

    return CardRuntimeConfig(
        cards_enabled=True,
        card_repository=card_repository,
        card_provider=card_provider,
        webhook_secret=webhook_secret,
        asa_handler=asa_handler,
        rain_webhook_secret=getattr(rain_settings, "webhook_secret", "")
        or env.get("RAIN_WEBHOOK_SECRET", ""),
        bridge_webhook_secret=getattr(bridge_cards_settings, "webhook_secret", "")
        or env.get("BRIDGE_CARDS_WEBHOOK_SECRET", ""),
    )
