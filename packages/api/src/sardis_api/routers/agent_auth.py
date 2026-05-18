"""Compatibility import for agent-auth routes.

New code should import from `sardis_api.routes.identity.agent_auth`.
"""
import sys

from sardis_api.routes.identity import agent_auth as _implementation

sys.modules[__name__] = _implementation
