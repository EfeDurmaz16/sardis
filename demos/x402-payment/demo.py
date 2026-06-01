"""x402 HTTP 402 Payment Required — self-contained protocol round-trip.

An in-process resource server returns ``402 Payment Required`` with an x402
challenge. The agent client parses the challenge, signs a canonical payment
payload, retries with a ``PAYMENT-SIGNATURE`` header, and the server verifies +
settles. No network, no API key, no chain.

x402 is an open standard (the wire shape below is the standard, not anything
Sardis-private), so this demo is pure stdlib — it does not import the Sardis
engine. The HMAC signer stands in for an EOA so the demo is deterministic.

For the *audited, offline* Sardis x402 verifier (EIP-3009 authorization checks
with zero money at risk), see the `@sardis/reference` npm package:
    import { verifyTimingAndBinding } from "@sardis/reference";

Run:
    python demos/x402-payment/demo.py
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets

# x402 header names (per the open x402 spec).
X402_PAYMENT_REQUIRED_HEADER = "PAYMENT-REQUIRED"
X402_PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"
X402_PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"

# --- demo "wallet" (deterministic HMAC signer, stands in for an EOA) ---
PAYER_ADDRESS = "0xA11ce0000000000000000000000000000000A11C"
PAYER_SECRET = b"demo-wallet-secret-do-not-use-in-prod"


def sign(message: bytes) -> str:
    return hmac.new(PAYER_SECRET, message, hashlib.sha256).hexdigest()


def verify(message: bytes, signature: str, address: str) -> bool:
    if address != PAYER_ADDRESS:
        return False
    expected = hmac.new(PAYER_SECRET, message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _b64(obj: dict) -> str:
    return base64.b64encode(json.dumps(obj, separators=(",", ":")).encode()).decode()


def _unb64(value: str) -> dict:
    return json.loads(base64.b64decode(value).decode())


def canonical_message(challenge: dict, payer: str) -> bytes:
    """Deterministic byte string both sides sign/verify over."""
    return "|".join([
        challenge["payment_id"],
        payer,
        challenge["amount"],
        challenge["nonce"],
        challenge["payee_address"],
        challenge["network"],
    ]).encode()


# --- mock x402 server ---
class MockResourceServer:
    def __init__(self) -> None:
        self._open_challenges: dict[str, dict] = {}

    def get_resource(self, headers: dict[str, str]) -> tuple[int, dict[str, str], str]:
        if X402_PAYMENT_SIGNATURE_HEADER not in headers:
            nonce = secrets.token_hex(16)
            challenge = {
                "payment_id": "pay_" + secrets.token_hex(8),
                "resource_uri": "/api/premium/report",
                "amount": "1000000",  # 1 USDC in smallest unit (6 decimals)
                "currency": "USDC",
                "payee_address": "0xB0bdeadbeefdeadbeefdeadbeefdeadbeefB0Bd",
                "network": "base-sepolia",
                "token_address": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "nonce": nonce,
                "ttl_seconds": 300,
            }
            self._open_challenges[nonce] = challenge
            return (
                402,
                {X402_PAYMENT_REQUIRED_HEADER: _b64(challenge)},
                '{"error":"payment_required"}',
            )

        payload = _unb64(headers[X402_PAYMENT_SIGNATURE_HEADER])
        challenge = self._open_challenges.get(payload["nonce"])
        if challenge is None:
            return 400, {}, '{"error":"unknown_nonce"}'

        message = canonical_message(challenge, payload["payer_address"])
        if payload["amount"] != challenge["amount"]:
            return 402, {}, '{"error":"amount_mismatch"}'
        if not verify(message, payload["signature"], payload["payer_address"]):
            return 402, {}, '{"error":"bad_signature"}'

        settlement = {
            "payment_id": payload["payment_id"],
            "status": "settled",
            "tx_hash": "0xsettled" + payload["nonce"][:24],
        }
        return 200, {X402_PAYMENT_RESPONSE_HEADER: _b64(settlement)}, '{"report":"agent_economy_q2.json"}'


# --- agent client ---
def agent_pay_and_fetch(server: MockResourceServer) -> None:
    print("[agent] GET /api/premium/report")
    status, headers, body = server.get_resource({})
    print(f"[server] -> HTTP {status} {body}")
    assert status == 402

    challenge = _unb64(headers[X402_PAYMENT_REQUIRED_HEADER])
    print(
        f"[agent] parsed challenge: {challenge['amount']} {challenge['currency']} "
        f"on {challenge['network']} -> {challenge['payee_address'][:10]}..."
    )

    signature = sign(canonical_message(challenge, PAYER_ADDRESS))
    payload = {
        "payment_id": challenge["payment_id"],
        "payer_address": PAYER_ADDRESS,
        "amount": challenge["amount"],
        "nonce": challenge["nonce"],
        "signature": signature,
    }
    print("[agent] signed payment payload, retrying with PAYMENT-SIGNATURE header")

    status, response_headers, body = server.get_resource(
        {X402_PAYMENT_SIGNATURE_HEADER: _b64(payload)}
    )
    print(f"[server] -> HTTP {status} {body}")
    assert status == 200

    settlement = _unb64(response_headers[X402_PAYMENT_RESPONSE_HEADER])
    print(f"[agent] settlement: status={settlement['status']} tx={settlement['tx_hash']}")
    print("[demo] OK -- paid resource fetched in one round-trip after 402")


if __name__ == "__main__":
    agent_pay_and_fetch(MockResourceServer())
