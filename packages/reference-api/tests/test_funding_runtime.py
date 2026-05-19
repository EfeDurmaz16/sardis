from types import SimpleNamespace

import pytest

from server.funding_runtime import (
    StripeFundingRuntimeConfig,
    configure_funding_adapters,
    configure_recurring_autofund_handler,
    resolve_stripe_funding_runtime_config,
)


def _settings(**overrides):
    defaults = {
        "chain_mode": "simulated",
        "stripe": SimpleNamespace(
            api_key="",
            webhook_secret="",
            treasury_financial_account_id="",
            connected_account_id="",
            connected_account_map_json="",
        ),
        "circle_cpn": SimpleNamespace(
            api_key="",
            base_url="",
            payout_path="",
            status_path="",
            auth_style="",
            timeout_seconds=10.0,
            program_id="",
        ),
        "rain": SimpleNamespace(api_key=""),
        "bridge_cards": SimpleNamespace(api_key=""),
        "coinbase": SimpleNamespace(
            topup_api_key="",
            topup_base_url="",
            topup_path="",
        ),
        "funding": SimpleNamespace(primary_adapter="", fallback_adapter=""),
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


def test_resolve_stripe_funding_runtime_prefers_settings_values() -> None:
    config = resolve_stripe_funding_runtime_config(
        _settings(
            stripe=SimpleNamespace(
                api_key="settings_stripe_key",
                webhook_secret="settings_webhook",
                treasury_financial_account_id="fa_settings",
                connected_account_id="acct_settings",
                connected_account_map_json='{"org_a":"acct_a","org_blank":""}',
            ),
            circle_cpn=SimpleNamespace(api_key="settings_cpn_key"),
        ),
        environ={
            "STRIPE_API_KEY": "env_stripe_key",
            "STRIPE_CONNECTED_ACCOUNT_ID": "acct_env",
            "SARDIS_CIRCLE_CPN__API_KEY": "env_cpn_key",
        },
    )

    assert config.stripe_api_key == "settings_stripe_key"
    assert config.stripe_webhook_secret == "settings_webhook"
    assert config.stripe_financial_account_id == "fa_settings"
    assert config.stripe_connected_account_default == "acct_settings"
    assert config.connected_account_map == {"org_a": "acct_a"}
    assert config.circle_cpn_api_key == "settings_cpn_key"
    assert config.should_configure_funding_runtime is True


def test_resolve_stripe_funding_runtime_falls_back_to_env_values() -> None:
    config = resolve_stripe_funding_runtime_config(
        _settings(),
        environ={
            "STRIPE_SECRET_KEY": "env_secret_key",
            "STRIPE_WEBHOOK_SECRET": "env_webhook",
            "STRIPE_TREASURY_FINANCIAL_ACCOUNT_ID": "fa_env",
            "STRIPE_CONNECTED_ACCOUNT_ID": "acct_env",
            "STRIPE_CONNECTED_ACCOUNT_MAP_JSON": '{"org_env":"acct_env_2"}',
            "CIRCLE_CPN_API_KEY": "cpn_env",
        },
    )

    assert config.stripe_api_key == "env_secret_key"
    assert config.stripe_webhook_secret == "env_webhook"
    assert config.stripe_financial_account_id == "fa_env"
    assert config.stripe_connected_account_default == "acct_env"
    assert config.connected_account_map == {"org_env": "acct_env_2"}
    assert config.circle_cpn_api_key == "cpn_env"
    assert config.should_configure_funding_runtime is True


def test_resolve_stripe_funding_runtime_ignores_invalid_connected_account_map() -> None:
    config = resolve_stripe_funding_runtime_config(
        _settings(),
        environ={"STRIPE_CONNECTED_ACCOUNT_MAP_JSON": "not-json"},
    )

    assert config.connected_account_map == {}
    assert config.should_configure_funding_runtime is False


def test_resolve_stripe_funding_runtime_enables_for_live_chain_without_provider_keys() -> None:
    config = resolve_stripe_funding_runtime_config(
        _settings(chain_mode="live"),
        environ={},
    )

    assert config.should_configure_funding_runtime is True


def test_resolve_stripe_funding_runtime_enables_for_non_stripe_adapter_credentials() -> None:
    rain_config = resolve_stripe_funding_runtime_config(
        _settings(rain=SimpleNamespace(api_key="rain_settings_key")),
        environ={},
    )
    bridge_config = resolve_stripe_funding_runtime_config(
        _settings(),
        environ={"BRIDGE_API_KEY": "bridge_env_key"},
    )
    coinbase_config = resolve_stripe_funding_runtime_config(
        _settings(coinbase=SimpleNamespace(topup_api_key="coinbase_settings_key")),
        environ={},
    )

    assert rain_config.should_configure_funding_runtime is True
    assert bridge_config.should_configure_funding_runtime is True
    assert coinbase_config.should_configure_funding_runtime is True


class FakeStripeIssuingFundingAdapter:
    def __init__(self, treasury_provider: object) -> None:
        self.treasury_provider = treasury_provider


class FakeHttpTopupFundingAdapter:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class FakeCircleCPNFundingAdapter:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


def _runtime_config(circle_cpn_api_key: str = "") -> StripeFundingRuntimeConfig:
    return StripeFundingRuntimeConfig(
        stripe_api_key="",
        stripe_webhook_secret="",
        stripe_financial_account_id="",
        stripe_connected_account_default="",
        connected_account_map={},
        circle_cpn_api_key=circle_cpn_api_key,
        should_configure_funding_runtime=True,
    )


def _configure_adapters(settings=None, environ=None, treasury_provider=None, cpn_key=""):
    return configure_funding_adapters(
        settings or _settings(),
        treasury_provider=treasury_provider,
        stripe_funding_runtime=_runtime_config(cpn_key),
        environ=environ or {},
        stripe_issuing_funding_adapter_cls=FakeStripeIssuingFundingAdapter,
        http_topup_funding_adapter_cls=FakeHttpTopupFundingAdapter,
        circle_cpn_funding_adapter_cls=FakeCircleCPNFundingAdapter,
    )


def test_configure_funding_adapters_builds_stripe_primary() -> None:
    treasury_provider = object()
    config = _configure_adapters(
        settings=_settings(funding=SimpleNamespace(primary_adapter="stripe", fallback_adapter="")),
        treasury_provider=treasury_provider,
    )

    assert isinstance(config.primary_adapter, FakeStripeIssuingFundingAdapter)
    assert config.primary_adapter.treasury_provider is treasury_provider
    assert config.fallback_adapter is None
    assert config.ordered_adapters == [config.primary_adapter]


def test_configure_funding_adapters_skips_stripe_without_treasury_provider() -> None:
    config = _configure_adapters(
        settings=_settings(funding=SimpleNamespace(primary_adapter="stripe", fallback_adapter="")),
    )

    assert config.primary_adapter is None
    assert config.ordered_adapters == []


def test_configure_funding_adapters_builds_rain_bridge_and_coinbase() -> None:
    rain_config = _configure_adapters(
        settings=_settings(
            funding=SimpleNamespace(primary_adapter="rain", fallback_adapter="bridge"),
            rain=SimpleNamespace(
                api_key="rain_key",
                base_url="https://rain.example",
                funding_topup_path="/rain/topups",
                program_id="rain_program",
            ),
            bridge_cards=SimpleNamespace(
                api_key="bridge_key",
                api_secret="bridge_secret",
                cards_base_url="https://bridge.example",
                funding_topup_path="/bridge/topups",
                program_id="bridge_program",
            ),
        )
    )
    coinbase_config = _configure_adapters(
        settings=_settings(
            funding=SimpleNamespace(primary_adapter="coinbase_cdp", fallback_adapter=""),
            coinbase=SimpleNamespace(
                topup_api_key="coinbase_key",
                topup_base_url="https://coinbase.example",
                topup_path="/coinbase/topups",
            ),
        )
    )

    assert rain_config.primary_adapter.kwargs == {
        "provider": "rain",
        "rail": "stablecoin",
        "base_url": "https://rain.example",
        "api_key": "rain_key",
        "topup_path": "/rain/topups",
        "auth_style": "bearer",
        "program_id": "rain_program",
    }
    assert rain_config.fallback_adapter.kwargs == {
        "provider": "bridge",
        "rail": "stablecoin",
        "base_url": "https://bridge.example",
        "api_key": "bridge_key",
        "api_secret": "bridge_secret",
        "topup_path": "/bridge/topups",
        "auth_style": "x_api_key",
        "program_id": "bridge_program",
    }
    assert coinbase_config.primary_adapter.kwargs == {
        "provider": "coinbase_cdp",
        "rail": "stablecoin",
        "base_url": "https://coinbase.example",
        "api_key": "coinbase_key",
        "topup_path": "/coinbase/topups",
        "auth_style": "bearer",
    }


def test_configure_funding_adapters_builds_circle_cpn_from_runtime_config() -> None:
    config = _configure_adapters(
        settings=_settings(
            funding=SimpleNamespace(primary_adapter="circle_cpn", fallback_adapter=""),
            circle_cpn=SimpleNamespace(
                api_key="",
                base_url="https://circle.example",
                payout_path="/payouts",
                status_path="/status/{payment_id}",
                auth_style="x_api_key",
                timeout_seconds=3.5,
                program_id="circle_program",
            ),
        ),
        cpn_key="runtime_cpn_key",
    )

    assert isinstance(config.primary_adapter, FakeCircleCPNFundingAdapter)
    assert config.primary_adapter.kwargs == {
        "api_key": "runtime_cpn_key",
        "base_url": "https://circle.example",
        "payout_path": "/payouts",
        "status_path": "/status/{payment_id}",
        "auth_style": "x_api_key",
        "timeout_seconds": 3.5,
        "program_id": "circle_program",
    }


def test_configure_funding_adapters_skips_unknown_and_missing_credentials() -> None:
    config = _configure_adapters(
        settings=_settings(
            funding=SimpleNamespace(primary_adapter="unknown", fallback_adapter="rain"),
        ),
        environ={},
    )

    assert config.primary_adapter is None
    assert config.fallback_adapter is None
    assert config.ordered_adapters == []


class FakeRecurringBillingService:
    def __init__(self) -> None:
        self.handler = None
        self.allow_simulated_fallback = None

    def configure_autofund_handler(self, handler, *, allow_simulated_fallback: bool) -> None:
        self.handler = handler
        self.allow_simulated_fallback = allow_simulated_fallback


class FakeFundingRequest:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


def _token_type(token_raw: str) -> str:
    if token_raw not in {"USDC", "EURC"}:
        raise ValueError(token_raw)
    return token_raw


@pytest.mark.asyncio
async def test_configure_recurring_autofund_handler_routes_request() -> None:
    service = FakeRecurringBillingService()
    adapter = object()
    captured = {}

    async def execute_funding_with_failover(adapters, request):
        captured["adapters"] = adapters
        captured["request"] = request
        return SimpleNamespace(provider="rain", transfer_id="tr_123"), [object(), object()]

    configured = configure_recurring_autofund_handler(
        service,
        [adapter],
        chain_mode="live",
        funding_request_cls=FakeFundingRequest,
        execute_funding_with_failover_func=execute_funding_with_failover,
        token_type_cls=_token_type,
        normalize_token_amount_func=lambda token_type, amount_minor: amount_minor / 100,
    )

    assert configured is True
    assert service.allow_simulated_fallback is False
    assert await service.handler(
        {
            "id": "sub_123",
            "wallet_id": "wallet_123",
            "chain": "base",
            "token": "usdc",
        },
        1234,
    ) == "tr_123"
    assert captured["adapters"] == [adapter]
    assert captured["request"].kwargs == {
        "amount": 12.34,
        "currency": "USD",
        "description": "Recurring auto-fund for subscription sub_123",
        "metadata": {
            "source": "recurring_billing",
            "subscription_id": "sub_123",
            "wallet_id": "wallet_123",
            "chain": "base",
            "token": "USDC",
        },
    }


@pytest.mark.asyncio
async def test_configure_recurring_autofund_handler_rejects_invalid_requests() -> None:
    service = FakeRecurringBillingService()

    async def execute_funding_with_failover(adapters, request):
        return SimpleNamespace(provider="rain", transfer_id="tr_123"), []

    configure_recurring_autofund_handler(
        service,
        [object()],
        chain_mode="live",
        funding_request_cls=FakeFundingRequest,
        execute_funding_with_failover_func=execute_funding_with_failover,
        token_type_cls=_token_type,
        normalize_token_amount_func=lambda token_type, amount_minor: amount_minor,
    )

    with pytest.raises(ValueError, match="unsupported_autofund_token:BAD"):
        await service.handler({"token": "bad"}, 100)
    with pytest.raises(ValueError, match="autofund_amount_must_be_positive"):
        await service.handler({"token": "USDC"}, 0)


def test_configure_recurring_autofund_handler_fails_closed_in_live_mode() -> None:
    service = FakeRecurringBillingService()

    configured = configure_recurring_autofund_handler(
        service,
        [],
        chain_mode="live",
    )

    assert configured is False
    assert service.handler is None
    assert service.allow_simulated_fallback is False


def test_configure_recurring_autofund_handler_leaves_simulated_mode_unconfigured() -> None:
    service = FakeRecurringBillingService()

    configured = configure_recurring_autofund_handler(
        service,
        [],
        chain_mode="simulated",
    )

    assert configured is False
    assert service.handler is None
    assert service.allow_simulated_fallback is None
