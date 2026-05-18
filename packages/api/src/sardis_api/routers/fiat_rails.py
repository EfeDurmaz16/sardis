"""Compatibility import for provider-backed fiat rail routes.

New code should import from `sardis_api.routes.providers.fiat_rails`.
"""

import sys

from sardis_api.routes.providers import fiat_rails as _implementation

_legacy_name = __name__
globals().update({key: value for key, value in _implementation.__dict__.items() if key != "__name__"})
sys.modules[_legacy_name] = _implementation
