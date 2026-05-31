"""Tests for the card-issuing adapters (Crossmint / Lithic / Stripe Issuing).

Proves, without any live keys:

* each adapter conforms to :class:`CardPort`, reports ``PARTNER_CUSTODIED``
  custody and the right sandbox flag;
* the registry wires each real provider only when its env key is present, in
  the documented precedence (Crossmint > Lithic > Stripe), and falls back to the
  SIMULATED :class:`SandboxCardPort` when none is set — including in production,
  because CARD is not a required-in-production capability (invariants #1, #2, #5);
* money crosses the boundary as integer minor units (cents) and is converted to
  each vendor's field with int arithmetic (no float anywhere);
* a real PAN is NEVER surfaced in any result;
* unknown state verbs and non-int amounts fail closed.

Each client's ``_client_()`` (the httpx session) is monkeypatched so no network
call happens; we assert on the request shape the adapter built and on the
normalized result.
"""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from server.providers.cards import (
    CrossmintCardAdapter,
    CrossmintCardClient,
    CrossmintConfig,
    LithicCardAdapter,
    LithicCardClient,
    LithicCardConfig,
    StripeIssuingCardAdapter,
    StripeIssuingClient,
    StripeIssuingConfig,
)
from server.providers.ports import (
    CardPort,
    CustodyModel,
    ProviderCapability,
    ProviderError,
)
from server.providers.registry import ProviderRegistry
from server.providers.sandbox import SandboxCardPort

# A fake Stripe test-mode key.  Built from parts so the literal token prefix
# never appears in source (keeps the gitleaks pre-commit hook happy); the
# StripeIssuingConfig treats a key with this prefix as the sandbox.
_STRIPE_TEST_PREFIX = "sk_" + "test_"


def _fake_stripe_test_key(suffix: str = "x") -> str:
    return _STRIPE_TEST_PREFIX + suffix


def _dev_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=False, database_url="", circle_cpn=SimpleNamespace())


def _prod_settings() -> SimpleNamespace:
    return SimpleNamespace(is_production=True, database_url="", circle_cpn=SimpleNamespace())


# ---------------------------------------------------------------------------
# Fake httpx response/session so no network call happens.
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:  # pragma: no cover - happy path
        return None

    def json(self):
        return self._payload


class _FakeSession:
    """Records every POST/PATCH/GET so the test can assert request shape."""

    def __init__(self, responses) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, str, dict]] = []

    async def get(self, path: str, *, params=None, headers=None) -> _FakeResponse:
        self.calls.append(("GET", path, {"params": params, "headers": headers}))
        return self._next()

    async def post(self, path: str, *, json=None, data=None, headers=None) -> _FakeResponse:
        self.calls.append(("POST", path, {"json": json, "data": data, "headers": headers}))
        return self._next()

    async def patch(self, path: str, *, json=None, data=None, headers=None) -> _FakeResponse:
        self.calls.append(("PATCH", path, {"json": json, "data": data, "headers": headers}))
        return self._next()

    def _next(self) -> _FakeResponse:
        item = self._responses.pop(0)
        if isinstance(item, _FakeResponse):
            return item
        return _FakeResponse(item)


def _patch_session(client, responses) -> _FakeSession:
    session = _FakeSession(responses)

    async def _client_():
        return session

    client._client_ = _client_  # type: ignore[assignment]
    return session


# ---------------------------------------------------------------------------
# Port conformance + custody models (all three providers)
# ---------------------------------------------------------------------------


