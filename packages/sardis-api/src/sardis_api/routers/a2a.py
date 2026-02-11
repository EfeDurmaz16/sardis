"""Agent-to-Agent (A2A) payment endpoints.

Enables first-class agent-to-agent transfers:
- POST /pay          — Direct agent-to-agent payment by agent IDs
- POST /messages     — Inbound A2A message handler (payment requests, etc.)
- GET  /agent-card   — Sardis agent card for discovery
"""
from __future__ import annotations

import hashlib
import logging
import time
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_v2_core import AgentRepository, WalletRepository
from sardis_v2_core.tokens import TokenType, to_raw_token_amount
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_chain.executor import ChainExecutor
from sardis_ledger.records import LedgerStore
from sardis_api.authz import Principal, require_principal
from sardis_api.idempotency import get_idempotency_key, run_idempotent

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])

# Public router for unauthenticated endpoints (agent card)
public_router = APIRouter()


# ============================================================================
# Dependencies
# ============================================================================

class A2ADependencies:
    def __init__(
        self,
        wallet_repo: WalletRepository,
        agent_repo: AgentRepository,
        chain_executor: ChainExecutor | None = None,
        wallet_manager: Any | None = None,
        ledger: LedgerStore | None = None,
    ):
        self.wallet_repo = wallet_repo
        self.agent_repo = agent_repo
        self.chain_executor = chain_executor
        self.wallet_manager = wallet_manager
        self.ledger = ledger


def get_deps() -> A2ADependencies:
    raise NotImplementedError("Dependency override required")


# ============================================================================
# Request/Response Models
# ============================================================================

class A2APayRequest(BaseModel):
    """Request for agent-to-agent payment."""
    sender_agent_id: str = Field(..., description="Source agent ID (payer)")
    recipient_agent_id: str = Field(..., description="Destination agent ID (payee)")
    amount: Decimal = Field(..., gt=0, description="Amount in token units (e.g. 10.50)")
    token: str = Field(default="USDC")
    chain: str = Field(default="base_sepolia")
    memo: Optional[str] = Field(default=None, description="Optional memo for audit trail")
    reference: Optional[str] = Field(default=None, description="External reference (order, invoice)")


class A2APayResponse(BaseModel):
    """Response from agent-to-agent payment."""
    success: bool
    tx_hash: str
    status: str
    sender_agent_id: str
    recipient_agent_id: str
    sender_wallet_id: str
    recipient_wallet_id: str
    from_address: str
    to_address: str
    amount: str
    token: str
    chain: str
    memo: Optional[str] = None
    reference: Optional[str] = None
    ledger_tx_id: Optional[str] = None
    audit_anchor: Optional[str] = None


class A2AMessageRequest(BaseModel):
    """Inbound A2A message."""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str
    sender_id: str
    recipient_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    signature: Optional[str] = None
    signature_algorithm: str = "Ed25519"


class A2AMessageResponse(BaseModel):
    """Outbound A2A message response."""
    message_id: str
    message_type: str
    sender_id: str
    recipient_id: str
    status: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    correlation_id: Optional[str] = None
    in_reply_to: Optional[str] = None
    error: Optional[str] = None
    error_code: Optional[str] = None


# ============================================================================
# POST /pay — Agent-to-Agent Direct Payment
# ============================================================================

