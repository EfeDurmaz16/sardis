"""Fiat on-ramp and off-ramp API endpoints."""
from __future__ import annotations

import hashlib
import hmac
import logging
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core import AgentRepository
from sardis_api.idempotency import get_idempotency_key, run_idempotent
from sardis_api.webhook_replay import run_with_replay_protection

logger = logging.getLogger(__name__)
ONRAMPER_WEBHOOK_TOLERANCE_SECONDS = 300

router = APIRouter(dependencies=[Depends(require_principal)])
public_router = APIRouter()


# ---- Request/Response Models ----

class OnrampWidgetRequest(BaseModel):
    """Request to generate an Onramper widget URL."""
    wallet_id: str
    amount_usd: Optional[Decimal] = None
    chain: str = Field(default="base")
    token: str = Field(default="USDC")


class OnrampWidgetResponse(BaseModel):
    widget_url: str
    wallet_address: str
    chain: str
    token: str


class OnrampQuoteRequest(BaseModel):
    amount_usd: Decimal = Field(gt=0)
    payment_method: str = Field(default="creditcard")
    chain: str = Field(default="base")
    token: str = Field(default="USDC")


class OfframpQuoteRequest(BaseModel):
    input_token: str = Field(default="USDC")
    input_amount: Decimal = Field(gt=0, description="Amount in token units (e.g. 100.00 USDC)")
    input_chain: str = Field(default="base")
    output_currency: str = Field(default="USD")


class OfframpQuoteResponse(BaseModel):
    quote_id: str
    input_token: str
    input_amount: str
    input_chain: str
    output_currency: str
    output_amount: str
    fee: str
    exchange_rate: str
    expires_at: str


class OfframpExecuteRequest(BaseModel):
    quote_id: str
    wallet_id: str
    destination_account: str = Field(description="Bank account ID or Lithic funding account ID")


class OfframpExecuteResponse(BaseModel):
    transaction_id: str
    status: str
    input_amount: str
    output_amount: str
    provider_reference: Optional[str] = None


class OfframpStatusResponse(BaseModel):
    transaction_id: str
    status: str
    input_token: str
    input_amount: str
    output_currency: str
    output_amount: str
    created_at: str
    completed_at: Optional[str] = None
    failure_reason: Optional[str] = None


class BankAccountModel(BaseModel):
    account_holder_name: str
    account_number: str
    routing_number: str
    account_type: str = Field(default="checking", pattern="^(checking|savings)$")
    bank_name: Optional[str] = None


class MerchantAccountModel(BaseModel):
    name: str
    bank_account: BankAccountModel
    merchant_id: Optional[str] = None
    category: Optional[str] = None


class WithdrawRequest(BaseModel):
    wallet_id: str
    amount_usd: Decimal = Field(gt=0)
    bank_account: BankAccountModel


class WithdrawResponse(BaseModel):
    tx_hash: str
    payout_id: str
    estimated_arrival: Optional[str] = None
    fee: str
    status: str


class PayMerchantRequest(BaseModel):
    wallet_id: str
    amount_usd: Decimal = Field(gt=0)
    merchant: MerchantAccountModel


class PayMerchantResponse(BaseModel):
    status: str
    payment_id: Optional[str] = None
    merchant_received: Optional[str] = None
    fee: Optional[str] = None
    tx_hash: Optional[str] = None
    approval_request: Optional[dict] = None


# ---- Dependencies ----

@dataclass
class RampDependencies:
    wallet_repo: object  # WalletRepository
    agent_repo: AgentRepository
    offramp_service: object  # OfframpService
    onramper_api_key: str = ""
    onramper_webhook_secret: str = ""
    bridge_webhook_secret: str = ""
    fiat_ramp: object | None = None  # SardisFiatRamp (optional, requires BRIDGE_API_KEY)


def get_deps() -> RampDependencies:
    raise NotImplementedError("Dependency override required")


def _verify_onramper_signature(
    *,
    body: bytes,
    signature_header: str,
    timestamp_header: str,
    secret: str,
) -> bool:
    """Verify Onramper webhook signature with replay protection.

    Supports two formats:
    1) Stripe-style: ``t=<ts>,v1=<hex>`` with signed payload ``ts.body``
    2) Legacy: raw hex HMAC over body, with timestamp provided in a separate header
    """
    if not signature_header:
        return False

    now = int(time.time())
    signature_header = signature_header.strip()

    # Format 1: t=<timestamp>,v1=<signature>
    if "t=" in signature_header and "v1=" in signature_header:
        parts: dict[str, str] = {}
        for part in signature_header.split(","):
            key, _, value = part.partition("=")
            parts[key.strip()] = value.strip()

        ts_raw = parts.get("t", "")
        sig = parts.get("v1", "")
        if not ts_raw or not sig:
            return False
        try:
            ts = int(ts_raw)
        except ValueError:
            return False
        if abs(now - ts) > ONRAMPER_WEBHOOK_TOLERANCE_SECONDS:
            return False

        signed_payload = f"{ts}.".encode() + body
        expected = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected)

    # Format 2: legacy raw body HMAC + required timestamp header
    if not timestamp_header:
        return False
    try:
        ts = int(timestamp_header)
    except ValueError:
        return False
    if abs(now - ts) > ONRAMPER_WEBHOOK_TOLERANCE_SECONDS:
        return False

    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature_header, expected)


