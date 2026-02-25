"""On-chain payment endpoints."""

from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_v2_core.tokens import TokenType, to_raw_token_amount

router = APIRouter()


class OnChainPaymentRequest(BaseModel):
    to: str
    amount: Decimal = Field(gt=0)
    token: str = "USDC"
    chain: str = "base"
    memo: Optional[str] = None
    rail: Optional[Literal["turnkey", "cdp"]] = Field(
        default=None,
        description="Execution rail override. If omitted, uses server default.",
    )
    cdp_wallet_id: Optional[str] = Field(
        default=None,
        description="Optional CDP wallet id override. Falls back to wallet.cdp_wallet_id.",
    )


class OnChainPaymentResponse(BaseModel):
    tx_hash: Optional[str] = None
    explorer_url: Optional[str] = None
    status: str = "submitted"
    approval_id: Optional[str] = None


@dataclass
class OnChainPaymentDependencies:
    wallet_repo: Any
    agent_repo: Any
    chain_executor: Any
    policy_store: Any = None
    approval_service: Any = None
    coinbase_cdp_provider: Any = None
    default_on_chain_provider: Optional[str] = None


def get_deps() -> OnChainPaymentDependencies:
    raise NotImplementedError("must be overridden")


PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"\boverride\s+safety\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+policy\b", re.IGNORECASE),
    re.compile(r"\bdisable\s+compliance\b", re.IGNORECASE),
)


def _explorer_url(chain: str, tx_hash: str) -> Optional[str]:
    c = (chain or "").strip().lower()
    if c in {"base", "base-mainnet"}:
        return f"https://basescan.org/tx/{tx_hash}"
    if c in {"base_sepolia", "base-sepolia"}:
        return f"https://sepolia.basescan.org/tx/{tx_hash}"
    return None


async def _require_wallet_access(wallet: Any, principal: Principal, deps: OnChainPaymentDependencies) -> None:
    if principal.is_admin:
        return
    if deps.agent_repo is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="agent_repository_not_configured",
        )
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _contains_prompt_injection_signal(text: Optional[str]) -> Optional[str]:
    value = (text or "").strip()
    if not value:
        return None
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(value):
            return pattern.pattern
    return None


