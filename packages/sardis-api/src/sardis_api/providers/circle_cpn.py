"""Circle Payments Network provider client."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx


class CircleCPNError(RuntimeError):
    """Raised for Circle CPN request/response errors."""


@dataclass(frozen=True)
class CircleCPNPayment:
    payment_id: str
    status: str
    raw: dict[str, Any]


class CircleCPNClient:
    """Minimal async client for Circle Payments Network payment operations."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = "https://api.circle.com",
        payout_path: str = "/v1/cpn/payments",
        collection_path: str = "/v1/cpn/collections",
        status_path: str = "/v1/cpn/payments/{payment_id}",
        auth_style: str = "bearer",
        timeout_seconds: float = 20.0,
        program_id: str = "",
    ) -> None:
        if not api_key:
            raise ValueError("Circle CPN API key is required")
        self._api_key = api_key
        self._base_url = (base_url or "").rstrip("/")
        self._payout_path = payout_path
        self._collection_path = collection_path
        self._status_path = status_path
        self._auth_style = (auth_style or "bearer").strip().lower()
        self._timeout_seconds = timeout_seconds
        self._program_id = program_id
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            if self._auth_style == "x_api_key":
                headers["X-API-Key"] = self._api_key
            else:
                headers["Authorization"] = f"Bearer {self._api_key}"
            if self._program_id:
                headers["X-Program-Id"] = self._program_id
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=self._timeout_seconds,
                headers=headers,
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
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        try:
            response = await client.request(method, path, json=json_payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise CircleCPNError(f"circle_cpn_http_error:{exc.response.status_code}") from exc
        except httpx.HTTPError as exc:
            raise CircleCPNError("circle_cpn_network_error") from exc

        data = response.json()
        if not isinstance(data, dict):
            raise CircleCPNError("circle_cpn_invalid_response_shape")
        return data

    def _normalize_payment(self, payload: dict[str, Any]) -> CircleCPNPayment:
        payment_id = str(
            payload.get("payment_id")
            or payload.get("paymentId")
            or payload.get("id")
            or ""
        )
        if not payment_id:
            raise CircleCPNError("circle_cpn_missing_payment_id")
        status = str(payload.get("status") or "unknown")
        return CircleCPNPayment(payment_id=payment_id, status=status, raw=payload)

    async def create_payout(self, payload: dict[str, Any]) -> CircleCPNPayment:
        result = await self._request("POST", self._payout_path, json_payload=payload)
        return self._normalize_payment(result)

    async def create_collection(self, payload: dict[str, Any]) -> CircleCPNPayment:
        result = await self._request("POST", self._collection_path, json_payload=payload)
        return self._normalize_payment(result)

    async def get_payment_status(self, payment_id: str) -> CircleCPNPayment:
        if not payment_id:
            raise ValueError("payment_id is required")
        path = self._status_path.replace("{payment_id}", payment_id)
        result = await self._request("GET", path)
        if "id" not in result and "payment_id" not in result and "paymentId" not in result:
            result["id"] = payment_id
        return self._normalize_payment(result)
