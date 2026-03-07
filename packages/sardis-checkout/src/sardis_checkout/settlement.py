"""Settlement service for merchant checkout payments."""
from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Optional

_CHECKOUT_CHAIN = os.getenv("SARDIS_CHECKOUT_CHAIN", "base")

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
        offramp_service: Optional[Any] = None,
        merchant_webhook_service: Optional[Any] = None,
    ):
        self._merchant_repo = merchant_repo
        self._offramp = offramp_service
        self._webhooks = merchant_webhook_service

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
            from sardis_v2_core.tokens import to_raw_token_amount, TokenType
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