# ---- Onramp Endpoints ----

@router.post("/onramp/widget", response_model=OnrampWidgetResponse)
async def generate_onramp_widget(
    request: OnrampWidgetRequest,
    deps: RampDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Generate an Onramper widget URL with wallet address pre-filled."""
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    address = wallet.get_address(request.chain)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No address for chain {request.chain}",
        )

    # Build Onramper widget URL
    params = {
        "apiKey": deps.onramper_api_key,
        "defaultCrypto": request.token.lower(),
        "wallets": f"{request.token.upper()}:{address}",
        "networkWallets": f"{request.chain.upper()}:{address}",
    }
    if request.amount_usd:
        params["defaultAmount"] = str(request.amount_usd)

    query = "&".join(f"{k}={v}" for k, v in params.items())
    widget_url = f"https://buy.onramper.com?{query}"

    return OnrampWidgetResponse(
        widget_url=widget_url,
        wallet_address=address,
        chain=request.chain,
        token=request.token,
    )


@router.get("/onramp/quote")
async def get_onramp_quote(
    amount_usd: Decimal,
    payment_method: str = "creditcard",
    chain: str = "base",
    token: str = "USDC",
    deps: RampDependencies = Depends(get_deps),
):
    """Proxy to Onramper quotes API."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.onramper.com/quotes",
                params={
                    "amount": str(amount_usd),
                    "sourceCurrency": "usd",
                    "destinationCurrency": token.lower(),
                    "paymentMethod": payment_method,
                    "network": chain,
                },
                headers={"Authorization": f"Bearer {deps.onramper_api_key}"},
            )
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as e:
        logger.error("Onramper quote error: %s", e)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch onramp quote")


