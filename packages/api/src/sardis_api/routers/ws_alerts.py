"""Compatibility import for alert websocket routes.

New code should import from `sardis_api.routes.operations.ws_alerts`.
"""
import sys

from sardis_api.routes.operations import ws_alerts as _implementation

_legacy_name = __name__
globals().update({key: value for key, value in _implementation.__dict__.items() if key != "__name__"})
sys.modules[_legacy_name] = _implementation
