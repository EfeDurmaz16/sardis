"""Spending Mandate pre-execution hook.

Validates payments against active spending mandates before policy
checks and chain execution. This hook runs early in the pipeline
because mandate authorization is the highest-level permission check.

If no mandate exists for the agent/wallet, the hook approves (skip)
to maintain backward compatibility — mandates are opt-in.

Usage::

    from sardis_v2_core.hooks.mandate_hook import mandate_validation_hook
    pipeline.add_hook(mandate_validation_hook)
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from sardis_v2_core.pre_execution_pipeline import HookResult

logger = logging.getLogger("sardis.hooks.mandate")


async def mandate_validation_hook(intent: Any) -> HookResult:
    """Validate a payment intent against active spending mandates.

    Looks up active mandates for the agent_id or wallet_id on the intent.
    If a mandate exists, validates: status, merchant scope, amount limits,
    rail permissions. If no mandate exists, skips (backward compatible).

    Sets intent.mandate_id if validation passes.
    """
    agent_id = getattr(intent, "agent_id", None)
    wallet_id = getattr(intent, "wallet_id", None)
    org_id = getattr(intent, "organization_id", None) or getattr(intent, "org_id", None)

    if not org_id:
        return HookResult(decision="skip", reason="No org_id on intent")

    # Look up active mandate
    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            # Try agent_id first, then wallet_id
            mandate_row = None
            if agent_id:
                mandate_row = await conn.fetchrow(
                    """SELECT * FROM spending_mandates
                       WHERE org_id = $1 AND agent_id = $2 AND status = 'active'
                       ORDER BY created_at DESC LIMIT 1""",
                    org_id, agent_id,
                )
            if not mandate_row and wallet_id:
                mandate_row = await conn.fetchrow(
                    """SELECT * FROM spending_mandates
                       WHERE org_id = $1 AND wallet_id = $2 AND status = 'active'
                       ORDER BY created_at DESC LIMIT 1""",
                    org_id, wallet_id,
                )

            if not mandate_row:
                # No mandate — pass through (backward compatible)
                return HookResult(decision="skip", reason="No active mandate found")

    except Exception as exc:
        logger.error("Mandate lookup failed: %s", exc)
        # Fail open on lookup errors to avoid blocking payments when DB is down
        return HookResult(decision="skip", reason=f"Mandate lookup error: {exc}")

    # Validate mandate
    mandate_id = mandate_row["id"]
    mandate_status = mandate_row["status"]

    # Check status
    if mandate_status != "active":
        return HookResult(
            decision="reject",
            reason=f"Mandate {mandate_id} is {mandate_status}",
            evidence={"mandate_id": mandate_id, "error_code": "MANDATE_NOT_ACTIVE"},
        )

    # Check expiration
    expires_at = mandate_row.get("expires_at")
    if expires_at:
        from datetime import UTC, datetime
        if datetime.now(UTC) > expires_at.replace(tzinfo=UTC) if expires_at.tzinfo is None else expires_at:
            return HookResult(
                decision="reject",
                reason=f"Mandate {mandate_id} has expired",
                evidence={"mandate_id": mandate_id, "error_code": "MANDATE_EXPIRED"},
            )

    # Check per-transaction amount
    amount = getattr(intent, "amount", None) or getattr(intent, "amount_minor", 0)
    if isinstance(amount, int) and amount > 1000:
        # Likely minor units (e.g., cents) — convert to major
        amount = Decimal(amount) / Decimal(1_000_000)
    amount = Decimal(str(amount))

    per_tx = mandate_row.get("amount_per_tx")
    if per_tx is not None and amount > per_tx:
        return HookResult(
            decision="reject",
            reason=f"Amount {amount} exceeds mandate per-tx limit {per_tx}",
            evidence={"mandate_id": mandate_id, "error_code": "MANDATE_AMOUNT_EXCEEDED"},
        )

    # Check total budget
    amount_total = mandate_row.get("amount_total")
    spent_total = mandate_row.get("spent_total", Decimal(0))
    if amount_total is not None:
        remaining = amount_total - spent_total
        if amount > remaining:
            return HookResult(
                decision="reject",
                reason=f"Amount {amount} exceeds mandate remaining budget {remaining}",
                evidence={"mandate_id": mandate_id, "error_code": "MANDATE_BUDGET_EXHAUSTED"},
            )

    # Check merchant scope
    merchant = getattr(intent, "merchant_domain", None) or getattr(intent, "destination", None)
    merchant_scope = mandate_row.get("merchant_scope") or {}
    if merchant and merchant_scope:
        blocked = merchant_scope.get("blocked", [])
        if merchant in blocked:
            return HookResult(
                decision="reject",
                reason=f"Merchant {merchant} blocked by mandate",
                evidence={"mandate_id": mandate_id, "error_code": "MANDATE_MERCHANT_BLOCKED"},
            )
        allowed = merchant_scope.get("allowed")
        if allowed and merchant not in allowed:
            return HookResult(
                decision="reject",
                reason=f"Merchant {merchant} not in mandate allowed list",
                evidence={"mandate_id": mandate_id, "error_code": "MANDATE_MERCHANT_NOT_ALLOWED"},
            )

    # Check rail permission
    rail = getattr(intent, "rail", None) or getattr(intent, "payment_rail", None)
    allowed_rails = mandate_row.get("allowed_rails") or []
    if rail and allowed_rails and rail not in allowed_rails:
        return HookResult(
            decision="reject",
            reason=f"Rail {rail} not permitted by mandate (allowed: {allowed_rails})",
            evidence={"mandate_id": mandate_id, "error_code": "MANDATE_RAIL_NOT_ALLOWED"},
        )

    # Check approval threshold
    approval_mode = mandate_row.get("approval_mode", "auto")
    approval_threshold = mandate_row.get("approval_threshold")

    if approval_mode == "always_human":
        # Set flag on intent for downstream approval routing
        if hasattr(intent, "requires_approval"):
            intent.requires_approval = True
        logger.info("Mandate %s: always_human approval mode, flagging for approval", mandate_id)

    elif approval_mode == "threshold" and approval_threshold is not None:
        if amount > approval_threshold:
            if hasattr(intent, "requires_approval"):
                intent.requires_approval = True
            logger.info(
                "Mandate %s: amount %s exceeds threshold %s, flagging for approval",
                mandate_id, amount, approval_threshold,
            )

    # Set mandate_id on intent for downstream audit
    if hasattr(intent, "mandate_id"):
        intent.mandate_id = mandate_id

    # Update spent_total on the mandate
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                "UPDATE spending_mandates SET spent_total = spent_total + $1, updated_at = now() WHERE id = $2",
                amount, mandate_id,
            )
    except Exception as exc:
        logger.error("Failed to update mandate spent_total: %s", exc)
        # Don't fail the payment over spend tracking failure

    logger.info("Mandate %s: approved payment of %s", mandate_id, amount)

    return HookResult(
        decision="approve",
        reason=f"Mandate {mandate_id} validated",
        evidence={"mandate_id": mandate_id, "mandate_version": mandate_row.get("version", 1)},
    )
