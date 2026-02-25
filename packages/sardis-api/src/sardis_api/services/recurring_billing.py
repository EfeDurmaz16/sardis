"""Recurring billing engine for scheduled subscription payments."""

from __future__ import annotations

import calendar
import hashlib
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable, Optional

from sardis_chain.executor import STABLECOIN_ADDRESSES
from sardis_v2_core.mandates import PaymentMandate, VCProof
from sardis_v2_core.tokens import TokenType, to_raw_token_amount

logger = logging.getLogger("sardis.recurring")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def compute_next_billing(current: datetime, billing_cycle: str, billing_day: int) -> datetime:
    cycle = (billing_cycle or "monthly").strip().lower()
    if cycle == "daily":
        return current + timedelta(days=1)
    if cycle == "weekly":
        return current + timedelta(days=7)
    if cycle == "yearly":
        return current + timedelta(days=365)

    # Monthly default.
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    year = current.year
    month = current.month + 1
    if month == 13:
        month = 1
        year += 1
    max_day = calendar.monthrange(year, month)[1]
    day = min(max(1, int(billing_day)), max_day)
    return current.replace(year=year, month=month, day=day)


@dataclass(slots=True)
class RecurringBillingResult:
    subscription_id: str
    billing_event_id: str
    status: str
    tx_hash: Optional[str] = None
    reason: Optional[str] = None


AutoFundHandler = Callable[[dict[str, Any], int], Awaitable[str]]


