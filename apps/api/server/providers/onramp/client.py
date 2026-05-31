"""Thin HTTP clients for the fiat->crypto onramp providers Sardis aggregates.

Three providers live here, each researched against its CURRENT (2026) API:

Onramper (aggregator)
---------------------
Researched via WebSearch + the official docs index (``docs.onramper.com/llms.txt``
and ``docs.onramper.com/docs/integration-steps-1`` / ``sign-api-request``):

* **Auth:** ``Authorization: <apiKey>`` header.  Public keys are ``pk_prod_…`` /
  ``pk_test_…``; the raw key value is the header value (no ``Bearer`` prefix).
* **Base URLs:** production ``https://api.onramper.com``; staging
  ``https://api-stg.onramper.com``.
* **Create transaction:** ``POST /checkout/intent`` — "initiates a transaction
  and returns relevant data, including redirect type and URL"; response carries
  a ``transactionInformation`` object with the redirect URL the user completes.
* **Status:** ``GET /transactions/{transactionId}``.
* **Request fields:** ``onramp``, ``source`` (fiat), ``destination`` (crypto/
  Onramper token id), ``amount``, ``type`` ("buy"), ``paymentMethod``,
  ``network``, ``wallet`` (``{address, memo}``), ``partnerContext``.  When
  request signing is enabled, the body carries ``signature`` (hex HMAC-SHA256
  over the signed wallet fields) + ``signContent``; the signing secret is a
  *separate* key Onramper provisions, supplied via env, never hardcoded.
* **Webhooks:** HMAC-SHA256; verification already lives in
  ``server/routes/wallets/ramp.py`` (kept the canonical verifier).

Transak (backend-minted widget URL)
------------------------------------
Researched against the current API-based widget-URL migration
(``docs.transak.com/guides/migration-to-api-based-transak-widget-url``,
``/reference/refresh-access-token``, ``/api/public/create-widget-url``) — the
same two-step flow Sardis already ships server-side in ``sardis-cloud``
(``app/api/onramp/transak/route.ts``):

* **Auth / two-step:** the secret is server-side only.
  1. ``POST {refreshToken}`` with ``{"apiKey": …}`` body + ``api-secret: <secret>``
     header  ->  ``{ data: { accessToken } }``.
  2. ``POST {session}`` with ``access-token: <accessToken>`` header and
     ``{ "widgetParams": {…} }``  ->  ``{ data: { widgetUrl } }`` (single-use,
     ~5 min TTL).
* **Base URLs:** staging ``api-stg.transak.com`` / ``api-gateway-stg.transak.com``;
  production ``api.transak.com`` / ``api-gateway.transak.com``.
* **widgetParams:** ``apiKey``, ``referrerDomain``, ``walletAddress``,
  ``fiatAmount`` (decimal string), ``cryptoCurrencyCode``, ``network``,
  ``fiatCurrency``.

Daimo Pay (crypto wallet funding, any-token -> USDC)
----------------------------------------------------
Researched via context7 ``/websites/paydocs_daimo`` (``paydocs.daimo.com/payments-api``):

* **Auth:** ``Api-Key: <key>`` header.
* **Base URL:** ``https://pay.daimo.com``.
* **Create payment:** ``POST /api/payment`` with body ``{display:{intent,…},
  destination:{destinationAddress, chainId, tokenAddress, amountUnits, calldata?},
  refundAddress?, externalId?, metadata?}``.  ``amountUnits`` is a *precise
  decimal string* ("1.00") — the destination receives **exactly** that amount.
  Native token is ``0x0000000000000000000000000000000000000000``.
  Response: ``{ id, url, payment:{ status, … } }`` where ``url`` is the hosted
  checkout page.
* **Status:** ``GET /api/payment/{id}`` -> Payment object whose ``status`` is
  one of ``payment_unpaid`` / ``payment_started`` / ``payment_completed`` /
  ``payment_bounced``.

Custody: Daimo Pay is **non-custodial** — the payer funds from any wallet/chain
and funds settle straight to the destination address; Daimo never custodies.
Onramper + Transak are **partner-custodied** — the underlying onramp takes the
user's fiat and delivers crypto to the destination wallet.

Every client only *executes* an instruction the orchestrator already authorized.
No policy / KYA / sanctions / mandate checks happen here (those live in the
moat).  No secret is hardcoded; credentials arrive via the registry from env.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# -- Onramper --------------------------------------------------------------
_ONRAMPER_PROD_BASE = "https://api.onramper.com"
_ONRAMPER_STAGING_BASE = "https://api-stg.onramper.com"

# -- Transak ---------------------------------------------------------------
_TRANSAK_PROD_REFRESH = "https://api.transak.com/partners/api/v2/refresh-token"
_TRANSAK_PROD_SESSION = "https://api-gateway.transak.com/api/v2/auth/session"
_TRANSAK_STAGING_REFRESH = "https://api-stg.transak.com/partners/api/v2/refresh-token"
_TRANSAK_STAGING_SESSION = "https://api-gateway-stg.transak.com/api/v2/auth/session"

# -- Daimo Pay -------------------------------------------------------------
_DAIMO_BASE = "https://pay.daimo.com"

_DEFAULT_TIMEOUT = 20.0


def _is_sandbox_env(environment: str) -> bool:
    return environment.strip().lower() in {"sandbox", "staging", "test", "development", "dev"}


# =========================================================================
# Onramper
# =========================================================================


@dataclass(frozen=True)
class OnramperConfig:
    """Resolved Onramper credentials/runtime.  Never logged."""

    api_key: str
    environment: str = "production"
    #: Separate Onramper-provisioned secret for request signing (optional).
    signing_secret: str | None = None
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


@dataclass
class OnramperTransaction:
    """Normalized Onramper checkout-intent result."""

    transaction_id: str
    redirect_url: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class OnramperClient:
    """``POST /checkout/intent`` + ``GET /transactions/{id}`` over httpx."""

    def __init__(self, config: OnramperConfig) -> None:
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

    def _sign_wallet(self, wallet_address: str, wallet_memo: str | None) -> dict[str, str]:
        """Build the optional signed-request fields.

        Onramper signs the wallet fields with HMAC-SHA256 (hex) using a
        separate provisioned secret.  When no signing secret is configured the
        request is sent unsigned (allowed for unsigned-mode partner accounts).
        """
        if not self._config.signing_secret:
            return {}
        # signContent is the concatenation of the signed wallet values.
        sign_content = wallet_address + (wallet_memo or "")
        signature = hmac.new(
            self._config.signing_secret.encode(),
            sign_content.encode(),
            hashlib.sha256,
        ).hexdigest()
        return {"signature": signature, "signContent": sign_content}

    async def create_checkout_intent(
        self,
        *,
        source_currency: str,
        destination_token: str,
        amount: str,
        wallet_address: str,
        network: str,
        payment_method: str = "creditcard",
        onramp: str | None = None,
        wallet_memo: str | None = None,
        partner_context: str | None = None,
    ) -> OnramperTransaction:
        """``POST /checkout/intent`` — initiate a buy transaction."""
        body: dict[str, Any] = {
            "source": source_currency.lower(),
            "destination": destination_token.lower(),
            "amount": amount,
            "type": "buy",
            "paymentMethod": payment_method,
            "network": network.lower(),
            "wallet": {"address": wallet_address, "memo": wallet_memo},
        }
        if onramp:
            body["onramp"] = onramp
        if partner_context:
            body["partnerContext"] = partner_context
        body.update(self._sign_wallet(wallet_address, wallet_memo))

        client = await self._client_()
        resp = await client.post("/checkout/intent", json=body)
        resp.raise_for_status()
        data = resp.json()
        info = data.get("transactionInformation") or data.get("message") or {}
        if not isinstance(info, dict):
            info = {}
        return OnramperTransaction(
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
# Transak
# =========================================================================


@dataclass(frozen=True)
class TransakConfig:
    """Resolved Transak partner credentials/runtime.  Never logged."""

    api_key: str
    api_secret: str
    environment: str = "staging"
    referrer_domain: str = "app.sardis.sh"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        return _is_sandbox_env(self.environment)


@dataclass
class TransakWidget:
    """Normalized Transak minted widget URL."""

    widget_url: str
    raw: dict[str, Any] = field(default_factory=dict)


class TransakClient:
    """Backend two-step mint of a single-use Transak widget URL.

    The secret stays server-side: step 1 exchanges key+secret for a short-lived
    access token; step 2 mints the widget URL the client iframes.
    """

    def __init__(self, config: TransakConfig) -> None:
        if not config.api_key or not config.api_secret:
            raise ValueError("Transak API key and secret are required")
        self._config = config
        if config.is_sandbox:
            self._refresh_url = _TRANSAK_STAGING_REFRESH
            self._session_url = _TRANSAK_STAGING_SESSION
        else:
            self._refresh_url = _TRANSAK_PROD_REFRESH
            self._session_url = _TRANSAK_PROD_SESSION
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=self._config.timeout_seconds,
                headers={"Content-Type": "application/json", "Accept": "application/json"},
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _access_token(self) -> str:
        client = await self._client_()
        resp = await client.post(
            self._refresh_url,
            json={"apiKey": self._config.api_key},
            headers={"api-secret": self._config.api_secret},
        )
        resp.raise_for_status()
        token = (resp.json().get("data") or {}).get("accessToken")
        if not token:
            raise RuntimeError("transak_no_access_token")
        return str(token)

    async def create_widget_url(
        self,
        *,
        wallet_address: str,
        crypto_currency_code: str,
        network: str,
        fiat_amount: str | None = None,
        fiat_currency: str = "USD",
        referrer_domain: str | None = None,
    ) -> TransakWidget:
        """Mint a single-use widget URL (two-step backend flow)."""
        access_token = await self._access_token()
        widget_params: dict[str, str] = {
            "apiKey": self._config.api_key,
            "referrerDomain": referrer_domain or self._config.referrer_domain,
            "walletAddress": wallet_address,
            "cryptoCurrencyCode": crypto_currency_code.upper(),
            "network": network.lower(),
            "fiatCurrency": fiat_currency.upper(),
        }
        if fiat_amount is not None:
            widget_params["fiatAmount"] = fiat_amount

        client = await self._client_()
        resp = await client.post(
            self._session_url,
            json={"widgetParams": widget_params},
            headers={"access-token": access_token},
        )
        resp.raise_for_status()
        data = resp.json()
        widget_url = (data.get("data") or {}).get("widgetUrl")
        if not widget_url:
            raise RuntimeError("transak_no_widget_url")
        return TransakWidget(widget_url=str(widget_url), raw=data)


# =========================================================================
# Daimo Pay
# =========================================================================


@dataclass(frozen=True)
class DaimoConfig:
    """Resolved Daimo Pay credentials/runtime.  Never logged."""

    api_key: str
    environment: str = "production"
    timeout_seconds: float = _DEFAULT_TIMEOUT

    @property
    def is_sandbox(self) -> bool:
        # Daimo Pay has a single base URL; "sandbox" is a Sardis-side label so a
        # non-prod deployment never reports a result as a settled production
        # movement.  The real network path is identical.
        return _is_sandbox_env(self.environment)


@dataclass
class DaimoPayment:
    """Normalized Daimo Pay payment."""

    id: str
    url: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class DaimoClient:
    """``POST /api/payment`` + ``GET /api/payment/{id}`` over httpx."""

    def __init__(self, config: DaimoConfig) -> None:
        if not config.api_key:
            raise ValueError("Daimo Pay API key is required")
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    @property
    def is_sandbox(self) -> bool:
        return self._config.is_sandbox

    async def _client_(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=_DAIMO_BASE,
                timeout=self._config.timeout_seconds,
                headers={
                    "Api-Key": self._config.api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def create_payment(
        self,
        *,
        intent: str,
        destination_address: str,
        chain_id: int,
        token_address: str,
        amount_units: str,
        refund_address: str | None = None,
        external_id: str | None = None,
        metadata: dict[str, str] | None = None,
        redirect_uri: str | None = None,
    ) -> DaimoPayment:
        """``POST /api/payment`` — create a hosted any-token->USDC payment.

        ``amount_units`` is a precise decimal string; the destination receives
        EXACTLY that amount.  No float is ever used to build it.
        """
        display: dict[str, Any] = {"intent": intent}
        if redirect_uri:
            display["redirectUri"] = redirect_uri
        body: dict[str, Any] = {
            "display": display,
            "destination": {
                "destinationAddress": destination_address,
                "chainId": chain_id,
                "tokenAddress": token_address,
                "amountUnits": amount_units,
            },
        }
        if refund_address:
            body["refundAddress"] = refund_address
        if external_id:
            body["externalId"] = external_id
        if metadata:
            body["metadata"] = metadata

        client = await self._client_()
        resp = await client.post("/api/payment", json=body)
        resp.raise_for_status()
        data = resp.json()
        payment = data.get("payment") or {}
        return DaimoPayment(
            id=str(data.get("id") or payment.get("id") or ""),
            url=data.get("url"),
            status=str(payment.get("status", "payment_unpaid")),
            raw=data,
        )

    async def get_payment(self, payment_id: str) -> DaimoPayment:
        client = await self._client_()
        resp = await client.get(f"/api/payment/{payment_id}")
        resp.raise_for_status()
        data = resp.json()
        return DaimoPayment(
            id=str(data.get("id", payment_id)),
            url=data.get("url"),
            status=str(data.get("status", "payment_unpaid")),
            raw=data,
        )
