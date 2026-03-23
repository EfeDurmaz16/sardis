"""State-specific handler callbacks for payment lifecycle events.

When a payment transitions into or out of a state, registered handlers
fire automatically.  This decouples side-effects (webhooks, timers,
logging) from the core state machine logic.

Architecture:
─────────────────────────────────────────────────────────────────────
  PaymentStateMachine.transition()
    └─ StateHandlerRegistry.fire_on_exit(old_state, ...)
    └─ StateHandlerRegistry.fire_on_enter(new_state, ...)
─────────────────────────────────────────────────────────────────────

Each handler is an async callable that receives the machine and the
transition record.  Handlers are executed in registration order.
A failing handler logs the error but does NOT block the transition —
the state change has already been committed by the time handlers fire.

Usage::

    from sardis_v2_core.state_handlers import (
        StateHandlerRegistry,
        register_default_handlers,
    )
    from sardis_v2_core.state_machine import PaymentStateMachine, PaymentState

    registry = StateHandlerRegistry()
    register_default_handlers(registry)

    # Custom handler
    async def notify_treasury(machine, record):
        await treasury_client.notify_settlement(machine.payment_object_id)

    registry.register_on_enter(PaymentState.SETTLED, notify_treasury)

See also:
  - ``state_machine.py`` — core state machine and transition validation
  - ``settlement_lock.py`` — advisory lock for concurrent access
  - ``webhooks.py`` — webhook delivery for external consumers
"""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .state_machine import PaymentState, PaymentStateMachine, StateTransitionRecord

logger = logging.getLogger("sardis.state_handlers")

# Type alias for handler functions.
# A handler receives the machine (for context) and the transition record
# (for audit details), and performs async side-effects.
StateHandler = Callable[["PaymentStateMachine", "StateTransitionRecord"], Awaitable[None]]


# =============================================================================
# Handler Registry
# =============================================================================

class StateHandlerRegistry:
    """Registry for state entry/exit handlers.

    Maintains two maps — on_enter and on_exit — keyed by PaymentState.
    Multiple handlers can be registered per state and they execute in
    registration order.
    """

    def __init__(self) -> None:
        self._on_enter: dict[PaymentState, list[StateHandler]] = defaultdict(list)
        self._on_exit: dict[PaymentState, list[StateHandler]] = defaultdict(list)

    def register_on_enter(self, state: PaymentState, handler: StateHandler) -> None:
        """Register a handler to fire when entering ``state``.

        Args:
            state: The target state that triggers this handler.
            handler: Async callable ``(machine, record) -> None``.
        """
        self._on_enter[state].append(handler)
        logger.debug("Registered on_enter handler for %s: %s", state.value, handler.__name__)

    def register_on_exit(self, state: PaymentState, handler: StateHandler) -> None:
        """Register a handler to fire when leaving ``state``.

        Args:
            state: The source state that triggers this handler.
            handler: Async callable ``(machine, record) -> None``.
        """
        self._on_exit[state].append(handler)
        logger.debug("Registered on_exit handler for %s: %s", state.value, handler.__name__)

    async def fire_on_enter(
        self,
        state: PaymentState,
        machine: PaymentStateMachine,
        record: StateTransitionRecord,
    ) -> None:
        """Execute all on_enter handlers for ``state``.

        Handlers run sequentially in registration order.  Exceptions are
        logged but do NOT propagate — the state transition has already
        been committed.

        Args:
            state: The state being entered.
            machine: The payment state machine instance.
            record: The transition record that caused the state change.
        """
        handlers = self._on_enter.get(state, [])
        for handler in handlers:
            try:
                await handler(machine, record)
            except Exception:
                logger.exception(
                    "on_enter handler %s failed for payment %s entering %s",
                    handler.__name__,
                    machine.payment_object_id,
                    state.value,
                )

    async def fire_on_exit(
        self,
        state: PaymentState,
        machine: PaymentStateMachine,
        record: StateTransitionRecord,
    ) -> None:
        """Execute all on_exit handlers for ``state``.

        Handlers run sequentially in registration order.  Exceptions are
        logged but do NOT propagate.

        Args:
            state: The state being exited.
            machine: The payment state machine instance.
            record: The transition record that caused the state change.
        """
        handlers = self._on_exit.get(state, [])
        for handler in handlers:
            try:
                await handler(machine, record)
            except Exception:
                logger.exception(
                    "on_exit handler %s failed for payment %s exiting %s",
                    handler.__name__,
                    machine.payment_object_id,
                    state.value,
                )

    def handler_count(self, state: PaymentState) -> dict[str, int]:
        """Return the number of registered handlers for a given state.

        Useful for diagnostics and testing.

        Returns:
            Dict with "on_enter" and "on_exit" counts.
        """
        return {
            "on_enter": len(self._on_enter.get(state, [])),
            "on_exit": len(self._on_exit.get(state, [])),
        }


