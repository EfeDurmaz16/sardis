"""Sardis MPP — Policy-governed Machine Payments Protocol for AI agents.

Built on pympp 0.4.2 (co-authored by Stripe and Tempo, MIT/Apache-2.0).
Every HTTP 402 payment goes through Sardis policy enforcement before funds move.

Supports multiple payment methods:
  - Tempo (crypto): pathUSD/USDC on Tempo mainnet
  - Stripe (fiat): cards/wallets via Shared Payment Tokens (SPT)

Usage with pympp 0.4.2 API::

    from sardis_mpp import SardisMPPClient, MPPPaymentDenied
    from mpp.methods.tempo import tempo, TempoAccount, ChargeIntent

    # Set up Tempo payment method (pympp canonical API)
    account = TempoAccount.from_key("0x...")
    tempo_method = tempo(
        account=account,
        intents={"charge": ChargeIntent(chain_id=4217)},
    )

    # Create Sardis-governed MPP client
    client = SardisMPPClient(
        methods=[tempo_method],
        policy_checker=my_policy_fn,
    )

    # Agent accesses paid API — 402 handled automatically with policy check
    async with client:
        response = await client.get("https://api.example.com/premium-data")

Constants (from pympp _defaults.py):
    CHAIN_ID_MAINNET = 4217
    CHAIN_ID_TESTNET = 42431
    ESCROW_CONTRACT_MAINNET = "0x33b901018174DDabE4841042ab76ba85D4e24f25"
    ESCROW_CONTRACT_TESTNET = "0xe1c4d3dce17bc111181ddf716f75bae49e61a336"
    FEE_PAYER_TESTNET_URL = "https://sponsor.moderato.tempo.xyz"
    PATH_USD = "0x20c0000000000000000000000000000000000000"
    USDC_BRIDGED = "0x20C000000000000000000000b9537d11c60E8b50"
"""

from sardis_mpp.client import (
    MPPPaymentDenied,
    MPPPaymentRecord,
    MPPSessionManager,
    SardisMPPClient,
    SardisPolicyTransport,
)
from sardis_mpp.stripe_method import SardisStripeMPPMethod

__all__ = [
    "MPPPaymentDenied",
    "MPPPaymentRecord",
    "MPPSessionManager",
    "SardisMPPClient",
    "SardisPolicyTransport",
    "SardisStripeMPPMethod",
]
