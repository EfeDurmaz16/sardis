"""Compatibility import for ERC-8183 protocol routes.

New code should import from `sardis_api.routes.protocol.erc8183`.
"""
import sys

from sardis_api.routes.protocol import erc8183 as _implementation

sys.modules[__name__] = _implementation
