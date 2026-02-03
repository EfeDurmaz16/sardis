"""Virtual Card API endpoints with dependency injection."""
from __future__ import annotations

import hashlib
import hmac
import logging
from decimal import Decimal
from typing import Optional, List, Any
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core import AgentRepository

logger = logging.getLogger(__name__)


# ---- Request/Response Models ----

class IssueCardRequest(BaseModel):
    """Request to issue a new virtual card."""
    wallet_id: str
    card_type: str = Field(default="multi_use")
    limit_per_tx: Decimal = Field(default=Decimal("500.00"))
    limit_daily: Decimal = Field(default=Decimal("2000.00"))
    limit_monthly: Decimal = Field(default=Decimal("10000.00"))
    locked_merchant_id: Optional[str] = None
    funding_source: str = Field(default="stablecoin")


class FundCardRequest(BaseModel):
    """Request to fund a card."""
    amount: Decimal = Field(gt=0)
    source: str = Field(default="stablecoin")


class UpdateLimitsRequest(BaseModel):
    """Request to update card spending limits."""
    limit_per_tx: Optional[Decimal] = None
    limit_daily: Optional[Decimal] = None
    limit_monthly: Optional[Decimal] = None


class CardTransactionResponse(BaseModel):
    """Card transaction response."""
    transaction_id: str
    card_id: str
    amount: str
    currency: str
    merchant_name: str
    merchant_category: str
    status: str
    created_at: str
    settled_at: Optional[str] = None
    decline_reason: Optional[str] = None


class SimulatePurchaseRequest(BaseModel):
    """Demo helper: simulate a merchant purchase and run policy enforcement."""

    amount: Decimal = Field(gt=0, description="Amount in USD (demo assumes 1 USD ~= 1 USDC)")
    currency: str = Field(default="USD")
    merchant_name: str = Field(default="Demo Merchant")
    mcc_code: str = Field(default="5734", description="4-digit MCC code (e.g., 7995 for gambling)")
    status: str = Field(default="approved", description="Provider status to simulate")
    decline_reason: Optional[str] = Field(default=None, description="Optional decline reason")


# ---- Backward-compatible empty router (so existing imports don't break) ----
router = APIRouter()


# ---- Factory function with dependency injection ----

