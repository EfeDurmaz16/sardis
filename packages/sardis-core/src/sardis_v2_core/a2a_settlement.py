"""Agent-to-Agent Settlement Engine.

This module handles settlement of escrowed funds between agents:
- On-chain settlement: Transfer from escrow wallet to payee wallet
- Off-chain settlement: Internal ledger transfer for same-platform agents
- Double-entry ledger recording for audit trail

Settlement Flow:
    1. Escrow is in RELEASED state
    2. Settlement engine determines on-chain vs off-chain
    3. Execute transfer (blockchain or ledger)
    4. Record settlement in ledger for audit
    5. Return settlement result

Usage:
    from sardis_v2_core.a2a_settlement import SettlementEngine

    engine = SettlementEngine()

    # Settle escrow on-chain
    result = await engine.settle_on_chain(escrow)

    # Or settle off-chain (internal ledger)
    result = await engine.settle_off_chain(escrow)
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, Literal
from uuid import uuid4

from .a2a_escrow import Escrow, EscrowState
from .database import Database
from .exceptions import (
    SardisValidationError,
    SardisConflictError,
    SardisTransactionFailedError,
)


@dataclass(slots=True)
class SettlementResult:
    """
    Settlement execution result.

    Records the outcome of a settlement operation, including
    transaction hash, settlement type, and ledger entries.
    """
    escrow_id: str
    tx_hash: Optional[str]
    settlement_type: Literal["on_chain", "off_chain"]
    ledger_entries: list[str]
    settled_at: datetime
    payer_agent_id: str
    payee_agent_id: str
    amount: Decimal
    token: str
    chain: str


class SettlementEngine:
    """
    Handles settlement of agent-to-agent escrow payments.

    Supports both on-chain (blockchain transfer) and off-chain
    (internal ledger) settlement paths with full audit trail.
    """

    async def settle_on_chain(self, escrow: Escrow) -> SettlementResult:
        """
        Execute on-chain settlement (blockchain transfer).

        Transfers escrowed funds from escrow wallet to payee's wallet
        on the blockchain. Records the transaction in the ledger.

        Args:
            escrow: Escrow to settle

        Returns:
            SettlementResult with transaction hash

        Raises:
            SardisValidationError: If escrow not in RELEASED state
            SardisTransactionFailedError: If on-chain transfer fails
        """
        # Validate escrow state
        if escrow.state != EscrowState.RELEASED:
            raise SardisValidationError(
                f"Escrow must be in RELEASED state for settlement (current: {escrow.state.value})",
                field="state",
            )

        now = datetime.now(timezone.utc)
        settlement_id = f"settlement_{uuid4().hex[:16]}"

        # TODO: Integrate with chain executor for actual on-chain transfer
        # For now, generate a simulated tx_hash
        # In production, this would call:
        #   tx_hash = await chain_executor.transfer(
        #       from_wallet=escrow_wallet,
        #       to_wallet=payee_wallet,
        #       amount=escrow.amount,
        #       token=escrow.token,
        #       chain=escrow.chain,
        #   )
        tx_hash = f"0x{uuid4().hex}"

        # Record settlement in ledger
        ledger_entries = await self.record_settlement(
            escrow=escrow,
            settlement_tx=tx_hash,
            settlement_type="on_chain",
        )

        # Store settlement record in database
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO settlements (
                    id, escrow_id, settlement_type, tx_hash, amount, token, chain,
                    payer_agent_id, payee_agent_id, settled_at, ledger_entries
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                settlement_id,
                escrow.id,
                "on_chain",
                tx_hash,
                escrow.amount,
                escrow.token,
                escrow.chain,
                escrow.payer_agent_id,
                escrow.payee_agent_id,
                now,
                ledger_entries,
            )

        return SettlementResult(
            escrow_id=escrow.id,
            tx_hash=tx_hash,
            settlement_type="on_chain",
            ledger_entries=ledger_entries,
            settled_at=now,
            payer_agent_id=escrow.payer_agent_id,
            payee_agent_id=escrow.payee_agent_id,
            amount=escrow.amount,
            token=escrow.token,
            chain=escrow.chain,
        )

    async def settle_off_chain(self, escrow: Escrow) -> SettlementResult:
        """
        Execute off-chain settlement (internal ledger transfer).

        Transfers funds via internal ledger without on-chain transaction.
        Used when both agents are on the same platform with internal balances.

        Args:
            escrow: Escrow to settle

        Returns:
            SettlementResult without transaction hash

        Raises:
            SardisValidationError: If escrow not in RELEASED state
        """
        # Validate escrow state
        if escrow.state != EscrowState.RELEASED:
            raise SardisValidationError(
                f"Escrow must be in RELEASED state for settlement (current: {escrow.state.value})",
                field="state",
            )

        now = datetime.now(timezone.utc)
        settlement_id = f"settlement_{uuid4().hex[:16]}"

        # Record off-chain transfer in ledger (double-entry)
        ledger_entries = await self.record_settlement(
            escrow=escrow,
            settlement_tx=settlement_id,
            settlement_type="off_chain",
        )

        # Store settlement record in database
        async with Database.connection() as conn:
            await conn.execute(
                """
                INSERT INTO settlements (
                    id, escrow_id, settlement_type, tx_hash, amount, token, chain,
                    payer_agent_id, payee_agent_id, settled_at, ledger_entries
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                settlement_id,
                escrow.id,
                "off_chain",
                None,  # No on-chain tx_hash for off-chain settlements
                escrow.amount,
                escrow.token,
                escrow.chain,
                escrow.payer_agent_id,
                escrow.payee_agent_id,
                now,
                ledger_entries,
            )

        return SettlementResult(
            escrow_id=escrow.id,
            tx_hash=None,
            settlement_type="off_chain",
            ledger_entries=ledger_entries,
            settled_at=now,
            payer_agent_id=escrow.payer_agent_id,
            payee_agent_id=escrow.payee_agent_id,
            amount=escrow.amount,
            token=escrow.token,
            chain=escrow.chain,
        )

    async def record_settlement(
        self,
        escrow: Escrow,
        settlement_tx: str,
        settlement_type: Literal["on_chain", "off_chain"] = "on_chain",
    ) -> list[str]:
        """
        Record settlement in double-entry ledger.

        Creates ledger entries for both debit (escrow) and credit (payee)
        to maintain a complete audit trail.

        Args:
            escrow: Escrow being settled
            settlement_tx: Transaction hash or settlement ID
            settlement_type: Type of settlement (on_chain or off_chain)

        Returns:
            List of ledger entry IDs created
        """
        now = datetime.now(timezone.utc)
        ledger_entries = []

        async with Database.transaction() as conn:
            # Debit entry: Escrow account (funds leaving escrow)
            debit_entry_id = f"entry_{uuid4().hex[:16]}"
            await conn.execute(
                """
                INSERT INTO ledger_entries_v2 (
                    entry_id, tx_id, account_id, entry_type, amount, currency,
                    chain, chain_tx_hash, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                debit_entry_id,
                settlement_tx,
                f"escrow:{escrow.id}",
                "debit",
                escrow.amount,
                escrow.token,
                escrow.chain,
                settlement_tx if settlement_type == "on_chain" else None,
                {
                    "settlement_type": settlement_type,
                    "escrow_id": escrow.id,
                    "payer_agent_id": escrow.payer_agent_id,
                    "payee_agent_id": escrow.payee_agent_id,
                },
                "confirmed",
                now,
            )
            ledger_entries.append(debit_entry_id)

            # Credit entry: Payee account (funds received)
            credit_entry_id = f"entry_{uuid4().hex[:16]}"
            await conn.execute(
                """
                INSERT INTO ledger_entries_v2 (
                    entry_id, tx_id, account_id, entry_type, amount, currency,
                    chain, chain_tx_hash, metadata, status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                """,
                credit_entry_id,
                settlement_tx,
                f"agent:{escrow.payee_agent_id}",
                "credit",
                escrow.amount,
                escrow.token,
                escrow.chain,
                settlement_tx if settlement_type == "on_chain" else None,
                {
                    "settlement_type": settlement_type,
                    "escrow_id": escrow.id,
                    "payer_agent_id": escrow.payer_agent_id,
                    "payee_agent_id": escrow.payee_agent_id,
                },
                "confirmed",
                now,
            )
            ledger_entries.append(credit_entry_id)

        return ledger_entries

    async def get_settlement(self, escrow_id: str) -> Optional[SettlementResult]:
        """
        Get settlement result for an escrow.

        Args:
            escrow_id: Escrow identifier

        Returns:
            SettlementResult if found, None otherwise
        """
        async with Database.connection() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, escrow_id, settlement_type, tx_hash, amount, token, chain,
                       payer_agent_id, payee_agent_id, settled_at, ledger_entries
                FROM settlements
                WHERE escrow_id = $1
                """,
                escrow_id,
            )

            if not row:
                return None

            return SettlementResult(
                escrow_id=row["escrow_id"],
                tx_hash=row["tx_hash"],
                settlement_type=row["settlement_type"],
                ledger_entries=row["ledger_entries"],
                settled_at=row["settled_at"],
                payer_agent_id=row["payer_agent_id"],
                payee_agent_id=row["payee_agent_id"],
                amount=row["amount"],
                token=row["token"],
                chain=row["chain"],
            )

    async def list_settlements(
        self,
        agent_id: Optional[str] = None,
        settlement_type: Optional[Literal["on_chain", "off_chain"]] = None,
        limit: int = 100,
    ) -> list[SettlementResult]:
        """
        List settlements with optional filters.

        Args:
            agent_id: Filter by payer or payee agent ID
            settlement_type: Filter by settlement type
            limit: Maximum number of results

        Returns:
            List of SettlementResult instances
        """
        query_parts = ["SELECT * FROM settlements WHERE 1=1"]
        params: list = []
        param_idx = 1

        if agent_id:
            query_parts.append(
                f" AND (payer_agent_id = ${param_idx} OR payee_agent_id = ${param_idx})"
            )
            params.append(agent_id)
            param_idx += 1

        if settlement_type:
            query_parts.append(f" AND settlement_type = ${param_idx}")
            params.append(settlement_type)
            param_idx += 1

        query_parts.append(f" ORDER BY settled_at DESC LIMIT ${param_idx}")
        params.append(limit)

        query = "".join(query_parts)

        async with Database.connection() as conn:
            rows = await conn.fetch(query, *params)
            return [
                SettlementResult(
                    escrow_id=row["escrow_id"],
                    tx_hash=row["tx_hash"],
                    settlement_type=row["settlement_type"],
                    ledger_entries=row["ledger_entries"],
                    settled_at=row["settled_at"],
                    payer_agent_id=row["payer_agent_id"],
                    payee_agent_id=row["payee_agent_id"],
                    amount=row["amount"],
                    token=row["token"],
                    chain=row["chain"],
                )
                for row in rows
            ]
