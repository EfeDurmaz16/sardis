"""Control Plane domain — intent submission and routing.

Thin wrapper around sardis_v2_core.control_plane.ControlPlane,
configured with the app's actual service instances.
"""
from __future__ import annotations

import logging
from typing import Optional

from sardis_v2_core.control_plane import ControlPlane
from sardis_v2_core.execution_intent import ExecutionIntent, ExecutionResult, SimulationResult

logger = logging.getLogger(__name__)

_instance: Optional[ControlPlane] = None


def init_control_plane(
    policy_evaluator=None,
    compliance_checker=None,
    chain_executor=None,
    ledger_recorder=None,
) -> ControlPlane:
    """Initialize the control plane with the app's service instances."""
    global _instance
    _instance = ControlPlane(
        policy_evaluator=policy_evaluator,
        compliance_checker=compliance_checker,
        chain_executor=chain_executor,
        ledger_recorder=ledger_recorder,
    )
    logger.info("ControlPlane domain initialized")
    return _instance


def get_control_plane() -> Optional[ControlPlane]:
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
