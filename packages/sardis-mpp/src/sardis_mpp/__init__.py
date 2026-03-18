"""Sardis MPP (Machine Payments Protocol) client.

Policy-governed HTTP 402 payment handling for AI agents.
Agents can access paid APIs and services through MPP while Sardis
enforces spending policies, approval workflows, and audit trails.

MPP is an open standard co-authored by Stripe and Tempo for
machine-to-machine payments.

Usage:
    from sardis_mpp import MPPClient

    client = MPPClient(
        wallet_address="0x...",
        chain="tempo",
        policy_checker=my_policy_fn,
        signer=my_turnkey_signer,
    )

    # Automatically handles 402 challenges with policy enforcement
    response = await client.get("https://api.example.com/data")
"""

from sardis_mpp.client import MPPClient, MPPPaymentDenied, MPPSession

__all__ = ["MPPClient", "MPPPaymentDenied", "MPPSession"]
