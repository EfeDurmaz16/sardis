"""Compatibility import for Agentic Commerce Protocol routes.

New code should import from `sardis_api.routes.protocol.acp`.
"""
import sys

from sardis_api.routes.protocol import acp as _implementation

sys.modules[__name__] = _implementation
