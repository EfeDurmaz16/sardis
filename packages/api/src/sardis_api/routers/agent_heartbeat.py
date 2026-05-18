"""Compatibility import for agent heartbeat routes.

New code should import from `sardis_api.routes.agents.agent_heartbeat`.
"""
import sys

from sardis_api.routes.agents import agent_heartbeat as _implementation

sys.modules[__name__] = _implementation
