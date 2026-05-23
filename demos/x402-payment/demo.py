"""x402 HTTP 402 Payment Required — end-to-end demo.

Spins up an in-process mock resource server that returns HTTP 402 with an
x402 PaymentRequired challenge. A client (the "agent") parses the challenge,
constructs a signed payment payload using Sardis' x402 protocol primitives,
sends it back via the PAYMENT-SIGNATURE header, and the server verifies +
settles.

No network, no API key — uses Sardis sandbox primitives directly.
"""
from __future__ import annotations

import hashlib
import hmac

from sardis.protocol.x402 import (
    X402_PAYMENT_REQUIRED_HEADER,
    X402_PAYMENT_RESPONSE_HEADER,
    X402_PAYMENT_SIGNATURE_HEADER,
    X402HeaderBuilder,
    X402PaymentPayload,
    generate_challenge,
    parse_challenge_header,
    verify_payment_payload,
)

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


# --- mock x402 server ---
class MockResourceServer:
    def __init__(self) -> None:
        self._open_challenges: dict[str, object] = {}

    def get_resource(self, headers: dict[str, str]) -> tuple[int, dict[str, str], str]:
        if X402_PAYMENT_SIGNATURE_HEADER not in headers:
            response = generate_challenge(
                resource_uri="/api/premium/report",
                amount="1000000",  # 1 USDC in smallest unit
                currency="USDC",
                payee_address="0xB0bdeadbeefdeadbeefdeadbeefdeadbeefB0Bd",
                network="base-sepolia",
                token_address="0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                ttl_seconds=300,
            )
            self._open_challenges[response.challenge.nonce] = response.challenge
            headers_out = X402HeaderBuilder.build_payment_required_header(response.challenge)
            return 402, headers_out, '{"error":"payment_required"}'

        payload = X402HeaderBuilder.parse_payment_signature_header(
            headers[X402_PAYMENT_SIGNATURE_HEADER]
        )
        challenge = self._open_challenges.get(payload.nonce)
        if challenge is None:
            return 400, {}, '{"error":"unknown_nonce"}'

        result = verify_payment_payload(
            payload, challenge, verify_signature_fn=verify
        )
        if not result.accepted:
            return 402, {}, f'{{"error":"{result.reason}"}}'

        settlement = {
            "payment_id": payload.payment_id,
            "status": "settled",
            "tx_hash": "0xsettled" + payload.nonce[:24],
        }
        response_headers = X402HeaderBuilder.build_payment_response_header(settlement)
        return 200, response_headers, '{"report":"agent_economy_q2.json"}'


# --- agent client ---
def agent_pay_and_fetch(server: MockResourceServer) -> None:
    print("[agent] GET /api/premium/report")
    status, headers, body = server.get_resource({})
    print(f"[server] -> HTTP {status} {body}")
    assert status == 402

    challenge_header = headers[X402_PAYMENT_REQUIRED_HEADER]
    challenge = parse_challenge_header(challenge_header)
    print(
        f"[agent] parsed challenge: {challenge.amount} {challenge.currency} "
        f"on {challenge.network} -> {challenge.payee_address[:10]}..."
    )

    canonical = "|".join([
        challenge.payment_id,
        PAYER_ADDRESS,
        challenge.amount,
        challenge.nonce,
        challenge.payee_address,
        challenge.network,
    ]).encode()
    signature = sign(canonical)

    payload = X402PaymentPayload(
        payment_id=challenge.payment_id,
        payer_address=PAYER_ADDRESS,
        amount=challenge.amount,
        nonce=challenge.nonce,
        signature=signature,
    )
    pay_headers = X402HeaderBuilder.build_payment_signature_header(payload)
    print("[agent] signed payment payload, retrying with PAYMENT-SIGNATURE header")

    status, response_headers, body = server.get_resource(pay_headers)
    print(f"[server] -> HTTP {status} {body}")
    assert status == 200

    settlement_header = response_headers[X402_PAYMENT_RESPONSE_HEADER]
    print(f"[agent] settlement header received: {settlement_header[:32]}...")
    print("[demo] OK — paid resource fetched in one round-trip after 402")


if __name__ == "__main__":
    agent_pay_and_fetch(MockResourceServer())
