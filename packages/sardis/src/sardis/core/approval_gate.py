"""ApprovalGate — the orchestrator's human-in-the-loop collaborator.

Bundles the durable :class:`ApprovalRequestStore` with a delivery notifier so
the orchestrator can, at its ``requires_approval`` branch:

1. create a durable, signed :class:`ApprovalRequest` (status ``pending``),
2. relay it to a human via the notifier (delivery only — never decides),
3. return a *pending* result (no money moves),

and later, when a human decision is relayed back:

4. record the decision as signed evidence on the request,
5. on **approve**, hand the bound mandate-chain snapshot back to the orchestrator
   to re-run ``execute_chain`` idempotently — re-checking policy / mandate /
   revocation at execution time (never trusting a stale approval),
6. on **deny / expire**, keep the request terminal and the money blocked.

The notifier is typed structurally (``send_approval_request`` /
``record_decision``) so it accepts the provider-layer ``NotificationPort``
without this core package importing the apps/api provider modules.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol

from .approval_request import (
    ApprovalRequest,
    ApprovalState,
    DecisionChannel,
    build_approval_request,
)
from .approval_request_repository import ApprovalRequestStore

logger = logging.getLogger("sardis.approval_gate")


class _Notifier(Protocol):
    """Structural type for the provider-layer NotificationPort (delivery only)."""

    async def send_approval_request(
        self,
        *,
        approval_id: str,
        agent_id: str | None,
        amount: str,
        currency: str,
        counterparty: str | None,
        reason: str,
        channels: tuple[str, ...] = ...,
        require_step_up: bool = ...,
        metadata: dict[str, Any] | None = ...,
    ) -> Any: ...


def hash_snapshot(obj: Any) -> str:
    """SHA-256 over a canonical JSON of a snapshot dict/object.

    Used to bind the policy + mandate state that was in effect when approval was
    demanded, so re-execution can detect drift (revocation / limit change).
    """
    if obj is None:
        return ""
    if hasattr(obj, "to_dict"):
        obj = obj.to_dict()
    canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ApprovalGate:
    """Engine-side approval orchestration.  Owns the durable store + notifier."""

    #: Above this token-unit amount, approvals require OTP step-up of the
    #: approver before they can be recorded approved.
    HIGH_VALUE_STEP_UP_THRESHOLD = Decimal("10000")

    def __init__(
        self,
        *,
        store: ApprovalRequestStore,
        notifier: _Notifier | None = None,
        signing_secret: str | None = None,
        default_channels: tuple[str, ...] = ("dashboard",),
        expires_in_hours: int = 24,
        step_up_threshold: Decimal | None = None,
    ) -> None:
        self._store = store
        self._notifier = notifier
        self._secret = signing_secret
        self._default_channels = default_channels
        self._expires_in_hours = expires_in_hours
        self._step_up_threshold = (
            step_up_threshold
            if step_up_threshold is not None
            else self.HIGH_VALUE_STEP_UP_THRESHOLD
        )

    # ── create + deliver (the requires_approval branch) ────────────────

    async def open_request(
        self,
        *,
        agent_id: str | None,
        mandate_id: str | None,
        amount: Decimal,
        currency: str,
        counterparty: str | None,
        reason: str,
        spending_mandate_id: str | None = None,
        policy_hash: str = "",
        mandate_hash: str = "",
        chain_snapshot: Any | None = None,
        channels: tuple[str, ...] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ApprovalRequest:
        """Create a durable pending request and relay it to the human.

        Delivery is best-effort: a failed relay leaves the request pending and
        durable (a human can still decide via the dashboard).  Delivery NEVER
        decides the outcome.
        """
        amount = Decimal(str(amount))
        requires_step_up = amount > self._step_up_threshold
        request = build_approval_request(
            agent_id=agent_id,
            mandate_id=mandate_id,
            amount=amount,
            currency=currency,
            counterparty=counterparty,
            reason=reason,
            spending_mandate_id=spending_mandate_id,
            policy_hash=policy_hash,
            mandate_hash=mandate_hash,
            expires_in_hours=self._expires_in_hours,
            requires_step_up=requires_step_up,
            chain_snapshot=chain_snapshot,
            metadata=metadata,
        )
        await self._store.create(request)

        chosen = channels or self._default_channels
        if self._notifier is not None:
            try:
                delivery = await self._notifier.send_approval_request(
                    approval_id=request.id,
                    agent_id=agent_id,
                    amount=str(amount),
                    currency=currency,
                    counterparty=counterparty,
                    reason=reason,
                    channels=chosen,
                    require_step_up=requires_step_up,
                    metadata=metadata,
                )
                request.metadata["delivery"] = {
                    "provider": getattr(delivery, "provider", None),
                    "handle": getattr(delivery, "handle", None),
                    "channels": list(getattr(delivery, "channels", ()) or ()),
                    "step_up_issued": getattr(delivery, "step_up_issued", False),
                    "ok": getattr(delivery, "ok", False),
                }
                await self._store.save(request)
            except Exception as exc:  # noqa: BLE001 - delivery is best-effort
                logger.warning(
                    "approval %s delivery failed (request still pending+durable): %s",
                    request.id, exc,
                )
                request.metadata["delivery"] = {"ok": False, "error": str(exc)}
                await self._store.save(request)
        return request

    # ── record a human decision (inbound) ──────────────────────────────

    async def record_decision(
        self,
        *,
        approval_id: str,
        decision: str,
        approver: str,
        channel: DecisionChannel = DecisionChannel.DASHBOARD,
        step_up_verified: bool = False,
        reason: str | None = None,
    ) -> ApprovalRequest:
        """Apply a human decision to the durable request, with signed evidence.

        Fail-closed: an expired request can no longer be approved; a request
        requiring step-up cannot be approved without ``step_up_verified``.
        """
        request = await self._store.get(approval_id)
        if request is None:
            raise ValueError(f"approval request {approval_id} not found")

        # Lazily expire a pending-but-past-deadline request before deciding.
        if request.is_expired():
            request.expire(secret=self._secret)
            await self._store.save(request)
            return request

        norm = decision.strip().lower()
        if norm.startswith("approv"):
            request.approve(
                approver=approver,
                channel=channel,
                step_up_verified=step_up_verified,
                secret=self._secret,
            )
        elif norm.startswith("den") or norm.startswith("reject"):
            request.deny(
                approver=approver,
                reason=reason,
                channel=channel,
                secret=self._secret,
            )
        else:
            raise ValueError(f"unknown decision verb: {decision!r}")

        await self._store.save(request)
        return request

    # ── expiry sweep ────────────────────────────────────────────────────

    async def sweep_expired(self, *, as_of: datetime | None = None) -> int:
        """Mark all past-deadline pending requests expired (fail-closed)."""
        expired = await self._store.list_expired_pending(as_of=as_of)
        for request in expired:
            request.expire(secret=self._secret)
            await self._store.save(request)
        return len(expired)

    async def get(self, approval_id: str) -> ApprovalRequest | None:
        return await self._store.get(approval_id)

    async def mark_reexecuted(self, request: ApprovalRequest) -> ApprovalRequest:
        """Flip the idempotency flag so an approved request settles exactly once."""
        request.reexecuted = True
        await self._store.save(request)
        return request

    @staticmethod
    def is_approved_and_unspent(request: ApprovalRequest) -> bool:
        """True iff the request is approved and has not yet been re-executed."""
        return request.status == ApprovalState.APPROVED and not request.reexecuted
