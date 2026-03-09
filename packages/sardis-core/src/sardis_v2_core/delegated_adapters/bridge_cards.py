"""Bridge-to-Stripe treasury card pre-funding adapter.

This module implements the ``FundingRailAdapter`` protocol for the
Bridge-to-Stripe treasury flow used to pre-fund virtual card programs.

When an agent wallet holds USDC it can be converted to USD and pushed
into a Stripe Issuing balance via Bridge's payout API.  This adapter
translates a provider-neutral ``FundingRequest`` into Bridge HTTP calls
and returns a normalised ``FundingResult``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

import httpx

from ..funding import FundingRequest, FundingResult
from ..funding_ports import (  # noqa: F401 – imported for type-checking
    FundingRail,
    FundingRailAdapter,
)

logger = logging.getLogger(__name__)


class BridgeCardFundingAdapter:
    """FundingRailAdapter that routes Bridge stablecoin payouts into Stripe treasury.

    Implements the :class:`~sardis_v2_core.funding_ports.FundingRailAdapter`
    structural protocol — no explicit base class needed.

    Constructor args:
        api_key: Bridge API key (``Authorization: Bearer`` header)
        base_url: Bridge API base URL, e.g. ``https://api.bridge.xyz/v0``
        funding_path: Path for card-funding endpoint, default ``/transfers``
        timeout_seconds: HTTP request timeout
        api_secret: Optional secondary secret forwarded as ``X-API-Secret``
        program_id: Optional card program identifier forwarded as ``X-Program-Id``
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        funding_path: str = "/transfers",
        timeout_seconds: float = 20.0,
        api_secret: str = "",
        program_id: str = "",
    ) -> None:
        if not api_key:
            raise ValueError("BridgeCardFundingAdapter: api_key is required")
        if not base_url:
            raise ValueError("BridgeCardFundingAdapter: base_url is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._funding_path = funding_path
        self._timeout_seconds = timeout_seconds
        self._api_secret = api_secret
        self._program_id = program_id

    # ── FundingRailAdapter protocol ──────────────────────────────────────

    @property
    def provider(self) -> str:
        return "bridge_cards"

    @property
    def rail(self) -> FundingRail:
        return "fiat"

    # ── Public methods ───────────────────────────────────────────────────

    async def fund(self, request: FundingRequest) -> FundingResult:
        """POST a card pre-funding transfer to Bridge and return a normalised result.

        The request body follows Bridge's transfer API shape.  The response is
        normalised back to a ``FundingResult`` using the same field-extraction
        logic as :class:`~sardis_v2_core.funding.HttpTopupFundingAdapter`.
        """
        url = f"{self._base_url}/{self._funding_path.lstrip('/')}"
        payload: dict[str, Any] = {
            "amount": str(request.amount),
            "currency": request.currency.upper(),
            "description": request.description,
            "metadata": request.metadata,
        }
        if request.connected_account_id:
            payload["connected_account_id"] = request.connected_account_id

        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                url,
                headers=self._build_headers(),
                json=payload,
            )
        response.raise_for_status()
        body: dict[str, Any] = response.json() if response.content else {}

        transfer_id = str(
            body.get("id")
            or body.get("transfer_id")
            or body.get("payout_id")
            or "unknown"
        )
        amount_value = Decimal(str(body.get("amount") or request.amount))
        currency_value = str(body.get("currency") or request.currency).upper()
        status_value = str(body.get("status") or "processing")
        resp_metadata: dict[str, Any] = (
            body.get("metadata")
            if isinstance(body.get("metadata"), dict)
            else {}
        )

        logger.info(
            "BridgeCardFundingAdapter.fund success transfer_id=%s status=%s",
            transfer_id,
            status_value,
        )

        return FundingResult(
            provider=self.provider,
            rail=self.rail,
            transfer_id=transfer_id,
            amount=amount_value,
            currency=currency_value,
            status=status_value,
            metadata=resp_metadata,
        )

    async def quote(self, request: FundingRequest) -> dict[str, Any]:
        """Return a synthetic quote for the given funding request.

        Bridge does not expose a dedicated pre-quote endpoint for card
        funding, so we compute an estimate based on the flat fee structure
        documented in the Bridge partner agreement (0.5 % per transfer).
        """
        fee_rate = Decimal("0.005")
        fee_amount = (request.amount * fee_rate).quantize(Decimal("0.01"))
        net_amount = request.amount - fee_amount

        return {
            "provider": self.provider,
            "rail": self.rail,
            "input_amount": str(request.amount),
            "input_currency": request.currency.upper(),
            "fee_amount": str(fee_amount),
            "fee_rate": str(fee_rate),
            "net_amount": str(net_amount),
            "output_currency": request.currency.upper(),
            "estimated_settlement": "1-2 business days",
        }

    async def status(self, transfer_id: str) -> dict[str, Any]:
        """GET the current status of a Bridge transfer by its ID."""
        url = f"{self._base_url}/{self._funding_path.lstrip('/')}/{transfer_id}"
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url, headers=self._build_headers())
        response.raise_for_status()
        body: dict[str, Any] = response.json() if response.content else {}
        return {
            "transfer_id": transfer_id,
            "status": body.get("status", "unknown"),
            "amount": body.get("amount"),
            "currency": body.get("currency"),
            "raw": body,
        }

    # ── Private helpers ──────────────────────────────────────────────────

    def _build_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "sardis-core/bridge-cards-funding-adapter",
            "Authorization": f"Bearer {self._api_key}",
        }
        if self._api_secret:
            headers["X-API-Secret"] = self._api_secret
        if self._program_id:
            headers["X-Program-Id"] = self._program_id
        return headers
