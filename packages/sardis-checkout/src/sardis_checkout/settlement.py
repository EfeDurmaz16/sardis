"""Settlement service for merchant checkout payments.

Settlement routing priority (Protocol v1.1):
1. Internal ledger — both parties on Sardis, ~1ms DB transaction
2. Same-chain stablecoin — direct TIP-20/ERC-20 transfer
3. Cross-chain — CCTP or MPP bridge
4. Fiat off-ramp — Bridge.xyz or CPN
"""
from __future__ import annotations

import logging
import os
from typing import Any

_CHECKOUT_CHAIN = os.getenv("SARDIS_CHECKOUT_CHAIN", "base")

# Tempo chain identifiers
_TEMPO_CHAINS = {"tempo", "tempo_testnet"}

logger = logging.getLogger(__name__)


class SettlementService:
    """
    Handles per-transaction and batch settlement for merchants.

    - USDC merchants: mark as settled immediately (funds already in wallet)
    - Fiat merchants: trigger Bridge offramp to bank account
    """

    def __init__(
        self,
        merchant_repo: Any,
        offramp_service: Any | None = None,
        merchant_webhook_service: Any | None = None,
        cpn_adapter: Any | None = None,
        stripe_connect_provider: Any | None = None,
    ):
        self._merchant_repo = merchant_repo
        self._offramp = offramp_service
        self._webhooks = merchant_webhook_service
        self._cpn_adapter = cpn_adapter
        self._stripe_connect = stripe_connect_provider

    async def settle_session(self, session_id: str) -> None:
        """
        Per-transaction settlement.

        For USDC merchants: mark settled (funds already on-chain).
        For fiat merchants: trigger Bridge offramp to bank account.
        """
        session = await self._merchant_repo.get_session(session_id)
        if not session:
            logger.error("Settlement: session %s not found", session_id)
            return
        if session.status != "paid":
            logger.warning("Settlement: session %s status is %s, skipping", session_id, session.status)
            return

        merchant = await self._merchant_repo.get_merchant(session.merchant_id)
        if not merchant:
            logger.error("Settlement: merchant %s not found", session.merchant_id)
            return

        # Internal ledger settlement (Protocol v1.1 fast path)
        # When both parties are on Sardis, skip external rails entirely (~1ms)
        if merchant.settlement_preference == "internal" or (
            merchant.settlement_preference == "usdc"
            and getattr(session, "payer_on_sardis", False)
            and getattr(merchant, "on_sardis", False)
        ):
            await self._settle_internal(session_id, session, merchant)
            return

        # Tempo settlement: TIP-20 stablecoin transfer (pathUSD)
        if _CHECKOUT_CHAIN in _TEMPO_CHAINS or merchant.settlement_preference == "tempo":
            await self._settle_tempo(session_id, session, merchant)
            return

        if merchant.settlement_preference == "usdc":
            # USDC settlement: funds already in merchant wallet, just mark settled
            await self._merchant_repo.update_session(
                session_id,
                status="settled",
                settlement_status="completed",
            )
            if self._webhooks and merchant.webhook_url:
                await self._webhooks.deliver(
                    merchant=merchant,
                    event_type="settlement.completed",
                    payload={
                        "session_id": session_id,
                        "amount": str(session.amount),
                        "currency": session.currency,
                        "settlement_method": "usdc",
                    },
                )
            return

        if merchant.settlement_preference == "cpn":
            # CPN settlement: fund merchant via Circle Payments Network
            if not self._cpn_adapter:
                logger.error("Settlement: no CPN adapter configured for session %s", session_id)
                await self._merchant_repo.update_session(
                    session_id, settlement_status="failed"
                )
                return

            try:
                from decimal import Decimal

                from sardis_v2_core.funding import FundingRequest

                request = FundingRequest(
                    amount=Decimal(str(session.amount)),
                    currency=session.currency or "USD",
                    description=f"Settlement for session {session_id}",
                    connected_account_id=getattr(merchant, "cpn_account_id", None),
                    metadata={"session_id": session_id, "merchant_id": session.merchant_id},
                )
                result = await self._cpn_adapter.fund(request)

                await self._merchant_repo.update_session(
                    session_id,
                    settlement_status="processing",
                    offramp_id=result.transfer_id,
                )

                if self._webhooks and merchant.webhook_url:
                    await self._webhooks.deliver(
                        merchant=merchant,
                        event_type="settlement.initiated",
                        payload={
                            "session_id": session_id,
                            "amount": str(session.amount),
                            "currency": session.currency,
                            "settlement_method": "cpn",
                            "transfer_id": result.transfer_id,
                        },
                    )
            except Exception:
                logger.exception("CPN settlement failed for session %s", session_id)
                await self._merchant_repo.update_session(
                    session_id, settlement_status="failed"
                )
            return

        # Stripe Connect settlement: transfer to merchant's connected account
        if merchant.settlement_preference == "stripe_connect":
            await self._settle_stripe_connect(session_id, session, merchant)
            return

        # Fiat settlement via Bridge offramp
        if not self._offramp:
            logger.error("Settlement: no offramp provider configured")
            await self._merchant_repo.update_session(
                session_id, settlement_status="failed"
            )
            return

        if not merchant.bank_account:
            logger.error("Settlement: merchant %s has no bank account", merchant.merchant_id)
            await self._merchant_repo.update_session(
                session_id, settlement_status="failed"
            )
            return

        try:
            # Get quote from Bridge
            from sardis_v2_core.tokens import TokenType, to_raw_token_amount
            amount_minor = to_raw_token_amount(TokenType.USDC, session.amount)

            quote = await self._offramp.get_quote(
                input_token="USDC",
                input_amount_minor=amount_minor,
                input_chain=_CHECKOUT_CHAIN,
                output_currency="USD",
            )

            # Get merchant settlement wallet address
            source_address = ""
            if merchant.settlement_wallet_id:
                # Use the settlement wallet address on base
                from sardis_v2_core.database import Database
                row = await Database.fetchrow(
                    """
                    SELECT w.chain_address FROM wallets w
                    JOIN agents a ON a.id = w.agent_id
                    WHERE w.external_id = $1
                    """,
                    merchant.settlement_wallet_id,
                )
                if row:
                    source_address = row["chain_address"] or ""

            destination_account = merchant.bank_account.get("bridge_account_id", "")
            if not destination_account:
                logger.error("Settlement: no bridge_account_id for merchant %s", merchant.merchant_id)
                await self._merchant_repo.update_session(
                    session_id, settlement_status="failed"
                )
                return

            # Execute offramp
            tx = await self._offramp.execute(
                quote=quote,
                source_address=source_address,
                destination_account=destination_account,
                wallet_id=merchant.settlement_wallet_id,
            )

            await self._merchant_repo.update_session(
                session_id,
                settlement_status="processing",
                offramp_id=tx.transaction_id,
            )

            if self._webhooks and merchant.webhook_url:
                await self._webhooks.deliver(
                    merchant=merchant,
                    event_type="settlement.initiated",
                    payload={
                        "session_id": session_id,
                        "amount": str(session.amount),
                        "currency": session.currency,
                        "settlement_method": "bridge",
                        "offramp_id": tx.transaction_id,
                    },
                )

        except Exception:
            logger.exception("Settlement failed for session %s", session_id)
            await self._merchant_repo.update_session(
                session_id, settlement_status="failed"
            )

    async def poll_settlement_status(self) -> int:
        """
        Poll Bridge for status of processing settlements.
        Returns count of completed settlements.
        """
        if not self._offramp:
            return 0

        sessions = await self._merchant_repo.get_processing_settlements()
        completed = 0

        for session in sessions:
            if not session.offramp_id:
                continue
            try:
                tx = await self._offramp.get_status(session.offramp_id)
                if tx.status.value == "completed":
                    await self._merchant_repo.update_session(
                        session.session_id,
                        status="settled",
                        settlement_status="completed",
                        settlement_tx_hash=tx.provider_reference or tx.transaction_id,
                    )
                    completed += 1

                    merchant = await self._merchant_repo.get_merchant(session.merchant_id)
                    if self._webhooks and merchant and merchant.webhook_url:
                        await self._webhooks.deliver(
                            merchant=merchant,
                            event_type="settlement.completed",
                            payload={
                                "session_id": session.session_id,
                                "amount": str(session.amount),
                                "currency": session.currency,
                                "settlement_method": "bridge",
                                "offramp_id": session.offramp_id,
                            },
                        )
                elif tx.status.value == "failed":
                    await self._merchant_repo.update_session(
                        session.session_id,
                        settlement_status="failed",
                    )
            except Exception:
                logger.exception("Failed to poll settlement for session %s", session.session_id)

        return completed

    async def settle_merchant(self, merchant_id: str) -> dict[str, Any]:
        """
        Batch settlement for a merchant — retry any failed per-tx settlements.
        Also used for manual Coinbase Offramp triggering.
        """
        sessions = await self._merchant_repo.list_sessions_by_merchant(
            merchant_id, status="paid"
        )
        results = {"settled": 0, "failed": 0, "skipped": 0}

        for session in sessions:
            if session.settlement_status == "completed":
                results["skipped"] += 1
                continue
            try:
                await self.settle_session(session.session_id)
                results["settled"] += 1
            except Exception:
                logger.exception("Batch settle failed for session %s", session.session_id)
                results["failed"] += 1

        return results

    async def _settle_stripe_connect(self, session_id: str, session: Any, merchant: Any) -> None:
        """
        Stripe Connect settlement: transfer funds to merchant's connected Stripe account.

        After an agent pays in stablecoin, we transfer the equivalent fiat amount
        to the merchant's Stripe Express account. Stripe's automatic payout schedule
        then sends it to their bank. The merchant sees USD, never USDC.
        """
        if not self._stripe_connect:
            logger.error("Settlement: no Stripe Connect provider configured for session %s", session_id)
            await self._merchant_repo.update_session(session_id, settlement_status="failed")
            return

        if not merchant.stripe_account_id:
            logger.error("Settlement: merchant %s has no Stripe Connect account", merchant.merchant_id)
            await self._merchant_repo.update_session(session_id, settlement_status="failed")
            return

        if not merchant.stripe_payouts_enabled:
            logger.error("Settlement: merchant %s Stripe payouts not enabled", merchant.merchant_id)
            await self._merchant_repo.update_session(session_id, settlement_status="failed")
            return

        try:

            # Convert stablecoin amount to cents (1 USDC = 100 cents)
            net = session.net_amount if session.net_amount is not None else session.amount
            amount_cents = int(net * 100)

            if amount_cents <= 0:
                logger.error("Settlement: invalid amount for session %s", session_id)
                await self._merchant_repo.update_session(session_id, settlement_status="failed")
                return

            # Create transfer to connected account
            result = await self._stripe_connect.create_transfer(
                account_id=merchant.stripe_account_id,
                amount_cents=amount_cents,
                currency="usd",
                description=f"Sardis settlement for session {session_id}",
                metadata={
                    "sardis_session_id": session_id,
                    "sardis_merchant_id": merchant.merchant_id,
                },
                transfer_group=f"sardis_{session_id}",
            )

            # Track the payout
            from sardis_v2_core.database import Database
            await Database.execute(
                """
                INSERT INTO stripe_connect_payouts
                    (merchant_id, session_id, stripe_transfer_id, amount_cents, currency, status)
                VALUES (
                    (SELECT id FROM merchants WHERE external_id = $1),
                    $2, $3, $4, $5, 'pending'
                )
                """,
                merchant.merchant_id, session_id, result.transfer_id, amount_cents, "usd",
            )

            await self._merchant_repo.update_session(
                session_id,
                status="settled",
                settlement_status="completed",
                settlement_tx_hash=result.transfer_id,
            )

            if self._webhooks and merchant.webhook_url:
                await self._webhooks.deliver(
                    merchant=merchant,
                    event_type="settlement.completed",
                    payload={
                        "session_id": session_id,
                        "amount": str(net),
                        "currency": "USD",
                        "settlement_method": "stripe_connect",
                        "stripe_transfer_id": result.transfer_id,
                    },
                )

            logger.info(
                "Stripe Connect settlement completed for session %s: transfer %s ($%s)",
                session_id, result.transfer_id, f"{net:.2f}",
            )

        except Exception:
            logger.exception("Stripe Connect settlement failed for session %s", session_id)
            await self._merchant_repo.update_session(session_id, settlement_status="failed")

    async def _settle_internal(self, session_id: str, session: Any, merchant: Any) -> None:
        """
        Internal ledger settlement (Protocol v1.1 Section 1.3).

        Both payer and merchant are on Sardis — skip external rail entirely.
        Single DB transaction, ~1ms. This is the PayPal model.
        """
        try:
            await self._merchant_repo.update_session(
                session_id,
                status="settled",
                settlement_status="completed",
                settlement_method="internal_ledger",
            )
            if self._webhooks and merchant.webhook_url:
                await self._webhooks.deliver(
                    merchant=merchant,
                    event_type="settlement.completed",
                    payload={
                        "session_id": session_id,
                        "amount": str(session.amount),
                        "currency": session.currency,
                        "settlement_method": "internal_ledger",
                    },
                )
            logger.info("Internal ledger settlement completed for session %s", session_id)
        except Exception:
            logger.exception("Internal settlement failed for session %s", session_id)
            await self._merchant_repo.update_session(
                session_id, settlement_status="failed"
            )

    async def _settle_tempo(self, session_id: str, session: Any, merchant: Any) -> None:
        """
        Tempo settlement via TIP-20 stablecoin transfer (pathUSD).

        When payer and merchant are both on Tempo, settle via direct
        TIP-20 transfer. When only one party is on Tempo, fall back
        to cross-chain settlement via CCTP.
        """
        try:
            # For USDC merchants on Tempo: funds already in merchant wallet via TIP-20
            if merchant.settlement_preference in ("usdc", "tempo"):
                await self._merchant_repo.update_session(
                    session_id,
                    status="settled",
                    settlement_status="completed",
                    settlement_method="tempo_tip20",
                )
                if self._webhooks and merchant.webhook_url:
                    await self._webhooks.deliver(
                        merchant=merchant,
                        event_type="settlement.completed",
                        payload={
                            "session_id": session_id,
                            "amount": str(session.amount),
                            "currency": session.currency,
                            "settlement_method": "tempo_tip20",
                        },
                    )
                logger.info("Tempo TIP-20 settlement completed for session %s", session_id)
                return

            # Cross-chain: Tempo → Base/Ethereum via CCTP bridge
            logger.warning(
                "Cross-chain Tempo settlement not yet implemented for session %s, "
                "marking for manual review",
                session_id,
            )
            await self._merchant_repo.update_session(
                session_id,
                status="pending_review",
                settlement_status="pending_manual_review",
                settlement_method="tempo_cross_chain_pending",
            )
        except Exception:
            logger.exception("Tempo settlement failed for session %s", session_id)
            await self._merchant_repo.update_session(
                session_id, settlement_status="failed"
            )
