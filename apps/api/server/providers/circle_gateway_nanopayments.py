"""Circle Gateway Nanopayments provider adapter."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class CircleGatewayError(RuntimeError):
    """Raised when Circle Gateway returns an unexpected response."""


@dataclass(frozen=True)
class CirclePaymentIntent:
    """Normalized payment intent result returned by Circle Gateway."""

    payment_intent_id: str
    status: str
    raw: dict[str, Any]


class CircleGatewayNanopaymentsClient:
    """Minimal client for Circle Gateway Nanopayments payment-intent lifecycle."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://gateway-api.circle.com",
        timeout_seconds: float = 20.0,
    ) -> None:
        if not api_key:
            raise ValueError("Circle Gateway API key is required")
        self._api_key = api_key
        self._base_url = (base_url or "").rstrip("/")
        self._timeout = timeout_seconds
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.request(method, path, json=json)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:1000]
            logger.error(
                "Circle Gateway error method=%s path=%s status=%s body=%s",
                method,
                path,
                exc.response.status_code,
                body,
            )
            raise CircleGatewayError(
                f"circle_gateway_http_error:{exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise CircleGatewayError("circle_gateway_network_error") from exc

        data = response.json()
        if isinstance(data, dict):
            return data
        raise CircleGatewayError("circle_gateway_invalid_response_shape")

    def _to_intent(self, data: dict[str, Any]) -> CirclePaymentIntent:
        payment_intent_id = (
            data.get("paymentIntentId")
            or data.get("payment_intent_id")
            or data.get("id")
        )
        if not payment_intent_id:
            raise CircleGatewayError("circle_gateway_missing_payment_intent_id")
        status = str(data.get("status") or "unknown")
        return CirclePaymentIntent(
            payment_intent_id=str(payment_intent_id),
            status=status,
            raw=data,
        )

    async def create_payment_intent(self, payload: dict[str, Any]) -> CirclePaymentIntent:
        """Create a Circle payment intent."""
        result = await self._request("POST", "/v1/payment-intents", json=payload)
        return self._to_intent(result)

    async def attach_signature(
        self,
        payment_intent_id: str,
        payload: dict[str, Any],
    ) -> CirclePaymentIntent:
        """Attach a signed proof to an existing payment intent."""
        result = await self._request(
            "PUT",
            f"/v1/payment-intents/{payment_intent_id}",
            json=payload,
        )
        return self._to_intent(result)

    async def settle_payment_intent(self, payment_intent_id: str) -> CirclePaymentIntent:
        """Settle a payment intent through Circle Gateway."""
        result = await self._request(
            "POST",
            f"/v1/payment-intents/{payment_intent_id}/settle",
            json={},
        )
        return self._to_intent(result)

