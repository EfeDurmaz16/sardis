# x402 payment demo

30 seconds: an HTTP server replies `402 Payment Required` with an x402
challenge. The Sardis agent client parses the challenge, signs a payment
payload, retries the request with `PAYMENT-SIGNATURE`, and the server
verifies + settles. All in-process, no network.

```python
from sardis.protocol.x402 import generate_challenge, verify_payment_payload

challenge_resp = generate_challenge(
    resource_uri="/api/premium/report",
    amount="1000000", currency="USDC",
    payee_address="0xB0b...", network="base-sepolia",
    token_address="0x036C...",
)
# ...agent signs canonical payload, server calls verify_payment_payload(payload, challenge)
```

## Run

```bash
make demo
```

## What's exercised

- `sardis.protocol.x402.generate_challenge` — server-side 402 builder
- `X402HeaderBuilder` — v2 PAYMENT-SIGNATURE / PAYMENT-RESPONSE headers
- `verify_payment_payload` with a pluggable signature verifier (HMAC stand-in
  for an EOA, deterministic for the demo)
