"""Circle Payments Network funding adapter."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from .funding import FundingRequest, FundingResult
from .funding_ports import FundingRailAdapter


class CircleCPNFundingAdapter(FundingRailAdapter):
    """Funding adapter backed by Circle Payments Network payment APIs."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        payout_path: str,
        status_path: str,
        auth_style: str = "bearer",
        timeout_seconds: float = 20.0,
        program_id: str = "",
        collection_path: str = "/v1/cpn/collections",
    ) -> None:
        if not api_key:
            raise ValueError("circle_cpn: api_key is required")
        if not base_url:
            raise ValueError("circle_cpn: base_url is required")
        if not payout_path:
            raise ValueError("circle_cpn: payout_path is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._payout_path = payout_path
        self._status_path = status_path
        self._auth_style = (auth_style or "bearer").strip().lower()
        self._timeout_seconds = float(timeout_seconds)
        self._program_id = program_id
        self._collection_path = collection_path

    @property
    def provider(self) -> str:
        return "circle_cpn"

    @property
    def rail(self) -> str:
        return "fiat"

    def _headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "sardis-core/circle-cpn-adapter",
        }
        if self._auth_style == "x_api_key":
            headers["X-API-Key"] = self._api_key
        else:
            headers["Authorization"] = f"Bearer {self._api_key}"
        if self._program_id:
            headers["X-Program-Id"] = self._program_id
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        *,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/{path.lstrip('/')}"
        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method,
                url,
                headers=self._headers(),
                json=payload,
            )
        response.raise_for_status()
        if not response.content:
            return {}
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("circle_cpn_invalid_response_shape")
        return data

    async def fund(self, request: FundingRequest) -> FundingResult:
        payload: dict[str, Any] = {
            "amount": str(request.amount),
            "currency": request.currency.upper(),
            "description": request.description,
            "metadata": request.metadata,
        }
        if request.connected_account_id:
            payload["connected_account_id"] = request.connected_account_id

        body = await self._request("POST", self._payout_path, payload=payload)

        transfer_id = str(
            body.get("id")
            or body.get("payment_id")
            or body.get("paymentId")
            or body.get("transfer_id")
            or ""
        )
        if not transfer_id:
            raise RuntimeError("circle_cpn_missing_transfer_id")

        amount_value = Decimal(str(body.get("amount") or request.amount))
        currency_value = str(body.get("currency") or request.currency).upper()
        status_value = str(body.get("status") or "processing")

        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

        return FundingResult(
            provider=self.provider,
            rail=self.rail,
            transfer_id=transfer_id,
            amount=amount_value,
            currency=currency_value,
            status=status_value,
            metadata=metadata,
        )

    async def collect(self, request: FundingRequest) -> FundingResult:
        """Initiate a collection (inbound payment) into the Sardis Circle account.

        Mirrors the ``fund()`` flow but POSTs to the collection endpoint so that
        funds flow *into* the platform account rather than out to a connected
        account.
        """
        payload: dict[str, Any] = {
            "amount": str(request.amount),
            "currency": request.currency.upper(),
            "description": request.description,
            "metadata": request.metadata,
        }
        if request.connected_account_id:
            payload["connected_account_id"] = request.connected_account_id

        body = await self._request("POST", self._collection_path, payload=payload)

        transfer_id = str(
            body.get("id")
            or body.get("collection_id")
            or body.get("collectionId")
            or body.get("payment_id")
            or body.get("paymentId")
            or body.get("transfer_id")
            or ""
        )
        if not transfer_id:
            raise RuntimeError("circle_cpn_missing_collection_id")

        amount_value = Decimal(str(body.get("amount") or request.amount))
        currency_value = str(body.get("currency") or request.currency).upper()
        status_value = str(body.get("status") or "processing")

        metadata = body.get("metadata") if isinstance(body.get("metadata"), dict) else {}

        return FundingResult(
            provider=self.provider,
            rail=self.rail,
            transfer_id=transfer_id,
            amount=amount_value,
            currency=currency_value,
            status=status_value,
            metadata=metadata,
        )

    async def quote(self, request: FundingRequest) -> dict[str, Any]:
        # CPN quote surfaces vary by account configuration; return a local synthetic quote.
        return {
            "provider": self.provider,
            "rail": self.rail,
            "amount": str(request.amount),
            "currency": request.currency.upper(),
            "description": request.description,
            "quote_type": "synthetic",
        }

    async def status(self, transfer_id: str) -> dict[str, Any]:
        if not transfer_id:
            raise ValueError("transfer_id is required")
        if not self._status_path:
            return {"id": transfer_id, "status": "unknown"}

        path = self._status_path.replace("{payment_id}", transfer_id)
        body = await self._request("GET", path)
        if "id" not in body and "payment_id" not in body and "paymentId" not in body:
            body["id"] = transfer_id
        return body
