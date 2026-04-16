"""Unified Payment Client — protocol-agnostic payment for AI agents.

One interface, three rails. The agent calls `pay()` and Sardis picks
the best protocol based on merchant capabilities and agent mandate.

Usage:
    client = UnifiedPaymentClient(
        api_url="https://api.sardis.sh",
        api_key="your_api_key_here",
        wallet_id="wal_xxx",
        agent_id="agent_xxx",
    )

    # Auto-selects best protocol (direct USDC, x402, or MPP)
    result = await client.pay(
        to="api.openai.com",
        amount=Decimal("5.00"),
        mandate_id="mandate_xxx",  # optional
    )

    # Or force a specific protocol
    result = await client.pay(
        to="api.openai.com",
        amount=Decimal("5.00"),
        protocol="x402",  # force x402
    )
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger("sardis.unified_payment")


class PaymentProtocol(str, Enum):
    """Available payment protocols."""
    AUTO = "auto"       # Sardis picks the best one
    DIRECT = "direct"   # On-chain USDC transfer
    X402 = "x402"       # HTTP 402 API micropayments (Coinbase)
    MPP = "mpp"         # Stripe Machine Payments Protocol
    ACP = "acp"         # OpenAI Agentic Commerce Protocol
    UCP = "ucp"         # Google Universal Commerce Protocol
    AP2 = "ap2"         # Google Agent Payment Protocol v2
    VISA_ICC = "visa_icc"  # Visa Intelligent Commerce Connect


class PaymentStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REQUIRES_APPROVAL = "requires_approval"


@dataclass(frozen=True)
class PaymentResult:
    """Result of a unified payment."""
    status: PaymentStatus
    protocol: PaymentProtocol
    tx_id: str | None = None
    tx_hash: str | None = None
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    merchant: str = ""
    session_id: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MerchantCapabilities:
    """What protocols a merchant supports."""
    merchant: str
    supports_direct: bool = False
    supports_x402: bool = False
    supports_mpp: bool = False
    supports_acp: bool = False      # OpenAI Agentic Commerce Protocol
    supports_ucp: bool = False      # Google Universal Commerce Protocol
    supports_ap2: bool = False      # Google Agent Payment Protocol v2
    supports_visa_icc: bool = False # Visa Intelligent Commerce Connect
    settlement_address: str | None = None  # For direct USDC
    x402_endpoint: str | None = None       # For x402
    mpp_merchant_id: str | None = None     # For MPP/Stripe
    acp_merchant_url: str | None = None    # For OpenAI ACP
    ucp_merchant_url: str | None = None    # For Google UCP


class UnifiedPaymentClient:
    """Protocol-agnostic payment client for AI agents.

    Handles protocol selection, mandate validation, and payment execution
    through a single `pay()` method. The agent doesn't need to know
    whether it's paying via x402, MPP, or direct USDC.
    """

    def __init__(
        self,
        *,
        api_url: str = "https://api.sardis.sh",
        api_key: str = "",
        wallet_id: str = "",
        agent_id: str = "",
        default_chain: str = "base",
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._api_key = api_key
        self._wallet_id = wallet_id
        self._agent_id = agent_id
        self._default_chain = default_chain

    async def pay(
        self,
        *,
        to: str,
        amount: Decimal | str,
        currency: str = "USD",
        protocol: PaymentProtocol | str = PaymentProtocol.AUTO,
        mandate_id: str | None = None,
        purpose: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PaymentResult:
        """Execute a payment using the best available protocol.

        Args:
            to: Merchant identifier (domain, address, or merchant_id)
            amount: Payment amount
            currency: Currency code (default: USD)
            protocol: Force a specific protocol, or AUTO for best selection
            mandate_id: Spending mandate to validate against
            purpose: Human-readable purpose for audit trail
            metadata: Additional metadata for the payment

        Returns:
            PaymentResult with status, protocol used, and transaction details
        """
        amount = Decimal(str(amount))
        protocol = PaymentProtocol(protocol) if isinstance(protocol, str) else protocol

        # Step 1: Discover merchant capabilities
        capabilities = await self._discover_merchant(to)

        # Step 2: Select protocol
        selected = self._select_protocol(protocol, capabilities)

        # Step 3: Validate mandate (if provided)
        if mandate_id:
            mandate_ok = await self._validate_mandate(
                mandate_id=mandate_id,
                amount=amount,
                merchant=to,
            )
            if not mandate_ok.get("approved"):
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    protocol=selected,
                    amount=amount,
                    currency=currency,
                    merchant=to,
                    error=f"Mandate denied: {mandate_ok.get('reason', 'unknown')}",
                )

        # Step 4: Execute via selected protocol
        logger.info(
            "Paying %s %s %s to %s via %s",
            amount, currency, f"(mandate={mandate_id})" if mandate_id else "",
            to, selected.value,
        )

        if selected == PaymentProtocol.DIRECT:
            return await self._pay_direct(to, amount, currency, purpose, metadata)
        elif selected == PaymentProtocol.X402:
            return await self._pay_x402(to, amount, currency, capabilities, purpose, metadata)
        elif selected == PaymentProtocol.MPP:
            return await self._pay_mpp(to, amount, currency, capabilities, purpose, metadata)
        elif selected in (PaymentProtocol.ACP, PaymentProtocol.UCP, PaymentProtocol.AP2, PaymentProtocol.VISA_ICC):
            return await self._pay_protocol_gateway(
                to, amount, currency, selected, capabilities, purpose, metadata,
            )
        else:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                protocol=selected,
                amount=amount,
                merchant=to,
                error=f"No suitable payment protocol for {to}",
            )

    async def discover(self, merchant: str) -> MerchantCapabilities:
        """Discover what payment protocols a merchant supports."""
        return await self._discover_merchant(merchant)

    def _select_protocol(
        self, preferred: PaymentProtocol, caps: MerchantCapabilities
    ) -> PaymentProtocol:
        """Select the best protocol based on preference and capabilities.

        Priority (highest to lowest):
        1. MPP — Stripe fiat settlement, lowest friction for merchants
        2. ACP — OpenAI ecosystem, growing adoption
        3. UCP — Google ecosystem
        4. Visa ICC — Card network backed, enterprise trust
        5. AP2 — Google consortium standard
        6. x402 — API micropayments, simple
        7. Direct USDC — Always available, on-chain
        """
        if preferred != PaymentProtocol.AUTO:
            return preferred

        if caps.supports_mpp:
            return PaymentProtocol.MPP
        if caps.supports_acp:
            return PaymentProtocol.ACP
        if caps.supports_ucp:
            return PaymentProtocol.UCP
        if caps.supports_visa_icc:
            return PaymentProtocol.VISA_ICC
        if caps.supports_ap2:
            return PaymentProtocol.AP2
        if caps.supports_x402:
            return PaymentProtocol.X402
        if caps.supports_direct:
            return PaymentProtocol.DIRECT

        return PaymentProtocol.DIRECT

    async def _discover_merchant(self, merchant: str) -> MerchantCapabilities:
        """Discover merchant capabilities via /.well-known/sardis.json or API."""
        import httpx

        caps = MerchantCapabilities(merchant=merchant)

        # Try sardis.json discovery
        if "." in merchant and not merchant.startswith("0x"):
            url = f"https://{merchant}" if not merchant.startswith("http") else merchant
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.get(f"{url}/.well-known/sardis.json")
                    if resp.status_code == 200:
                        data = resp.json()
                        accepts = data.get("accepts", [])
                        return MerchantCapabilities(
                            merchant=merchant,
                            supports_direct="sardis" in accepts or "direct" in accepts,
                            supports_x402="x402" in accepts,
                            supports_mpp="mpp" in accepts,
                            mpp_merchant_id=data.get("merchant_id"),
                        )
            except Exception:
                pass  # Discovery failed, fallback

        # Try x402 probe (HEAD request, check for 402)
        if "." in merchant:
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    resp = await client.head(f"https://{merchant}")
                    if resp.status_code == 402:
                        return MerchantCapabilities(
                            merchant=merchant,
                            supports_x402=True,
                            x402_endpoint=f"https://{merchant}",
                        )
            except Exception:
                pass

        # Check Sardis API for registered merchant
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(
                    f"{self._api_url}/api/v2/merchants/lookup",
                    params={"domain": merchant},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return MerchantCapabilities(
                        merchant=merchant,
                        supports_direct=True,
                        supports_mpp=bool(data.get("stripe_account_id")),
                        settlement_address=data.get("settlement_wallet_id"),
                        mpp_merchant_id=data.get("merchant_id"),
                    )
        except Exception:
            pass

        # Default: assume direct USDC is possible
        return MerchantCapabilities(merchant=merchant, supports_direct=True)

    async def _validate_mandate(
        self, mandate_id: str, amount: Decimal, merchant: str
    ) -> dict[str, Any]:
        """Check payment against spending mandate via API."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    f"{self._api_url}/api/v2/mandates/{mandate_id}/check",
                    json={"amount": str(amount), "merchant": merchant},
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if resp.status_code == 200:
                    return resp.json()
        except Exception as e:
            logger.warning("Mandate validation failed: %s", e)

        # Fail-open in dev, fail-closed in prod
        import os
        if os.getenv("SARDIS_ENVIRONMENT", "dev") == "dev":
            return {"approved": True, "reason": "dev mode — mandate check skipped"}
        return {"approved": False, "reason": "Mandate validation unavailable"}

    async def _pay_direct(
        self, to: str, amount: Decimal, currency: str,
        purpose: str | None, metadata: dict | None,
    ) -> PaymentResult:
        """Pay via direct on-chain USDC transfer."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._api_url}/api/v2/pay",
                    json={
                        "wallet_id": self._wallet_id,
                        "to": to,
                        "amount": str(amount),
                        "currency": currency,
                        "purpose": purpose,
                        "metadata": metadata or {},
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return PaymentResult(
                        status=PaymentStatus.COMPLETED,
                        protocol=PaymentProtocol.DIRECT,
                        tx_id=data.get("payment_id"),
                        tx_hash=data.get("tx_hash"),
                        amount=amount,
                        currency=currency,
                        merchant=to,
                    )
                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    protocol=PaymentProtocol.DIRECT,
                    amount=amount,
                    merchant=to,
                    error=f"API error: {resp.status_code}",
                )
        except Exception as e:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                protocol=PaymentProtocol.DIRECT,
                amount=amount,
                merchant=to,
                error=str(e),
            )

    async def _pay_x402(
        self, to: str, amount: Decimal, currency: str,
        caps: MerchantCapabilities, purpose: str | None, metadata: dict | None,
    ) -> PaymentResult:
        """Pay via x402 protocol (HTTP 402 challenge-response)."""
        import httpx

        endpoint = caps.x402_endpoint or f"https://{to}"

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                # Step 1: Get 402 challenge
                resp = await client.get(endpoint)
                if resp.status_code != 402:
                    return PaymentResult(
                        status=PaymentStatus.FAILED,
                        protocol=PaymentProtocol.X402,
                        amount=amount,
                        merchant=to,
                        error=f"Expected 402, got {resp.status_code}",
                    )

                # Step 2: Resolve via Sardis x402 handler
                challenge_data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
                resolve_resp = await client.post(
                    f"{self._api_url}/api/v2/x402/resolve",
                    json={
                        "challenge": challenge_data,
                        "endpoint": endpoint,
                        "wallet_id": self._wallet_id,
                        "agent_id": self._agent_id,
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )

                if resolve_resp.status_code in (200, 201):
                    data = resolve_resp.json()
                    return PaymentResult(
                        status=PaymentStatus.COMPLETED,
                        protocol=PaymentProtocol.X402,
                        tx_id=data.get("payment_id"),
                        tx_hash=data.get("tx_hash"),
                        amount=amount,
                        currency=currency,
                        merchant=to,
                    )

                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    protocol=PaymentProtocol.X402,
                    amount=amount,
                    merchant=to,
                    error=f"x402 resolve failed: {resolve_resp.status_code}",
                )
        except Exception as e:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                protocol=PaymentProtocol.X402,
                amount=amount,
                merchant=to,
                error=str(e),
            )

    async def _pay_mpp(
        self, to: str, amount: Decimal, currency: str,
        caps: MerchantCapabilities, purpose: str | None, metadata: dict | None,
    ) -> PaymentResult:
        """Pay via MPP (Stripe Machine Payments Protocol)."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._api_url}/api/v2/mpp/pay",
                    json={
                        "merchant_id": caps.mpp_merchant_id or to,
                        "amount": str(amount),
                        "currency": currency,
                        "wallet_id": self._wallet_id,
                        "agent_id": self._agent_id,
                        "purpose": purpose,
                        "metadata": metadata or {},
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return PaymentResult(
                        status=PaymentStatus.COMPLETED,
                        protocol=PaymentProtocol.MPP,
                        tx_id=data.get("payment_id"),
                        session_id=data.get("session_id"),
                        amount=amount,
                        currency=currency,
                        merchant=to,
                    )

                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    protocol=PaymentProtocol.MPP,
                    amount=amount,
                    merchant=to,
                    error=f"MPP error: {resp.status_code}",
                )
        except Exception as e:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                protocol=PaymentProtocol.MPP,
                amount=amount,
                merchant=to,
                error=str(e),
            )

    async def _pay_protocol_gateway(
        self, to: str, amount: Decimal, currency: str,
        protocol: PaymentProtocol, caps: MerchantCapabilities,
        purpose: str | None, metadata: dict | None,
    ) -> PaymentResult:
        """Route payment through Sardis protocol gateway.

        Handles ACP (OpenAI), UCP (Google), AP2, and Visa ICC
        through a unified gateway endpoint. The gateway translates
        Sardis payment intent into the target protocol format.
        """
        import httpx

        protocol_config = {
            PaymentProtocol.ACP: {
                "gateway_path": "/api/v2/gateway/acp",
                "merchant_url_field": "acp_merchant_url",
            },
            PaymentProtocol.UCP: {
                "gateway_path": "/api/v2/gateway/ucp",
                "merchant_url_field": "ucp_merchant_url",
            },
            PaymentProtocol.AP2: {
                "gateway_path": "/api/v2/ap2/pay",
                "merchant_url_field": None,
            },
            PaymentProtocol.VISA_ICC: {
                "gateway_path": "/api/v2/gateway/visa-icc",
                "merchant_url_field": None,
            },
        }

        config = protocol_config.get(protocol, {})
        gateway_path = config.get("gateway_path", f"/api/v2/gateway/{protocol.value}")

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self._api_url}{gateway_path}",
                    json={
                        "merchant": to,
                        "amount": str(amount),
                        "currency": currency,
                        "wallet_id": self._wallet_id,
                        "agent_id": self._agent_id,
                        "purpose": purpose,
                        "metadata": metadata or {},
                    },
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    return PaymentResult(
                        status=PaymentStatus.COMPLETED,
                        protocol=protocol,
                        tx_id=data.get("payment_id"),
                        tx_hash=data.get("tx_hash"),
                        session_id=data.get("session_id"),
                        amount=amount,
                        currency=currency,
                        merchant=to,
                    )

                return PaymentResult(
                    status=PaymentStatus.FAILED,
                    protocol=protocol,
                    amount=amount,
                    merchant=to,
                    error=f"{protocol.value} gateway error: {resp.status_code}",
                )
        except Exception as e:
            return PaymentResult(
                status=PaymentStatus.FAILED,
                protocol=protocol,
                amount=amount,
                merchant=to,
                error=str(e),
            )
