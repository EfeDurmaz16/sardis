"""Control Plane domain — intent submission and routing.

Thin wrapper around sardis_v2_core.control_plane.ControlPlane,
configured with the app's actual service instances.
"""
from __future__ import annotations

import logging

from sardis_v2_core.control_plane import ControlPlane
from sardis_v2_core.execution_intent import ExecutionIntent, ExecutionResult, SimulationResult

logger = logging.getLogger(__name__)

_instance: ControlPlane | None = None


def init_control_plane(
    policy_evaluator=None,
    compliance_checker=None,
    chain_executor=None,
    ledger_recorder=None,
    execution_mode_router=None,
) -> ControlPlane:
    """Initialize the control plane with the app's service instances.

    If execution_mode_router is provided and chain_executor supports
    multi-modal execution, the router is used to select execution mode.
    """
    global _instance

    # If a mode router is provided and the executor supports multi-modal,
    # wrap the chain executor with MultiModalExecutionAdapter.
    if execution_mode_router is not None and chain_executor is not None:
        from sardis_api.domains.multi_modal_executor import MultiModalExecutionAdapter
        if not isinstance(chain_executor, MultiModalExecutionAdapter):
            chain_executor = MultiModalExecutionAdapter(
                crypto_executor=chain_executor,
                mode_router=execution_mode_router,
            )

    _instance = ControlPlane(
        policy_evaluator=policy_evaluator,
        compliance_checker=compliance_checker,
        chain_executor=chain_executor,
        ledger_recorder=ledger_recorder,
    )
    logger.info("ControlPlane domain initialized")
    return _instance


def get_control_plane() -> ControlPlane | None:
    """Get the initialized control plane, or None."""
    return _instance


async def submit_intent(intent: ExecutionIntent) -> ExecutionResult:
    """Submit an intent for execution."""
    if _instance is None:
        raise RuntimeError("ControlPlane not initialized")
    return await _instance.submit(intent)


async def simulate_intent(intent: ExecutionIntent) -> SimulationResult:
    """Simulate an intent without execution."""
    if _instance is None:
        raise RuntimeError("ControlPlane not initialized")
    return await _instance.simulate(intent)
