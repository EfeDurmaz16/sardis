"""Sardis MPP — Policy-governed Machine Payments Protocol for AI agents.

Built on the official pympp SDK (co-authored by Stripe and Tempo).
Every HTTP 402 payment goes through Sardis policy enforcement before funds move.

Usage:
    from sardis_mpp import SardisMPPClient, MPPPaymentDenied
    from mpp.methods.tempo.client import TempoMethod
    from mpp.methods.tempo.account import TempoAccount
    from eth_account import Account

    # Set up Tempo payment method
    account = TempoAccount(Account.from_key("0x..."))
    tempo = TempoMethod(account=account, rpc_url="https://rpc.tempo.xyz")

    # Create Sardis-governed MPP client
    client = SardisMPPClient(
        methods=[tempo],
        policy_checker=my_policy_fn,  # 12-check pipeline
    )

    # Agent accesses paid API — 402 handled automatically with policy check
    response = await client.get("https://api.example.com/premium-data")
"""

from sardis_mpp.client import (
    MPPPaymentDenied,
    MPPPaymentRecord,
    SardisMPPClient,
    SardisPolicyTransport,
)

__all__ = [
    "MPPPaymentDenied",
    "MPPPaymentRecord",
    "SardisMPPClient",
    "SardisPolicyTransport",
]
