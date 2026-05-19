"""Preferred import namespace for the Sardis core package.

The historical import package is ``sardis_v2_core``. Keep it available for
compatibility, but use ``sardis_core`` in new docs and examples.
"""

from __future__ import annotations

import sys

import sardis_v2_core as _legacy
from sardis_v2_core import *  # noqa: F403

__all__ = getattr(_legacy, "__all__", [name for name in dir(_legacy) if not name.startswith("_")])
__version__ = getattr(_legacy, "__version__", "0.3.0")

# Let imports such as `sardis_core.circuit_breaker` resolve to the existing
# module files while the migration updates internal imports gradually.
__path__ = _legacy.__path__

for _name, _module in list(sys.modules.items()):
    if _name.startswith("sardis_v2_core."):
        sys.modules.setdefault(_name.replace("sardis_v2_core", "sardis_core", 1), _module)