@router.post("/{wallet_id}/pay/onchain", response_model=OnChainPaymentResponse, status_code=status.HTTP_200_OK)
async def pay_onchain(
    wallet_id: str,
    request: OnChainPaymentRequest,
    deps: OnChainPaymentDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
    await _require_wallet_access(wallet, principal, deps)

    # Policy enforcement gate (fail-closed in production when policy store missing).
    if deps.policy_store is None:
        if (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower() in {"prod", "production"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="policy_store_not_configured",
            )
    else:
        policy = await deps.policy_store.fetch_policy(wallet.agent_id)
        if policy is not None:
            allowed, reason = policy.validate_payment(
                amount=request.amount,
                fee=Decimal("0"),
                merchant_id=request.to,
                mcc_code=None,
                merchant_category="onchain_transfer",
            )
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=reason or "spending_policy_denied",
                )
            if hasattr(policy, "validate_execution_context"):
                rails_ok, rails_reason = policy.validate_execution_context(
                    destination=request.to,
                    chain=request.chain,
                    token=request.token,
                )
                if not rails_ok:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=rails_reason or "execution_context_denied",
                    )
            if reason == "requires_approval":
                if deps.approval_service is not None:
                    approval = await deps.approval_service.create_approval(
                        action="onchain_payment",
                        requested_by=wallet.agent_id,
                        agent_id=wallet.agent_id,
                        wallet_id=wallet.wallet_id,
                        vendor=request.to,
                        amount=request.amount,
                        purpose="On-chain payment",
                        reason="policy_requires_approval",
                        urgency="medium",
                        organization_id=principal.organization_id,
                        metadata={
                            "wallet_id": wallet_id,
                            "token": request.token,
                            "chain": request.chain,
                            "rail": request.rail,
                            "memo": request.memo,
                        },
                    )
                    return OnChainPaymentResponse(
                        tx_hash=None,
                        explorer_url=None,
                        status="pending_approval",
                        approval_id=approval.id,
                    )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="requires_approval",
                )

    # Prompt-injection guard for agent-provided memo/input strings.
    if os.getenv("SARDIS_PROMPT_INJECTION_GUARD_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}:
        match = _contains_prompt_injection_signal(request.memo)
        if match:
            if deps.approval_service is not None:
                approval = await deps.approval_service.create_approval(
                    action="onchain_payment",
                    requested_by=wallet.agent_id,
                    agent_id=wallet.agent_id,
                    wallet_id=wallet.wallet_id,
                    vendor=request.to,
                    amount=request.amount,
                    purpose="On-chain payment",
                    reason=f"prompt_injection_signal_detected:{match}",
                    urgency="high",
                    organization_id=principal.organization_id,
                    metadata={
                        "wallet_id": wallet_id,
                        "token": request.token,
                        "chain": request.chain,
                        "rail": request.rail,
                        "memo": request.memo,
                    },
                )
                return OnChainPaymentResponse(
                    tx_hash=None,
                    explorer_url=None,
                    status="pending_approval",
                    approval_id=approval.id,
                )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="prompt_injection_signal_detected",
            )

    use_cdp_rail = False
    if request.rail:
        use_cdp_rail = request.rail == "cdp"
    elif deps.default_on_chain_provider == "coinbase_cdp":
        use_cdp_rail = True

    if use_cdp_rail:
        if request.token.upper() != "USDC":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cdp_rail_only_supports_usdc",
            )
        if not deps.coinbase_cdp_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="coinbase_cdp_not_configured",
            )
        cdp_wallet_id = request.cdp_wallet_id or getattr(wallet, "cdp_wallet_id", None)
        if not cdp_wallet_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="cdp_wallet_id_required",
            )
        try:
            tx_hash = await deps.coinbase_cdp_provider.send_usdc(
                cdp_wallet_id=cdp_wallet_id,
                to_address=request.to,
                amount_usdc=request.amount,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"cdp_payment_failed: {exc}",
            ) from exc
        return OnChainPaymentResponse(
            tx_hash=tx_hash,
            explorer_url=_explorer_url(request.chain, tx_hash),
            status="submitted",
        )

    source_address = wallet.get_address(request.chain)
    if not source_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No address for chain {request.chain}",
        )

    try:
        amount_minor = to_raw_token_amount(TokenType(request.token.upper()), request.amount)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported_token: {request.token}",
        ) from exc

    nonce = hashlib.sha256(
        f"{wallet_id}:{request.chain}:{request.token}:{request.to}:{request.amount}:{request.memo or ''}".encode()
    ).hexdigest()
    mandate = PaymentMandate(
        mandate_id=f"onchain_{nonce[:16]}",
        mandate_type="payment",
        issuer=f"wallet:{wallet_id}",
        subject=wallet.agent_id,
        expires_at=int(time.time()) + 300,
        nonce=nonce,
        proof=VCProof(
            verification_method=f"wallet:{wallet_id}#key-1",
            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            proof_value="onchain-payment",
        ),
        domain="sardis.sh",
        purpose="checkout",
        chain=request.chain,
        token=request.token.upper(),
        amount_minor=amount_minor,
        destination=request.to,
        audit_hash=hashlib.sha256(
            f"{wallet_id}:{request.to}:{amount_minor}:{request.chain}:{request.memo or ''}".encode()
        ).hexdigest(),
        wallet_id=wallet_id,
        account_type=wallet.account_type,
        smart_account_address=wallet.smart_account_address,
        merchant_domain=request.memo or "onchain",
    )

    if not deps.chain_executor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="chain_executor_not_configured",
        )
    try:
        receipt = await deps.chain_executor.dispatch_payment(mandate)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"onchain_payment_failed: {exc}",
        ) from exc

    tx_hash = receipt.tx_hash if hasattr(receipt, "tx_hash") else str(receipt)
    return OnChainPaymentResponse(
        tx_hash=tx_hash,
        explorer_url=_explorer_url(request.chain, tx_hash),
        status="submitted",
    )
