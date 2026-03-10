"""Stripe Billing configuration for developer plan tiers."""
from __future__ import annotations
from pydantic_settings import BaseSettings


class BillingConfig(BaseSettings):
    stripe_secret_key: str = ""
    stripe_publishable_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_starter: str = ""      # Stripe price ID for $49/mo
    stripe_price_growth: str = ""        # Stripe price ID for $249/mo
    billing_enabled: bool = False

    model_config = {"env_prefix": "SARDIS_BILLING_"}


PLAN_LIMITS = {
    "free": {
        "api_calls_per_month": 1_000,
        "agents": 2,
        "tx_fee_bps": 150,              # 1.5%
        "monthly_tx_volume_cents": 100_000,  # $1,000
    },
    "starter": {
        "api_calls_per_month": 50_000,
        "agents": 10,
        "tx_fee_bps": 100,              # 1.0%
        "monthly_tx_volume_cents": 2_500_000,  # $25,000
    },
    "growth": {
        "api_calls_per_month": 500_000,
        "agents": 100,
        "tx_fee_bps": 75,               # 0.75%
        "monthly_tx_volume_cents": 25_000_000,  # $250,000
    },
    "enterprise": {
        "api_calls_per_month": None,     # unlimited
        "agents": None,                  # unlimited
        "tx_fee_bps": 50,               # 0.5%
        "monthly_tx_volume_cents": None, # unlimited
    },
}

PLAN_PRICES_CENTS = {
    "free": 0,
    "starter": 4_900,
    "growth": 24_900,
    "enterprise": 0,  # custom pricing
}
