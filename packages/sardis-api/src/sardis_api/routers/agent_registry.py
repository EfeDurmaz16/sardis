"""Compatibility import for agent registry routes.

New code should import from `sardis_api.routes.agents.agent_registry`.
"""
import sys

from sardis_api.routes.agents import agent_registry as _implementation

sys.modules[__name__] = _implementation
