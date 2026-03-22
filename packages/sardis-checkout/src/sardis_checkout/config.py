"""Checkout configuration."""
from __future__ import annotations

import os

# Supported checkout chains and their stablecoin token addresses
CHECKOUT_CHAIN_CONFIG = {
    "base": {
        "chain_id": 8453,
        "usdc_address": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "fee_model": "native",  # ETH gas
    },
    "base_sepolia": {
        "chain_id": 84532,
        "usdc_address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
        "fee_model": "native",
    },
    "tempo": {
        "chain_id": 4217,
        "usdc_address": "0x20c0000000000000000000000000000000000000",  # pathUSD
        "usdc_e_address": "0x20C000000000000000000000b9537d11c60E8b50",  # Bridged USDC.e
        "fee_model": "tip20",  # Gas paid in stablecoin
    },
    "tempo_testnet": {
        "chain_id": 42429,
        "usdc_address": "0x20c0000000000000000000000000000000000000",
        "fee_model": "tip20",
    },
}


def get_checkout_chain() -> str:
    """Get the configured checkout chain."""
    chain = os.getenv("SARDIS_CHECKOUT_CHAIN", "base")
    if chain not in CHECKOUT_CHAIN_CONFIG:
        raise ValueError(
            f"Unsupported checkout chain: {chain}. "
            f"Supported: {', '.join(CHECKOUT_CHAIN_CONFIG.keys())}"
        )
    return chain


def get_checkout_chain_config() -> dict:
    """Get the configuration for the current checkout chain."""
    chain = get_checkout_chain()
    return CHECKOUT_CHAIN_CONFIG[chain]


def get_enabled_payment_methods() -> list[str]:
    """Get list of enabled payment methods from environment config.

    Default: card, apple_pay, google_pay, link
    Optional (require Stripe activation): klarna, paypal
    """
    configured = os.getenv(
        "SARDIS_CHECKOUT_PAYMENT_METHODS",
        "card,apple_pay,google_pay,link",
    )
    return [m.strip() for m in configured.split(",") if m.strip()]
