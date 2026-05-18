"""Compatibility import for agent lifecycle routes.

New code should import from `sardis_api.routes.agents.agents`.
"""
import sys

from sardis_api.routes.agents import agents as _implementation

sys.modules[__name__] = _implementation
