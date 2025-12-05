# Sardis V2 – Current Status (Mar 2025)

## ✅ What’s in place
- Mandate chain persistence and replay cache durability using SQLite (AP2 flows survive restarts).
- Ledger entries are now written to disk (audit anchors + chain receipts).
- Payment orchestrator returns compliance metadata; `/api/v2/ap2/payments/execute` exposes it.
- Python/TS SDKs can call the AP2 endpoint (`execute_ap2_payment`) and see compliance info.
- Docs/README updated with dev setup, pytest instructions, AP2 flow guide, and example bundle.
- Tests added for replay cache, mandate verification, and FastAPI AP2 flow (require PyNaCl).

## ⚠️ Outstanding issue
```
pip3 install /Users/efebarandurmaz/Downloads/pynacl-1.6.1-cp38-abi3-macosx_10_10_universal2.whl
ERROR: [Errno 1] Operation not permitted: '/Users/efebarandurmaz/Library/Python/3.13'
```
- Cause: sandboxed environment blocks writing to `~/Library/Python/3.13` even with `--user`.
- Result: PyNaCl isn’t installed, so tests needing Ed25519 signatures cannot run here.

## ⏭ Next steps once PyNaCl is installed
1. Activate a writable venv (`python3 -m venv .venv && source .venv/bin/activate`) and install the wheel there, or install from PyPI on a network-enabled machine.
2. Run the new tests:
   - `pytest tests/test_mandate_chain_verifier.py tests/test_ap2_payment_api.py tests/test_replay_cache.py`
3. Extend compliance adapter with a mock external service + denial-path tests.
4. Add CLI/SDK examples that build signed bundles using `tests/ap2_helpers.build_signed_bundle`.
