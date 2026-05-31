"""Thin HTTP clients for the crypto->fiat *offramp* providers Sardis aggregates.

Three providers live here, each researched against its CURRENT (2026) API.  None
of these authorizes, initiates, or settles money on its own: each only *executes*
an instruction the orchestrator already authorized (no policy / KYA / sanctions /
mandate checks happen here — those live in the moat).  No secret is hardcoded;
credentials arrive via the registry from env.  Money crosses the boundary as
integer minor units and is rendered to the vendors' decimal-string fields with
``Decimal`` only — never ``float``.

Onramper (offramp aggregator)
-----------------------------
Researched via WebSearch + ``docs.onramper.com`` (``/docs/integration-steps-1``,
``/docs/supported-widget-parameters-offramp``, ``/docs/optional-webhook-setup``):

* **Auth:** ``Authorization: <apiKey>`` header — the raw key is the header value
  (no ``Bearer`` prefix), same as the onramp side.
* **Base URLs:** production ``https://api.onramper.com``; staging
  ``https://api-stg.onramper.com``.
* **Create sell transaction:** ``POST /checkout/intent`` with ``type: "sell"``;
  ``source`` is the crypto (Onramper token id), ``destination`` is the fiat,
  ``amount`` is the crypto sell amount (decimal string), ``paymentMethod`` is the
  payout method (e.g. ``"banktransfer"``), ``network`` the source chain, and a
  ``wallet`` object carries the source address.  Response carries a
  ``transactionInformation`` object with the redirect URL the user completes the
  crypto send / KYC in.
* **Status:** ``GET /transactions/{transactionId}``.  Also delivered via
  HMAC-SHA256 webhooks (verifier already lives in ``routes/wallets/ramp.py``).

Custody: **partner-custodied** — the selected offramp takes custody of the
crypto and settles fiat to the user's payout destination.

Transak Stream (address-based, agent-friendly programmatic offramp)
-------------------------------------------------------------------
Researched via context7 ``/websites/transak`` (whitelabel ``POST /v2/orders`` /
``api/v2/orders``, advanced-query "Configure Multiple Wallet Addresses",
websocket order events) + WebSearch (``transak.com/stream``,
``docs.transak.com/docs/transak-stream``):

Transak Stream is the *wallet-address-based* offramp model — after a one-time
setup (KYC + payout details) the user is provisioned a unique deposit address
per crypto/network; sending crypto to that address triggers an automatic fiat
payout to the pre-registered bank/card, no widget interaction.  This client
creates the **sell order** that yields the deposit (``payin``) address.

* **Auth:** ``x-api-key: <apiKey>`` header (key from the Transak dashboard).
* **Base URLs:** staging ``https://api-stg.transak.com`` /
  ``https://api-gateway-stg.transak.com``; production ``https://api.transak.com`` /
  ``https://api-gateway.transak.com``.
* **Create sell order:** ``POST /api/v2/orders`` with a body carrying
  ``isBuyOrSell: "SELL"``, ``cryptoCurrency``, ``network``, ``fiatCurrency``,
  ``cryptoAmount``, ``paymentInstrumentId`` (payout rail, e.g.
  ``"sepa_bank_transfer"`` / ``"gbp_bank_transfer"``), ``partnerUserId``,
  ``partnerOrderId``, and the payout/wallet linkage.  Response returns an
  ``orderId``, ``status``, and the deposit address (``walletAddress`` /
  ``payinAddress``) the user must send crypto to.
* **Status:** delivered via webhook + Pusher websocket events keyed by
  ``<apiKey>_<partnerOrderId>``; there is no settle-by-polling GET that returns a
  fabricated state, so ``get_status`` reports the order as last-known/``created``
  rather than inventing a settlement.

Custody: **partner-custodied** — Transak takes custody of the crypto at the
deposit address and settles fiat to the registered payout account.

Coinbase Offramp (CDP — ACH / PayPal)
-------------------------------------
Researched via ``docs.cdp.coinbase.com`` (offramp overview, session-token-auth,
create-session-token, create-sell-quote, generating-offramp-url) + the CDP JWT
auth docs (``/get-started/authentication/jwt-authentication``) and
``coinbase/cdp-sdk``:

* **Auth:** short-lived JWT (Bearer) signed with the CDP API key (Ed25519 EdDSA
  or EC ES256).  Claims: ``sub`` = key name/id, ``iss`` = ``"cdp"``, ``aud`` =
  ``["cdp_service"]``, a ``uris`` claim ``["<METHOD> <host><path>"]``, ``nbf`` /
  ``exp`` (~2 min), ``kid`` header = key name, plus a random ``nonce`` header.
  Host: ``api.developer.coinbase.com``.
* **Create session token:** ``POST /onramp/v1/token`` with ``{addresses:[{address,
  blockchains:[…]}], assets:[…], clientIp}`` -> ``{token}`` (single-use).
* **Create sell quote:** ``POST /onramp/v1/sell/quote`` with ``{sellCurrency,
  sellAmount, cashoutCurrency, paymentMethod, country, partnerUserId,
  sourceAddress?, subdivision?, redirectUrl?}`` -> ``{quote_id, offramp_url?,
  cashout_subtotal, cashout_total, coinbase_fee, sell_amount}``.
  Payment methods: ``ACH_BANK_ACCOUNT``, ``PAYPAL``, ``CARD``, ``RTP``,
  ``FIAT_WALLET``, ``CRYPTO_ACCOUNT`` (and guest/Apple-Pay variants).
* **Offramp URL:** ``https://pay.coinbase.com/v3/sell/input?sessionToken=<token>
  &partnerUserRef=<id>&redirectUrl=<url>`` with optional ``defaultNetwork`` /
  ``defaultAsset`` / ``presetCryptoAmount`` / ``defaultCashoutMethod``.
* **Status:** Transaction Status API (poll); offramp requires the user to have a
  Coinbase account with linked bank details.

Custody: **partner-custodied** — Coinbase takes custody of the sent crypto and
pays out fiat to the linked ACH bank / PayPal account.
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Onramper --------------------------------------------------------------
_ONRAMPER_PROD_BASE = "https://api.onramper.com"
_ONRAMPER_STAGING_BASE = "https://api-stg.onramper.com"

# -- Transak Stream --------------------------------------------------------
_TRANSAK_PROD_GATEWAY = "https://api-gateway.transak.com"
_TRANSAK_STAGING_GATEWAY = "https://api-gateway-stg.transak.com"

# -- Coinbase Offramp (CDP) ------------------------------------------------
_CDP_API_HOST = "api.developer.coinbase.com"
_CDP_API_BASE = f"https://{_CDP_API_HOST}"
_CDP_OFFRAMP_PAGE = "https://pay.coinbase.com/v3/sell/input"

_DEFAULT_TIMEOUT = 20.0


def _is_sandbox_env(environment: str) -> bool:
    return environment.strip().lower() in {
        "sandbox",
        "staging",
        "test",
        "development",
        "dev",
    }


# =========================================================================
# Onramper (offramp / sell)
# =========================================================================


@dataclass(frozen=True)
class OnramperOfframpConfig:
    """Resolved Onramper offramp credentials/runtime.  Never logged."""

    api_key: str
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


@dataclass
class OnramperSellTransaction:
    """Normalized Onramper sell (offramp) checkout-intent result."""

    transaction_id: str
    redirect_url: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class OnramperOfframpClient:
    """``POST /checkout/intent`` (type=sell) + ``GET /transactions/{id}``."""

    def __init__(self, config: OnramperOfframpConfig) -> None:
        if not config.api_key:
            raise ValueError("Onramper API key is required")
        self._config = config
        self._base_url = _ONRAMPER_STAGING_BASE if config.is_sandbox else _ONRAMPER_PROD_BASE
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._config.timeout_seconds,
                headers={
                    # Onramper takes the raw key as the Authorization value.
                    "Authorization": self._config.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def create_sell_intent(
        self,
        *,
        source_token: str,
        destination_fiat: str,
        amount: str,
        wallet_address: str,
        network: str,
        payment_method: str = "banktransfer",
        offramp: str | None = None,
        partner_context: str | None = None,
    ) -> OnramperSellTransaction:
        """``POST /checkout/intent`` — initiate a *sell* (offramp) transaction.

        ``amount`` is the crypto sell amount as a precise decimal string built
        with ``Decimal`` upstream — never a float.
        """
        body: dict[str, Any] = {
            "source": source_token.lower(),
            "destination": destination_fiat.lower(),
            "amount": amount,
            "type": "sell",
            "paymentMethod": payment_method,
            "network": network.lower(),
            "wallet": {"address": wallet_address},
        }
        if offramp:
            body["onramp"] = offramp
        if partner_context:
            body["partnerContext"] = partner_context

        client = await self._client_()
        resp = await client.post("/checkout/intent", json=body)
        resp.raise_for_status()
        data = resp.json()
        info = data.get("transactionInformation") or data.get("message") or {}
        if not isinstance(info, dict):
            info = {}
        return OnramperSellTransaction(
            transaction_id=str(
                data.get("transactionId")
                or info.get("transactionId")
                or info.get("sessionId")
                or ""
            ),
            redirect_url=info.get("url") or data.get("url"),
            status=str(data.get("status", "created")),
            raw=data,
        )

    async def get_transaction(self, transaction_id: str) -> dict[str, Any]:
        client = await self._client_()
        resp = await client.get(f"/transactions/{transaction_id}")
        resp.raise_for_status()
        return resp.json()


# =========================================================================
# Transak Stream (address-based offramp)
# =========================================================================


@dataclass(frozen=True)
class TransakStreamConfig:
    """Resolved Transak Stream credentials/runtime.  Never logged."""

    api_key: str
    environment: str = "staging"
    partner_id: str | None = None
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


@dataclass
class TransakStreamOrder:
    """Normalized Transak Stream sell order: the deposit address is the payload.

    ``deposit_address`` is the unique payin address the user sends crypto to;
    sending to it triggers the automatic fiat payout to the registered bank/card.
    """

    order_id: str
    deposit_address: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class TransakStreamClient:
    """``POST /api/v2/orders`` (isBuyOrSell=SELL) -> deposit/payin address.

    The crypto->fiat settlement is fully programmatic: once the order exists the
    user (or an agent) sends ``cryptoAmount`` of ``cryptoCurrency`` on
    ``network`` to ``deposit_address`` and Transak auto-pays the linked fiat
    account.  Status arrives via webhook / Pusher websocket (channel
    ``<apiKey>_<partnerOrderId>``), so there is no settle-by-GET that fabricates
    a state.
    """

    def __init__(self, config: TransakStreamConfig) -> None:
        if not config.api_key:
            raise ValueError("Transak Stream API key is required")
        self._config = config
        self._gateway = _TRANSAK_STAGING_GATEWAY if config.is_sandbox else _TRANSAK_PROD_GATEWAY
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._gateway,
                timeout=self._config.timeout_seconds,
                headers={
                    "x-api-key": self._config.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def create_sell_order(
        self,
        *,
        crypto_currency: str,
        network: str,
        fiat_currency: str,
        crypto_amount: str,
        payment_instrument_id: str,
        partner_user_id: str,
        partner_order_id: str,
        quote_id: str | None = None,
        wallet_address: str | None = None,
    ) -> TransakStreamOrder:
        """``POST /api/v2/orders`` — create a SELL order; returns deposit address.

        ``crypto_amount`` is a precise decimal string built with ``Decimal``
        upstream — never a float.  The user funds the returned deposit address.
        """
        body: dict[str, Any] = {
            "isBuyOrSell": "SELL",
            "cryptoCurrency": crypto_currency.upper(),
            "network": network.lower(),
            "fiatCurrency": fiat_currency.upper(),
            "cryptoAmount": crypto_amount,
            "paymentInstrumentId": payment_instrument_id,
            "partnerUserId": partner_user_id,
            "partnerOrderId": partner_order_id,
        }
        if quote_id:
            body["quoteId"] = quote_id
        if wallet_address:
            # Refund / source wallet for the sell.
            body["walletAddress"] = wallet_address

        client = await self._client_()
        resp = await client.post("/api/v2/orders", json=body)
        resp.raise_for_status()
        envelope = resp.json()
        data = envelope.get("data") or envelope
        if not isinstance(data, dict):
            data = {}
        deposit = (
            data.get("payinAddress") or data.get("depositAddress") or data.get("walletAddress")
        )
        return TransakStreamOrder(
            order_id=str(data.get("orderId") or data.get("id") or ""),
            deposit_address=str(deposit) if deposit else None,
            status=str(data.get("status", "AWAITING_PAYMENT_FROM_USER")),
            raw=envelope,
        )


# =========================================================================
# Coinbase Offramp (CDP)
# =========================================================================


@dataclass(frozen=True)
class CoinbaseOfframpConfig:
    """Resolved CDP offramp credentials/runtime.  Never logged.

    ``api_key_name`` is the CDP key id/name; ``api_key_private`` is the EdDSA
    (Ed25519) or EC (ES256) private key used to sign the short-lived JWT.
    """

    api_key_name: str
    api_key_private: str
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        # CDP offramp has a single production host; "sandbox" is a Sardis-side
        # label so a non-prod deployment never reports a result as a settled
        # production movement of funds.  The network path is identical.
        return _is_sandbox_env(self.environment)


@dataclass
class CoinbaseSellQuote:
    """Normalized Coinbase sell quote + offramp URL."""

    quote_id: str
    offramp_url: str | None
    cashout_total: dict[str, Any]
    raw: dict[str, Any] = field(default_factory=dict)


def _b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _cdp_jwt(
    *,
    api_key_name: str,
    api_key_private: str,
    request_method: str,
    request_path: str,
    expires_in: int = 120,
) -> str:
    """Sign a short-lived CDP JWT (Bearer) for ``METHOD api.developer.../path``.

    Uses PyJWT (already a dependency) over the EdDSA (Ed25519) or ES256 key.
    Mirrors ``coinbase/cdp-sdk``'s ``generateJwt``: claims ``sub``/``iss``/
    ``aud``/``uris``/``nbf``/``exp`` + headers ``kid`` and a random ``nonce``.
    The private key is never logged and lives only in the signing call.
    """
    import jwt as _jwt

    now = int(time.time())
    uri = f"{request_method.upper()} {_CDP_API_HOST}{request_path}"
    claims = {
        "sub": api_key_name,
        "iss": "cdp",
        "aud": ["cdp_service"],
        "nbf": now,
        "exp": now + expires_in,
        "uris": [uri],
    }
    headers = {"kid": api_key_name, "nonce": _b64url(secrets.token_bytes(16))}

    key = api_key_private
    # EC keys are PEM; Ed25519 keys may arrive base64 (32-byte seed) or PEM.
    if "BEGIN" in key:
        algorithm = "ES256"
    else:
        # Treat as a raw Ed25519 private seed (CDP "Ed25519" key format).
        import base64

        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
        )

        raw = base64.b64decode(key)
        seed = raw[:32]  # CDP encodes seed||public; the seed is the first 32B.
        key = Ed25519PrivateKey.from_private_bytes(seed)  # type: ignore[assignment]
        algorithm = "EdDSA"

    return _jwt.encode(claims, key, algorithm=algorithm, headers=headers)


class CoinbaseOfframpClient:
    """CDP offramp: session token -> sell quote -> hosted offramp URL.

    Each request mints a fresh ~2-minute JWT scoped to that exact method+path.
    """

    def __init__(self, config: CoinbaseOfframpConfig) -> None:
        if not config.api_key_name or not config.api_key_private:
            raise ValueError("Coinbase CDP API key name and private key are required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_CDP_API_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _auth_header(self, *, method: str, path: str) -> dict[str, str]:
        token = _cdp_jwt(
            api_key_name=self._config.api_key_name,
            api_key_private=self._config.api_key_private,
            request_method=method,
            request_path=path,
        )
        return {"Authorization": f"Bearer {token}"}

    async def create_session_token(
        self,
        *,
        address: str,
        blockchains: list[str],
        assets: list[str] | None = None,
        client_ip: str | None = None,
    ) -> str:
        """``POST /onramp/v1/token`` -> single-use session token."""
        path = "/onramp/v1/token"
        body: dict[str, Any] = {"addresses": [{"address": address, "blockchains": blockchains}]}
        if assets:
            body["assets"] = assets
        if client_ip:
            body["clientIp"] = client_ip
        client = await self._client_()
        resp = await client.post(
            path, json=body, headers=self._auth_header(method="POST", path=path)
        )
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token") or (data.get("data") or {}).get("token")
        if not token:
            raise RuntimeError("coinbase_no_session_token")
        return str(token)

    async def create_sell_quote(
        self,
        *,
        sell_currency: str,
        sell_amount: str,
        cashout_currency: str,
        payment_method: str,
        country: str,
        partner_user_id: str,
        source_address: str | None = None,
        subdivision: str | None = None,
        redirect_url: str | None = None,
    ) -> CoinbaseSellQuote:
        """``POST /onramp/v1/sell/quote`` — quote a crypto->fiat sale.

        ``sell_amount`` is a precise decimal string built with ``Decimal``
        upstream — never a float.
        """
        path = "/onramp/v1/sell/quote"
        body: dict[str, Any] = {
            "sellCurrency": sell_currency.upper(),
            "sellAmount": sell_amount,
            "cashoutCurrency": cashout_currency.upper(),
            "paymentMethod": payment_method,
            "country": country.upper(),
            "partnerUserId": partner_user_id,
        }
        if source_address:
            body["sourceAddress"] = source_address
        if subdivision:
            body["subdivision"] = subdivision
        if redirect_url:
            body["redirectUrl"] = redirect_url
        client = await self._client_()
        resp = await client.post(
            path, json=body, headers=self._auth_header(method="POST", path=path)
        )
        resp.raise_for_status()
        data = resp.json()
        return CoinbaseSellQuote(
            quote_id=str(data.get("quote_id") or data.get("quoteId") or ""),
            offramp_url=data.get("offramp_url") or data.get("offrampUrl"),
            cashout_total=data.get("cashout_total") or data.get("cashoutTotal") or {},
            raw=data,
        )

    @staticmethod
    def build_offramp_url(
        *,
        session_token: str,
        partner_user_ref: str,
        redirect_url: str,
        default_network: str | None = None,
        default_asset: str | None = None,
        preset_crypto_amount: str | None = None,
        default_cashout_method: str | None = None,
    ) -> str:
        """Assemble the hosted ``pay.coinbase.com/v3/sell/input`` URL.

        The session token (not the wallet address) is the credential in the URL,
        per CDP's session-token model.
        """
        from urllib.parse import urlencode

        params: dict[str, str] = {
            "sessionToken": session_token,
            "partnerUserRef": partner_user_ref,
            "redirectUrl": redirect_url,
        }
        if default_network:
            params["defaultNetwork"] = default_network
        if default_asset:
            params["defaultAsset"] = default_asset
        if preset_crypto_amount is not None:
            params["presetCryptoAmount"] = preset_crypto_amount
        if default_cashout_method:
            params["defaultCashoutMethod"] = default_cashout_method
        return f"{_CDP_OFFRAMP_PAGE}?{urlencode(params)}"


__all__ = [
    "CoinbaseOfframpClient",
    "CoinbaseOfframpConfig",
    "CoinbaseSellQuote",
    "OnramperOfframpClient",
    "OnramperOfframpConfig",
    "OnramperSellTransaction",
    "TransakStreamClient",
    "TransakStreamConfig",
    "TransakStreamOrder",
]
