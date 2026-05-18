"""Compatibility import for onramp wallet funding routes.

New code should import from `sardis_api.routes.wallets.onramp`.
"""
from sardis_api.routes.wallets.onramp import *  # noqa: F401,F403
from sardis_api.routes.wallets.onramp import (
    _get_conduit_onramp_service,
    _get_turnkey_onramp_service,
    _resolve_wallet_address,
)
