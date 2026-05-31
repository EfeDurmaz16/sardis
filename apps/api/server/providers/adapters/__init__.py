"""Port adapters wrapping existing real provider clients.

Each adapter normalizes a vendor client's responses into the unified port
envelopes and declares its custody model — without changing client behavior.
"""

from __future__ import annotations

from .circle import CircleCpnOfframpAdapter
from .conduit import ConduitOnrampAdapter
from .lithic import LithicFiatAccountAdapter
from .turnkey import TurnkeyCustodyAdapter, TurnkeyOnrampAdapter

__all__ = [
    "CircleCpnOfframpAdapter",
    "ConduitOnrampAdapter",
    "LithicFiatAccountAdapter",
    "TurnkeyCustodyAdapter",
    "TurnkeyOnrampAdapter",
]
