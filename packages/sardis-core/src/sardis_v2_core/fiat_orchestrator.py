"""End-to-End Fiat Payment Flow Orchestrator.

Orchestrates complete payment flows tying together:
- StripeTreasuryProvider (platform fiat holding)
- StripeIssuingProvider (virtual cards)
- RampRouter (crypto ↔ fiat conversion)
- SubLedgerManager (per-agent balance tracking)

Flow Examples:

1. Agent pays with virtual card (crypto → fiat → card):
   Agent says "Pay $50 to OpenAI"
   → Policy check
   → Off-ramp: USDC → USD via RampRouter
   → Fund Treasury: Fiat arrives in Stripe Treasury
   → Sub-ledger: Credit agent's sub-balance
   → Fund Issuing: Treasury → Issuing balance
   → Sub-ledger: Move from available → held
   → Card payment: Authorization
   → Sub-ledger: Settle transaction
   → Ledger: Record in audit trail

2. Deposit fiat to agent (fiat → sub-ledger):
   Wire/ACH to Sardis Treasury
   → Treasury webhook: received_credit
   → Identify agent from reference/metadata
   → Sub-ledger: Credit agent's sub-balance

3. Agent withdraws to bank (sub-ledger → fiat → bank):
   Agent says "Send $200 to my bank"
   → Policy check
   → Sub-ledger: Debit available balance
   → Treasury: Create outbound payment
   → Record in audit trail
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal, Optional

from .stripe_treasury import StripeTreasuryProvider
from .sub_ledger import SubLedgerManager

logger = logging.getLogger(__name__)


@dataclass
class FiatPaymentResult:
    """Result of a fiat payment flow operation."""
    status: Literal["completed", "pending", "failed"]
    flow: str  # "card_payment", "deposit", "withdrawal", "crypto_fund"
    agent_id: str
    amount: Decimal
    reference_id: str = ""
    description: str = ""
    sub_ledger_tx_id: str = ""
    treasury_tx_id: str = ""
    card_tx_id: str = ""
    ramp_session_id: str = ""
    error: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class FiatPaymentOrchestrator:
    """Orchestrates end-to-end fiat payment flows for AI agents.

    Ties together:
    - StripeTreasuryProvider (platform fiat holding)
    - StripeIssuingProvider (virtual cards)
    - RampRouter (crypto ↔ fiat conversion)
    - SubLedgerManager (per-agent balance tracking)

    Architecture:
    - Platform has 1 Stripe Treasury Financial Account
    - Each agent has a sub-ledger account tracking their portion
    - Cards are funded from Treasury via Issuing balance
    - All operations maintain sub-ledger consistency

    Usage:
        treasury = StripeTreasuryProvider(...)
        sub_ledger = SubLedgerManager(treasury)
        ramp_router = RampRouter([...])
        issuing = StripeIssuingProvider(...)

        orchestrator = FiatPaymentOrchestrator(
            treasury=treasury,
            sub_ledger=sub_ledger,
            ramp_router=ramp_router,
            issuing_provider=issuing,
        )

        # Fund card from crypto
        result = await orchestrator.fund_card_from_crypto(
            agent_id="agent_123",
            amount_usd=Decimal("50.00"),
            wallet_address="0x...",
        )

        # Pay with card
        result = await orchestrator.pay_with_card(
            agent_id="agent_123",
            amount_usd=Decimal("25.00"),
            card_id="card_xyz",
        )
    """

    def __init__(
        self,
        treasury: StripeTreasuryProvider,
        sub_ledger: SubLedgerManager,
        ramp_router: Optional[object] = None,  # RampRouter type hint avoided for circular import
        issuing_provider: Optional[object] = None,  # StripeIssuingProvider
    ):
        """Initialize the fiat payment orchestrator.

        Args:
            treasury: Platform Stripe Treasury provider
            sub_ledger: Sub-ledger manager for per-agent balances
            ramp_router: Optional RampRouter for crypto ↔ fiat conversion
            issuing_provider: Optional StripeIssuingProvider for virtual cards
        """
        self._treasury = treasury
        self._sub_ledger = sub_ledger
        self._ramp_router = ramp_router
        self._issuing = issuing_provider
        logger.info("FiatPaymentOrchestrator initialized")

    async def pay_with_card(
        self,
        agent_id: str,
        amount_usd: Decimal,
        card_id: str,
        description: str = "",
    ) -> FiatPaymentResult:
        """Execute card payment flow: ensure funds, authorize card.

        Flow:
        1. Check sub-ledger available balance
        2. Move funds from available → held
        3. Fund Issuing balance (if needed)
        4. Card authorization happens via webhook
        5. Settle transaction in sub-ledger

        Args:
            agent_id: Agent identifier
            amount_usd: Payment amount in USD
            card_id: Card identifier to use
            description: Payment description

        Returns:
            FiatPaymentResult with status and transaction IDs
        """
        logger.info(
            "Starting card payment flow: agent=%s, amount=$%s, card=%s",
            agent_id, amount_usd, card_id,
        )

        try:
            # 1. Check agent has sufficient balance
            account = await self._sub_ledger.get_balance(agent_id)
            if account.available_balance < amount_usd:
                error_msg = (
                    f"Insufficient balance: ${account.available_balance} < ${amount_usd}"
                )
                logger.warning(error_msg)
                return FiatPaymentResult(
                    status="failed",
                    flow="card_payment",
                    agent_id=agent_id,
                    amount=amount_usd,
                    error=error_msg,
                )

            # 2. Move funds from available to held
            tx = await self._sub_ledger.fund_card(
                agent_id=agent_id,
                amount=amount_usd,
                card_id=card_id,
            )
            logger.info("Funds held in sub-ledger: tx_id=%s", tx.tx_id)

            # 3. Fund Issuing balance from Treasury (if needed)
            try:
                issuing_transfer = await self._treasury.fund_issuing_balance(
                    amount=amount_usd,
                    description=f"Fund card {card_id} for agent {agent_id}",
                )
                logger.info("Issuing balance funded: %s", issuing_transfer.id)
                treasury_tx_id = issuing_transfer.id
            except Exception as e:
                logger.error("Failed to fund Issuing balance: %s", e)
                # Rollback: release held funds
                await self._sub_ledger.release_card_hold(
                    agent_id=agent_id,
                    amount=amount_usd,
                    card_id=card_id,
                )
                return FiatPaymentResult(
                    status="failed",
                    flow="card_payment",
                    agent_id=agent_id,
                    amount=amount_usd,
                    error=f"Failed to fund Issuing balance: {e}",
                )

            # 4. Card authorization will happen via Stripe webhook
            # The actual payment is processed by StripeIssuingProvider
            # This orchestrator just ensures funds are available

            return FiatPaymentResult(
                status="pending",
                flow="card_payment",
                agent_id=agent_id,
                amount=amount_usd,
                reference_id=card_id,
                description=description or f"Card payment via {card_id}",
                sub_ledger_tx_id=tx.tx_id,
                treasury_tx_id=treasury_tx_id,
                card_tx_id=card_id,
            )

        except Exception as e:
            logger.error("Card payment flow failed: %s", e)
            return FiatPaymentResult(
                status="failed",
                flow="card_payment",
                agent_id=agent_id,
                amount=amount_usd,
                error=str(e),
            )

    async def deposit_fiat(
        self,
        agent_id: str,
        amount_usd: Decimal,
        reference_id: str,
        source: str = "wire",
    ) -> FiatPaymentResult:
        """Record fiat deposit to agent's sub-ledger account.

        Flow:
        1. Verify agent account exists (create if needed)
        2. Credit sub-ledger available balance
        3. Record in audit trail

        Args:
            agent_id: Agent identifier
            amount_usd: Deposit amount in USD
            reference_id: External reference (e.g., wire transfer ID)
            source: Deposit source ("wire", "ach", "stripe_balance")

        Returns:
            FiatPaymentResult with status and transaction IDs
        """
        logger.info(
            "Starting fiat deposit flow: agent=%s, amount=$%s, source=%s",
            agent_id, amount_usd, source,
        )

        try:
            # 1. Ensure agent account exists
            account = await self._sub_ledger.get_account(agent_id)
            if not account:
                logger.info("Creating sub-ledger account for agent %s", agent_id)
                account = await self._sub_ledger.create_account(agent_id)

            # 2. Credit sub-ledger
            tx = await self._sub_ledger.deposit(
                agent_id=agent_id,
                amount=amount_usd,
                reference_id=reference_id,
                description=f"Deposit via {source}",
                metadata={"source": source},
            )
            logger.info(
                "Deposit completed: agent=%s, amount=$%s, new_balance=$%s",
                agent_id, amount_usd, account.available_balance + amount_usd,
            )

            return FiatPaymentResult(
                status="completed",
                flow="deposit",
                agent_id=agent_id,
                amount=amount_usd,
                reference_id=reference_id,
                description=f"Deposit via {source}",
                sub_ledger_tx_id=tx.tx_id,
            )

        except Exception as e:
            logger.error("Deposit flow failed: %s", e)
            return FiatPaymentResult(
                status="failed",
                flow="deposit",
                agent_id=agent_id,
                amount=amount_usd,
                error=str(e),
            )

    async def withdraw_to_bank(
        self,
        agent_id: str,
        amount_usd: Decimal,
        destination_account: str,
        description: str = "",
    ) -> FiatPaymentResult:
        """Withdraw from agent's sub-ledger to external bank.

        Flow:
        1. Check sub-ledger available balance
        2. Debit sub-ledger
        3. Create Treasury outbound payment
        4. Record in audit trail

        Args:
            agent_id: Agent identifier
            amount_usd: Withdrawal amount in USD
            destination_account: Bank account identifier (Stripe PaymentMethod ID)
            description: Withdrawal description

        Returns:
            FiatPaymentResult with status and transaction IDs
        """
        logger.info(
            "Starting withdrawal flow: agent=%s, amount=$%s, destination=%s",
            agent_id, amount_usd, destination_account,
        )

        try:
            # 1. Check sufficient balance
            account = await self._sub_ledger.get_balance(agent_id)
            if account.available_balance < amount_usd:
                error_msg = (
                    f"Insufficient balance: ${account.available_balance} < ${amount_usd}"
                )
                logger.warning(error_msg)
                return FiatPaymentResult(
                    status="failed",
                    flow="withdrawal",
                    agent_id=agent_id,
                    amount=amount_usd,
                    error=error_msg,
                )

            # 2. Debit sub-ledger first (fail-closed)
            tx = await self._sub_ledger.withdraw(
                agent_id=agent_id,
                amount=amount_usd,
                reference_id=destination_account,
                description=description or f"Withdrawal to {destination_account}",
            )
            logger.info("Sub-ledger debited: tx_id=%s", tx.tx_id)

            # 3. Create Treasury outbound payment
            try:
                payment = await self._treasury.create_outbound_payment(
                    amount=amount_usd,
                    destination_account=destination_account,
                    destination_type="ach",  # Default to ACH
                    description=description or f"Withdrawal for agent {agent_id}",
                    metadata={"agent_id": agent_id, "sub_ledger_tx_id": tx.tx_id},
                )
                logger.info("Treasury outbound payment created: %s", payment.id)

                return FiatPaymentResult(
                    status="pending",
                    flow="withdrawal",
                    agent_id=agent_id,
                    amount=amount_usd,
                    reference_id=destination_account,
                    description=description or f"Withdrawal to bank",
                    sub_ledger_tx_id=tx.tx_id,
                    treasury_tx_id=payment.id,
                )

            except Exception as e:
                logger.error("Treasury payment failed, rolling back sub-ledger: %s", e)
                # Rollback: credit the amount back
                await self._sub_ledger.deposit(
                    agent_id=agent_id,
                    amount=amount_usd,
                    reference_id=f"rollback_{tx.tx_id}",
                    description=f"Rollback failed withdrawal: {e}",
                )
                return FiatPaymentResult(
                    status="failed",
                    flow="withdrawal",
                    agent_id=agent_id,
                    amount=amount_usd,
                    error=f"Treasury payment failed: {e}",
                )

        except Exception as e:
            logger.error("Withdrawal flow failed: %s", e)
            return FiatPaymentResult(
                status="failed",
                flow="withdrawal",
                agent_id=agent_id,
                amount=amount_usd,
                error=str(e),
            )

    async def fund_card_from_crypto(
        self,
        agent_id: str,
        amount_usd: Decimal,
        wallet_address: str,
        chain: str = "base",
    ) -> FiatPaymentResult:
        """Off-ramp crypto and fund card: USDC → fiat → card.

        Flow:
        1. Off-ramp: USDC → USD via RampRouter
        2. Wait for fiat to arrive in Treasury
        3. Credit agent's sub-ledger
        4. Fund Issuing balance
        5. Agent can now use card

        Args:
            agent_id: Agent identifier
            amount_usd: Amount in USD to fund
            wallet_address: Agent's wallet address with USDC
            chain: Blockchain (default: "base")

        Returns:
            FiatPaymentResult with status and transaction IDs
        """
        logger.info(
            "Starting crypto-to-card funding: agent=%s, amount=$%s, chain=%s",
            agent_id, amount_usd, chain,
        )

        if not self._ramp_router:
            return FiatPaymentResult(
                status="failed",
                flow="crypto_fund",
                agent_id=agent_id,
                amount=amount_usd,
                error="RampRouter not configured",
            )

        try:
            # 1. Create off-ramp session
            # In production, this would get bank account from Treasury
            bank_account = {
                "account_number": "placeholder",
                "routing_number": "placeholder",
            }

            ramp_session = await self._ramp_router.get_best_offramp(
                amount_crypto=amount_usd,  # 1:1 for USDC
                crypto_currency="USDC",
                chain=chain,
                fiat_currency="USD",
                bank_account=bank_account,
                wallet_id=agent_id,
                metadata={"purpose": "card_funding"},
            )
            logger.info(
                "Off-ramp session created: %s via %s",
                ramp_session.session_id, ramp_session.provider,
            )

            # 2. Only settle balances once provider reports completion.
            # Pending/processing sessions must wait for webhook-driven treasury credit.
            ramp_status_raw = getattr(ramp_session, "status", "pending")
            ramp_status = str(getattr(ramp_status_raw, "value", ramp_status_raw)).strip().lower()
            if ramp_status != "completed":
                logger.info(
                    "Off-ramp session pending settlement: session=%s status=%s",
                    ramp_session.session_id,
                    ramp_status,
                )
                return FiatPaymentResult(
                    status="pending",
                    flow="crypto_fund",
                    agent_id=agent_id,
                    amount=amount_usd,
                    reference_id=wallet_address,
                    description=f"Off-ramp session created; waiting for settlement ({ramp_status})",
                    ramp_session_id=ramp_session.session_id,
                )

            # 3. Ensure agent account exists
            account = await self._sub_ledger.get_account(agent_id)
            if not account:
                logger.info("Creating sub-ledger account for agent %s", agent_id)
                account = await self._sub_ledger.create_account(agent_id)

            # 4. Credit sub-ledger
            tx = await self._sub_ledger.deposit(
                agent_id=agent_id,
                amount=amount_usd,
                reference_id=ramp_session.session_id,
                description=f"Crypto off-ramp from {chain}",
                metadata={
                    "ramp_provider": ramp_session.provider,
                    "chain": chain,
                    "wallet_address": wallet_address,
                },
            )
            logger.info("Sub-ledger credited from off-ramp: tx_id=%s", tx.tx_id)

            # 5. Fund Issuing balance
            try:
                issuing_transfer = await self._treasury.fund_issuing_balance(
                    amount=amount_usd,
                    description=f"Fund card for agent {agent_id}",
                )
                logger.info("Issuing balance funded: %s", issuing_transfer.id)

                return FiatPaymentResult(
                    status="completed",
                    flow="crypto_fund",
                    agent_id=agent_id,
                    amount=amount_usd,
                    reference_id=wallet_address,
                    description=f"Funded from crypto on {chain}",
                    sub_ledger_tx_id=tx.tx_id,
                    treasury_tx_id=issuing_transfer.id,
                    ramp_session_id=ramp_session.session_id,
                )

            except Exception as e:
                logger.error("Failed to fund Issuing balance: %s", e)
                # Sub-ledger already credited, so funds are available
                # Just return pending status
                return FiatPaymentResult(
                    status="pending",
                    flow="crypto_fund",
                    agent_id=agent_id,
                    amount=amount_usd,
                    reference_id=wallet_address,
                    description=f"Funded from crypto, pending Issuing transfer",
                    sub_ledger_tx_id=tx.tx_id,
                    ramp_session_id=ramp_session.session_id,
                    error=f"Issuing funding failed: {e}",
                )

        except Exception as e:
            logger.error("Crypto funding flow failed: %s", e)
            return FiatPaymentResult(
                status="failed",
                flow="crypto_fund",
                agent_id=agent_id,
                amount=amount_usd,
                error=str(e),
            )

    async def get_agent_summary(
        self,
        agent_id: str,
    ) -> dict:
        """Get comprehensive agent financial summary.

        Returns:
            Dictionary with:
            - agent_id
            - sub_ledger_balance (available, pending, held, total)
            - recent_transactions
            - treasury_status
        """
        logger.info("Fetching agent summary: %s", agent_id)

        try:
            # Get sub-ledger account
            account = await self._sub_ledger.get_balance(agent_id)

            # Get recent transactions
            transactions = await self._sub_ledger.get_transactions(
                agent_id=agent_id,
                limit=10,
            )

            # Get Treasury balance (platform level)
            treasury_balance = await self._treasury.get_balance()

            summary = {
                "agent_id": agent_id,
                "sub_ledger": {
                    "available": float(account.available_balance),
                    "pending": float(account.pending_balance),
                    "held": float(account.held_balance),
                    "total": float(account.total_balance),
                    "currency": account.currency,
                },
                "recent_transactions": [
                    {
                        "tx_id": tx.tx_id,
                        "type": tx.tx_type.value,
                        "amount": float(tx.amount),
                        "balance_after": float(tx.balance_after),
                        "description": tx.description,
                        "created_at": tx.created_at.isoformat(),
                    }
                    for tx in transactions
                ],
                "treasury_status": {
                    "available": float(treasury_balance.available),
                    "pending_inbound": float(treasury_balance.pending_inbound),
                    "pending_outbound": float(treasury_balance.pending_outbound),
                },
            }

            return summary

        except Exception as e:
            logger.error("Failed to get agent summary: %s", e)
            return {
                "agent_id": agent_id,
                "error": str(e),
            }

    async def handle_treasury_credit(
        self,
        event_data: dict,
    ) -> Optional[FiatPaymentResult]:
        """Handle incoming Treasury credit webhook - auto-credit agent.

        When fiat arrives in Treasury (wire/ACH), this webhook fires.
        We extract the agent_id from metadata and credit their sub-ledger.

        Args:
            event_data: Treasury webhook event data

        Returns:
            FiatPaymentResult if agent credited, None if not applicable
        """
        logger.info("Handling Treasury credit webhook: %s", event_data.get("id"))

        try:
            # Extract amount and metadata
            amount = Decimal(str(event_data.get("amount", 0))) / 100
            metadata = event_data.get("metadata", {})
            reference_id = event_data.get("id", "")

            # Extract agent_id from metadata
            agent_id = metadata.get("agent_id")
            if not agent_id:
                logger.warning("No agent_id in Treasury credit metadata, skipping")
                return None

            # Credit agent's sub-ledger
            result = await self.deposit_fiat(
                agent_id=agent_id,
                amount_usd=amount,
                reference_id=reference_id,
                source=event_data.get("source_type", "wire"),
            )

            logger.info(
                "Treasury credit processed: agent=%s, amount=$%s, status=%s",
                agent_id, amount, result.status,
            )

            return result

        except Exception as e:
            logger.error("Failed to handle Treasury credit: %s", e)
            return None

    async def settle_card_transaction(
        self,
        agent_id: str,
        amount_usd: Decimal,
        card_id: str,
        card_tx_id: str,
    ) -> FiatPaymentResult:
        """Settle a card transaction in the sub-ledger.

        Called after card authorization is settled by Stripe.
        Moves funds from held → settled (deducted from balance).

        Args:
            agent_id: Agent identifier
            amount_usd: Transaction amount
            card_id: Card identifier
            card_tx_id: Card transaction ID

        Returns:
            FiatPaymentResult with settlement status
        """
        logger.info(
            "Settling card transaction: agent=%s, amount=$%s, tx=%s",
            agent_id, amount_usd, card_tx_id,
        )

        try:
            # Settle in sub-ledger (deduct from held balance)
            tx = await self._sub_ledger.settle_card_transaction(
                agent_id=agent_id,
                amount=amount_usd,
                card_id=card_id,
                tx_id=card_tx_id,
            )

            logger.info("Card transaction settled: sub_ledger_tx=%s", tx.tx_id)

            return FiatPaymentResult(
                status="completed",
                flow="card_settlement",
                agent_id=agent_id,
                amount=amount_usd,
                reference_id=card_tx_id,
                description=f"Settled card transaction {card_tx_id}",
                sub_ledger_tx_id=tx.tx_id,
                card_tx_id=card_tx_id,
            )

        except Exception as e:
            logger.error("Card settlement failed: %s", e)
            return FiatPaymentResult(
                status="failed",
                flow="card_settlement",
                agent_id=agent_id,
                amount=amount_usd,
                error=str(e),
            )
