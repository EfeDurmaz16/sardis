from types import SimpleNamespace

from server.funding_runtime import resolve_stripe_funding_runtime_config


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
        "circle_cpn": SimpleNamespace(api_key=""),
        "rain": SimpleNamespace(api_key=""),
        "bridge_cards": SimpleNamespace(api_key=""),
        "coinbase": SimpleNamespace(topup_api_key=""),
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
