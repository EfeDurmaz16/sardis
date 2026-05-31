"""External provider adapters for sardis-api.

Concrete adapters in this package:
  - lithic_treasury — Lithic-backed treasury operations
  - circle_cpn       — Circle Customer Programmable Network
  - circle_gateway_nanopayments — Circle nanopayments gateway

These are imported on-demand by their respective routes (e.g.
``server.routes.wallets.treasury``). This module intentionally does not
eagerly re-export the concrete vendor clients to avoid importing optional
adapters at app boot. Booting via re-exports of long-deleted modules
(``base``, ``supabase``) caused gunicorn worker crash loops on Cloud Run —
see the 2026-04-07 incident in feedback_diligence_methodology.md.

The unified provider port layer lives in the sub-packages:
  - ``server.providers.ports``    — typed capability port protocols + types
  - ``server.providers.registry`` — env -> client construction (ProviderRegistry)
  - ``server.providers.adapters`` — adapters over the existing vendor clients
  - ``server.providers.sandbox``  — sandbox/mock impls (no live keys required)

These are imported lazily by callers; ``__init__`` stays import-light on
purpose.
"""