def create_cards_router(
    card_repo,
    card_provider,
    webhook_secret: str | None = None,
    offramp_service=None,
    chain_executor=None,
    wallet_repo=None,
    policy_store=None,
    agent_repo: AgentRepository | None = None,
) -> APIRouter:
    """Create a cards router with injected dependencies."""
    r = APIRouter()
    auth_deps = [Depends(require_principal)]

    async def _evaluate_policy_for_card(
        *,
        wallet_id: str,
        amount: Decimal,
        mcc_code: str | None,
    ) -> tuple[bool, str]:
        if not policy_store or not wallet_repo:
            return True, "OK"
        wallet = await wallet_repo.get(wallet_id)
        if not wallet:
            return True, "OK"
        policy = await policy_store.fetch_policy(wallet.agent_id)
        if not policy:
            return True, "OK"
        ok, reason = policy.validate_payment(
            amount=amount,
            fee=Decimal("0"),
            mcc_code=mcc_code,
        )
        return ok, reason

    async def _require_wallet_access(wallet_id: str, principal: Principal):
        if not wallet_repo or not agent_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="wallet_or_agent_repository_not_configured",
            )
        wallet = await wallet_repo.get(wallet_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        agent = await agent_repo.get(wallet.agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        if not principal.is_admin and agent.owner_id != principal.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return wallet

    def _parse_timestamp(value: Any) -> datetime | None:
        """
        Best-effort timestamp parsing:
        - ISO8601 strings
        - epoch seconds / epoch millis (int/float)
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if isinstance(value, (int, float)):
            # Heuristic: millis if large
            ts = float(value)
            if ts > 1e12:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)
        if isinstance(value, str):
            s = value.strip()
            if not s:
                return None
            # Support "Z" suffix
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(s)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                return None
        return None

    def _normalize_event_type(value: Any) -> str:
        return str(value or "").strip().lower()

    def _normalize_tx_status(event_type: str, tx: dict[str, Any]) -> tuple[str, datetime | None, str | None]:
        """
        Normalize provider statuses into a stable internal status.
        Returns: (status, settled_at, decline_reason)
        """
        raw_status = str(tx.get("status") or "").strip().lower()
        decline_reason = tx.get("decline_reason") or tx.get("reason")

        # Settlement time (best-effort)
        settled_at = (
            _parse_timestamp(tx.get("settled_at"))
            or _parse_timestamp(tx.get("settlement_at"))
            or _parse_timestamp(tx.get("settledAt"))
        )

        # Event-type based normalization (most reliable)
        if "settled" in event_type:
            return "settled", settled_at or datetime.now(timezone.utc), decline_reason
        if "declined" in event_type:
            return "declined", settled_at, decline_reason

        # Status-based fallback
        if raw_status in ("declined", "denied"):
            return "declined", settled_at, decline_reason
        if raw_status in ("approved", "authorized", "auth_approved"):
            return "approved", settled_at, decline_reason
        if raw_status in ("pending", "processing"):
            return "pending", settled_at, decline_reason
        if raw_status in ("settled", "completed"):
            return "settled", settled_at or datetime.now(timezone.utc), decline_reason

        return raw_status or "pending", settled_at, decline_reason

    def _auto_freeze_enabled() -> bool:
        import os
        env = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").lower()
        explicit = os.getenv("SARDIS_AUTO_FREEZE_ON_POLICY_DENY")
        if explicit is None:
            return env not in ("prod", "production")
        return explicit.strip().lower() in ("1", "true", "yes")

    @r.post("", status_code=status.HTTP_201_CREATED, dependencies=auth_deps)
    async def issue_card(request: IssueCardRequest, principal: Principal = Depends(require_principal)):
        await _require_wallet_access(request.wallet_id, principal)

        card_id = f"vc_{uuid.uuid4().hex[:16]}"
        provider_result = await card_provider.create_card(
            card_id=card_id,
            wallet_id=request.wallet_id,
            card_type=request.card_type,
            limit_per_tx=float(request.limit_per_tx),
            limit_daily=float(request.limit_daily),
            limit_monthly=float(request.limit_monthly),
        )
        row = await card_repo.create(
            card_id=card_id,
            wallet_id=request.wallet_id,
            provider="lithic",
            provider_card_id=provider_result.provider_card_id,
            card_type=request.card_type,
            limit_per_tx=float(request.limit_per_tx),
            limit_daily=float(request.limit_daily),
            limit_monthly=float(request.limit_monthly),
        )
        return row

    @r.get("", dependencies=auth_deps)
    async def list_cards(
        wallet_id: Optional[str] = Query(None),
        limit: int = Query(default=50, ge=1, le=100),
        offset: int = Query(default=0, ge=0),
        principal: Principal = Depends(require_principal),
    ):
        if wallet_id:
            await _require_wallet_access(wallet_id, principal)
            return await card_repo.get_by_wallet_id(wallet_id)
        if principal.is_admin:
            return []
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="wallet_id_required")

    @r.get("/{card_id}", dependencies=auth_deps)
    async def get_card(card_id: str, principal: Principal = Depends(require_principal)):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)
        return card

    @r.post("/{card_id}/fund", dependencies=auth_deps)
    async def fund_card(card_id: str, request: FundCardRequest, principal: Principal = Depends(require_principal)):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)

        # If offramp_service is available, use real USDC→USD→Lithic flow
        if offramp_service and chain_executor and wallet_repo and request.source == "stablecoin":
            wallet_id = card.get("wallet_id")
            if not wallet_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card not linked to wallet")

            wallet = await wallet_repo.get(wallet_id)
            if not wallet:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked wallet not found")

            amount_minor = int(request.amount * 10**6)

            # 1. Get offramp quote (USDC→USD)
            try:
                quote = await offramp_service.get_quote(
                    input_token="USDC",
                    input_amount_minor=amount_minor,
                    input_chain="base",
                    output_currency="USD",
                )
            except Exception as e:
                logger.error("Offramp quote failed: %s", e)
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to get offramp quote")

            # 2. Get source address from wallet
            source_address = wallet.get_address("base") or ""
            for chain, addr in wallet.addresses.items():
                if addr:
                    source_address = addr
                    break

            if not source_address:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet has no on-chain address")

            # 3. Get destination (Lithic funding account or Bridge deposit)
            import os
            funding_account = os.getenv("LITHIC_FUNDING_ACCOUNT_ID", "")

            # 4. Execute offramp (Bridge converts USDC→USD→Lithic)
            try:
                tx = await offramp_service.execute(
                    quote=quote,
                    source_address=source_address,
                    destination_account=funding_account,
                )
            except Exception as e:
                logger.error("Offramp execute failed: %s", e)
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to execute offramp")

            # 5. Update card spend limit via Lithic provider
            try:
                await card_provider.fund_card(card_id=card_id, amount=float(request.amount))
            except Exception as e:
                logger.warning("Lithic fund_card call failed (offramp still processing): %s", e)

            # 6. Update funded_amount in DB
            current = card.get("funded_amount", 0) or 0
            row = await card_repo.update_funded_amount(card_id, float(current) + float(request.amount))
            return {
                **(row or {}),
                "offramp_tx_id": tx.transaction_id,
                "offramp_status": tx.status.value,
            }

        # Fallback: simple provider-based funding
        await card_provider.fund_card(card_id=card_id, amount=float(request.amount))
        current = card.get("funded_amount", 0) or 0
        row = await card_repo.update_funded_amount(card_id, float(current) + float(request.amount))
        return row

    @r.post("/{card_id}/freeze", dependencies=auth_deps)
    async def freeze_card(card_id: str, principal: Principal = Depends(require_principal)):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)
        await card_provider.freeze_card(provider_card_id=card.get("provider_card_id"))
        row = await card_repo.update_status(card_id, "frozen")
        return row

    @r.post("/{card_id}/unfreeze", dependencies=auth_deps)
    async def unfreeze_card(card_id: str, principal: Principal = Depends(require_principal)):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)
        await card_provider.unfreeze_card(provider_card_id=card.get("provider_card_id"))
        row = await card_repo.update_status(card_id, "active")
        return row

    @r.delete("/{card_id}", dependencies=auth_deps)
    async def cancel_card(card_id: str, principal: Principal = Depends(require_principal)):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)
        await card_provider.cancel_card(provider_card_id=card.get("provider_card_id"))
        row = await card_repo.update_status(card_id, "cancelled")
        return row

    @r.patch("/{card_id}/limits", dependencies=auth_deps)
    async def update_card_limits(card_id: str, request: UpdateLimitsRequest, principal: Principal = Depends(require_principal)):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)
        row = await card_repo.update_limits(
            card_id,
            limit_per_tx=float(request.limit_per_tx) if request.limit_per_tx is not None else None,
            limit_daily=float(request.limit_daily) if request.limit_daily is not None else None,
            limit_monthly=float(request.limit_monthly) if request.limit_monthly is not None else None,
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        return row

    @r.get("/{card_id}/transactions", dependencies=auth_deps)
    async def list_card_transactions(
        card_id: str,
        limit: int = Query(default=50, ge=1, le=100),
        principal: Principal = Depends(require_principal),
    ):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)
        return await card_repo.list_transactions(card_id, limit)

    @r.post("/{card_id}/simulate-purchase", status_code=status.HTTP_201_CREATED, dependencies=auth_deps)
    async def simulate_purchase(card_id: str, request: SimulatePurchaseRequest, principal: Principal = Depends(require_principal)):
        """
        Demo helper endpoint.

        Simulates a card transaction, runs policy checks, records it, and (optionally)
        freezes the card if a policy denial occurs.
        """
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)

        amount = Decimal(str(request.amount))
        ok, reason = await _evaluate_policy_for_card(
            wallet_id=card.get("wallet_id") or "",
            amount=amount,
            mcc_code=request.mcc_code,
        )

        status_value = request.status
        decline_reason: str | None = request.decline_reason
        if not ok:
            status_value = "declined_policy"
            decline_reason = reason
            if _auto_freeze_enabled() and card.get("provider_card_id"):
                try:
                    await card_provider.freeze_card(provider_card_id=card.get("provider_card_id"))
                    await card_repo.update_status(card_id, "frozen")
                except Exception:
                    logger.exception("Failed to auto-freeze card after policy denial")

        txn_id = f"txn_sim_{uuid.uuid4().hex[:12]}"
        row = await card_repo.record_transaction(
            card_id=card_id,
            transaction_id=txn_id,
            provider_tx_id=txn_id,
            amount=float(amount),
            currency=request.currency,
            merchant_name=request.merchant_name,
            merchant_category=request.mcc_code,
            decline_reason=decline_reason,
            status=status_value,
        )
        return {
            "transaction": row,
            "policy": {"allowed": ok, "reason": reason},
            "card": await card_repo.get_by_card_id(card_id),
        }

    def _normalize_card_status(value: Any) -> str:
        s = str(value or "").strip().lower()
        # Common patterns across providers
        if s in ("open", "active", "enabled"):
            return "active"
        if s in ("frozen", "disabled", "locked"):
            return "frozen"
        if s in ("cancelled", "canceled", "closed", "terminated"):
            return "cancelled"
        if s in ("pending", "created", "issued"):
            return "pending"
        # fallback: keep internal enum-ish strings stable
        if "freeze" in s:
            return "frozen"
        if "cancel" in s or "close" in s or "terminate" in s:
            return "cancelled"
        if "active" in s or "open" in s:
            return "active"
        return s or "pending"

    @r.post("/webhooks", status_code=status.HTTP_200_OK)
    async def receive_card_webhook(request: Request):
        body = await request.body()

        if webhook_secret:
            signature = request.headers.get("x-lithic-hmac")
            if not signature:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing webhook signature")
            expected = hmac.new(
                webhook_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

        import json
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

        event_type = _normalize_event_type(payload.get("event_type") or payload.get("type"))
        card_token = payload.get("card_token") or payload.get("data", {}).get("card_token") or payload.get("cardToken")

        # Card lifecycle events (status sync). We only require webhook signature (not JWT/API key).
        if "card." in event_type and "transaction" not in event_type:
            data = payload.get("data", {}) or {}
            card_token = (
                payload.get("card_token")
                or data.get("card_token")
                or payload.get("cardToken")
                or data.get("token")
                or payload.get("token")
            )
            card_status = (
                data.get("status")
                or (data.get("card") or {}).get("status")
                or payload.get("status")
            )

            if card_token and card_status:
                card = await card_repo.get_by_card_id(card_token)
                if not card and hasattr(card_repo, "get_by_provider_card_id"):
                    try:
                        card = await card_repo.get_by_provider_card_id(card_token)
                    except Exception:
                        card = None
                if card:
                    internal_card_id = card.get("card_id") or card_token
                    await card_repo.update_status(internal_card_id, _normalize_card_status(card_status))

            logger.info("Processed card lifecycle event_type=%s", event_type)
            return {"status": "received"}

        # We accept multiple Lithic-ish transaction event types but treat them similarly.
        is_tx_event = "transaction" in event_type and card_token
        if is_tx_event:
            txn = payload.get("data", {}) or {}
            card = await card_repo.get_by_card_id(card_token)
            if not card and hasattr(card_repo, "get_by_provider_card_id"):
                try:
                    card = await card_repo.get_by_provider_card_id(card_token)
                except Exception:
                    card = None
            if card:
                internal_card_id = card.get("card_id") or card_token
                amount = Decimal(str(txn.get("amount", 0) or 0))
                mcc_code = txn.get("merchant", {}).get("mcc") or txn.get("mcc") or "0000"
                ok, reason = await _evaluate_policy_for_card(
                    wallet_id=card.get("wallet_id") or "",
                    amount=amount,
                    mcc_code=str(mcc_code),
                )
                status_value, settled_at, decline_reason = _normalize_tx_status(event_type, txn)
                if not ok:
                    status_value = "declined_policy"
                    decline_reason = reason
                    if _auto_freeze_enabled() and card.get("provider_card_id"):
                        try:
                            await card_provider.freeze_card(provider_card_id=card.get("provider_card_id"))
                            await card_repo.update_status(internal_card_id, "frozen")
                        except Exception:
                            logger.exception("Failed to auto-freeze card after policy denial")
                await card_repo.record_transaction(
                    card_id=internal_card_id,
                    transaction_id=txn.get("token", f"txn_{uuid.uuid4().hex[:12]}"),
                    amount=txn.get("amount", 0),
                    currency=txn.get("currency", "USD"),
                    merchant_name=txn.get("merchant", {}).get("descriptor", "Unknown"),
                    merchant_category=str(mcc_code),
                    merchant_id=txn.get("merchant", {}).get("token") or txn.get("merchant_id"),
                    decline_reason=decline_reason,
                    status=status_value,
                    settled_at=settled_at,
                )

        logger.info("Processed webhook event_type=%s", event_type)
        return {"status": "received"}

    return r
