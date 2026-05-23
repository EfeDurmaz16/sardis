"""Inbound payment service — orchestrates deposit lifecycle.

Flow: External Payer → Agent Wallet (on-chain) → AML Screen → Ledger Credit → Webhook
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .database import Database
from .webhooks import (
    EventType,
    create_deposit_event,
)

logger = logging.getLogger(__name__)


class InboundPaymentService:
    """Core orchestration service for inbound deposits."""

    def __init__(
        self,
        event_bus: Any,
        ledger: Any,
        sanctions_service: Any,
        wallet_repo: Any,
        deposit_monitor: Any | None = None,
    ):
        self._event_bus = event_bus
        self._ledger = ledger
        self._sanctions = sanctions_service
        self._wallet_repo = wallet_repo
        self._deposit_monitor = deposit_monitor

    # ------------------------------------------------------------------
    # DepositMonitor callback — main entry point
    # ------------------------------------------------------------------
    async def on_deposit_callback(self, deposit: Any) -> None:
        """DepositMonitor callback. Handles full deposit lifecycle.

        Called by DepositMonitor when a deposit is detected or confirmed.
        """
        status = deposit.status.value if hasattr(deposit.status, "value") else str(deposit.status)

        if status == "detected":
            await self._handle_detected(deposit)
        elif status in ("confirmed", "confirming"):
            await self._handle_confirmed(deposit)

    # ------------------------------------------------------------------
    # DETECTED phase — persist + emit
    # ------------------------------------------------------------------
    async def _handle_detected(self, deposit: Any) -> None:
        """Persist deposit to DB and emit DEPOSIT_DETECTED."""
        wallet_id, agent_id = await self._resolve_wallet(deposit.to_address)
        amount_str = str(deposit.amount_decimal) if hasattr(deposit, "amount_decimal") else str(
            Decimal(deposit.amount_minor) / Decimal(10 ** deposit.decimals)
        )

        await Database.execute(
            """
            INSERT INTO deposits (
                deposit_id, tx_hash, chain, token, from_address, to_address,
                amount_minor, amount, decimals, block_number, confirmations,
                status, agent_id, wallet_id, detected_at, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11,
                'detected', $12, $13, $14, NOW()
            )
            ON CONFLICT (deposit_id) DO NOTHING
            """,
            deposit.deposit_id,
            deposit.tx_hash,
            deposit.chain,
            deposit.token,
            deposit.from_address,
            deposit.to_address,
            deposit.amount_minor,
            amount_str,
            deposit.decimals,
            getattr(deposit, "block_number", None),
            getattr(deposit, "confirmations", 0),
            agent_id,
            wallet_id,
            getattr(deposit, "detected_at", datetime.now(UTC)),
        )

        if self._event_bus:
            event = create_deposit_event(
                event_type=EventType.DEPOSIT_DETECTED,
                deposit_id=deposit.deposit_id,
                wallet_id=wallet_id or "",
                agent_id=agent_id or "",
                tx_hash=deposit.tx_hash,
                chain=deposit.chain,
                token=deposit.token,
                amount=Decimal(amount_str),
                from_address=deposit.from_address,
                to_address=deposit.to_address,
                status="detected",
                confirmations=getattr(deposit, "confirmations", 0),
            )
            await self._event_bus.emit(
                EventType.DEPOSIT_DETECTED,
                event.data,
                agent_id=agent_id,
                fire_and_forget=True,
            )

        logger.info(
            "Deposit detected id=%s tx=%s chain=%s amount=%s %s → %s",
            deposit.deposit_id,
            deposit.tx_hash,
            deposit.chain,
            amount_str,
            deposit.token,
            deposit.to_address,
        )

    # ------------------------------------------------------------------
    # CONFIRMED phase — AML screen, ledger credit, reconcile, emit
    # ------------------------------------------------------------------
    async def _handle_confirmed(self, deposit: Any) -> None:
        """AML screen sender, create CREDIT ledger entry, reconcile invoices."""
        wallet_id, agent_id = await self._resolve_wallet(deposit.to_address)
        amount_str = str(deposit.amount_decimal) if hasattr(deposit, "amount_decimal") else str(
            Decimal(deposit.amount_minor) / Decimal(10 ** deposit.decimals)
        )

        # 1. AML screening (fail-closed)
        aml_ok, aml_result, aml_details = await self._screen_sender(
            deposit.from_address, deposit.chain
        )
        if not aml_ok:
            await Database.execute(
                """
                UPDATE deposits SET
                    status = 'failed',
                    aml_screening_result = $2,
                    aml_screening_details = $3::jsonb
                WHERE deposit_id = $1
                """,
                deposit.deposit_id,
                aml_result,
                _json_str(aml_details),
            )
            # Emit compliance alert
            if self._event_bus:
                await self._event_bus.emit(
                    EventType.COMPLIANCE_ALERT,
                    {
                        "alert_type": "deposit_aml_block",
                        "deposit_id": deposit.deposit_id,
                        "from_address": deposit.from_address,
                        "chain": deposit.chain,
                        "screening_result": aml_result,
                    },
                    agent_id=agent_id,
                    fire_and_forget=True,
                )
            logger.warning(
                "Deposit AML blocked id=%s from=%s result=%s",
                deposit.deposit_id,
                deposit.from_address,
                aml_result,
            )
            return

        # 2. Create CREDIT ledger entry
        ledger_entry_id = await self._create_credit_entry(
            deposit, wallet_id, agent_id, amount_str
        )

        # 3. Auto-reconcile with payment requests
        payment_request_id = await self._auto_reconcile(
            deposit, wallet_id, amount_str
        )

        # 4. Update deposit record → credited
        now = datetime.now(UTC)
        await Database.execute(
            """
            UPDATE deposits SET
                status = 'credited',
                agent_id = $2,
                wallet_id = $3,
                confirmations = $4,
                confirmed_at = $5,
                credited_at = $6,
                ledger_entry_id = $7,
                payment_request_id = $8,
                aml_screening_result = $9,
                aml_screening_details = $10::jsonb
            WHERE deposit_id = $1
            """,
            deposit.deposit_id,
            agent_id,
            wallet_id,
            getattr(deposit, "confirmations", 1),
            getattr(deposit, "confirmed_at", now),
            now,
            ledger_entry_id,
            payment_request_id,
            aml_result,
            _json_str(aml_details),
        )

        # 5. Mark credited in DepositMonitor
        if self._deposit_monitor:
            self._deposit_monitor.mark_credited(deposit.deposit_id)

        # 6. Emit events: DEPOSIT_CONFIRMED + WALLET_FUNDED + PAYMENT_RECEIVED
        if self._event_bus:
            base_kwargs = {
                "deposit_id": deposit.deposit_id,
                "wallet_id": wallet_id or "",
                "agent_id": agent_id or "",
                "tx_hash": deposit.tx_hash,
                "chain": deposit.chain,
                "token": deposit.token,
                "amount": Decimal(amount_str),
                "from_address": deposit.from_address,
                "to_address": deposit.to_address,
                "confirmations": getattr(deposit, "confirmations", 1),
                "payment_request_id": payment_request_id,
                "ledger_entry_id": ledger_entry_id,
            }

            for evt_type in (
                EventType.DEPOSIT_CONFIRMED,
                EventType.WALLET_FUNDED,
                EventType.PAYMENT_RECEIVED,
            ):
                event = create_deposit_event(
                    event_type=evt_type, status="credited", **base_kwargs
                )
                await self._event_bus.emit(
                    evt_type,
                    event.data,
                    agent_id=agent_id,
                    fire_and_forget=True,
                )

        logger.info(
            "Deposit credited id=%s tx=%s ledger=%s reconciled=%s",
            deposit.deposit_id,
            deposit.tx_hash,
            ledger_entry_id,
            payment_request_id or "none",
        )

    # ------------------------------------------------------------------
    # AML screening (fail-closed)
    # ------------------------------------------------------------------
    async def _screen_sender(
        self, from_address: str, chain: str
    ) -> tuple[bool, str, dict]:
        """Fail-closed AML. If screening fails → block deposit."""
        if not self._sanctions:
            # No sanctions service → fail closed in production
            logger.warning("No sanctions service configured — blocking deposit (fail-closed)")
            return False, "no_sanctions_service", {}

        try:
            result = await self._sanctions.screen_address(from_address, chain=chain)
            if result.should_block:
                return (
                    False,
                    f"blocked:{result.risk_level.value if hasattr(result.risk_level, 'value') else result.risk_level}",
                    {
                        "risk_level": str(result.risk_level.value if hasattr(result.risk_level, 'value') else result.risk_level),
                        "is_sanctioned": result.is_sanctioned,
                        "matches": [str(m) for m in (result.matches or [])],
                    },
                )
            return (
                True,
                f"clear:{result.risk_level.value if hasattr(result.risk_level, 'value') else result.risk_level}",
                {
                    "risk_level": str(result.risk_level.value if hasattr(result.risk_level, 'value') else result.risk_level),
                    "is_sanctioned": False,
                },
            )
        except Exception as e:
            logger.error("AML screening failed for %s: %s — blocking (fail-closed)", from_address, e)
            return False, "screening_error", {"error": str(e)}

    # ------------------------------------------------------------------
    # Ledger CREDIT entry
    # ------------------------------------------------------------------
    async def _create_credit_entry(
        self,
        deposit: Any,
        wallet_id: str | None,
        agent_id: str | None,
        amount_str: str,
    ) -> str | None:
        """Create a CREDIT ledger entry for the deposit."""
        if not self._ledger:
            return None

        try:

            entry_id = f"le_{uuid4().hex[:16]}"
            account_id = wallet_id or agent_id or deposit.to_address

            # Use ledger_entries_v2 directly for full-precision CREDIT
            await Database.execute(
                """
                INSERT INTO ledger_entries_v2 (
                    entry_id, tx_id, account_id, entry_type, amount, fee,
                    currency, chain, chain_tx_hash, block_number,
                    status, metadata, created_at
                ) VALUES (
                    $1, $2, $3, 'CREDIT', $4, 0, $5, $6, $7, $8,
                    'confirmed', $9::jsonb, NOW()
                )
                """,
                entry_id,
                f"deposit:{deposit.deposit_id}",
                account_id,
                Decimal(amount_str),
                deposit.token,
                deposit.chain,
                deposit.tx_hash,
                getattr(deposit, "block_number", None),
                _json_str({
                    "source": "inbound_deposit",
                    "deposit_id": deposit.deposit_id,
                    "from_address": deposit.from_address,
                }),
            )
            return entry_id
        except Exception as e:
            logger.error("Failed to create ledger CREDIT for deposit %s: %s", deposit.deposit_id, e)
            return None

    # ------------------------------------------------------------------
    # Auto-reconciliation with payment requests
    # ------------------------------------------------------------------
    async def _auto_reconcile(
        self,
        deposit: Any,
        wallet_id: str | None,
        amount_str: str,
    ) -> str | None:
        """Match deposit to pending payment_requests by address+amount+token."""
        if not wallet_id:
            return None

        try:
            row = await Database.fetchrow(
                """
                SELECT request_id, invoice_id FROM payment_requests
                WHERE receive_address = $1
                  AND token = $2
                  AND amount = $3
                  AND status = 'pending'
                ORDER BY created_at ASC
                LIMIT 1
                """,
                deposit.to_address,
                deposit.token,
                amount_str,
            )
            if not row:
                return None

            request_id = row["request_id"]
            now = datetime.now(UTC)

            await Database.execute(
                """
                UPDATE payment_requests SET
                    status = 'fulfilled',
                    amount_received = $2,
                    deposit_id = $3,
                    updated_at = $4
                WHERE request_id = $1
                """,
                request_id,
                amount_str,
                deposit.deposit_id,
                now,
            )

            # Auto-reconcile linked invoice
            invoice_id = row.get("invoice_id")
            if invoice_id:
                await reconcile_invoice_with_deposit(
                    invoice_id=invoice_id,
                    amount_paid=amount_str,
                    deposit_id=deposit.deposit_id,
                )

            logger.info(
                "Payment request %s reconciled with deposit %s",
                request_id,
                deposit.deposit_id,
            )
            return request_id

        except Exception as e:
            logger.error("Auto-reconciliation failed for deposit %s: %s", deposit.deposit_id, e)
            return None

    # ------------------------------------------------------------------
    # Wallet address resolution
    # ------------------------------------------------------------------
    async def _resolve_wallet(self, address: str) -> tuple[str | None, str | None]:
        """Resolve wallet_id and agent_id from an on-chain address."""
        try:
            row = await Database.fetchrow(
                """
                SELECT w.external_id AS wallet_id, a.external_id AS agent_id
                FROM wallets w
                JOIN agents a ON w.agent_id = a.id
                WHERE w.addresses::text LIKE $1
                LIMIT 1
                """,
                f"%{address}%",
            )
            if row:
                return row["wallet_id"], row["agent_id"]
        except Exception as e:
            logger.warning("Failed to resolve wallet for address %s: %s", address, e)
        return None, None

    # ------------------------------------------------------------------
    # Startup registration
    # ------------------------------------------------------------------
    async def register_wallet_addresses(self) -> int:
        """Startup: load all wallets and register with DepositMonitor."""
        if not self._deposit_monitor:
            return 0

        try:
            rows = await Database.fetch(
                "SELECT external_id, addresses, agent_id FROM wallets WHERE is_active = TRUE"
            )
            count = 0
            for row in rows:
                addresses = row.get("addresses") or {}
                if isinstance(addresses, str):
                    import json
                    addresses = json.loads(addresses)
                agent_ext = await Database.fetchval(
                    "SELECT external_id FROM agents WHERE id = $1",
                    row["agent_id"],
                )
                for chain, addr in addresses.items():
                    if addr:
                        self._deposit_monitor.add_receive_address(
                            address=addr,
                            agent_id=agent_ext or str(row["agent_id"]),
                            chains=[chain],
                        )
                        count += 1
            logger.info("Registered %d wallet addresses with DepositMonitor", count)
            return count
        except Exception as e:
            logger.error("Failed to register wallet addresses: %s", e)
            return 0

    async def register_single_wallet(self, wallet: Any) -> None:
        """Called when a new wallet is created — register with DepositMonitor."""
        if not self._deposit_monitor:
            return

        addresses = wallet.addresses if hasattr(wallet, "addresses") else {}
        agent_id = wallet.agent_id if hasattr(wallet, "agent_id") else ""
        for chain, addr in addresses.items():
            if addr:
                self._deposit_monitor.add_receive_address(
                    address=addr,
                    agent_id=agent_id,
                    chains=[chain],
                )
        logger.debug("Registered new wallet %s with DepositMonitor", getattr(wallet, "wallet_id", ""))


# ------------------------------------------------------------------
# Invoice auto-reconciliation (standalone function for reuse)
# ------------------------------------------------------------------
async def reconcile_invoice_with_deposit(
    invoice_id: str,
    amount_paid: str,
    deposit_id: str,
) -> bool:
    """Reconcile an invoice with a confirmed deposit.

    Updates invoice status from pending → paid when deposit amount matches.
    """
    try:
        row = await Database.fetchrow(
            "SELECT invoice_id, amount, status FROM invoices WHERE invoice_id = $1",
            invoice_id,
        )
        if not row:
            logger.warning("Invoice %s not found for reconciliation", invoice_id)
            return False

        if row["status"] == "paid":
            return True  # Already paid

        now = datetime.now(UTC)
        invoice_amount = Decimal(row["amount"])
        paid_amount = Decimal(amount_paid)

        new_status = "paid" if paid_amount >= invoice_amount else "partial"

        await Database.execute(
            """
            UPDATE invoices SET
                status = $2,
                amount_paid = $3,
                paid_at = $4,
                updated_at = $5
            WHERE invoice_id = $1
            """,
            invoice_id,
            new_status,
            amount_paid,
            now if new_status == "paid" else None,
            now,
        )
        logger.info(
            "Invoice %s reconciled → %s (paid=%s, deposit=%s)",
            invoice_id,
            new_status,
            amount_paid,
            deposit_id,
        )
        return True
    except Exception as e:
        logger.error("Invoice reconciliation failed for %s: %s", invoice_id, e)
        return False


def _json_str(data: dict) -> str:
    """Serialize dict to JSON string for JSONB columns."""
    import json
    return json.dumps(data, default=str)
