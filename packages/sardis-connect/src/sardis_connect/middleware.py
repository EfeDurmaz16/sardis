"""Sardis Connect middleware for FastAPI.

Makes any API agent-ready by adding:
1. /.well-known/sardis.json — agent discovery manifest
2. /sardis/pay — payment initiation endpoint
3. /sardis/verify — payment verification endpoint
4. Optional: x402 middleware for automatic 402 responses on priced endpoints
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from decimal import Decimal
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .models import PricedEndpoint, PricingModel, ServiceManifest

logger = logging.getLogger("sardis.connect")

_SARDIS_API_DEFAULT = "https://api.sardis.sh"


class PayRequest(BaseModel):
    """Agent requests payment for an endpoint."""
    endpoint: str
    amount: str | None = None
    currency: str = "USD"
    payer_wallet_id: str | None = None
    mandate_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PayResponse(BaseModel):
    """Payment session created for agent."""
    session_id: str
    client_secret: str
    checkout_url: str
    amount: str
    currency: str
    status: str = "pending"


class VerifyRequest(BaseModel):
    """Verify a payment was completed."""
    session_id: str


class VerifyResponse(BaseModel):
    """Payment verification result."""
    verified: bool
    session_id: str
    amount: str
    currency: str
    payer_id: str | None = None
    error: str | None = None


class UsageReportRequest(BaseModel):
    """Report metered usage for a session."""
    session_id: str
    endpoint: str
    units: int = Field(..., gt=0, description="Number of units consumed (tokens, calls, etc.)")
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsageReportResponse(BaseModel):
    """Usage report confirmation with calculated charge."""
    session_id: str
    endpoint: str
    units: int
    unit_price: str
    total_charge: str
    currency: str


class SardisConnect:
    """Main integration class. Add to your FastAPI app in 3 lines.

    Usage:
        from sardis_connect import SardisConnect

        sardis = SardisConnect(api_key="mch_live_xxx")
        app.include_router(sardis.router)

    This adds:
        GET  /.well-known/sardis.json  — Agent discovery manifest
        POST /sardis/pay              — Create payment session
        POST /sardis/verify           — Verify payment completed
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        merchant_id: str | None = None,
        service_name: str = "API Service",
        service_description: str = "API endpoints available for agent payments",
        base_url: str | None = None,
        endpoints: list[PricedEndpoint] | None = None,
        sardis_api_url: str | None = None,
        webhook_secret: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("SARDIS_MERCHANT_API_KEY", "")
        self._merchant_id = merchant_id or os.environ.get("SARDIS_MERCHANT_ID", "")
        self._service_name = service_name
        self._service_description = service_description
        self._base_url = base_url or os.environ.get("SARDIS_CONNECT_BASE_URL", "")
        self._endpoints: list[PricedEndpoint] = endpoints or []
        self._sardis_api = sardis_api_url or os.environ.get("SARDIS_API_URL", _SARDIS_API_DEFAULT)
        self._webhook_secret = webhook_secret or os.environ.get("SARDIS_WEBHOOK_SECRET", "")

        self._router = APIRouter(tags=["sardis-connect"])
        self._setup_routes()

    @property
    def router(self) -> APIRouter:
        """FastAPI router to include in your app."""
        return self._router

    def add_endpoint(self, endpoint: PricedEndpoint) -> None:
        """Register a priced endpoint after initialization."""
        self._endpoints.append(endpoint)

    def price(
        self,
        path: str,
        amount: Decimal | str = "0.01",
        currency: str = "USD",
        description: str = "",
        method: str = "POST",
        category: str | None = None,
    ) -> PricedEndpoint:
        """Convenience method to add a priced endpoint.

        Usage:
            sardis.price("/api/generate", amount="0.05", description="Generate text")
        """
        ep = PricedEndpoint(
            path=path,
            method=method,
            price=Decimal(str(amount)),
            currency=currency,
            description=description,
            category=category,
        )
        self._endpoints.append(ep)
        return ep

    def meter(
        self,
        path: str,
        per_unit: Decimal | str = "0.001",
        unit: str = "token",
        currency: str = "USD",
        description: str = "",
        method: str = "POST",
        category: str | None = None,
    ) -> PricedEndpoint:
        """Register a metered (usage-based) endpoint.

        Instead of a fixed price per call, the agent pays per unit consumed.
        After the API call, the merchant reports actual usage via /sardis/usage.

        Usage:
            sardis.meter("/api/generate", per_unit="0.001", unit="token")
            # Agent uses 1500 tokens → charged $1.50
        """
        ep = PricedEndpoint(
            path=path,
            method=method,
            price=Decimal(str(per_unit)),
            currency=currency,
            description=description,
            pricing_model=PricingModel.PER_UNIT,
            unit_name=unit,
            category=category,
        )
        self._endpoints.append(ep)
        return ep

    def _get_manifest(self) -> dict[str, Any]:
        """Build the service manifest for agent discovery."""
        manifest = ServiceManifest(
            name=self._service_name,
            description=self._service_description,
            base_url=self._base_url,
            endpoints=self._endpoints,
            merchant_id=self._merchant_id,
        )
        return {
            "version": manifest.version,
            "name": manifest.name,
            "description": manifest.description,
            "base_url": manifest.base_url,
            "merchant_id": manifest.merchant_id,
            "accepts": manifest.accepts,
            "endpoints": [
                {
                    "path": ep.path,
                    "method": ep.method,
                    "price": str(ep.price),
                    "currency": ep.currency,
                    "description": ep.description,
                    "pricing_model": ep.pricing_model.value,
                    "unit_name": ep.unit_name,
                    "category": ep.category,
                    "rate_limit": ep.rate_limit,
                    "requires_auth": ep.requires_auth,
                }
                for ep in self._endpoints
            ],
        }

    def _setup_routes(self) -> None:
        """Register discovery, payment, and verification routes."""

        @self._router.get("/.well-known/sardis.json")
        async def sardis_manifest() -> dict[str, Any]:
            """Agent discovery endpoint.

            AI agents fetch this to learn what the API offers,
            what it costs, and how to pay.
            """
            return self._get_manifest()

        @self._router.post("/sardis/pay", response_model=PayResponse)
        async def sardis_pay(body: PayRequest) -> PayResponse:
            """Create a payment session for an agent.

            The agent calls this before accessing a priced endpoint.
            Returns a checkout URL or session for payment.
            """
            # Find the endpoint pricing
            endpoint = self._find_endpoint(body.endpoint)
            if not endpoint:
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint '{body.endpoint}' not found in pricing manifest",
                )

            amount = body.amount or str(endpoint.price)

            # Create checkout session via Sardis API
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._sardis_api}/api/v2/merchant-checkout/sessions",
                    json={
                        "merchant_id": self._merchant_id,
                        "amount": amount,
                        "currency": body.currency,
                        "description": endpoint.description or f"Payment for {endpoint.path}",
                        "metadata": {
                            "endpoint": body.endpoint,
                            "mandate_id": body.mandate_id,
                            **body.metadata,
                        },
                    },
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )

                if resp.status_code != 201:
                    logger.error("Sardis API error: %s %s", resp.status_code, resp.text)
                    raise HTTPException(
                        status_code=502,
                        detail="Failed to create payment session",
                    )

                data = resp.json()

            return PayResponse(
                session_id=data["session_id"],
                client_secret=data.get("client_secret", ""),
                checkout_url=data.get("checkout_url", ""),
                amount=amount,
                currency=body.currency,
            )

        @self._router.post("/sardis/verify", response_model=VerifyResponse)
        async def sardis_verify(body: VerifyRequest) -> VerifyResponse:
            """Verify that a payment session was completed.

            Agents call this after payment to prove they paid.
            Merchants should check this before granting access.
            """
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    f"{self._sardis_api}/api/v2/merchant-checkout/sessions/{body.session_id}",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )

                if resp.status_code != 200:
                    return VerifyResponse(
                        verified=False,
                        session_id=body.session_id,
                        amount="0",
                        currency="USD",
                        error="Session not found",
                    )

                data = resp.json()

            is_paid = data.get("status") in ("paid", "settled")
            return VerifyResponse(
                verified=is_paid,
                session_id=body.session_id,
                amount=data.get("amount", "0"),
                currency=data.get("currency", "USD"),
                payer_id=data.get("payer_wallet_id"),
                error=None if is_paid else f"Session status: {data.get('status')}",
            )

        @self._router.post("/sardis/webhooks")
        async def sardis_webhook(request: Request) -> dict[str, str]:
            """Receive payment webhooks from Sardis.

            Merchants can use this to get real-time notifications
            when payments complete.
            """
            if not self._webhook_secret:
                raise HTTPException(status_code=501, detail="Webhooks not configured")

            payload = await request.body()
            signature = request.headers.get("X-Sardis-Signature", "")

            if not self._verify_webhook(payload, signature):
                raise HTTPException(status_code=400, detail="Invalid webhook signature")

            data = json.loads(payload)
            event_type = data.get("event_type", "")

            logger.info("Sardis webhook: %s", event_type)
            # Merchants can override this by subclassing SardisConnect
            return {"status": "ok"}

        @self._router.post("/sardis/usage")
        async def report_usage(body: UsageReportRequest) -> UsageReportResponse:
            """Report metered usage for a payment session.

            After an agent uses a metered endpoint, the merchant reports
            actual usage (e.g., tokens consumed). Sardis calculates the
            charge and settles based on per-unit pricing.

            Usage:
                POST /sardis/usage
                {"session_id": "mcs_xxx", "endpoint": "/api/generate", "units": 1500}
            """
            endpoint = self._find_endpoint(body.endpoint)
            if not endpoint:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            if endpoint.pricing_model != PricingModel.PER_UNIT:
                raise HTTPException(status_code=400, detail="Endpoint is not metered")

            unit_price = endpoint.price
            total = Decimal(str(body.units)) * unit_price

            # Report usage to Sardis API for settlement
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._sardis_api}/api/v2/merchant-checkout/sessions/{body.session_id}/usage",
                    json={
                        "units": body.units,
                        "unit_name": endpoint.unit_name or "unit",
                        "unit_price": str(unit_price),
                        "total_amount": str(total),
                        "endpoint": body.endpoint,
                        "metadata": body.metadata,
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )

                if resp.status_code not in (200, 201):
                    logger.warning("Usage report failed: %s", resp.text)

            return UsageReportResponse(
                session_id=body.session_id,
                endpoint=body.endpoint,
                units=body.units,
                unit_price=str(unit_price),
                total_charge=str(total),
                currency=endpoint.currency,
            )

    def _find_endpoint(self, path: str) -> PricedEndpoint | None:
        """Find a priced endpoint by path."""
        for ep in self._endpoints:
            if ep.path == path:
                return ep
        return None

    def _verify_webhook(self, payload: bytes, signature: str) -> bool:
        """Verify HMAC-SHA256 webhook signature."""
        if not self._webhook_secret:
            return False
        expected = hmac.new(
            self._webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)


class SardisPaywall:
    """FastAPI dependency for protecting endpoints with payment verification.

    Usage:
        paywall = sardis.paywall("/api/generate")

        @app.post("/api/generate")
        async def generate(paid: bool = Depends(paywall)):
            if not paid:
                raise HTTPException(402, "Payment required")
            return {"result": "..."}
    """

    def __init__(self, sardis: SardisConnect, endpoint_path: str) -> None:
        self._sardis = sardis
        self._path = endpoint_path

    async def __call__(self, request: Request) -> bool:
        """Check if the request has a valid payment session."""
        session_id = (
            request.headers.get("X-Sardis-Session")
            or request.query_params.get("sardis_session")
        )
        if not session_id:
            return False

        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._sardis._sardis_api}/api/v2/merchant-checkout/sessions/{session_id}",
                headers={"Authorization": f"Bearer {self._sardis._api_key}"},
            )
            if resp.status_code != 200:
                return False
            data = resp.json()
            return data.get("status") in ("paid", "settled")