@public_router.post("/onramp/webhook", status_code=status.HTTP_200_OK)
async def onramp_webhook(
    request: Request,
    deps: RampDependencies = Depends(get_deps),
):
    """Handle Onramper transaction completion webhook."""
    body = await request.body()

    # Verify webhook signature if secret is configured
    if not deps.onramper_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Onramper webhook verification not configured",
        )
    signature = request.headers.get("x-onramper-signature", "")
    timestamp_header = (
        request.headers.get("x-onramper-timestamp")
        or request.headers.get("onramper-signature-timestamp", "")
    )
    if not _verify_onramper_signature(
        body=body,
        signature_header=signature,
        timestamp_header=timestamp_header,
        secret=deps.onramper_webhook_secret,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_id = payload.get("id") or payload.get("event_id") or payload.get("token") or hashlib.sha256(body).hexdigest()
    async def _process() -> dict:
        event_type = payload.get("type", "")
        tx_data = payload.get("payload", payload)

        if event_type in ("transaction.completed", "completed"):
            wallet_address = tx_data.get("wallet_address") or tx_data.get("destinationAddress", "")
            amount = tx_data.get("crypto_amount") or tx_data.get("amount", 0)
            token = tx_data.get("crypto_currency") or tx_data.get("currency", "USDC")
            tx_hash = tx_data.get("tx_hash") or tx_data.get("transactionHash", "")
            chain = tx_data.get("network") or tx_data.get("chain", "base")

            logger.info(
                "Onramp completed: address=%s amount=%s token=%s tx_hash=%s chain=%s",
                wallet_address, amount, token, tx_hash, chain,
            )

            # Find wallet by address and record the on-ramp transaction
            try:
                # Find wallet by searching through all wallets for matching address
                wallet = None
                all_wallets = await deps.wallet_repo.list(limit=10000)
                for w in all_wallets:
                    if wallet_address.lower() in [addr.lower() for addr in w.addresses.values()]:
                        wallet = w
                        break

                if wallet:
                    logger.info(
                        f"Onramp credited: wallet_id={wallet.wallet_id} amount={amount} {token} tx_hash={tx_hash}"
                    )
                    # Note: Wallet balance is already on-chain (non-custodial)
                    # The funds are already in the wallet address - no manual credit needed
                    # This log serves as an audit trail of the on-ramp event
                else:
                    logger.warning(
                        f"Onramp completed but wallet not found for address: {wallet_address}"
                    )
            except Exception as e:
                logger.error(f"Error processing onramp webhook: {e}", exc_info=True)
                # Don't fail the webhook - we've logged the transaction
                # The funds are still on-chain and accessible

        return {"status": "received"}

    return await run_with_replay_protection(
        request=request,
        provider="onramper",
        event_id=str(event_id),
        body=body,
        ttl_seconds=7 * 24 * 60 * 60,
        response_on_duplicate={"status": "received"},
        fn=_process,
    )


@public_router.post("/bridge/webhook", status_code=status.HTTP_200_OK)
async def bridge_webhook(
    request: Request,
    deps: RampDependencies = Depends(get_deps),
):
    """Handle Bridge.xyz transfer status webhook.

    Bridge sends webhooks for transfer lifecycle events:
    - transfer.created, transfer.processing, transfer.completed, transfer.failed, transfer.refunded
    """
    body = await request.body()

    # Verify HMAC-SHA256 signature
    if not deps.bridge_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Bridge webhook verification not configured",
        )
    signature = request.headers.get("bridge-signature", "")
    if not signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")

    expected = hmac.new(
        deps.bridge_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    import json
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_id = payload.get("id") or payload.get("event_id") or hashlib.sha256(body).hexdigest()

    async def _process() -> dict:
        event_type = payload.get("type", "")
        transfer_data = payload.get("data", payload)
        transfer_id = transfer_data.get("transfer_id") or transfer_data.get("id", "")

        status_map = {
            "transfer.completed": "completed",
            "transfer.failed": "failed",
            "transfer.processing": "processing",
            "transfer.refunded": "refunded",
            "transfer.created": "pending",
        }

        mapped_status = status_map.get(event_type)
        if mapped_status and transfer_id:
            logger.info(
                "Bridge webhook: transfer_id=%s event=%s status=%s",
                transfer_id, event_type, mapped_status,
            )
            # Update transaction status via offramp_service if it tracks this transfer
            try:
                tx = await deps.offramp_service.get_status(transfer_id)
                logger.info(
                    "Bridge transfer updated: id=%s old_status=%s new_status=%s",
                    transfer_id, tx.status.value if hasattr(tx.status, 'value') else tx.status, mapped_status,
                )
            except (ValueError, Exception) as e:
                # Transfer not tracked by our service - that's OK, log it
                logger.info("Bridge webhook for untracked transfer %s: %s", transfer_id, e)
        else:
            logger.info("Bridge webhook: unhandled event_type=%s", event_type)

        return {"status": "received"}

    return await run_with_replay_protection(
        request=request,
        provider="bridge",
        event_id=str(event_id),
        body=body,
        ttl_seconds=7 * 24 * 60 * 60,
        response_on_duplicate={"status": "received"},
        fn=_process,
    )


# ---- Offramp Endpoints ----

@router.post("/offramp/quote", response_model=OfframpQuoteResponse)
async def get_offramp_quote(
    request: OfframpQuoteRequest,
    deps: RampDependencies = Depends(get_deps),
):
    """Get a USDC to USD off-ramp quote."""
    # Convert to minor units (6 decimals for USDC)
    amount_minor = int(request.input_amount * 10**6)

    quote = await deps.offramp_service.get_quote(
        input_token=request.input_token,
        input_amount_minor=amount_minor,
        input_chain=request.input_chain,
        output_currency=request.output_currency,
    )

    return OfframpQuoteResponse(
        quote_id=quote.quote_id,
        input_token=quote.input_token,
        input_amount=str(request.input_amount),
        input_chain=quote.input_chain,
        output_currency=quote.output_currency,
        output_amount=f"{quote.output_amount_cents / 100:.2f}",
        fee=f"{quote.fee_cents / 100:.2f}",
        exchange_rate=str(quote.exchange_rate),
        expires_at=quote.expires_at.isoformat(),
    )


@router.post("/offramp/execute", response_model=OfframpExecuteResponse)
async def execute_offramp(
    request: OfframpExecuteRequest,
    http_request: Request,
    deps: RampDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Execute USDC to USD off-ramp (send USDC to Bridge, receive USD)."""
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Re-fetch the quote to verify it
    # In production, you'd cache quotes and look up by ID
    # For now, we trust the quote_id and pass through to the provider
    source_address = wallet.get_address("base") or ""
    if not source_address:
        # Try any available address
        for chain, addr in wallet.addresses.items():
            if addr:
                source_address = addr
                break

    if not source_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet has no on-chain address",
        )

    # Look up cached quote by ID
    quote = deps.offramp_service.get_cached_quote(request.quote_id)
    if not quote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quote not found or expired. Please request a new quote.",
        )

    idem_key = get_idempotency_key(http_request) or f"{request.wallet_id}:{request.quote_id}:{request.destination_account}"

    async def _execute() -> tuple[int, object]:
        tx = await deps.offramp_service.execute(
            quote=quote,
            source_address=source_address,
            destination_account=request.destination_account,
            wallet_id=request.wallet_id,
        )

        return 200, OfframpExecuteResponse(
            transaction_id=tx.transaction_id,
            status=tx.status.value,
            input_amount=f"{tx.input_amount_minor / 10**6:.2f}",
            output_amount=f"{tx.output_amount_cents / 100:.2f}",
            provider_reference=tx.provider_reference,
        )

    return await run_idempotent(
        request=http_request,
        principal=principal,
        operation="ramp.offramp.execute",
        key=str(idem_key),
        payload=request.model_dump(),
        fn=_execute,
        ttl_seconds=7 * 24 * 60 * 60,
    )


@router.get("/offramp/status/{tx_id}", response_model=OfframpStatusResponse)
async def get_offramp_status(
    tx_id: str,
    deps: RampDependencies = Depends(get_deps),
):
    """Check off-ramp transaction status."""
    try:
        tx = await deps.offramp_service.get_status(tx_id)
    except (ValueError, Exception) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return OfframpStatusResponse(
        transaction_id=tx.transaction_id,
        status=tx.status.value,
        input_token=tx.input_token,
        input_amount=f"{tx.input_amount_minor / 10**6:.2f}",
        output_currency=tx.output_currency,
        output_amount=f"{tx.output_amount_cents / 100:.2f}",
        created_at=tx.created_at.isoformat(),
        completed_at=tx.completed_at.isoformat() if tx.completed_at else None,
        failure_reason=tx.failure_reason,
    )


@router.post("/withdraw", response_model=WithdrawResponse)
async def withdraw_to_bank(
    request: WithdrawRequest,
    deps: RampDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Withdraw from Sardis wallet to bank account via Bridge."""
    if not deps.fiat_ramp:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Bank withdrawal not configured (requires BRIDGE_API_KEY)",
        )

    # Authorization check
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    from sardis_ramp.ramp_types import BankAccount

    bank_account = BankAccount(
        account_holder_name=request.bank_account.account_holder_name,
        account_number=request.bank_account.account_number,
        routing_number=request.bank_account.routing_number,
        account_type=request.bank_account.account_type,
        bank_name=request.bank_account.bank_name,
    )

    try:
        result = await deps.fiat_ramp.withdraw_to_bank(
            wallet_id=request.wallet_id,
            amount_usd=float(request.amount_usd),
            bank_account=bank_account,
        )
    except Exception as e:
        logger.error("Bank withdrawal failed: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return WithdrawResponse(
        tx_hash=result.tx_hash,
        payout_id=result.payout_id,
        estimated_arrival=str(result.estimated_arrival) if result.estimated_arrival else None,
        fee=str(result.fee),
        status=result.status,
    )


@router.post("/pay-merchant", response_model=PayMerchantResponse)
async def pay_merchant_fiat(
    request: PayMerchantRequest,
    deps: RampDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Pay merchant in USD from crypto wallet via Bridge."""
    if not deps.fiat_ramp:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Merchant payment not configured (requires BRIDGE_API_KEY)",
        )

    # Authorization check
    wallet = await deps.wallet_repo.get(request.wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    from sardis_ramp.ramp_types import BankAccount, MerchantAccount

    bank_account = BankAccount(
        account_holder_name=request.merchant.bank_account.account_holder_name,
        account_number=request.merchant.bank_account.account_number,
        routing_number=request.merchant.bank_account.routing_number,
        account_type=request.merchant.bank_account.account_type,
        bank_name=request.merchant.bank_account.bank_name,
    )
    merchant = MerchantAccount(
        name=request.merchant.name,
        bank_account=bank_account,
        merchant_id=request.merchant.merchant_id,
        category=request.merchant.category,
    )

    try:
        result = await deps.fiat_ramp.pay_merchant_fiat(
            wallet_id=request.wallet_id,
            amount_usd=float(request.amount_usd),
            merchant=merchant,
        )
    except Exception as e:
        logger.error("Merchant payment failed: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return PayMerchantResponse(
        status=result.status,
        payment_id=result.payment_id,
        merchant_received=str(result.merchant_received) if result.merchant_received else None,
        fee=str(result.fee) if result.fee else None,
        tx_hash=result.tx_hash,
        approval_request=result.approval_request,
    )
