#!/usr/bin/env python3
"""
Simple payment
==============

The smallest possible Sardis example: execute one policy-checked payment with
the unified `pay` endpoint.

Concept: `client.pay.execute(...)` runs the full authority path (mandate ->
policy -> compliance -> execute -> signed ledger) in a single call.

Requires a Sardis API key (the client talks to a Sardis deployment):
    export SARDIS_API_KEY=sk_live_...
    # optional: export SARDIS_API_URL=https://your-sardis-api.example.com
    python examples/simple_payment.py
"""
from __future__ import annotations

import os
import sys

from sardis import Sardis


def main() -> None:
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        sys.exit("SARDIS_API_KEY not set. export SARDIS_API_KEY=sk_live_... and retry.")

    client = Sardis(api_key=api_key)

    # One call = mandate verification + policy + compliance + execution + ledger.
    result = client.pay.execute(
        to="0xRecipientAddressOrMerchantDomain",
        amount="2.00",
        currency="USDC",
        chain="base",  # omit to let Sardis auto-route the cheapest chain
    )

    print(f"status:   {result.get('status')}")
    print(f"tx_hash:  {result.get('tx_hash')}")
    print(f"chain:    {result.get('chain')}")
    print(f"ledger:   {result.get('ledger_tx_id')}")


if __name__ == "__main__":
    main()
