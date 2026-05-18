"""Compatibility import for agent event routes.

New code should import from `sardis_api.routes.agents.agent_events`.
"""
import sys

from sardis_api.routes.agents import agent_events as _implementation

sys.modules[__name__] = _implementation
