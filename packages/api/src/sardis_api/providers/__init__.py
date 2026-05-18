"""External provider adapters for sardis-api.

Concrete adapters in this package:
  - lithic_treasury — Lithic-backed treasury operations
  - circle_cpn       — Circle Customer Programmable Network
  - circle_gateway_nanopayments — Circle nanopayments gateway

These are imported on-demand by their respective routes (e.g.
``sardis_api.routes.wallets.treasury``). This module intentionally does not
re-export anything to avoid eager imports of optional adapters at app
boot. Booting via re-exports of long-deleted modules (``base``,
``supabase``) caused gunicorn worker crash loops on Cloud Run — see
the 2026-04-07 incident in feedback_diligence_methodology.md.
"""
