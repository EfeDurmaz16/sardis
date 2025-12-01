"""Shared helpers for AP2 mandate testing."""
from __future__ import annotations

import base64
import time
from uuid import uuid4

from nacl import signing

from sardis_protocol.schemas import AP2PaymentExecuteRequest
from sardis_v2_core.identity import AgentIdentity


def build_signed_bundle(domain: str = "merchant.example", amount_minor: int = 100_00) -> AP2PaymentExecuteRequest:
    identity, seed = AgentIdentity.generate()
    signer = signing.SigningKey(seed)
    now = int(time.time())
    expires = now + 600
    subject = identity.agent_id

    def _proof(tag: bytes) -> dict[str, str]:
        return {
            "type": "DataIntegrityProof",
            "verification_method": f"did:agent#ed25519:{identity.agent_id}",
            "created": "2024-01-01T00:00:00Z",
            "proof_value": base64.b64encode(tag).decode(),
        }

    intent = {
        "mandate_id": f"intent-{uuid4().hex}",
        "mandate_type": "intent",
        "issuer": "did:sardis:issuer",
        "subject": subject,
        "expires_at": expires,
        "nonce": "nonce-intent",
        "proof": _proof(b"intent"),
        "domain": domain,
        "purpose": "intent",
        "scope": ["digital"],
        "requested_amount": amount_minor,
    }

    cart = {
        "mandate_id": f"cart-{uuid4().hex}",
        "mandate_type": "cart",
        "issuer": "did:sardis:issuer",
        "subject": subject,
        "expires_at": expires,
        "nonce": "nonce-cart",
        "proof": _proof(b"cart"),
        "domain": domain,
        "purpose": "cart",
        "merchant_domain": domain,
        "line_items": [{"sku": "sku-1", "description": "Test", "amount_minor": amount_minor}],
        "currency": "USD",
        "subtotal_minor": amount_minor,
        "taxes_minor": 0,
    }

    payment = {
        "mandate_id": f"payment-{uuid4().hex}",
        "mandate_type": "payment",
        "issuer": "did:sardis:issuer",
        "subject": subject,
        "expires_at": expires,
        "nonce": "nonce-pay",
        "proof": _proof(b"placeholder"),
        "domain": domain,
        "purpose": "checkout",
        "chain": "base",
        "token": "USDC",
        "amount_minor": amount_minor,
        "destination": "0xmerchant",
        "audit_hash": "audit-hash",
    }

    payload = "|".join(
        [
            payment["mandate_id"],
            payment["subject"],
            str(payment["amount_minor"]),
            payment["token"],
            payment["chain"],
            payment["destination"],
            payment["audit_hash"],
        ]
    ).encode()
    signature = signer.sign(payload).signature
    payment["proof"]["proof_value"] = base64.b64encode(signature).decode()

    return AP2PaymentExecuteRequest(intent=intent, cart=cart, payment=payment)
