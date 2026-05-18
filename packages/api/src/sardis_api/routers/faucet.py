"""Compatibility import for developer faucet routes.

New code should import from `sardis_api.routes.developer.faucet`.
"""

import sys

from sardis_api.routes.developer import faucet as _implementation

_legacy_name = __name__
globals().update({key: value for key, value in _implementation.__dict__.items() if key != "__name__"})
sys.modules[_legacy_name] = _implementation
