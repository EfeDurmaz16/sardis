"""Sardis Connect — Make any API agent-ready in 3 lines.

Usage:
    from sardis_connect import SardisConnect

    sardis = SardisConnect(api_key="mch_live_xxx")
    app.include_router(sardis.router)

That's it. Your API endpoints can now be discovered and paid for by AI agents.
"""

from sardis_connect.middleware import SardisConnect
from sardis_connect.models import PricedEndpoint, PricingTier, UsageRecord

__all__ = ["SardisConnect", "PricedEndpoint", "PricingTier", "UsageRecord"]
__version__ = "0.1.0"
