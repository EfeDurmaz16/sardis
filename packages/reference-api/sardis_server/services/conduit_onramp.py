"""Conduit Pay integration for fiat-to-USDC onramp on Tempo (native, no bridge).

Conduit is Tempo's official onramp partner, enabling direct fiat → USDC
settlement on Tempo without requiring a bridge hop.

Flow:
  1. Create customer (KYC/KYB via Conduit)
  2. Create a payment method (wallet destination)
  3. Get a quote (fiat → USDC with pricing)
  4. Create an onramp transaction (fiat → USDC on Tempo)
  5. Poll transaction status until completed

API reference: https://docs.conduit.financial/api-reference/introduction
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SANDBOX_BASE_URL = "https://sandbox-api.conduit.financial"
PRODUCTION_BASE_URL = "https://api.conduit.financial"
API_VERSION = "2024-12-01"

# Conduit-supported networks for USDC
SUPPORTED_NETWORKS = frozenset({"ethereum", "base", "solana", "polygon", "tempo"})

# Conduit-supported stablecoins
SUPPORTED_ASSETS = frozenset({"USDC", "USDT", "RLUSD"})


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConduitCustomer:
    """Result of creating a Conduit customer."""

    customer_id: str
    status: str
    kyb_link: str | None = None


@dataclass(frozen=True)
class ConduitQuote:
    """Result of creating a Conduit quote."""

    quote_id: str
    source_amount: str
    source_asset: str
    target_amount: str
    target_asset: str
    target_network: str
    expires_at: str


@dataclass(frozen=True)
class ConduitTransaction:
    """Result of creating a Conduit onramp transaction."""

    transaction_id: str
    quote_id: str
    status: str
    source_amount: str
    source_asset: str
    target_amount: str
    target_asset: str
    target_network: str
    deposit_instructions: dict[str, Any] | None = None
    created_at: str = ""


@dataclass(frozen=True)
class ConduitTransactionStatus:
    """Result of querying a Conduit transaction."""

    transaction_id: str
    status: str
    completed_at: str | None = None


@dataclass(frozen=True)
class ConduitPaymentMethod:
    """Result of creating a Conduit payment method (wallet destination)."""

    payment_method_id: str
    type: str
    network: str | None = None
    address: str | None = None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class ConduitOnrampService:
    """Conduit Pay integration for fiat → USDC on Tempo (native, no bridge).

    Authentication requires both ``X-API-Key`` and ``X-API-Secret`` headers,
    plus an ``Api-Version`` header.

    Environment variables:
      - ``CONDUIT_API_KEY``   — API key from the Conduit dashboard
      - ``CONDUIT_API_SECRET`` — API secret from the Conduit dashboard
      - ``CONDUIT_SANDBOX``   — ``"true"`` to use the sandbox environment
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        sandbox: bool = True,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.sandbox = sandbox
        self.base_url = SANDBOX_BASE_URL if sandbox else PRODUCTION_BASE_URL
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "X-API-Key": self.api_key,
                    "X-API-Secret": self.api_secret,
                    "Api-Version": API_VERSION,
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to the Conduit API."""
        client = self._get_client()
        resp = await client.request(method, path, json=json, params=params)

        if resp.status_code >= 400:
            detail = resp.text
            try:
                error_body = resp.json()
                errors = error_body.get("errors", [])
                if errors:
                    detail = "; ".join(
                        e.get("detail", str(e)) for e in errors
                    )
            except Exception:
                pass
            logger.error(
                "Conduit API error: %s %s → %d: %s",
                method, path, resp.status_code, detail,
            )
            raise ConduitAPIError(
                status_code=resp.status_code,
                detail=detail,
            )

        return resp.json()

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ------------------------------------------------------------------
    # Customer management
    # ------------------------------------------------------------------

    async def create_customer(
        self,
        business_legal_name: str,
        country: str = "USA",
        onboarding_flow: str = "kyb_link",
    ) -> ConduitCustomer:
        """Register a customer for KYC/KYB verification.

        Uses the ``kyb_link`` flow by default, which returns a hosted
        verification URL that the customer completes independently.

        Args:
            business_legal_name: Legal entity name.
            country: ISO 3166-1 alpha-3 country code (default ``USA``).
            onboarding_flow: ``"kyb_link"`` (hosted) or ``"direct"`` (API-managed).

        Returns:
            ``ConduitCustomer`` with the customer ID and optional KYB link.
        """
        body: dict[str, Any] = {
            "businessLegalName": business_legal_name,
            "country": country,
            "onboardingFlow": onboarding_flow,
        }

        data = await self._request("POST", "/customers", json=body)

        logger.info(
            "Conduit customer created: id=%s flow=%s",
            data.get("id"), onboarding_flow,
        )

        return ConduitCustomer(
            customer_id=data["id"],
            status=data.get("status", "created"),
            kyb_link=data.get("kybLink"),
        )

    async def get_customer(self, customer_id: str) -> dict[str, Any]:
        """Retrieve customer details including verification status."""
        return await self._request("GET", f"/customers/{customer_id}")

    # ------------------------------------------------------------------
    # Payment methods
    # ------------------------------------------------------------------

    async def create_wallet_payment_method(
        self,
        customer_id: str,
        wallet_address: str,
        network: str = "tempo",
        asset: str = "USDC",
    ) -> ConduitPaymentMethod:
        """Register a crypto wallet as a payment method for a customer.

        Args:
            customer_id: The Conduit customer ID.
            wallet_address: Destination wallet address (hex for EVM).
            network: Target blockchain network (default ``tempo``).
            asset: Target asset (default ``USDC``).

        Returns:
            ``ConduitPaymentMethod`` with the payment method ID.
        """
        body: dict[str, Any] = {
            "type": "crypto_wallet",
            "address": wallet_address,
            "network": network,
            "asset": asset,
        }

        data = await self._request(
            "POST",
            f"/customers/{customer_id}/payment-methods",
            json=body,
        )

        logger.info(
            "Conduit wallet payment method created: id=%s network=%s",
            data.get("id"), network,
        )

        return ConduitPaymentMethod(
            payment_method_id=data["id"],
            type="crypto_wallet",
            network=network,
            address=wallet_address,
        )

    # ------------------------------------------------------------------
    # Quotes
    # ------------------------------------------------------------------

    async def get_quote(
        self,
        amount_usd: str,
        target_asset: str = "USDC",
        target_network: str = "tempo",
        source_currency: str = "USD",
    ) -> ConduitQuote:
        """Get a quote for fiat → stablecoin conversion.

        Args:
            amount_usd: Source fiat amount as a string (e.g. ``"100.00"``).
            target_asset: Target crypto asset (default ``USDC``).
            target_network: Target blockchain network (default ``tempo``).
            source_currency: Source fiat currency code (default ``USD``).

        Returns:
            ``ConduitQuote`` with the locked rate and expiry.

        Raises:
            ValueError: If the target network or asset is unsupported.
        """
        network_lower = target_network.lower()
        if network_lower not in SUPPORTED_NETWORKS:
            raise ValueError(
                f"Unsupported network: {target_network!r}. "
                f"Supported: {', '.join(sorted(SUPPORTED_NETWORKS))}."
            )

        asset_upper = target_asset.upper()
        if asset_upper not in SUPPORTED_ASSETS:
            raise ValueError(
                f"Unsupported asset: {target_asset!r}. "
                f"Supported: {', '.join(sorted(SUPPORTED_ASSETS))}."
            )

        body: dict[str, Any] = {
            "source": {
                "amount": amount_usd,
                "asset": source_currency.upper(),
            },
            "target": {
                "asset": asset_upper,
                "network": network_lower,
            },
        }

        data = await self._request("POST", "/quotes", json=body)

        source = data.get("source", {})
        target = data.get("target", {})

        logger.info(
            "Conduit quote: id=%s %s %s → %s %s on %s, expires=%s",
            data.get("id"),
            source.get("amount"), source.get("asset"),
            target.get("amount"), target.get("asset"),
            target.get("network"),
            data.get("expiresAt"),
        )

        return ConduitQuote(
            quote_id=data["id"],
            source_amount=str(source.get("amount", amount_usd)),
            source_asset=str(source.get("asset", source_currency)),
            target_amount=str(target.get("amount", amount_usd)),
            target_asset=str(target.get("asset", asset_upper)),
            target_network=str(target.get("network", network_lower)),
            expires_at=str(data.get("expiresAt", "")),
        )

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    async def create_onramp_transaction(
        self,
        quote_id: str,
        source_payment_method_id: str,
        destination_payment_method_id: str,
        purpose: str = "TreasuryManagement",
        reference: str | None = None,
    ) -> ConduitTransaction:
        """Execute a fiat → USDC onramp transaction.

        The quote must be unexpired. Funds are deposited per the onramp
        instructions returned by the Conduit API.

        Args:
            quote_id: The quote ID from ``get_quote``.
            source_payment_method_id: Source bank account / payment method ID.
            destination_payment_method_id: Destination wallet payment method ID.
            purpose: Transaction purpose (e.g. ``"TreasuryManagement"``).
            reference: Optional custom reference string.

        Returns:
            ``ConduitTransaction`` with the transaction ID and deposit instructions.
        """
        body: dict[str, Any] = {
            "type": "onramp",
            "quote": quote_id,
            "source": source_payment_method_id,
            "destination": destination_payment_method_id,
            "purpose": purpose,
        }
        if reference:
            body["reference"] = reference

        data = await self._request("POST", "/transactions", json=body)

        source = data.get("source", {})
        destination = data.get("destination", {})
        instructions = data.get("onrampInstructions")

        logger.info(
            "Conduit onramp transaction: id=%s status=%s %s %s → %s %s",
            data.get("id"), data.get("status"),
            source.get("amount"), source.get("asset"),
            destination.get("amount"), destination.get("asset"),
        )

        return ConduitTransaction(
            transaction_id=data["id"],
            quote_id=quote_id,
            status=data.get("status", "created"),
            source_amount=str(source.get("amount", "")),
            source_asset=str(source.get("asset", "")),
            target_amount=str(destination.get("amount", "")),
            target_asset=str(destination.get("asset", "")),
            target_network=str(destination.get("network", "")),
            deposit_instructions=instructions,
            created_at=str(data.get("createdAt", "")),
        )

    async def get_transaction_status(
        self,
        transaction_id: str,
    ) -> ConduitTransactionStatus:
        """Poll the status of a Conduit transaction.

        Args:
            transaction_id: The transaction ID from ``create_onramp_transaction``.

        Returns:
            ``ConduitTransactionStatus`` with the current status.
        """
        data = await self._request("GET", f"/transactions/{transaction_id}")

        logger.info(
            "Conduit transaction status: id=%s status=%s",
            transaction_id, data.get("status"),
        )

        return ConduitTransactionStatus(
            transaction_id=transaction_id,
            status=data.get("status", "unknown"),
            completed_at=data.get("completedAt"),
        )


# ---------------------------------------------------------------------------
# Error class
# ---------------------------------------------------------------------------


class ConduitAPIError(Exception):
    """Raised when the Conduit API returns an error response."""

    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Conduit API {status_code}: {detail}")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_conduit_service() -> ConduitOnrampService | None:
    """Build a ConduitOnrampService from environment variables.

    Returns ``None`` if ``CONDUIT_API_KEY`` is not set.

    Env vars:
      - ``CONDUIT_API_KEY``    — required
      - ``CONDUIT_API_SECRET`` — required
      - ``CONDUIT_SANDBOX``    — ``"true"`` (default) or ``"false"``
    """
    api_key = os.getenv("CONDUIT_API_KEY")
    api_secret = os.getenv("CONDUIT_API_SECRET")

    if not api_key or not api_secret:
        return None

    sandbox = os.getenv("CONDUIT_SANDBOX", "true").lower() in ("true", "1", "yes")

    return ConduitOnrampService(
        api_key=api_key,
        api_secret=api_secret,
        sandbox=sandbox,
    )
