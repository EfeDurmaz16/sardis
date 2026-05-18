"""Compatibility import for commerce service directory routes.

New code should import from `sardis_api.routes.commerce.service_directory`.
"""

import sys

from sardis_api.routes.commerce import service_directory as _implementation

_legacy_name = __name__
globals().update({key: value for key, value in _implementation.__dict__.items() if key != "__name__"})
sys.modules[_legacy_name] = _implementation
