"""Sardis native PSP connector — stablecoin-native payments via ChainExecutor."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from decimal import Decimal
from typing import Any, Dict, Optional

from sardis_checkout.connectors.base import PSPConnector
from sardis_checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus, PSPType

logger = logging.getLogger(__name__)

CHECKOUT_BASE_URL = "https://checkout.sardis.sh"
SESSION_TIMEOUT_MINUTES = 15
DEFAULT_CHAIN = os.getenv("SARDIS_CHECKOUT_CHAIN", "base")


class SardisNativeConnector(PSPConnector):
    """
    Sardis native payment connector.

    Processes stablecoin payments directly via ChainExecutor without
    external PSP dependencies. Builds PaymentMandate internally,
    runs policy + compliance checks, dispatches on-chain.
    """

    def __init__(
        self,
        chain_executor: Any,
        wallet_manager: Any,
        compliance_engine: Any,
        ledger_store: Any,
        merchant_repo: Any,
        settlement_service: Optional[Any] = None,
        merchant_webhook_service: Optional[Any] = None,
        checkout_base_url: str = CHECKOUT_BASE_URL,
    ):
        self._chain_executor = chain_executor
        self._wallet_manager = wallet_manager
        self._compliance = compliance_engine
        self._ledger = ledger_store
        self._merchant_repo = merchant_repo
        self._settlement = settlement_service
        self._webhooks = merchant_webhook_service
        self._checkout_base_url = checkout_base_url.rstrip("/")

    @property
    def psp_type(self) -> PSPType:
        return PSPType.SARDIS

    async def create_checkout_session(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        """Create a merchant checkout session and return redirect URL."""
        from sardis_v2_core.merchant import MerchantCheckoutSession
        from datetime import datetime, timezone, timedelta

        merchant = await self._merchant_repo.get_merchant(request.metadata.get("merchant_id", ""))
        if not merchant:
            raise ValueError("Merchant not found")
        if not merchant.is_active:
            raise ValueError("Merchant is inactive")

        embed_origin = request.metadata.get("embed_origin")

        session = MerchantCheckoutSession(
            merchant_id=merchant.merchant_id,
            amount=request.amount,
            currency=request.currency,
            description=request.description,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata=request.metadata,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
            embed_origin=embed_origin,
        )
        await self._merchant_repo.create_session(session)

        # Fire checkout.created webhook
        if self._webhooks and merchant.webhook_url:
            asyncio.ensure_future(
                self._webhooks.deliver(
                    merchant=merchant,
                    event_type="checkout.created",
                    payload={
                        "session_id": session.session_id,
                        "amount": str(session.amount),
                        "currency": session.currency,
                        "status": "pending",
                    },
                )
            )

        return CheckoutResponse(
            checkout_id=session.session_id,
            redirect_url=f"{self._checkout_base_url}/s/{session.client_secret}",
            status=PaymentStatus.PENDING,
            psp_name="sardis",
            amount=request.amount,
            currency=request.currency,
            agent_id=request.agent_id,
            mandate_id=request.mandate_id,
            metadata={
                "merchant_id": merchant.merchant_id,
                "merchant_name": merchant.name,
                "session_id": session.session_id,
                "client_secret": session.client_secret,
            },
        )

    async def execute_payment(
        self,
        session_id: str,
        payer_wallet_id: str,
    ) -> dict[str, Any]:
        """
        Execute payment for a checkout session.

        Full pipeline:
        1. Acquire row lock (FOR UPDATE NOWAIT) to prevent double-pay
        2. Load payer wallet, validate active + not frozen
        3. Load merchant, get settlement wallet address
        4. Build PaymentMandate
        5. SpendingPolicy.evaluate() (if payer is agent)
        6. ComplianceEngine.preflight()
        7. Platform fee calculation
        8. Set idempotency key (DB unique constraint prevents duplicates)
        9. ChainExecutor.dispatch_payment() (net amount to merchant wallet)
        10. Fee dispatch (best-effort, to treasury wallet)
        11. WalletManager.async_record_spend()
        12. LedgerStore.append()
        13. Update session status = 'paid'
        14. Queue merchant webhook
        15. Trigger settlement for fiat merchants (fire-and-forget)
        """
        import inspect
        from sardis_v2_core.mandates import PaymentMandate, VCProof
        from sardis_v2_core.tokens import TokenType, to_raw_token_amount
        from sardis_v2_core.platform_fee import calculate_fee, get_treasury_address

        # Step 1: Acquire row lock to prevent concurrent payment
        try:
            session = await self._merchant_repo.get_session_for_update(session_id)
        except Exception as e:
            err_name = type(e).__name__
            if "LockNotAvailable" in err_name or "lock" in str(e).lower():
                raise ValueError("Payment already in progress") from e
            raise

        if not session:
            raise ValueError("Session not found")
        if session.status not in ("pending", "funded"):
            if session.status == "paid" and session.tx_hash:
                # Idempotent: return existing result
                return {
                    "session_id": session_id,
                    "status": "paid",
                    "tx_hash": session.tx_hash,
                    "amount": str(session.amount),
                    "currency": session.currency,
                    "merchant_id": session.merchant_id,
                    "platform_fee": str(session.platform_fee_amount),
                    "net_amount": str(session.net_amount) if session.net_amount else str(session.amount),
                }
            raise ValueError(f"Session status is '{session.status}', expected 'pending' or 'funded'")
        from datetime import datetime, timezone
        if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
            await self._merchant_repo.update_session(session_id, status="expired")
            # Fire checkout.expired webhook
            merchant_for_expiry = await self._merchant_repo.get_merchant(session.merchant_id)
            if self._webhooks and merchant_for_expiry and merchant_for_expiry.webhook_url:
                asyncio.ensure_future(
                    self._webhooks.deliver(
                        merchant=merchant_for_expiry,
                        event_type="checkout.expired",
                        payload={"session_id": session_id, "status": "expired"},
                    )
                )
            raise ValueError("Session has expired")

        merchant = await self._merchant_repo.get_merchant(session.merchant_id)
        if not merchant:
            raise ValueError("Merchant not found")

        # Step 2: Load and validate payer wallet
        wallet = await self._wallet_manager.get_wallet(payer_wallet_id)
        if not wallet:
            raise ValueError("Payer wallet not found")
        if not wallet.is_active:
            raise ValueError("Payer wallet is inactive")
        if getattr(wallet, "frozen", False):
            raise ValueError("Payer wallet is frozen")

        # Step 3: Get merchant settlement address
        if not merchant.settlement_wallet_id:
            raise ValueError("Merchant has no settlement wallet")

        merchant_wallet = await self._wallet_manager.get_wallet(merchant.settlement_wallet_id)
        if not merchant_wallet:
            raise ValueError("Merchant settlement wallet not found")

        chain = DEFAULT_CHAIN
        token = "USDC"
        destination = merchant_wallet.get_address(chain)
        if not destination:
            raise ValueError(f"Merchant wallet has no address on {chain}")

        source_address = wallet.get_address(chain)
        if not source_address:
            raise ValueError(f"Payer wallet has no address on {chain}")

        # Step 4: Build PaymentMandate
        idem_key = f"mcs:{session_id}:{payer_wallet_id}"
        digest = hashlib.sha256(idem_key.encode()).hexdigest()

        try:
            amount_minor = to_raw_token_amount(TokenType(token), session.amount)
        except Exception as exc:
            raise ValueError(f"Unsupported token: {token}") from exc

        mandate = PaymentMandate(
            mandate_id=f"mcs_{digest[:16]}",
            mandate_type="payment",
            issuer=f"wallet:{payer_wallet_id}",
            subject=wallet.agent_id,
            expires_at=int(time.time()) + 300,
            nonce=digest,
            proof=VCProof(
                verification_method=f"wallet:{payer_wallet_id}#key-1",
                created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                proof_value="sardis-checkout",
            ),
            domain=merchant.name or "sardis.sh",
            purpose="checkout",
            chain=chain,
            token=token,
            amount_minor=amount_minor,
            destination=destination,
            audit_hash=hashlib.sha256(
                f"{payer_wallet_id}:{destination}:{amount_minor}:{session_id}".encode()
            ).hexdigest(),
            wallet_id=payer_wallet_id,
            account_type=wallet.account_type,
            smart_account_address=wallet.smart_account_address,
            merchant_domain=merchant.name,
        )

        # Step 5: Policy check
        policy_result = await self._wallet_manager.async_validate_policies(mandate)
        if not getattr(policy_result, "allowed", False):
            reason = getattr(policy_result, "reason", None) or "policy_denied"
            await self._merchant_repo.update_session(session_id, status="failed")
            if self._webhooks and merchant.webhook_url:
                asyncio.ensure_future(
                    self._webhooks.deliver(
                        merchant=merchant,
                        event_type="payment.failed",
                        payload={"session_id": session_id, "reason": "policy_denied", "status": "failed"},
                    )
                )
            raise ValueError(f"Policy denied: {reason}")

        # Step 6: Compliance preflight
        compliance_result = await self._compliance.preflight(mandate)
        if not compliance_result.allowed:
            await self._merchant_repo.update_session(session_id, status="failed")
            if self._webhooks and merchant.webhook_url:
                asyncio.ensure_future(
                    self._webhooks.deliver(
                        merchant=merchant,
                        event_type="payment.failed",
                        payload={"session_id": session_id, "reason": "compliance_failed", "status": "failed"},
                    )
                )
            raise ValueError(f"Compliance check failed: {compliance_result.reason}")

        # Step 7: Platform fee calculation
        fee_calc = calculate_fee(session.amount, destination=destination)
        fee_tx_hash: str | None = None
        platform_fee_amount = Decimal("0")
        net_amount = session.amount

        if not fee_calc.fee_exempt and fee_calc.fee_amount > 0:
            platform_fee_amount = fee_calc.fee_amount
            net_amount = fee_calc.net_amount
            net_amount_minor = to_raw_token_amount(TokenType(token), fee_calc.net_amount)
            mandate.amount_minor = net_amount_minor

        # Step 8: Set idempotency key (DB unique constraint prevents duplicates)
        try:
            await self._merchant_repo.update_session(
                session_id,
                idempotency_key=idem_key,
                platform_fee_amount=platform_fee_amount,
                net_amount=net_amount,
            )
        except Exception as e:
            if "unique" in str(e).lower() or "duplicate" in str(e).lower():
                # Idempotent: another request already set this key
                existing = await self._merchant_repo.get_session(session_id)
                if existing and existing.status == "paid":
                    return {
                        "session_id": session_id,
                        "status": "paid",
                        "tx_hash": existing.tx_hash,
                        "amount": str(existing.amount),
                        "currency": existing.currency,
                        "merchant_id": existing.merchant_id,
                        "platform_fee": str(existing.platform_fee_amount),
                        "net_amount": str(existing.net_amount) if existing.net_amount else str(existing.amount),
                    }
                raise ValueError("Payment already in progress") from e
            raise

        # Step 9: Dispatch payment to merchant wallet
        try:
            receipt = await self._chain_executor.dispatch_payment(mandate)
        except Exception as e:
            await self._merchant_repo.update_session(session_id, status="failed")
            if self._webhooks and merchant.webhook_url:
                asyncio.ensure_future(
                    self._webhooks.deliver(
                        merchant=merchant,
                        event_type="payment.failed",
                        payload={"session_id": session_id, "reason": str(e), "status": "failed"},
                    )
                )
            raise ValueError(f"Payment failed: {e}") from e

        tx_hash = receipt.tx_hash if hasattr(receipt, "tx_hash") else str(receipt)

        # Step 10: Fee collection (best-effort)
        if not fee_calc.fee_exempt and fee_calc.fee_amount > 0:
            treasury_addr = get_treasury_address()
            if treasury_addr:
                try:
                    from sardis_v2_core.mandates import PaymentMandate as PM, VCProof as VP
                    fee_amount_minor = to_raw_token_amount(TokenType(token), fee_calc.fee_amount)
                    fee_mandate = PM(
                        mandate_id=f"fee_{digest[:16]}",
                        mandate_type="platform_fee",
                        issuer=f"wallet:{payer_wallet_id}",
                        subject=wallet.agent_id,
                        expires_at=int(time.time()) + 300,
                        nonce=f"fee_{digest}",
                        proof=VP(
                            verification_method=f"wallet:{payer_wallet_id}#key-1",
                            created=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                            proof_value="platform-fee",
                        ),
                        domain="sardis.sh",
                        purpose="platform_fee",
                        chain=chain,
                        token=token,
                        amount_minor=fee_amount_minor,
                        destination=treasury_addr,
                        audit_hash=hashlib.sha256(
                            f"fee:{payer_wallet_id}:{treasury_addr}:{fee_amount_minor}".encode()
                        ).hexdigest(),
                        wallet_id=payer_wallet_id,
                        account_type=wallet.account_type,
                        smart_account_address=wallet.smart_account_address,
                    )
                    fee_receipt = await self._chain_executor.dispatch_payment(fee_mandate)
                    fee_tx_hash = fee_receipt.tx_hash if hasattr(fee_receipt, "tx_hash") else str(fee_receipt)
                except Exception:
                    logger.exception("Failed to collect platform fee for session %s", session_id)

        # Step 11: Record spend
        try:
            await self._wallet_manager.async_record_spend(mandate)
        except Exception:
            logger.warning("Failed to record spend for session %s", session_id)

        # Step 12: Ledger append
        ledger_tx_id: str | None = None
        if self._ledger:
            try:
                if hasattr(self._ledger, "append_async"):
                    maybe_tx = self._ledger.append_async(payment_mandate=mandate, chain_receipt=receipt)
                else:
                    maybe_tx = self._ledger.append(payment_mandate=mandate, chain_receipt=receipt)
                tx = await maybe_tx if inspect.isawaitable(maybe_tx) else maybe_tx
                ledger_tx_id = getattr(tx, "tx_id", None)
            except Exception:
                logger.warning("Failed to append ledger for session %s", session_id)

        # Step 13: Update session
        await self._merchant_repo.update_session(
            session_id,
            status="paid",
            payer_wallet_id=payer_wallet_id,
            tx_hash=tx_hash,
            payment_method="wallet",
        )

        # Step 14: Queue merchant webhook (fire-and-forget)
        if self._webhooks and merchant.webhook_url:
            asyncio.ensure_future(
                self._webhooks.deliver(
                    merchant=merchant,
                    event_type="payment.completed",
                    payload={
                        "session_id": session_id,
                        "amount": str(session.amount),
                        "currency": session.currency,
                        "tx_hash": tx_hash,
                        "payer_wallet_id": payer_wallet_id,
                        "platform_fee": str(platform_fee_amount),
                        "net_amount": str(net_amount),
                        "status": "paid",
                    },
                )
            )

        # Step 15: Trigger settlement for fiat merchants (fire-and-forget)
        if merchant.settlement_preference == "fiat" and self._settlement:
            asyncio.ensure_future(self._settlement.settle_session(session_id))

        return {
            "session_id": session_id,
            "status": "paid",
            "tx_hash": tx_hash,
            "fee_tx_hash": fee_tx_hash,
            "ledger_tx_id": ledger_tx_id,
            "amount": str(session.amount),
            "currency": session.currency,
            "merchant_id": merchant.merchant_id,
            "platform_fee": str(platform_fee_amount),
            "net_amount": str(net_amount),
        }

    async def get_payment_status(
        self,
        session_id: str,
    ) -> PaymentStatus:
        """Get checkout session payment status."""
        session = await self._merchant_repo.get_session(session_id)
        if not session:
            return PaymentStatus.FAILED

        status_map = {
            "pending": PaymentStatus.PENDING,
            "funded": PaymentStatus.PROCESSING,
            "paid": PaymentStatus.COMPLETED,
            "settled": PaymentStatus.COMPLETED,
            "expired": PaymentStatus.EXPIRED,
            "failed": PaymentStatus.FAILED,
        }
        return status_map.get(session.status, PaymentStatus.PENDING)

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Sardis webhook signature (HMAC-SHA256).

        The native connector does not receive external PSP webhooks.
        Merchant webhook verification is handled by
        MerchantWebhookService.verify_signature() which has access to
        the per-merchant webhook_secret.

        This method satisfies the PSPConnector interface but should
        never be called in practice for the native connector.
        """
        raise NotImplementedError(
            "SardisNativeConnector.verify_webhook should not be called directly. "
            "Use MerchantWebhookService.verify_signature() instead."
        )

    async def handle_webhook(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> Dict[str, Any]:
        """Handle internal webhook (no external PSP webhooks for native connector)."""
        return payload
