# `protocol/experimental/` — Research / Experimental Adapters

**These modules are research and experimental code. They are NOT production.**

Nothing in this package makes a conformance claim. They are in-memory
simulations, draft-EIP sketches with unverified cryptography, or unwired
schemes with no production caller. They exist to explore protocol surface,
not to ship it. Do not reference them in pitches, docs, or marketing that
implies production capability, and do not depend on them from `core/`,
`routes/`, or `middleware/`.

Per the protocol audit (`docs/productization/research/PROTOCOL_STRATEGY.md`,
"quarantine-experimental" verdicts):

| Module | Why it is here |
|---|---|
| `erc8001.py` | Real draft EIP, but fake crypto: SHA-256 where keccak256 is required, fabricated selectors, signatures stored but never verified. |
| `kleros.py` | In-memory state machine with no on-chain interaction; `submit_ruling` is a local setter — defeats the point of Kleros. Real recourse is Circle RefundProtocol. |
| `paladin_privacy.py` | Paladin is not an ERC. No node/notary/ZK; "privacy" is a Python dict; fake selectors. Not part of the control-plane thesis. |
| `zkpass_transgate.py` | Honest fail-closed stub (`verify_proof` raises `NotImplementedError`); stale iDenfy framing (KYC is now Didit). |
| `x402_upto.py` | Real x402 streaming scheme name + Permit2 builder, but zero non-test consumers; `finalize()` settles nothing. |

If any of these is to graduate to production, it must be rebuilt as a thin,
correct adapter that speaks a real counterparty's wire format and feeds the
authority/evidence layer (mandate binding, policy, ledger) — and only then
moved out of `experimental/`.
