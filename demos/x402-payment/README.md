# x402 payment demo

An HTTP server replies `402 Payment Required` with an x402 challenge. The agent
client parses the challenge, signs a canonical payment payload, retries with a
`PAYMENT-SIGNATURE` header, and the server verifies + settles. All in-process,
no network, no API key, no chain.

x402 is an **open standard** — the wire shape used here is the standard, not
anything Sardis-private — so this demo is pure Python stdlib and imports no
Sardis engine. An HMAC signer stands in for an EOA so the run is deterministic.

```python
# server: 402 + challenge  ->  agent: sign canonical payload
#   ->  server: verify signature + amount  ->  200 + settlement header
```

## Run

```bash
make demo
# or just: python demo.py   (no dependencies)
```

## What's exercised

- The x402 round-trip: `402` challenge → `PAYMENT-SIGNATURE` retry → `200` +
  `PAYMENT-RESPONSE` settlement header
- Nonce-bound, amount-checked, signature-verified payment authorization
- Pluggable signature verification (HMAC stand-in for an EOA)

## Going further — the audited offline verifier

The pure, **audited** Sardis x402 verifier (EIP-3009 authorization timing +
binding checks, zero money at risk) ships in the `@sardis/reference` npm package:

```ts
import { verifyTimingAndBinding } from "@sardis/reference";
```