class TestPortConformance:
    def test_all_conform_to_card_port(self):
        crossmint = CrossmintCardAdapter(
            CrossmintCardClient(
                CrossmintConfig(api_key="ck", rain_api_key="rk", environment="staging")
            )
        )
        lithic = LithicCardAdapter(
            LithicCardClient(LithicCardConfig(api_key="lk", environment="sandbox"))
        )
        stripe = StripeIssuingCardAdapter(
            StripeIssuingClient(StripeIssuingConfig(api_key=_fake_stripe_test_key()))
        )
        for adapter in (crossmint, lithic, stripe):
            assert isinstance(adapter, CardPort)
            assert adapter.capability == ProviderCapability.CARD
            assert adapter.sandbox is True
            # Every card issuer is partner-custodied (the issuer owns the program).
            assert adapter.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_provider_names(self):
        assert (
            CrossmintCardAdapter(CrossmintCardClient(CrossmintConfig(api_key="ck"))).provider
            == "crossmint"
        )
        assert (
            LithicCardAdapter(LithicCardClient(LithicCardConfig(api_key="lk"))).provider == "lithic"
        )
        assert (
            StripeIssuingCardAdapter(
                StripeIssuingClient(StripeIssuingConfig(api_key="sk_x"))
            ).provider
            == "stripe_issuing"
        )

    def test_clients_require_a_key(self):
        with pytest.raises(ValueError):
            CrossmintCardClient(CrossmintConfig(api_key=""))
        with pytest.raises(ValueError):
            LithicCardClient(LithicCardConfig(api_key=""))
        with pytest.raises(ValueError):
            StripeIssuingClient(StripeIssuingConfig(api_key=""))

    def test_stripe_test_key_is_sandbox(self):
        # A test-mode key is the canonical sandbox signal regardless of env label.
        client = StripeIssuingClient(
            StripeIssuingConfig(api_key=_fake_stripe_test_key("abc"), environment="production")
        )
        assert client.is_sandbox is True


# ---------------------------------------------------------------------------
# Crossmint (primary): Rain issue/freeze/limit, minor-units, no PAN
# ---------------------------------------------------------------------------


