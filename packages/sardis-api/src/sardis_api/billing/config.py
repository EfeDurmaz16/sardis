"""Stripe Billing configuration for developer plan tiers.

Tiers (March 2026 CEO review):
  Dev:        $49/mo  — testnet only, 100 tx/mo, no SLA
  Starter:    $199/mo — production, unlimited tx, mainnet, SLA
  Growth:     $499/mo — + KYB, PEP screening, advanced audit, FX swaps
  Enterprise: custom  — white-glove, dedicated support

Stripe product/price IDs (test mode):
  Dev:     prod_UD3rDKTnyVml3R / price_1TEdkOQc1fanBcXKW9ttE0tR
  Starter: prod_UD3rxAQORDxoNy / price_1TEdkUQc1fanBcXKYZGl3tbr
  Growth:  prod_UD3sXYrsO9xbdn / price_1TEdkZQc1fanBcXKxqgxV94A
"""
from __future__ import annotations

from pydantic_settings import BaseSettings


class BillingConfig(BaseSettings):
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_dev: str = ""           # Stripe price ID for $49/mo
    stripe_price_starter: str = ""       # Stripe price ID for $199/mo
    stripe_price_growth: str = ""        # Stripe price ID for $499/mo
    billing_enabled: bool = False

    model_config = {"env_prefix": "SARDIS_BILLING_"}


PLAN_LIMITS = {
    "dev": {
        "api_calls_per_month": 1_000,
        "agents": 2,
        "tx_fee_bps": 150,              # 1.5%
        "monthly_tx_volume_cents": 100_000,  # $1,000
    },
    "starter": {
        "api_calls_per_month": 50_000,
        "agents": 25,
        "tx_fee_bps": 100,              # 1.0%
        "monthly_tx_volume_cents": 10_000_000,  # $100,000
    },
    "growth": {
        "api_calls_per_month": 500_000,
        "agents": 100,
        "tx_fee_bps": 75,               # 0.75%
        "monthly_tx_volume_cents": 100_000_000,  # $1,000,000
    },
    "enterprise": {
        "api_calls_per_month": None,     # unlimited
        "agents": None,                  # unlimited
        "tx_fee_bps": 50,               # 0.5% (negotiable)
        "monthly_tx_volume_cents": None, # unlimited
    },
}

PLAN_PRICES_CENTS = {
    "dev": 4_900,
    "starter": 19_900,
    "growth": 49_900,
    "enterprise": 0,  # custom pricing
}
