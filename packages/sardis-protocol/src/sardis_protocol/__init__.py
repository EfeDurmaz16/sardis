"""Deprecation shim — `sardis_protocol` is being consolidated into `sardis.protocol`.

Install the umbrella package and update imports:

    pip install sardis
    from sardis.protocol import MandateVerifier, X402Challenge, ...

This shim will be removed 2026-11-23 (6-month sunset window).
"""
import warnings

warnings.warn(
    "sardis_protocol is deprecated. Install `sardis` and use `from sardis.protocol import ...`. "
    "This shim will be removed 2026-11-23.",
    DeprecationWarning,
    stacklevel=2,
)

import sardis.protocol as _protocol  # noqa: E402
from sardis.protocol import *  # noqa: F401, F403, E402

# Make `from sardis_protocol.tap import X` resolve to `sardis.protocol.tap`.
__path__ = _protocol.__path__
__version__ = getattr(_protocol, "__version__", "0.99.0")