@router.post("/pay", response_model=A2APayResponse)
async def a2a_pay(
    req: A2APayRequest,
    request: Request,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Execute a direct agent-to-agent payment.

    Transfers tokens from sender agent's wallet to recipient agent's wallet.
    Both agents must exist, have active wallets, and have addresses on the
    specified chain. Policy checks are enforced on the sender's wallet.
    """
    # Idempotency key
    derived = f"a2a:{req.sender_agent_id}:{req.recipient_agent_id}:{req.amount}:{req.token}:{req.chain}:{req.reference or ''}"
    idem_key = get_idempotency_key(request) or derived

    async def _execute() -> tuple[int, object]:
        # Look up sender agent
        sender_agent = await deps.agent_repo.get(req.sender_agent_id)
        if not sender_agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sender agent not found")
        if not sender_agent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender agent is inactive")

        # Look up recipient agent
        recipient_agent = await deps.agent_repo.get(req.recipient_agent_id)
        if not recipient_agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recipient agent not found")
        if not recipient_agent.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient agent is inactive")

        # Look up sender wallet
        sender_wallet = await deps.wallet_repo.get_by_agent(req.sender_agent_id)
        if not sender_wallet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender agent has no wallet")
        if not sender_wallet.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender wallet is inactive")
        if sender_wallet.is_frozen:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sender wallet is frozen")

        # Look up recipient wallet
        recipient_wallet = await deps.wallet_repo.get_by_agent(req.recipient_agent_id)
        if not recipient_wallet:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Recipient agent has no wallet")

        # Get addresses
        sender_address = sender_wallet.get_address(req.chain)
        if not sender_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Sender wallet has no address on {req.chain}",
            )

        recipient_address = recipient_wallet.get_address(req.chain)
        if not recipient_address:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Recipient wallet has no address on {req.chain}",
            )

        if not deps.chain_executor:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Chain executor not available",
            )

        # Convert amount to minor units
        try:
            amount_minor = to_raw_token_amount(TokenType(req.token.upper()), req.amount)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported token: {req.token}",
            ) from exc

        # Build payment mandate
        digest = hashlib.sha256(str(idem_key).encode()).hexdigest()
        mandate = PaymentMandate(
            mandate_id=f"a2a_{digest[:16]}",
            mandate_type="payment",
            issuer=f"agent:{req.sender_agent_id}",
            subject=sender_wallet.agent_id,
            expires_at=int(time.time()) + 300,
            nonce=digest,
            proof=VCProof(
                verification_method=f"wallet:{sender_wallet.wallet_id}#key-1",
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                proof_value="a2a-transfer",
            ),
            domain="sardis.sh",
            purpose="a2a_transfer",
            chain=req.chain,
            token=req.token,
            amount_minor=amount_minor,
            destination=recipient_address,
            audit_hash=hashlib.sha256(
                f"a2a:{sender_wallet.wallet_id}:{recipient_wallet.wallet_id}:{amount_minor}:{req.memo or ''}".encode()
            ).hexdigest(),
            wallet_id=sender_wallet.wallet_id,
            merchant_domain="sardis.sh",
        )

        # Policy check on sender wallet
        if deps.wallet_manager:
            policy = await deps.wallet_manager.async_validate_policies(mandate)
            if not getattr(policy, "allowed", False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=getattr(policy, "reason", None) or "Policy denied A2A transfer",
                )

        # Execute transfer
        try:
            receipt = await deps.chain_executor.dispatch_payment(mandate)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"A2A transfer failed: {e}",
            ) from e

        # Record in ledger
        ledger_tx_id: str | None = None
        if deps.ledger:
            try:
                import inspect
                if hasattr(deps.ledger, "append_async"):
                    maybe_tx = deps.ledger.append_async(payment_mandate=mandate, chain_receipt=receipt)
                else:
                    maybe_tx = deps.ledger.append(payment_mandate=mandate, chain_receipt=receipt)
                tx = await maybe_tx if inspect.isawaitable(maybe_tx) else maybe_tx
                ledger_tx_id = getattr(tx, "tx_id", None)
            except Exception:
                pass

        logger.info(
            f"A2A payment: {req.sender_agent_id} -> {req.recipient_agent_id} | "
            f"{req.amount} {req.token} on {req.chain} | tx={getattr(receipt, 'tx_hash', str(receipt))}"
        )

        return 200, A2APayResponse(
            success=True,
            tx_hash=getattr(receipt, "tx_hash", str(receipt)),
            status="submitted",
            sender_agent_id=req.sender_agent_id,
            recipient_agent_id=req.recipient_agent_id,
            sender_wallet_id=sender_wallet.wallet_id,
            recipient_wallet_id=recipient_wallet.wallet_id,
            from_address=sender_address,
            to_address=recipient_address,
            amount=str(req.amount),
            token=req.token,
            chain=req.chain,
            memo=req.memo,
            reference=req.reference,
            ledger_tx_id=ledger_tx_id,
            audit_anchor=getattr(receipt, "audit_anchor", None),
        )

    return await run_idempotent(
        request=request,
        principal=principal,
        operation="a2a.pay",
        key=str(idem_key),
        payload=req.model_dump(),
        fn=_execute,
    )


# ============================================================================
# POST /messages — Inbound A2A Message Handler
# ============================================================================

@router.post("/messages", response_model=A2AMessageResponse)
async def handle_a2a_message(
    msg: A2AMessageRequest,
    request: Request,
    deps: A2ADependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """
    Handle inbound A2A messages (payment requests, credential verifications, etc.).

    Processes structured A2A messages according to the A2A protocol.
    Currently supports: payment_request, credential_request, ack.
    """
    logger.info(f"A2A message received: type={msg.message_type}, from={msg.sender_id}, to={msg.recipient_id}")

    if msg.message_type == "payment_request":
        return await _handle_payment_request(msg, request, deps)
    elif msg.message_type == "credential_request":
        return _handle_credential_request(msg)
    elif msg.message_type == "ack":
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="ack",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="received",
            in_reply_to=msg.message_id,
        )
    else:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="error",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            error=f"Unsupported message type: {msg.message_type}",
            error_code="unsupported_message_type",
        )


async def _handle_payment_request(
    msg: A2AMessageRequest,
    request: Request,
    deps: A2ADependencies,
) -> A2AMessageResponse:
    """Handle an inbound A2A payment request."""
    payload = msg.payload
    sender_agent_id = payload.get("sender_agent_id") or msg.sender_id
    recipient_agent_id = payload.get("recipient_agent_id") or msg.recipient_id
    amount_minor = payload.get("amount_minor", 0)
    token = payload.get("token", "USDC")
    chain = payload.get("chain", "base_sepolia")
    destination = payload.get("destination", "")

    if not destination or not amount_minor:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Missing required fields: destination, amount_minor",
            error_code="invalid_request",
        )

    # Look up recipient wallet to execute from
    recipient_wallet = await deps.wallet_repo.get_by_agent(recipient_agent_id)
    if not recipient_wallet:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error="Recipient agent has no wallet",
            error_code="no_wallet",
        )

    if not deps.chain_executor:
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            error="Chain executor not available",
            error_code="service_unavailable",
        )

    # Build mandate
    digest = hashlib.sha256(f"{msg.message_id}:{amount_minor}:{destination}".encode()).hexdigest()
    mandate = PaymentMandate(
        mandate_id=f"a2a_msg_{digest[:16]}",
        mandate_type="payment",
        issuer=f"agent:{sender_agent_id}",
        subject=recipient_wallet.agent_id,
        expires_at=int(time.time()) + 300,
        nonce=digest,
        proof=VCProof(
            verification_method=f"wallet:{recipient_wallet.wallet_id}#key-1",
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proof_value="a2a-message",
        ),
        domain="sardis.sh",
        purpose="a2a_transfer",
        chain=chain,
        token=token,
        amount_minor=amount_minor,
        destination=destination,
        audit_hash=hashlib.sha256(
            f"a2a_msg:{msg.message_id}:{amount_minor}:{destination}".encode()
        ).hexdigest(),
        wallet_id=recipient_wallet.wallet_id,
        merchant_domain="sardis.sh",
    )

    try:
        receipt = await deps.chain_executor.dispatch_payment(mandate)
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="completed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            payload={
                "success": True,
                "tx_hash": getattr(receipt, "tx_hash", str(receipt)),
                "chain": chain,
                "amount_minor": amount_minor,
                "token": token,
            },
        )
    except Exception as e:
        logger.error(f"A2A payment request failed: {e}")
        return A2AMessageResponse(
            message_id=str(uuid.uuid4()),
            message_type="payment_response",
            sender_id=msg.recipient_id,
            recipient_id=msg.sender_id,
            status="failed",
            in_reply_to=msg.message_id,
            correlation_id=msg.correlation_id,
            error=str(e),
            error_code="execution_failed",
        )


def _handle_credential_request(msg: A2AMessageRequest) -> A2AMessageResponse:
    """Handle an inbound credential verification request (stub)."""
    return A2AMessageResponse(
        message_id=str(uuid.uuid4()),
        message_type="credential_response",
        sender_id=msg.recipient_id,
        recipient_id=msg.sender_id,
        status="completed",
        in_reply_to=msg.message_id,
        correlation_id=msg.correlation_id,
        payload={
            "valid": True,
            "verified_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    )


# ============================================================================
# GET /agent-card — Sardis Agent Card for A2A Discovery
# ============================================================================

@public_router.get("/agent-card")
async def get_agent_card():
    """
    Return the Sardis agent card for A2A discovery.

    Other agents can use this to discover Sardis capabilities,
    supported tokens/chains, and API endpoints.
    """
    import os

    api_base = os.getenv("SARDIS_API_BASE_URL", "https://sardis-api-staging-482463483786.us-east1.run.app")

    return {
        "agent_id": "sardis-platform",
        "name": "Sardis Payment Agent",
        "version": "2.0.0",
        "description": "Sardis Payment OS - Secure AI payment infrastructure with policy guardrails",
        "operator": {
            "name": "Sardis",
            "url": "https://sardis.sh",
            "contact": "support@sardis.sh",
        },
        "capabilities": [
            "payment.execute",
            "payment.verify",
            "payment.refund",
            "mandate.ingest",
            "mandate.sign",
            "wallet.balance",
            "wallet.hold",
            "checkout.create",
            "checkout.complete",
            "x402.micropay",
        ],
        "payment": {
            "supported_tokens": ["USDC", "USDT", "EURC"],
            "supported_chains": ["base", "polygon", "ethereum", "arbitrum", "optimism"],
            "min_amount_minor": 100,
            "max_amount_minor": 10_000_000,
            "ap2_compliant": True,
            "x402_compliant": True,
            "ucp_compliant": True,
        },
        "endpoints": {
            "api": {
                "url": f"{api_base}/api/v2",
                "protocol": "https",
                "auth_required": True,
                "auth_type": "bearer",
            },
            "a2a": {
                "url": f"{api_base}/api/v2/a2a",
                "protocol": "https",
                "auth_required": True,
                "auth_type": "signature",
            },
            "mcp": "npx @sardis/mcp-server start",
        },
        "a2a_protocol": {
            "version": "1.0",
            "supported_messages": [
                "payment_request",
                "payment_response",
                "credential_request",
                "credential_response",
                "ack",
            ],
            "pay_endpoint": f"{api_base}/api/v2/a2a/pay",
            "messages_endpoint": f"{api_base}/api/v2/a2a/messages",
        },
    }