# =============================================================================
# Default Handlers
# =============================================================================

async def on_enter_escrowed(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into ESCROWED state.

    Actions:
      - Log that funds are now held in escrow.
      - Record timelock start for auto-release calculation.
    """
    logger.info(
        "Payment %s entered escrow. Actor: %s. "
        "Timelock timer started for auto-release.",
        machine.payment_object_id,
        record.actor,
    )
    # The timelock expiry is tracked externally (scheduler or DB column).
    # This handler establishes the audit record.


async def on_enter_settling(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into SETTLING state.

    Actions:
      - Log settlement initiation with chain/tx metadata.
    """
    tx_hash = record.metadata.get("tx_hash", "unknown")
    chain = record.metadata.get("chain", "unknown")
    logger.info(
        "Payment %s settlement started on %s (tx: %s). Actor: %s.",
        machine.payment_object_id,
        chain,
        tx_hash,
        record.actor,
    )


async def on_enter_disputing(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into DISPUTING state.

    Actions:
      - Log dispute filing with evidence deadline.
      - The evidence_deadline should be set in metadata by the caller.
    """
    evidence_deadline = record.metadata.get("evidence_deadline", "not_set")
    dispute_id = record.metadata.get("dispute_id", record.id)
    logger.info(
        "Payment %s dispute filed (dispute_id: %s). "
        "Evidence deadline: %s. Actor: %s.",
        machine.payment_object_id,
        dispute_id,
        evidence_deadline,
        record.actor,
    )


async def on_enter_expired(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into EXPIRED state.

    Actions:
      - Log expiration.
      - Any held funds should be released (triggered by the caller).
    """
    logger.info(
        "Payment %s expired. Any held funds should be released. "
        "Reason: %s. Actor: %s.",
        machine.payment_object_id,
        record.reason or "TTL exceeded",
        record.actor,
    )


async def on_enter_fulfilled(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into FULFILLED state.

    Actions:
      - Log completion.
      - Mark payment as complete for webhook delivery.
    """
    logger.info(
        "Payment %s fulfilled. Delivery confirmed by both parties. "
        "Actor: %s. Triggering completion webhook.",
        machine.payment_object_id,
        record.actor,
    )
    # Webhook delivery is handled by the orchestrator layer that
    # observes the transition log, not directly here.


async def on_enter_failed(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into FAILED state.

    Actions:
      - Log failure with chain error details.
    """
    error_detail = record.metadata.get("error", record.reason or "unknown")
    tx_hash = record.metadata.get("tx_hash", "none")
    logger.warning(
        "Payment %s settlement FAILED. Error: %s. Tx: %s. Actor: %s.",
        machine.payment_object_id,
        error_detail,
        tx_hash,
        record.actor,
    )


async def on_enter_refunded(
    machine: PaymentStateMachine,
    record: StateTransitionRecord,
) -> None:
    """Handle entry into REFUNDED state.

    Actions:
      - Log refund with amount/tx details.
    """
    refund_amount = record.metadata.get("refund_amount", "full")
    refund_tx = record.metadata.get("refund_tx_hash", "pending")
    logger.info(
        "Payment %s refunded (amount: %s, tx: %s). Actor: %s.",
        machine.payment_object_id,
        refund_amount,
        refund_tx,
        record.actor,
    )


def register_default_handlers(registry: StateHandlerRegistry) -> None:
    """Register the default set of state handlers.

    Call this once at application startup to wire up the standard
    logging and lifecycle handlers.

    Args:
        registry: The handler registry to populate.
    """
    # Import here to avoid circular import at module level
    from .state_machine import PaymentState

    registry.register_on_enter(PaymentState.ESCROWED, on_enter_escrowed)
    registry.register_on_enter(PaymentState.SETTLING, on_enter_settling)
    registry.register_on_enter(PaymentState.DISPUTING, on_enter_disputing)
    registry.register_on_enter(PaymentState.EXPIRED, on_enter_expired)
    registry.register_on_enter(PaymentState.FULFILLED, on_enter_fulfilled)
    registry.register_on_enter(PaymentState.FAILED, on_enter_failed)
    registry.register_on_enter(PaymentState.REFUNDED, on_enter_refunded)
