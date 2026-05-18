"""Compatibility import for agent activity routes.

New code should import from `sardis_api.routes.agents.agent_activity`.
"""
import sys

from sardis_api.routes.agents import agent_activity as _implementation

sys.modules[__name__] = _implementation
