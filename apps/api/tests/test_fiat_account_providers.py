"""Tests for the Dakota + Increase fiat-account adapters.

Proves:
  * each adapter conforms to its capability port (structural + runtime),
  * custody_model is PARTNER_CUSTODIED (a regulated partner holds the funds),
  * money crosses the boundary as integer minor units / Decimal — never float,
  * env-gating: the real adapter activates when its key is set; with NO keys
    the registry falls back to the SIMULATED sandbox impl so dev/tests run
    green without live keys,
  * webhook verification fails closed without a configured secret/key, and the
    real Increase (Svix) / Dakota (Ed25519) schemes verify a valid signature.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time
from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.dakota import (
    DakotaClient,
    DakotaConfig,
    DakotaFiatAccountAdapter,
)
from server.providers.increase import (
    IncreaseClient,
    IncreaseConfig,
    IncreaseFiatAccountAdapter,
    IncreaseOfframpAdapter,
)
from server.providers.ports import (
    CustodyModel,
    FiatAccountPort,
    OfframpPort,
    ProviderCapability,
    ProviderError,
)
from server.providers.registry import ProviderRegistry


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


# ---------------------------------------------------------------------------
# Port conformance + custody
# ---------------------------------------------------------------------------


class TestPortConformance:
    def test_dakota_conforms_to_fiat_account_port(self):
        adapter = DakotaFiatAccountAdapter(DakotaClient(DakotaConfig(api_key="k")))
        assert isinstance(adapter, FiatAccountPort)
        assert adapter.provider == "dakota"
        assert adapter.capability == ProviderCapability.FIAT_ACCOUNT
        assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED
        assert adapter.sandbox is True  # default env is sandbox

    def test_increase_fiat_conforms_to_port(self):
        adapter = IncreaseFiatAccountAdapter(IncreaseClient(IncreaseConfig(api_key="k")))
        assert isinstance(adapter, FiatAccountPort)
        assert adapter.provider == "increase"
        assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_increase_offramp_conforms_to_port(self):
        adapter = IncreaseOfframpAdapter(IncreaseClient(IncreaseConfig(api_key="k")))
        assert isinstance(adapter, OfframpPort)
        assert adapter.provider == "increase"
        assert adapter.capability == ProviderCapability.OFFRAMP
        assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_production_environment_not_sandbox(self):
        adapter = DakotaFiatAccountAdapter(
            DakotaClient(DakotaConfig(api_key="k", environment="production"))
        )
        assert adapter.sandbox is False


# ---------------------------------------------------------------------------
# Money correctness — integer minor units / Decimal, never float
# ---------------------------------------------------------------------------


class TestMoneyCorrectness:
    @pytest.mark.asyncio
    async def test_dakota_payout_sends_decimal_string_from_minor_units(self):
        captured: dict = {}

        class _FakeHttp:
            async def post(self, path, json=None):
                captured["path"] = path
                captured["json"] = json
                return _Resp({"id": "txn_1", "status": "processing", "asset": "USDC"})

            async def get(self, path):  # pragma: no cover - unused here
                return _Resp({})

        client = DakotaClient(DakotaConfig(api_key="k"))
        client._http_client = _FakeHttp()  # type: ignore[assignment]
        adapter = DakotaFiatAccountAdapter(client)

        # 12_500_000 base units = 12.5 USDC (6 decimals).
        txn = await adapter.create_payout(
            account_ref="acct_1",
            destination_ref="dest_1",
            amount_minor=12_500_000,
        )
        assert captured["json"]["amount"] == "12.5"
        assert captured["json"]["asset"] == "USDC"
        assert txn.amount_minor == 12_500_000
        assert isinstance(txn.amount_minor, int)
        assert txn.custody_model == CustodyModel.PARTNER_CUSTODIED

    @pytest.mark.asyncio
    async def test_dakota_rejects_non_int_amount(self):
        adapter = DakotaFiatAccountAdapter(DakotaClient(DakotaConfig(api_key="k")))
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                account_ref="a",
                destination_ref="b",
                amount_minor=Decimal("1.50"),  # type: ignore[arg-type]
            )

    def test_dakota_usdc_balance_is_exact_minor_units(self):
        balances = {
            "balances": [
                {"asset": "USDC", "network": "base", "amount": "10.25"},
                {"asset": "USDC", "network": "solana", "amount": "0.75"},
                {"asset": "ETH", "network": "base", "amount": "1.0"},
            ]
        }
        # 11.00 USDC across chains => 11_000_000 base units; ETH ignored.
        assert DakotaClient.usdc_minor_from_balances(balances) == 11_000_000

    @pytest.mark.asyncio
    async def test_increase_payout_sends_integer_cents(self):
        captured: dict = {}

        class _FakeHttp:
            async def post(self, path, json=None, headers=None):
                captured["path"] = path
                captured["json"] = json
                return _Resp({"id": "ach_1", "status": "pending_submission", "amount": json["amount"]})

        client = IncreaseClient(IncreaseConfig(api_key="k"))
        client._http_client = _FakeHttp()  # type: ignore[assignment]
        adapter = IncreaseFiatAccountAdapter(client)

        txn = await adapter.create_payout(
            account_ref="account_x",
            destination_ref="101050001:987654321:Acme Inc",
            amount_minor=5000,  # $50.00 in cents
            method="ACH_NEXT_DAY",
            memo="payroll",
        )
        assert captured["path"] == "/ach_transfers"
        assert captured["json"]["amount"] == 5000
        assert isinstance(captured["json"]["amount"], int)
        assert captured["json"]["routing_number"] == "101050001"
        assert captured["json"]["account_number"] == "987654321"
        assert txn.amount_minor == 5000
        assert txn.raw["rail"] == "ach"

    @pytest.mark.asyncio
    async def test_increase_wire_rail_routes_to_wire_endpoint(self):
        captured: dict = {}

        class _FakeHttp:
            async def post(self, path, json=None, headers=None):
                captured["path"] = path
                return _Resp({"id": "wire_1", "status": "pending", "amount": json["amount"]})

        client = IncreaseClient(IncreaseConfig(api_key="k"))
        client._http_client = _FakeHttp()  # type: ignore[assignment]
        adapter = IncreaseFiatAccountAdapter(client)
        txn = await adapter.create_payout(
            account_ref="account_x",
            destination_ref="101050001:987654321:Acme",
            amount_minor=10_000,
            method="WIRE",
        )
        assert captured["path"] == "/wire_transfers"
        assert txn.reference == "wire_1"

    @pytest.mark.asyncio
    async def test_increase_offramp_requires_source_account(self):
        adapter = IncreaseOfframpAdapter(IncreaseClient(IncreaseConfig(api_key="k")))
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=1000,
                destination_bank_ref="101050001:987654321",
            )

    @pytest.mark.asyncio
    async def test_increase_offramp_rejects_non_int_amount(self):
        adapter = IncreaseOfframpAdapter(IncreaseClient(IncreaseConfig(api_key="k")))
        with pytest.raises(ProviderError):
            await adapter.create_payout(
                source_chain="base",
                source_token="usdc",
                amount_minor=Decimal("10.00"),  # type: ignore[arg-type]
                destination_bank_ref="101050001:987654321",
                metadata={"source_account_id": "account_x"},
            )


# ---------------------------------------------------------------------------
# Webhook verification — fail closed without config; verify a real signature
# ---------------------------------------------------------------------------


class TestWebhookVerification:
    def test_increase_fails_closed_without_secret(self):
        client = IncreaseClient(IncreaseConfig(api_key="k"))  # no webhook_secret
        assert not client.verify_webhook(body=b"{}", headers={})

    def test_increase_verifies_standard_webhooks_signature(self):
        secret = "whsec_" + base64.b64encode(b"increase-secret").decode()
        client = IncreaseClient(IncreaseConfig(api_key="k", webhook_secret=secret))
        body = b'{"event":"transfer.updated"}'
        ts = str(int(time.time()))
        key = base64.b64decode(secret[len("whsec_") :])
        signed = b"%s.%s.%s" % (b"event_1", ts.encode(), body)
        good = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode()
        assert client.verify_webhook(
            body=body,
            headers={
                "webhook-id": "event_1",
                "webhook-timestamp": ts,
                "webhook-signature": f"v1,{good}",
            },
        )
        # Tampered signature rejected.
        assert not client.verify_webhook(
            body=body,
            headers={
                "webhook-id": "event_1",
                "webhook-timestamp": ts,
                "webhook-signature": "v1,AAAA",
            },
        )

    def test_dakota_fails_closed_without_public_key(self):
        client = DakotaClient(DakotaConfig(api_key="k"))  # no public key
        assert not client.verify_webhook(body=b"{}", headers={})

    def test_dakota_verifies_ed25519_signature(self):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        private = Ed25519PrivateKey.generate()
        public = private.public_key()
        from cryptography.hazmat.primitives import serialization

        pub_hex = public.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
        client = DakotaClient(
            DakotaConfig(api_key="k", webhook_public_key_hex=pub_hex)
        )
        body = b'{"data":{"object":{"status":"completed"}}}'
        ts = str(int(time.time()))
        sig = base64.b64encode(private.sign(ts.encode() + body)).decode()
        assert client.verify_webhook(
            body=body,
            headers={"X-Webhook-Signature": sig, "X-Webhook-Timestamp": ts},
        )
        # Body tamper => signature no longer valid.
        assert not client.verify_webhook(
            body=b'{"data":{"object":{"status":"failed"}}}',
            headers={"X-Webhook-Signature": sig, "X-Webhook-Timestamp": ts},
        )

    def test_dakota_rejects_stale_timestamp(self):
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        private = Ed25519PrivateKey.generate()
        pub_hex = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        ).hex()
        client = DakotaClient(
            DakotaConfig(api_key="k", webhook_public_key_hex=pub_hex)
        )
        body = b"{}"
        stale = str(int(time.time()) - 10_000)
        sig = base64.b64encode(private.sign(stale.encode() + body)).decode()
        assert not client.verify_webhook(
            body=body,
            headers={"X-Webhook-Signature": sig, "X-Webhook-Timestamp": stale},
        )


# ---------------------------------------------------------------------------
# Registry env-gating — real when keys set, sandbox fallback when absent
# ---------------------------------------------------------------------------


class TestRegistryEnvGating:
    def test_no_keys_falls_back_to_sandbox(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        fa = reg.get(ProviderCapability.FIAT_ACCOUNT)
        assert fa.sandbox is True
        assert fa.custody_model == CustodyModel.SIMULATED
        assert not reg.has_real(ProviderCapability.FIAT_ACCOUNT)

    def test_dakota_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"DAKOTA_API_KEY": "dk_test", "DAKOTA_ENVIRONMENT": "sandbox"},
        )
        assert reg.has_real(ProviderCapability.FIAT_ACCOUNT)
        fa = reg.get(ProviderCapability.FIAT_ACCOUNT)
        assert fa.provider == "dakota"
        assert fa.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_increase_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"INCREASE_API_KEY": "sandbox_key_test"},
        )
        assert reg.has_real(ProviderCapability.FIAT_ACCOUNT)
        assert reg.has_real(ProviderCapability.OFFRAMP)
        fa = reg.get(ProviderCapability.FIAT_ACCOUNT)
        off = reg.get(ProviderCapability.OFFRAMP)
        assert fa.provider == "increase"
        assert off.provider == "increase"

    def test_dakota_preferred_over_increase_for_fiat_account(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"DAKOTA_API_KEY": "dk_test", "INCREASE_API_KEY": "sandbox_key_test"},
        )
        # Dakota wins the fiat-account slot; Increase still backs offramp.
        assert reg.get(ProviderCapability.FIAT_ACCOUNT).provider == "dakota"
        assert reg.get(ProviderCapability.OFFRAMP).provider == "increase"


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload
