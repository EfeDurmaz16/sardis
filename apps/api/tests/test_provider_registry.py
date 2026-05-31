"""Tests for the unified provider port layer: types, registry, adapters.

Proves the three registry invariants:
  1. real impl when a provider's keys are set,
  2. sandbox impl when keys are absent (dev/test run green without live keys),
  3. fail-closed in production for required capabilities without keys.
"""

from __future__ import annotations

import time
from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.ports import (
    BridgePort,
    CardPort,
    CustodyModel,
    CustodyPort,
    FiatAccountPort,
    KycPort,
    KytPort,
    OfframpPort,
    OnrampPort,
    ProviderCapability,
    ProviderNotConfigured,
    SwapPort,
    from_minor_units,
    to_minor_units,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import (
    SandboxBridgePort,
    SandboxCardPort,
    SandboxCustodyPort,
    SandboxFiatAccountPort,
    SandboxKycPort,
    SandboxKytPort,
    SandboxOfframpPort,
    SandboxOnrampPort,
    SandboxSwapPort,
)


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


def _prod_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=True, database_url="", circle_cpn=SimpleNamespace())


# ---------------------------------------------------------------------------
# Money helpers — no float on money paths
# ---------------------------------------------------------------------------


class TestMoneyHelpers:
    def test_to_minor_units_exact(self):
        assert to_minor_units(Decimal("1.50"), 2) == 150
        assert to_minor_units("10", 6) == 10_000_000
        assert to_minor_units(0, 2) == 0

    def test_to_minor_units_rejects_excess_precision(self):
        with pytest.raises(ValueError):
            to_minor_units(Decimal("1.005"), 2)

    def test_to_minor_units_rejects_float(self):
        with pytest.raises(TypeError):
            to_minor_units(1.5, 2)  # type: ignore[arg-type]

    def test_round_trip(self):
        assert from_minor_units(150, 2) == Decimal("1.5")
        assert from_minor_units(to_minor_units("99.99", 2), 2) == Decimal("99.99")


# ---------------------------------------------------------------------------
# Sandbox impls conform to their protocols and are SIMULATED
# ---------------------------------------------------------------------------


class TestSandboxProtocols:
    @pytest.mark.parametrize(
        ("impl", "proto"),
        [
            (SandboxCustodyPort(provider="s"), CustodyPort),
            (SandboxFiatAccountPort(provider="s"), FiatAccountPort),
            (SandboxOnrampPort(provider="s"), OnrampPort),
            (SandboxOfframpPort(provider="s"), OfframpPort),
            (SandboxSwapPort(provider="s"), SwapPort),
            (SandboxBridgePort(provider="s"), BridgePort),
            (SandboxCardPort(provider="s"), CardPort),
            (SandboxKycPort(provider="s"), KycPort),
            (SandboxKytPort(provider="s"), KytPort),
        ],
    )
    def test_conforms_and_simulated(self, impl, proto):
        assert isinstance(impl, proto)
        assert impl.sandbox is True
        assert impl.custody_model == CustodyModel.SIMULATED

    @pytest.mark.asyncio
    async def test_sandbox_fiat_payout_is_minor_units(self):
        port = SandboxFiatAccountPort(provider="s")
        txn = await port.create_payout(
            account_ref="acct_1",
            destination_ref="bank_1",
            amount_minor=12_345,
            currency="USD",
        )
        assert isinstance(txn.amount_minor, int)
        assert txn.amount_minor == 12_345
        assert txn.custody_model == CustodyModel.SIMULATED
        assert txn.sandbox is True

    @pytest.mark.asyncio
    async def test_sandbox_kyt_reports_only(self):
        port = SandboxKytPort(provider="s")
        result = await port.screen_address(address="0xabc", chain="base")
        # Port reports a verdict; it never decides allow/deny (the moat does).
        assert result.status == "clear"
        assert result.ok is True


# ---------------------------------------------------------------------------
# Registry invariant #2: sandbox impl when keys absent (dev/test)
# ---------------------------------------------------------------------------


