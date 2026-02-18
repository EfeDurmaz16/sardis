"""Virtual Card API endpoints with dependency injection."""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
from decimal import Decimal
from typing import Optional, List, Any, Literal
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core import AgentRepository
from sardis_api.idempotency import get_idempotency_key, run_idempotent
from sardis_api.webhook_replay import run_with_replay_protection
from sardis_api.canonical_state_machine import normalize_lithic_card_event

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
    funding_source: str = Field(default="fiat")


class FundCardRequest(BaseModel):
    """Request to fund a card."""
    amount: Decimal = Field(gt=0)
    source: Optional[Literal["fiat", "stablecoin"]] = Field(
        default=None,
        description="If omitted, uses SARDIS_TREASURY_DEFAULT_ROUTE",
    )


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
    environment: str | None = None,
    offramp_service=None,
    chain_executor=None,
    wallet_repo=None,
    policy_store=None,
    treasury_repo=None,
    agent_repo: AgentRepository | None = None,
    canonical_repo=None,
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
            # In production, policy enforcement is mandatory
            # TODO: Migrate to PaymentOrchestrator gateway
            if environment and environment.lower() in ("production", "prod"):
                logger.error("CRITICAL: policy_store or wallet_repo not configured in production")
                return False, "policy_enforcement_unavailable_in_production"
            logger.warning("Policy store or wallet repo not configured - skipping policy check (non-production)")
            return True, "OK"
        wallet = await wallet_repo.get(wallet_id)
        if not wallet:
            return True, "OK"
        policy = await policy_store.fetch_policy(wallet.agent_id)
        if not policy:
            return True, "OK"
        # Resolve MCC code to category for category-specific rule matching
        merchant_category = None
        if mcc_code:
            from sardis_v2_core.mcc_service import get_mcc_info
            mcc_info = get_mcc_info(mcc_code)
            if mcc_info:
                merchant_category = mcc_info.category
        ok, reason = policy.validate_payment(
            amount=amount,
            fee=Decimal("0"),
            mcc_code=mcc_code,
            merchant_category=merchant_category,
        )
        return ok, reason

    async def _require_wallet_access(wallet_id: str, principal: Principal):
        if not wallet_repo or not agent_repo:
            # In production, missing repositories is a hard error. In dev/test,
            # allow unit-level router usage without wiring the full app deps.
            import os

            env = (os.getenv("SARDIS_ENVIRONMENT", "dev") or "dev").strip().lower()
            if env in ("prod", "production"):
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="wallet_or_agent_repository_not_configured",
                )
            return None
        wallet = await wallet_repo.get(wallet_id)
        if not wallet:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")
        agent = await agent_repo.get(wallet.agent_id)
        if not agent:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
        if not principal.is_admin and agent.owner_id != principal.organization_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return wallet

    async def _resolve_org_for_card(card: dict[str, Any] | None) -> str:
        if not card:
            return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
        wallet_id = str(card.get("wallet_id") or "")
        if not wallet_id or not wallet_repo or not agent_repo:
            return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
        try:
            wallet = await wallet_repo.get(wallet_id)
            if not wallet:
                return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
            agent = await agent_repo.get(wallet.agent_id)
            if agent and getattr(agent, "owner_id", None):
                return str(agent.owner_id)
        except Exception:
            logger.exception("Failed to resolve org for card=%s", card.get("card_id") if card else None)
        return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")

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

    def _treasury_default_route() -> str:
        configured = (os.getenv("SARDIS_TREASURY_DEFAULT_ROUTE", "fiat_first") or "fiat_first").strip().lower()
        if configured not in {"fiat_first", "stablecoin_first"}:
            configured = "fiat_first"
        return configured

    def _resolve_card_funding_source(requested_source: Optional[str]) -> Literal["fiat", "stablecoin"]:
        if requested_source in {"fiat", "stablecoin"}:
            return requested_source
        return "stablecoin" if _treasury_default_route() == "stablecoin_first" else "fiat"

    @r.post("", status_code=status.HTTP_201_CREATED, dependencies=auth_deps)
    async def issue_card(payload: IssueCardRequest, http_request: Request, principal: Principal = Depends(require_principal)):
        await _require_wallet_access(payload.wallet_id, principal)

        idem_key = get_idempotency_key(http_request)
        if not idem_key:
            idem_key = (
                f"{payload.wallet_id}:{payload.card_type}:{payload.limit_per_tx}:{payload.limit_daily}:"
                f"{payload.limit_monthly}:{payload.locked_merchant_id or ''}:{payload.funding_source}"
            )

        async def _issue() -> tuple[int, object]:
            digest = hashlib.sha256(str(idem_key).encode()).hexdigest()
            card_id = f"vc_{digest[:16]}"
            provider_result = await card_provider.create_card(
                card_id=card_id,
                wallet_id=payload.wallet_id,
                card_type=payload.card_type,
                limit_per_tx=float(payload.limit_per_tx),
                limit_daily=float(payload.limit_daily),
                limit_monthly=float(payload.limit_monthly),
            )
            row = await card_repo.create(
                card_id=card_id,
                wallet_id=payload.wallet_id,
                provider="lithic",
                provider_card_id=provider_result.provider_card_id,
                card_type=payload.card_type,
                limit_per_tx=float(payload.limit_per_tx),
                limit_daily=float(payload.limit_daily),
                limit_monthly=float(payload.limit_monthly),
            )
            return status.HTTP_201_CREATED, row

        return await run_idempotent(
            request=http_request,
            principal=principal,
            operation="cards.issue",
            key=str(idem_key),
            payload=payload.model_dump(),
            fn=_issue,
            ttl_seconds=7 * 24 * 60 * 60,
        )

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
    async def fund_card(
        card_id: str,
        payload: FundCardRequest,
        http_request: Request,
        principal: Principal = Depends(require_principal),
    ):
        card = await card_repo.get_by_card_id(card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        wallet_id = card.get("wallet_id")
        if wallet_id:
            await _require_wallet_access(str(wallet_id), principal)

        funding_source = _resolve_card_funding_source(payload.source)
        idem_key = get_idempotency_key(http_request) or f"{card_id}:{funding_source}:{payload.amount}"

        async def _fund() -> tuple[int, object]:
            reservation_id = f"tr_{uuid.uuid4().hex[:24]}"
            amount_minor = int((payload.amount * Decimal("100")).to_integral_value())

            async def _reservation(status_value: str, reason: str | None = None, reference_id: str | None = None):
                if not treasury_repo:
                    return
                await treasury_repo.create_reservation(
                    reservation_id=reservation_id,
                    organization_id=principal.organization_id,
                    wallet_id=str(wallet_id) if wallet_id else None,
                    card_id=card_id,
                    currency="USD",
                    amount_minor=amount_minor,
                    status=status_value,
                    reason=reason,
                    reference_id=reference_id,
                    metadata={"funding_source": funding_source},
                )

            await _reservation("held", reason="card_funding")

            # Stablecoin-backed card funding path (USDC -> USD -> Lithic)
            if funding_source == "stablecoin" and offramp_service and chain_executor and wallet_repo:
                if not wallet_id:
                    await _reservation("released", reason="card_not_linked")
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Card not linked to wallet")

                wallet = await wallet_repo.get(str(wallet_id))
                if not wallet:
                    await _reservation("released", reason="linked_wallet_not_found")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked wallet not found")

                from sardis_v2_core.tokens import TokenType, to_raw_token_amount
                stablecoin_amount_minor = to_raw_token_amount(TokenType.USDC, payload.amount)

                try:
                    quote = await offramp_service.get_quote(
                        input_token="USDC",
                        input_amount_minor=stablecoin_amount_minor,
                        input_chain="base",
                        output_currency="USD",
                    )
                except Exception as e:
                    logger.error("Offramp quote failed: %s", e)
                    await _reservation("released", reason="offramp_quote_failed")
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to get offramp quote")

                source_address = wallet.get_address("base") or ""
                for _, addr in wallet.addresses.items():
                    if addr:
                        source_address = addr
                        break
                if not source_address:
                    await _reservation("released", reason="wallet_address_missing")
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Wallet has no on-chain address")

                funding_account = ""
                if treasury_repo is not None:
                    funding_account = await treasury_repo.get_funding_account_for_org(
                        principal.organization_id,
                        preferred_role="ISSUING",
                    ) or ""
                if not funding_account:
                    funding_account = os.getenv("LITHIC_FUNDING_ACCOUNT_ID", "")
                if not funding_account:
                    await _reservation("released", reason="treasury_funding_account_not_mapped")
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="lithic_funding_account_not_configured")

                try:
                    tx = await offramp_service.execute(
                        quote=quote,
                        source_address=source_address,
                        destination_account=funding_account,
                        wallet_id=str(wallet_id),
                    )
                except Exception as e:
                    logger.error("Offramp execute failed: %s", e)
                    await _reservation("released", reason="offramp_execute_failed")
                    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to execute offramp")

                try:
                    await card_provider.fund_card(card_id=card_id, amount=float(payload.amount))
                except Exception as e:
                    logger.warning("Lithic fund_card call failed (offramp still processing): %s", e)

                current = card.get("funded_amount", 0) or 0
                row = await card_repo.update_funded_amount(card_id, float(current) + float(payload.amount))
                await _reservation("consumed", reference_id=str(tx.transaction_id))
                return 200, {
                    **(row or {}),
                    "offramp_tx_id": tx.transaction_id,
                    "offramp_status": tx.status.value,
                    "funding_source": "stablecoin",
                }

            if funding_source == "stablecoin":
                await _reservation("released", reason="stablecoin_path_not_configured")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="stablecoin_funding_not_configured",
                )

            # Fiat-first path: card is funded from issuer-side USD treasury.
            if treasury_repo is not None:
                mapped_funding_account = await treasury_repo.get_funding_account_for_org(
                    principal.organization_id,
                    preferred_role="ISSUING",
                )
                if not mapped_funding_account:
                    await _reservation("released", reason="fiat_treasury_not_mapped")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="fiat_treasury_account_not_mapped",
                    )

            await card_provider.fund_card(card_id=card_id, amount=float(payload.amount))
            current = card.get("funded_amount", 0) or 0
            row = await card_repo.update_funded_amount(card_id, float(current) + float(payload.amount))
            await _reservation("consumed", reference_id=card_id)
            return 200, {**(row or {}), "funding_source": "fiat"}

        return await run_idempotent(
            request=http_request,
            principal=principal,
            operation="cards.fund",
            key=str(idem_key),
            payload={"card_id": card_id, **payload.model_dump()},
            fn=_fund,
            ttl_seconds=7 * 24 * 60 * 60,
        )

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

        # If policy passed, attempt real Lithic sandbox authorization
        provider_tx_id: str | None = None
        if ok and card.get("provider_card_id") and hasattr(card_provider, "simulate_authorization"):
            try:
                amount_cents = int(amount * 100)
                lithic_tx = await card_provider.simulate_authorization(
                    provider_card_id=card.get("provider_card_id"),
                    amount_cents=amount_cents,
                    merchant_descriptor=request.merchant_name,
                )
                provider_tx_id = lithic_tx.provider_tx_id
                logger.info("Lithic sandbox authorization: %s", provider_tx_id)
            except Exception as exc:
                logger.warning("Lithic simulate_authorization failed (non-fatal): %s", exc)

        txn_id = f"txn_sim_{uuid.uuid4().hex[:12]}"
        row = await card_repo.record_transaction(
            card_id=card_id,
            transaction_id=txn_id,
            provider_tx_id=provider_tx_id or txn_id,
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
            "provider_tx_id": provider_tx_id,
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
        effective_env = (environment or os.getenv("SARDIS_ENVIRONMENT", "dev")).strip().lower()

        if not webhook_secret and effective_env in {"prod", "production"}:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="LITHIC_WEBHOOK_SECRET is required in production",
            )

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

        event_id = (
            payload.get("token")
            or payload.get("event_token")
            or payload.get("eventToken")
            or payload.get("id")
        )
        if not event_id:
            event_id = hashlib.sha256(body).hexdigest()

        async def _process() -> dict:
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
                    if canonical_repo is not None:
                        org_id = await _resolve_org_for_card(card)
                        tx_ref = str(
                            txn.get("token")
                            or txn.get("provider_tx_id")
                            or txn.get("transaction_id")
                            or f"{internal_card_id}:{event_id}"
                        )
                        normalized = normalize_lithic_card_event(
                            organization_id=org_id,
                            payload=payload,
                            event_type=event_type,
                            transaction_reference=tx_ref,
                        )
                        await canonical_repo.ingest_event(
                            normalized,
                            drift_tolerance_minor=int(os.getenv("SARDIS_CANONICAL_DRIFT_TOLERANCE_MINOR", "1000")),
                        )

            logger.info("Processed webhook event_type=%s", event_type)
            return {"status": "received"}

        return await run_with_replay_protection(
            request=request,
            provider="lithic",
            event_id=str(event_id),
            body=body,
            ttl_seconds=7 * 24 * 60 * 60,
            response_on_duplicate={"status": "received"},
            fn=_process,
        )

    return r