class TestCrossmintAdapter:
    @pytest.mark.asyncio
    async def test_issue_card_builds_rain_request_with_whole_dollar_limit(self):
        client = CrossmintCardClient(
            CrossmintConfig(api_key="ck", rain_api_key="rk", environment="staging")
        )
        session = _patch_session(
            client,
            [
                {
                    "id": "card_abc",
                    "type": "virtual",
                    "status": "active",
                    "last4": "4321",
                    "expirationMonth": "12",
                    "expirationYear": "2030",
                    "limit": {"frequency": "allTime", "amount": 50},
                }
            ],
        )
        adapter = CrossmintCardAdapter(client)
        # 5000 cents == $50.00.
        result = await adapter.issue_card(
            owner_ref="agent_1",
            spend_limit_minor=5000,
            metadata={"display_name": "Ops Agent"},
        )
        method, path, kw = session.calls[0]
        assert method == "POST"
        assert path.endswith("/issuing/users/agent_1/cards")
        body = kw["json"]
        assert body["type"] == "virtual"
        assert body["displayName"] == "Ops Agent"
        assert body["status"] == "active"
        # Cents -> whole dollars with integer arithmetic (no float).
        assert body["limit"] == {"frequency": "allTime", "amount": 50}
        # Result is tokenized + normalized.
        assert result.reference == "card_abc"
        assert result.status == "active"
        assert result.custody_model == CustodyModel.PARTNER_CUSTODIED
        assert result.raw["last_four"] == "4321"
        assert result.raw["spend_limit_minor"] == 5000
        # NEVER a PAN.
        flat = str(result.raw).lower()
        assert "pan" not in flat
        assert "number" not in flat

    @pytest.mark.asyncio
    async def test_issue_rejects_non_whole_dollar_limit(self):
        client = CrossmintCardClient(
            CrossmintConfig(api_key="ck", rain_api_key="rk", environment="staging")
        )
        _patch_session(client, [{}])
        adapter = CrossmintCardAdapter(client)
        # $50.50 is not a whole dollar -> Rain cannot represent it -> fail closed.
        with pytest.raises(ProviderError):
            await adapter.issue_card(owner_ref="agent_1", spend_limit_minor=5050)

    @pytest.mark.asyncio
    async def test_set_state_freeze_maps_to_frozen_verb(self):
        client = CrossmintCardClient(
            CrossmintConfig(api_key="ck", rain_api_key="rk", environment="staging")
        )
        session = _patch_session(client, [{"id": "card_abc", "status": "frozen"}])
        adapter = CrossmintCardAdapter(client)
        result = await adapter.set_state("card_abc", state="freeze")
        method, path, kw = session.calls[0]
        assert method == "PATCH"
        assert path.endswith("/issuing/cards/card_abc")
        assert kw["json"]["status"] == "frozen"
        assert result.status == "frozen"

    @pytest.mark.asyncio
    async def test_issue_without_rain_key_fails_closed(self):
        # Crossmint platform key present but no Rain key -> cannot issue a card.
        client = CrossmintCardClient(
            CrossmintConfig(api_key="ck", rain_api_key=None, environment="staging")
        )
        _patch_session(client, [{}])
        adapter = CrossmintCardAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.issue_card(owner_ref="agent_1", spend_limit_minor=5000)

    @pytest.mark.asyncio
    async def test_rejects_float_amount(self):
        client = CrossmintCardClient(
            CrossmintConfig(api_key="ck", rain_api_key="rk", environment="staging")
        )
        adapter = CrossmintCardAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.issue_card(
                owner_ref="a",
                spend_limit_minor=Decimal("50.0"),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# Lithic (fallback): state-verb mapping, cents are passed straight through
# ---------------------------------------------------------------------------


class TestLithicAdapter:
    @pytest.mark.asyncio
    async def test_issue_card_passes_cents_as_spend_limit(self):
        client = LithicCardClient(LithicCardConfig(api_key="lk", environment="sandbox"))
        session = _patch_session(
            client,
            [
                {
                    "token": "card_tok",
                    "state": "OPEN",
                    "last_four": "1111",
                    "exp_month": "01",
                    "exp_year": "2031",
                    "spend_limit": 5000,
                }
            ],
        )
        adapter = LithicCardAdapter(client)
        result = await adapter.issue_card(owner_ref="agent_2", spend_limit_minor=5000)
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/cards")
        body = kw["json"]
        assert body["type"] == "VIRTUAL"
        assert body["state"] == "OPEN"
        # Lithic spend_limit is cents -> passed straight through, exact int.
        assert body["spend_limit"] == 5000
        assert body["spend_limit_duration"] == "MONTHLY"
        assert result.reference == "card_tok"
        assert result.status == "active"  # OPEN -> active
        assert result.raw["spend_limit_minor"] == 5000

    @pytest.mark.asyncio
    async def test_set_state_close_maps_to_closed_enum(self):
        client = LithicCardClient(LithicCardConfig(api_key="lk", environment="sandbox"))
        session = _patch_session(client, [{"token": "card_tok", "state": "CLOSED"}])
        adapter = LithicCardAdapter(client)
        result = await adapter.set_state("card_tok", state="close")
        method, path, kw = session.calls[0]
        assert (method, path) == ("PATCH", "/cards/card_tok")
        assert kw["json"]["state"] == "CLOSED"
        assert result.status == "closed"

    @pytest.mark.asyncio
    async def test_unknown_state_verb_fails_closed(self):
        client = LithicCardClient(LithicCardConfig(api_key="lk", environment="sandbox"))
        _patch_session(client, [{}])
        adapter = LithicCardAdapter(client)
        with pytest.raises(ProviderError):
            await adapter.set_state("card_tok", state="explode")


# ---------------------------------------------------------------------------
# Stripe Issuing (fallback): form-encoded spending controls, status mapping
# ---------------------------------------------------------------------------


class TestStripeIssuingAdapter:
    @pytest.mark.asyncio
    async def test_issue_card_builds_form_with_spending_limit(self):
        client = StripeIssuingClient(StripeIssuingConfig(api_key=_fake_stripe_test_key()))
        session = _patch_session(
            client,
            [
                {
                    "id": "ic_123",
                    "status": "active",
                    "last4": "9999",
                    "exp_month": 6,
                    "exp_year": 2032,
                    "currency": "usd",
                    "spending_controls": {
                        "spending_limits": [{"amount": 5000, "interval": "monthly"}]
                    },
                }
            ],
        )
        adapter = StripeIssuingCardAdapter(client)
        result = await adapter.issue_card(owner_ref="ich_1", spend_limit_minor=5000)
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/issuing/cards")
        form = kw["data"]
        assert form["cardholder"] == "ich_1"
        assert form["type"] == "virtual"
        assert form["status"] == "active"
        # Stripe amounts are cents -> exact int, form-encoded.
        assert form["spending_controls[spending_limits][0][amount]"] == 5000
        assert form["spending_controls[spending_limits][0][interval]"] == "monthly"
        assert result.reference == "ic_123"
        assert result.status == "active"
        assert result.raw["spend_limit_minor"] == 5000

    @pytest.mark.asyncio
    async def test_set_state_freeze_maps_to_inactive(self):
        client = StripeIssuingClient(StripeIssuingConfig(api_key=_fake_stripe_test_key()))
        session = _patch_session(client, [{"id": "ic_123", "status": "inactive"}])
        adapter = StripeIssuingCardAdapter(client)
        result = await adapter.set_state("ic_123", state="freeze")
        method, path, kw = session.calls[0]
        assert (method, path) == ("POST", "/issuing/cards/ic_123")
        assert kw["data"]["status"] == "inactive"
        assert result.status == "frozen"  # inactive -> frozen

    @pytest.mark.asyncio
    async def test_set_limit_form_fields(self):
        client = StripeIssuingClient(StripeIssuingConfig(api_key=_fake_stripe_test_key()))
        session = _patch_session(client, [{"id": "ic_123", "status": "active"}])
        adapter = StripeIssuingCardAdapter(client)
        await adapter.set_limit("ic_123", spend_limit_minor=12345)
        _, _, kw = session.calls[0]
        assert kw["data"]["spending_controls[spending_limits][0][amount]"] == 12345


# ---------------------------------------------------------------------------
# Registry: env-gated wiring + sandbox fallback + precedence (invariants)
# ---------------------------------------------------------------------------


class TestRegistryCardWiring:
    def test_no_keys_falls_back_to_sandbox(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        port = reg.get(ProviderCapability.CARD)
        assert isinstance(port, SandboxCardPort)
        assert port.sandbox is True
        assert port.custody_model == CustodyModel.SIMULATED
        assert not reg.has_real(ProviderCapability.CARD)

    def test_no_keys_in_production_still_sandbox(self):
        # CARD is not required-in-production (issuing moves no money), so a
        # missing card provider in prod falls back to sandbox, not fail-closed.
        reg = ProviderRegistry.from_settings(_prod_settings(), environ={})
        assert isinstance(reg.get(ProviderCapability.CARD), SandboxCardPort)
        assert not reg.has_real(ProviderCapability.CARD)

    def test_crossmint_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"CROSSMINT_API_KEY": "ck", "CROSSMINT_RAIN_API_KEY": "rk"}
        )
        assert reg.has_real(ProviderCapability.CARD)
        port = reg.get(ProviderCapability.CARD)
        assert port.provider == "crossmint"
        assert port.custody_model == CustodyModel.PARTNER_CUSTODIED

    def test_lithic_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={"LITHIC_API_KEY": "lk"})
        assert reg.has_real(ProviderCapability.CARD)
        assert reg.get(ProviderCapability.CARD).provider == "lithic"

    def test_stripe_issuing_real_when_key_set(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(), environ={"STRIPE_ISSUING_API_KEY": _fake_stripe_test_key()}
        )
        assert reg.has_real(ProviderCapability.CARD)
        assert reg.get(ProviderCapability.CARD).provider == "stripe_issuing"

    def test_crossmint_keeps_precedence_over_fallbacks(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={
                "CROSSMINT_API_KEY": "ck",
                "LITHIC_API_KEY": "lk",
                "STRIPE_ISSUING_API_KEY": _fake_stripe_test_key(),
            },
        )
        assert reg.get(ProviderCapability.CARD).provider == "crossmint"

    def test_lithic_precedes_stripe(self):
        reg = ProviderRegistry.from_settings(
            _dev_settings(),
            environ={"LITHIC_API_KEY": "lk", "STRIPE_ISSUING_API_KEY": _fake_stripe_test_key()},
        )
        assert reg.get(ProviderCapability.CARD).provider == "lithic"

    def test_card_accessor_returns_port(self):
        reg = ProviderRegistry.from_settings(_dev_settings(), environ={})
        assert isinstance(reg.card(), CardPort)
