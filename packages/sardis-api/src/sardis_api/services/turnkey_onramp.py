"""Turnkey native fiat onramp service.

Wraps the Turnkey ``init_fiat_on_ramp`` activity and ``get_onramp_transaction_status``
query to let users convert fiat (USD, EUR, etc.) to crypto (USDC) directly inside the
app — no redirects required.

Supported providers:
  - Coinbase  (``FIAT_ON_RAMP_PROVIDER_COINBASE``)
  - MoonPay   (``FIAT_ON_RAMP_PROVIDER_MOONPAY``)

Reference: https://docs.turnkey.com/api-reference/activities/init-fiat-on-ramp
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ACTIVITY_TYPE = "ACTIVITY_TYPE_INIT_FIAT_ON_RAMP"

# Turnkey network enum values
NETWORK_MAP: dict[str, str] = {
    "base": "BASE",
    "ethereum": "ETHEREUM",
    "solana": "SOLANA",
    "bitcoin": "BITCOIN",
}

# Turnkey crypto currency enum values
CRYPTO_MAP: dict[str, str] = {
    "usdc": "USDC",
    "eth": "ETH",
    "sol": "SOL",
    "btc": "BTC",
}

# Turnkey payment method enum values
PAYMENT_METHODS = frozenset({
    "PAYMENT_METHOD_CREDIT_CARD",
    "PAYMENT_METHOD_DEBIT_CARD",
    "PAYMENT_METHOD_ACH_BANK_ACCOUNT",
    "PAYMENT_METHOD_APPLE_PAY",
    "PAYMENT_METHOD_GOOGLE_PAY",
})


class OnrampProvider(str, Enum):
    coinbase = "coinbase"
    moonpay = "moonpay"

    @property
    def turnkey_enum(self) -> str:
        return {
            "coinbase": "FIAT_ON_RAMP_PROVIDER_COINBASE",
            "moonpay": "FIAT_ON_RAMP_PROVIDER_MOONPAY",
        }[self.value]


class OnrampStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    failed = "failed"
    expired = "expired"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OnrampSession:
    """Result of creating a Turnkey onramp session."""

    session_id: str
    onramp_url: str
    transaction_id: str
    provider: str
    target_chain: str
    target_token: str
    wallet_address: str
    amount_usd: str | None


@dataclass(frozen=True)
class OnrampTransactionStatus:
    """Result of querying a Turnkey onramp transaction status."""

    transaction_id: str
    status: str


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class TurnkeyOnrampService:
    """Fiat onramp via Turnkey's native ``init_fiat_on_ramp`` activity.

    Requires a configured ``TurnkeyClient`` from ``sardis-wallet``.
    Provider API keys (Coinbase / MoonPay) must be uploaded to the Turnkey
    dashboard beforehand — they are **not** passed at runtime.
    """

    def __init__(self, turnkey_client: Any | None = None):
        self._client = turnkey_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create_onramp_session(
        self,
        wallet_address: str,
        amount_usd: str | None = None,
        currency: str = "USD",
        provider: str = "coinbase",
        network: str | None = None,
        crypto_currency: str = "usdc",
        country_code: str | None = None,
        country_subdivision_code: str | None = None,
        sandbox: bool | None = None,
    ) -> OnrampSession:
        """Create a Turnkey fiat-on-ramp session.

        Args:
            wallet_address: Destination wallet address (hex for EVM, base58 for Solana).
            amount_usd: Fiat amount as string (must exceed "20" per Turnkey rules).
            currency: ISO 4217 fiat currency code (default ``USD``).
            provider: ``"coinbase"`` or ``"moonpay"``.
            network: Target chain — ``"base"`` (default), ``"ethereum"``, ``"solana"``, ``"bitcoin"``.
            crypto_currency: Target crypto — ``"usdc"`` (default), ``"eth"``, ``"sol"``, ``"btc"``.
            country_code: ISO 3166-1 alpha-2 country code (optional).
            country_subdivision_code: ISO 3166-2 subdivision (required if US).
            sandbox: Force sandbox mode (defaults to env ``SARDIS_ENVIRONMENT != "production"``).

        Returns:
            ``OnrampSession`` with the widget URL and transaction ID.

        Raises:
            RuntimeError: If no Turnkey client is configured.
            ValueError: If the provider or network is unsupported.
        """
        if self._client is None:
            raise RuntimeError(
                "Turnkey client not configured. Set TURNKEY_API_KEY, "
                "TURNKEY_API_PRIVATE_KEY, and TURNKEY_ORGANIZATION_ID."
            )

        # Resolve provider enum
        try:
            prov = OnrampProvider(provider.lower())
        except ValueError:
            raise ValueError(
                f"Unsupported onramp provider: {provider!r}. "
                f"Choose 'coinbase' or 'moonpay'."
            )

        # Resolve network — prefer Base for USDC, fall back to Ethereum
        resolved_network = (network or self._default_network()).lower()
        turnkey_network = NETWORK_MAP.get(resolved_network)
        if turnkey_network is None:
            raise ValueError(
                f"Unsupported network: {resolved_network!r}. "
                f"Supported: {', '.join(NETWORK_MAP)}."
            )

        # Resolve crypto currency
        turnkey_crypto = CRYPTO_MAP.get(crypto_currency.lower())
        if turnkey_crypto is None:
            raise ValueError(
                f"Unsupported crypto currency: {crypto_currency!r}. "
                f"Supported: {', '.join(CRYPTO_MAP)}."
            )

        # Determine sandbox mode
        if sandbox is None:
            sandbox = os.getenv("SARDIS_ENVIRONMENT", "dev") != "production"

        # Build parameters
        parameters: dict[str, Any] = {
            "onrampProvider": prov.turnkey_enum,
            "walletAddress": wallet_address,
            "network": turnkey_network,
            "cryptoCurrencyCode": turnkey_crypto,
        }
        if amount_usd:
            parameters["fiatCurrencyAmount"] = str(amount_usd)
        if currency:
            parameters["fiatCurrencyCode"] = currency.upper()
        if country_code:
            parameters["countryCode"] = country_code.upper()
        if country_subdivision_code:
            parameters["countrySubdivisionCode"] = country_subdivision_code.upper()
        if sandbox:
            parameters["sandboxMode"] = True

        body = {
            "type": ACTIVITY_TYPE,
            "timestampMs": str(int(time.time() * 1000)),
            "organizationId": self._client.organization_id,
            "parameters": parameters,
        }

        logger.info(
            "Turnkey onramp: provider=%s network=%s crypto=%s wallet=%s amount=%s",
            prov.value,
            resolved_network,
            turnkey_crypto,
            wallet_address[:10] + "...",
            amount_usd or "user-chosen",
        )

        result = await self._client.post("/public/v1/submit/init_fiat_on_ramp", body)

        activity = result.get("activity", {})
        activity_id = activity.get("id", "")
        onramp_result = (
            activity.get("result", {}).get("initFiatOnRampResult", {})
        )

        onramp_url = onramp_result.get("onRampUrl", "")
        transaction_id = onramp_result.get("onRampTransactionId", "")

        logger.info(
            "Turnkey onramp session created: activity=%s tx=%s",
            activity_id,
            transaction_id,
        )

        return OnrampSession(
            session_id=activity_id,
            onramp_url=onramp_url,
            transaction_id=transaction_id,
            provider=prov.value,
            target_chain=resolved_network,
            target_token=turnkey_crypto,
            wallet_address=wallet_address,
            amount_usd=amount_usd,
        )

    async def get_transaction_status(
        self,
        transaction_id: str,
        refresh: bool = False,
    ) -> OnrampTransactionStatus:
        """Query the status of an onramp transaction.

        Args:
            transaction_id: The ``onRampTransactionId`` from the session.
            refresh: If ``True``, force a refresh from the provider.

        Returns:
            ``OnrampTransactionStatus`` with the current status string.
        """
        if self._client is None:
            raise RuntimeError("Turnkey client not configured.")

        body: dict[str, Any] = {
            "organizationId": self._client.organization_id,
            "transactionId": transaction_id,
        }
        if refresh:
            body["refresh"] = True

        result = await self._client.post(
            "/public/v1/query/get_onramp_transaction_status",
            body,
        )

        status_str = result.get("transactionStatus", "unknown")

        logger.info(
            "Turnkey onramp status: tx=%s status=%s",
            transaction_id,
            status_str,
        )

        return OnrampTransactionStatus(
            transaction_id=transaction_id,
            status=status_str,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _default_network() -> str:
        """Choose the default network from env or fall back to ``base``."""
        return os.getenv("SARDIS_ONRAMP_DEFAULT_NETWORK", "base")