class RecurringBillingService:
    def __init__(
        self,
        *,
        subscription_repo,
        wallet_repo,
        agent_repo,
        chain_executor,
        wallet_manager,
        compliance,
        autofund_handler: Optional[AutoFundHandler] = None,
    ):
        self._subscription_repo = subscription_repo
        self._wallet_repo = wallet_repo
        self._agent_repo = agent_repo
        self._chain_executor = chain_executor
        self._wallet_manager = wallet_manager
        self._compliance = compliance
        self._autofund_handler = autofund_handler

    async def _estimate_wallet_balance_minor(self, wallet: Any, chain: str, token: str) -> int:
        if not self._chain_executor:
            return 0
        address = wallet.get_address(chain)
        if not address:
            return 0
        token_address = STABLECOIN_ADDRESSES.get(chain, {}).get(token.upper())
        if not token_address:
            return 0
        rpc_client = self._chain_executor._get_rpc_client(chain)  # noqa: SLF001
        balance_data = "0x70a08231" + address[2:].lower().zfill(64)
        result = await rpc_client._call("eth_call", [{"to": token_address, "data": balance_data}, "latest"])  # noqa: SLF001
        if not result or result == "0x":
            return 0
        return int(result, 16)

    async def _maybe_autofund(self, subscription: dict[str, Any], amount_minor: int) -> Optional[str]:
        if not subscription.get("autofund_enabled"):
            return None
        if self._autofund_handler is not None:
            return await self._autofund_handler(subscription, amount_minor)
        # Default simulated autofund artifact for deterministic testing/dev flows.
        digest = hashlib.sha256(f"{subscription['id']}:{amount_minor}".encode()).hexdigest()[:16]
        return f"autofund_sim_{digest}"

    async def process_due_subscriptions(self, *, limit: int = 50) -> list[RecurringBillingResult]:
        now = _utc_now()
        due_subscriptions = await self._subscription_repo.list_due_subscriptions(now=now, limit=limit)
        if not due_subscriptions:
            return []

        results: list[RecurringBillingResult] = []
        for subscription in due_subscriptions:
            subscription_id = str(subscription.get("id", ""))
            wallet_id = str(subscription.get("wallet_id", ""))
            billing_event = await self._subscription_repo.create_billing_event(
                subscription_id=subscription_id,
                wallet_id=wallet_id,
                scheduled_at=now,
                amount_cents=int(subscription.get("amount_cents", 0) or 0),
                status="processing",
            )
            billing_event_id = str(billing_event.get("id", ""))
            try:
                wallet = await self._wallet_repo.get(wallet_id)
                if not wallet:
                    raise RuntimeError("wallet_not_found")
                if not wallet.is_active:
                    raise RuntimeError("wallet_inactive")

                destination = str(subscription.get("destination_address") or "").strip()
                if not destination:
                    raise RuntimeError("subscription_destination_missing")

                token = str(subscription.get("token") or "USDC").upper()
                chain = str(subscription.get("chain") or "base_sepolia").strip()
                amount_cents = int(subscription.get("amount_cents", 0) or 0)
                amount_decimal = Decimal(amount_cents) / Decimal(100)
                amount_minor = to_raw_token_amount(TokenType(token), amount_decimal)

                # Auto-fund branch if token balance is below next cycle amount.
                fund_tx_id: Optional[str] = None
                try:
                    balance_minor = await self._estimate_wallet_balance_minor(wallet, chain, token)
                except Exception:
                    balance_minor = 0
                if balance_minor < amount_minor and subscription.get("autofund_enabled"):
                    fund_tx_id = await self._maybe_autofund(subscription, amount_minor - balance_minor)
                    await self._subscription_repo.update_billing_event(
                        billing_event_id,
                        fund_tx_id=fund_tx_id,
                        status="funded" if fund_tx_id else "processing",
                    )

                digest = hashlib.sha256(f"{subscription_id}:{billing_event_id}:{int(time.time())}".encode()).hexdigest()
                mandate = PaymentMandate(
                    mandate_id=f"subpay_{digest[:16]}",
                    mandate_type="payment",
                    issuer=f"subscription:{subscription_id}",
                    subject=wallet.agent_id,
                    expires_at=int(time.time()) + 300,
                    nonce=digest,
                    proof=VCProof(
                        verification_method=f"subscription:{subscription_id}#schedule",
                        created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                        proof_value="recurring-billing-engine",
                    ),
                    domain="sardis.sh",
                    purpose="subscription",
                    chain=chain,
                    token=token,
                    amount_minor=amount_minor,
                    destination=destination,
                    audit_hash=hashlib.sha256(
                        f"{subscription_id}:{billing_event_id}:{destination}:{amount_minor}".encode()
                    ).hexdigest(),
                    wallet_id=wallet.wallet_id,
                    account_type=wallet.account_type,
                    smart_account_address=wallet.smart_account_address,
                    merchant_domain=str(subscription.get("merchant") or "subscription"),
                )

                policy_result = await self._wallet_manager.async_validate_policies(mandate)
                if not getattr(policy_result, "allowed", False):
                    raise RuntimeError(getattr(policy_result, "reason", None) or "policy_denied")

                compliance_result = await self._compliance.preflight(mandate)
                if not compliance_result.allowed:
                    raise RuntimeError(compliance_result.reason or "compliance_denied")

                receipt = await self._chain_executor.dispatch_payment(mandate)
                await self._wallet_manager.async_record_spend(mandate)

                next_billing = compute_next_billing(
                    current=subscription.get("next_billing") or now,
                    billing_cycle=str(subscription.get("billing_cycle") or "monthly"),
                    billing_day=int(subscription.get("billing_day", 1) or 1),
                )

                await self._subscription_repo.update_billing_event(
                    billing_event_id,
                    status="charged",
                    charge_tx_id=getattr(receipt, "tx_hash", None),
                )
                await self._subscription_repo.mark_subscription_charged(
                    subscription_id,
                    charged_at=now,
                    next_billing=next_billing,
                    charge_tx_id=getattr(receipt, "tx_hash", None),
                )

                results.append(
                    RecurringBillingResult(
                        subscription_id=subscription_id,
                        billing_event_id=billing_event_id,
                        status="charged",
                        tx_hash=getattr(receipt, "tx_hash", None),
                    )
                )
            except Exception as exc:
                reason = str(exc)
                logger.warning("Recurring charge failed sub=%s reason=%s", subscription_id, reason)
                await self._subscription_repo.update_billing_event(
                    billing_event_id,
                    status="failed",
                    error=reason,
                )
                await self._subscription_repo.mark_subscription_failed(subscription_id, error=reason)
                results.append(
                    RecurringBillingResult(
                        subscription_id=subscription_id,
                        billing_event_id=billing_event_id,
                        status="failed",
                        reason=reason,
                    )
                )

        return results
