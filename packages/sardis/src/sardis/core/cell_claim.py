"""CellClaimAlgorithm -- UTXO-style cell selection for agent payments.

Claims funding cells for payment objects using greedy selection with
``SELECT ... FOR UPDATE SKIP LOCKED`` to prevent concurrent claims on the
same cells.  This is the hot path for every agent payment:

    1. Query AVAILABLE cells by currency, ordered by value DESC
    2. Lock rows with SKIP LOCKED (non-blocking concurrency)
    3. Greedily select cells until the requested amount is covered
    4. If the last cell exceeds the remaining amount, split it
    5. Mark selected cells as CLAIMED with the mandate_id
    6. Return the claimed cells

The algorithm intentionally selects *largest first* so that fewer cells are
consumed per payment, reducing row-lock contention under load.

Usage::

    algo = CellClaimAlgorithm(pool)
    cells = await algo.claim_cells(
        mandate_id="mandate_abc123",
        amount=Decimal("42.50"),
        currency="USDC",
    )

    # Later: mark as spent
    await algo.spend_cells(
        cell_ids=[c.cell_id for c in cells],
        payment_object_id="po_xyz789",
    )
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from asyncpg import Pool

from .funding_cell import CellStatus, FundingCell

logger = logging.getLogger("sardis.cell_claim")


class InsufficientCellsError(Exception):
    """Raised when available cells cannot cover the requested amount."""

    def __init__(self, requested: Decimal, available: Decimal, currency: str) -> None:
        self.requested = requested
        self.available = available
        self.currency = currency
        super().__init__(
            f"Insufficient cells: requested {requested} {currency}, "
            f"available {available} {currency}"
        )


class CellClaimAlgorithm:
    """Claims funding cells for payment objects using UTXO-style selection.

    Uses ``SELECT ... FOR UPDATE SKIP LOCKED`` to prevent concurrent claims
    on the same cells -- essential for high-throughput agent payments.
    """

    def __init__(self, pool: Pool) -> None:
        self._pool = pool

    # ------------------------------------------------------------------
    # Core: claim
    # ------------------------------------------------------------------

    async def claim_cells(
        self,
        mandate_id: str,
        amount: Decimal,
        currency: str = "USDC",
    ) -> list[FundingCell]:
        """Select and claim cells that cover ``amount``.

        Algorithm:
        1. Lock AVAILABLE cells (largest first, SKIP LOCKED).
        2. Greedily accumulate until ``amount`` is met.
        3. Split the last cell if it overflows.
        4. Mark selected cells as CLAIMED.
        5. Return the claimed cells.

        Raises ``InsufficientCellsError`` if the available pool is too small.
        """
        if amount <= Decimal("0"):
            raise ValueError("Claim amount must be positive")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                # Step 1 -- lock available cells, largest first
                rows = await conn.fetch(
                    """
                    SELECT cell_id, commitment_id, value, currency, status,
                           owner_mandate_id, claimed_at, spent_at,
                           payment_object_id, created_at, metadata
                    FROM funding_cells
                    WHERE status = $1 AND currency = $2
                    ORDER BY value DESC
                    FOR UPDATE SKIP LOCKED
                    """,
                    CellStatus.AVAILABLE.value,
                    currency,
                )

                # Step 2 -- greedy selection
                selected_rows: list[Any] = []
                accumulated = Decimal("0")

                for row in rows:
                    if accumulated >= amount:
                        break
                    selected_rows.append(row)
                    accumulated += Decimal(str(row["value"]))

                if accumulated < amount:
                    raise InsufficientCellsError(
                        requested=amount,
                        available=accumulated,
                        currency=currency,
                    )

                # Step 3 -- split the last cell if it overshoots
                overshoot = accumulated - amount
                claimed_cells: list[FundingCell] = []

                for i, row in enumerate(selected_rows):
                    is_last = i == len(selected_rows) - 1

                    if is_last and overshoot > Decimal("0"):
                        # Reduce the last cell's value and create a remainder
                        claim_value = Decimal(str(row["value"])) - overshoot
                        remainder_id = f"cell_{uuid4().hex[:12]}"
                        now = datetime.now(UTC)

                        # Update the selected cell with reduced value + CLAIMED
                        await conn.execute(
                            """
                            UPDATE funding_cells
                            SET status = $2, owner_mandate_id = $3,
                                claimed_at = $4, value = $5
                            WHERE cell_id = $1
                            """,
                            row["cell_id"],
                            CellStatus.CLAIMED.value,
                            mandate_id,
                            now,
                            float(claim_value),
                        )

                        # Insert the remainder as a new AVAILABLE cell
                        await conn.execute(
                            """
                            INSERT INTO funding_cells (
                                cell_id, commitment_id, value, currency,
                                status, created_at, metadata
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                            """,
                            remainder_id,
                            row["commitment_id"],
                            float(overshoot),
                            currency,
                            CellStatus.AVAILABLE.value,
                            now,
                            "{}",
                        )

                        logger.info(
                            "Split cell %s: claimed %s, remainder %s -> %s",
                            row["cell_id"], claim_value, remainder_id, overshoot,
                        )

                        claimed_cells.append(
                            self._row_to_cell(row, overrides={
                                "status": CellStatus.CLAIMED,
                                "owner_mandate_id": mandate_id,
                                "claimed_at": now,
                                "value": claim_value,
                            })
                        )
                    else:
                        # Claim the full cell
                        now = datetime.now(UTC)
                        await conn.execute(
                            """
                            UPDATE funding_cells
                            SET status = $2, owner_mandate_id = $3, claimed_at = $4
                            WHERE cell_id = $1
                            """,
                            row["cell_id"],
                            CellStatus.CLAIMED.value,
                            mandate_id,
                            now,
                        )
                        claimed_cells.append(
                            self._row_to_cell(row, overrides={
                                "status": CellStatus.CLAIMED,
                                "owner_mandate_id": mandate_id,
                                "claimed_at": now,
                            })
                        )

                total_claimed = sum(c.value for c in claimed_cells)
                logger.info(
                    "Claimed %d cells for mandate %s: total=%s %s",
                    len(claimed_cells), mandate_id, total_claimed, currency,
                )
                return claimed_cells

    # ------------------------------------------------------------------
    # Release
    # ------------------------------------------------------------------

    async def release_cells(self, cell_ids: list[str]) -> None:
        """Return claimed cells back to AVAILABLE.

        Only cells in CLAIMED status are released; others are silently
        skipped (idempotent).
        """
        if not cell_ids:
            return

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    """
                    UPDATE funding_cells
                    SET status = $1, owner_mandate_id = NULL, claimed_at = NULL
                    WHERE cell_id = ANY($2) AND status = $3
                    """,
                    CellStatus.AVAILABLE.value,
                    cell_ids,
                    CellStatus.CLAIMED.value,
                )
                count = int(result.split()[-1]) if result else 0
                logger.info("Released %d / %d cells", count, len(cell_ids))

    # ------------------------------------------------------------------
    # Spend
    # ------------------------------------------------------------------

    async def spend_cells(self, cell_ids: list[str], payment_object_id: str) -> None:
        """Mark claimed cells as SPENT and attach the payment object ID."""
        if not cell_ids:
            return

        now = datetime.now(UTC)
        async with self._pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(
                    """
                    UPDATE funding_cells
                    SET status = $1, payment_object_id = $2, spent_at = $3
                    WHERE cell_id = ANY($4) AND status = $5
                    """,
                    CellStatus.SPENT.value,
                    payment_object_id,
                    now,
                    cell_ids,
                    CellStatus.CLAIMED.value,
                )
                count = int(result.split()[-1]) if result else 0
                logger.info(
                    "Spent %d / %d cells for payment %s",
                    count, len(cell_ids), payment_object_id,
                )

    # ------------------------------------------------------------------
    # Split
    # ------------------------------------------------------------------

    async def split_cell(self, cell_id: str, amounts: list[Decimal]) -> list[FundingCell]:
        """Split an AVAILABLE cell into smaller cells with given ``amounts``.

        The sum of ``amounts`` must equal the original cell's value.
        The original cell is marked as MERGED and new cells are created.
        """
        if not amounts:
            raise ValueError("amounts list must not be empty")
        if any(a <= Decimal("0") for a in amounts):
            raise ValueError("All split amounts must be positive")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT cell_id, commitment_id, value, currency, status,
                           owner_mandate_id, claimed_at, spent_at,
                           payment_object_id, created_at, metadata
                    FROM funding_cells
                    WHERE cell_id = $1 AND status = $2
                    FOR UPDATE
                    """,
                    cell_id,
                    CellStatus.AVAILABLE.value,
                )
                if row is None:
                    raise ValueError(f"Cell {cell_id} not found or not AVAILABLE")

                original_value = Decimal(str(row["value"]))
                total_split = sum(amounts)
                if total_split != original_value:
                    raise ValueError(
                        f"Split amounts sum to {total_split} but cell value is {original_value}"
                    )

                # Mark original as MERGED
                await conn.execute(
                    """
                    UPDATE funding_cells SET status = $2 WHERE cell_id = $1
                    """,
                    cell_id,
                    CellStatus.MERGED.value,
                )

                # Create new cells
                now = datetime.now(UTC)
                new_cells: list[FundingCell] = []
                for part_value in amounts:
                    new_id = f"cell_{uuid4().hex[:12]}"
                    await conn.execute(
                        """
                        INSERT INTO funding_cells (
                            cell_id, commitment_id, value, currency,
                            status, created_at, metadata
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        """,
                        new_id,
                        row["commitment_id"],
                        float(part_value),
                        row["currency"],
                        CellStatus.AVAILABLE.value,
                        now,
                        "{}",
                    )
                    new_cells.append(FundingCell(
                        cell_id=new_id,
                        commitment_id=row["commitment_id"],
                        value=part_value,
                        currency=row["currency"],
                        status=CellStatus.AVAILABLE,
                        created_at=now,
                    ))

                logger.info(
                    "Split cell %s (%s) into %d cells: %s",
                    cell_id, original_value, len(new_cells),
                    [str(a) for a in amounts],
                )
                return new_cells

    # ------------------------------------------------------------------
    # Merge
    # ------------------------------------------------------------------

    async def merge_cells(self, cell_ids: list[str]) -> FundingCell:
        """Combine multiple AVAILABLE cells into a single cell.

        All source cells must share the same ``commitment_id`` and
        ``currency``.  Source cells are marked as MERGED.
        """
        if len(cell_ids) < 2:
            raise ValueError("Need at least 2 cells to merge")

        async with self._pool.acquire() as conn:
            async with conn.transaction():
                rows = await conn.fetch(
                    """
                    SELECT cell_id, commitment_id, value, currency, status,
                           owner_mandate_id, claimed_at, spent_at,
                           payment_object_id, created_at, metadata
                    FROM funding_cells
                    WHERE cell_id = ANY($1) AND status = $2
                    FOR UPDATE
                    """,
                    cell_ids,
                    CellStatus.AVAILABLE.value,
                )

                if len(rows) != len(cell_ids):
                    found = {r["cell_id"] for r in rows}
                    missing = set(cell_ids) - found
                    raise ValueError(
                        f"Cells not found or not AVAILABLE: {missing}"
                    )

                # Validate same commitment and currency
                commitment_ids = {r["commitment_id"] for r in rows}
                currencies = {r["currency"] for r in rows}
                if len(commitment_ids) > 1:
                    raise ValueError(
                        f"Cannot merge cells from different commitments: {commitment_ids}"
                    )
                if len(currencies) > 1:
                    raise ValueError(
                        f"Cannot merge cells with different currencies: {currencies}"
                    )

                total_value = sum(Decimal(str(r["value"])) for r in rows)
                commitment_id = rows[0]["commitment_id"]
                currency = rows[0]["currency"]

                # Mark source cells as MERGED
                await conn.execute(
                    """
                    UPDATE funding_cells SET status = $1 WHERE cell_id = ANY($2)
                    """,
                    CellStatus.MERGED.value,
                    cell_ids,
                )

                # Create merged cell
                now = datetime.now(UTC)
                merged_id = f"cell_{uuid4().hex[:12]}"
                await conn.execute(
                    """
                    INSERT INTO funding_cells (
                        cell_id, commitment_id, value, currency,
                        status, created_at, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """,
                    merged_id,
                    commitment_id,
                    float(total_value),
                    currency,
                    CellStatus.AVAILABLE.value,
                    now,
                    "{}",
                )

                merged_cell = FundingCell(
                    cell_id=merged_id,
                    commitment_id=commitment_id,
                    value=total_value,
                    currency=currency,
                    status=CellStatus.AVAILABLE,
                    created_at=now,
                )

                logger.info(
                    "Merged %d cells into %s (value=%s %s)",
                    len(cell_ids), merged_id, total_value, currency,
                )
                return merged_cell

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_cell(
        row: Any,
        overrides: dict[str, Any] | None = None,
    ) -> FundingCell:
        """Convert a database row to a FundingCell, with optional overrides."""
        data: dict[str, Any] = {
            "cell_id": row["cell_id"],
            "commitment_id": row["commitment_id"],
            "value": Decimal(str(row["value"])),
            "currency": row["currency"],
            "status": CellStatus(row["status"]),
            "owner_mandate_id": row["owner_mandate_id"],
            "claimed_at": row["claimed_at"],
            "spent_at": row["spent_at"],
            "payment_object_id": row["payment_object_id"],
            "created_at": row["created_at"],
            "metadata": row["metadata"] if isinstance(row["metadata"], dict) else {},
        }
        if overrides:
            data.update(overrides)
        return FundingCell(**data)