class TestRegistrySandboxFallback:
    def test_dev_no_keys_returns_sandbox_for_all(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        for cap in ProviderCapability:
            impl = reg.get(cap)
            assert impl.sandbox is True, f"{cap} should be sandbox"
            assert impl.custody_model == CustodyModel.SIMULATED
            assert not reg.has_real(cap)

    def test_get_is_cached(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        a = reg.get(ProviderCapability.ONRAMP)
        b = reg.get(ProviderCapability.ONRAMP)
        assert a is b


# ---------------------------------------------------------------------------
# Registry invariant #1: real impl when keys set
# ---------------------------------------------------------------------------


class TestRegistryRealProviders:
    def test_lithic_real_when_key_set(self):
        # Build fake creds at runtime so secret-scanners do not flag literals.
        fake_key = "test_" + "abc"
        fake_secret = "wh" + "sec_" + "x"
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"LITHIC_API_KEY": fake_key, "LITHIC_WEBHOOK_SECRET": fake_secret},
        )
        assert reg.has_real(ProviderCapability.FIAT_ACCOUNT)
        fa = reg.get(ProviderCapability.FIAT_ACCOUNT)
        assert fa.provider == "lithic"
        assert fa.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_conduit_real_when_keys_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={
                "CONDUIT_API_KEY": "ck_test",
                "CONDUIT_API_SECRET": "cs_test",
                "CONDUIT_SANDBOX": "true",
            },
        )
        assert reg.has_real(ProviderCapability.ONRAMP)
        on = reg.get(ProviderCapability.ONRAMP)
        assert on.provider == "conduit"
        assert on.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_circle_cpn_real_when_enabled(self):
        settings = SimpleNamespace(
            is_production=False,
            database_url="",
            circle_cpn=SimpleNamespace(enabled=True, api_key="ck_cpn"),
        )
        reg = ProviderRegistry.from_settings(
            settings,
            environ={"CIRCLE_CPN_ENABLED": "true", "CIRCLE_CPN_API_KEY": "ck_cpn"},
        )
        assert reg.has_real(ProviderCapability.OFFRAMP)
        off = reg.get(ProviderCapability.OFFRAMP)
        assert off.provider == "circle_cpn"
        assert off.custody_model == CustodyModel.PARTNER_CUSTODIED


# ---------------------------------------------------------------------------
# Registry invariant #3: fail-closed in production without keys
# ---------------------------------------------------------------------------


class TestRegistryFailClosed:
    @pytest.mark.parametrize("cap", [ProviderCapability.CUSTODY, ProviderCapability.KYT])
    def test_required_capability_fails_closed_in_prod(self, cap):
        reg = ProviderRegistry(is_production=True)
        with pytest.raises(ProviderNotConfigured) as exc:
            reg.get(cap)
        assert exc.value.capability == cap

    def test_optional_capability_falls_back_in_prod(self):
        # Non-required capability with no provider falls back to sandbox (with a
        # warning) rather than crashing the app at resolution time.
        reg = ProviderRegistry(is_production=True)
        impl = reg.get(ProviderCapability.ONRAMP)
        assert impl.sandbox is True

    def test_from_settings_prod_no_keys_fails_closed_on_required(self):
        reg = ProviderRegistry.from_settings(_prod_settings(), environ={})
        with pytest.raises(ProviderNotConfigured):
            reg.get(ProviderCapability.CUSTODY)


# ---------------------------------------------------------------------------
# Adapter normalization over the real clients
# ---------------------------------------------------------------------------


class TestLithicAdapterNormalization:
    @pytest.mark.asyncio
    async def test_create_payout_uses_minor_units(self):
        from server.providers.adapters import LithicFiatAccountAdapter

        captured = {}

        class _FakeClient:
            _env = "sandbox"

            async def create_payment(self, req):
                captured["amount"] = req.amount
                captured["type"] = req.payment_type
                return SimpleNamespace(
                    token="pay_1",
                    status="PENDING",
                    pending_amount=req.amount,
                    currency="USD",
                    raw={"token": "pay_1"},
                )

        adapter = LithicFiatAccountAdapter(_FakeClient())
        txn = await adapter.create_payout(
            account_ref="facct_1",
            destination_ref="ext_1",
            amount_minor=5000,
            currency="USD",
        )
        # Amount passed through as integer cents; no float anywhere.
        assert captured["amount"] == 5000
        assert isinstance(captured["amount"], int)
        assert txn.amount_minor == 5000
        assert txn.reference == "pay_1"
        assert txn.custody_model == CustodyModel.PARTNER_CUSTODIED

    @pytest.mark.asyncio
    async def test_rejects_non_int_amount(self):
        from server.providers.adapters import LithicFiatAccountAdapter
        from server.providers.ports import ProviderError

        adapter = LithicFiatAccountAdapter(SimpleNamespace(_env="sandbox"))
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                account_ref="a",
                destination_ref="b",
                amount_minor=Decimal("50.00"),  # type: ignore[arg-type]
            )

    def test_verify_webhook_delegates_to_svix(self):
        """Adapter webhook verification uses the client's Svix verifier."""
        import base64

        from server.providers.lithic_treasury import LithicTreasuryClient
        from server.providers.adapters import LithicFiatAccountAdapter

        secret = "whsec_" + base64.b64encode(b"sekret").decode()
        client = LithicTreasuryClient(api_key="k", webhook_secret=secret)
        adapter = LithicFiatAccountAdapter(client)

        body = b'{"ok":true}'
        ts = str(int(time.time()))
        raw = secret[len("whsec_") :]
        key = base64.b64decode(raw)
        import hashlib
        import hmac

        signed = b"%s.%s.%s" % (b"msg_1", ts.encode(), body)
        good = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()

        assert adapter.verify_webhook(
            body=body,
            headers={
                "webhook-id": "msg_1",
                "webhook-timestamp": ts,
                "webhook-signature": f"v1,{good}",
            },
        )
        # Raw hex HMAC (the old, wrong scheme) is rejected.
        assert not adapter.verify_webhook(
            body=body,
            headers={
                "webhook-id": "msg_1",
                "webhook-timestamp": ts,
                "webhook-signature": "v1," + hmac.new(key, body, hashlib.sha256).hexdigest(),
            },
        )
