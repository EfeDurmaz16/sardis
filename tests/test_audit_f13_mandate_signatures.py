"""Test that Intent and Cart mandate signatures are verified."""
import base64
import time

from nacl.signing import SigningKey

from sardis_v2_core import SardisSettings
from sardis_v2_core.mandates import IntentMandate, CartMandate, VCProof
from sardis_protocol.verifier import MandateVerifier
from sardis_protocol.schemas import AP2PaymentExecuteRequest


def _keypair():
    """Create Ed25519 keypair using nacl."""
    sk = SigningKey.generate()
    return sk, bytes(sk.verify_key).hex()


def test_intent_signature_verified():
    """Intent mandate signatures must be verified."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)
    sk, pub_hex = _keypair()

    mandate_id = "test-intent"
    agent_id = "agent:test@example.com"
    domain = "example.com"
    nonce = "test-nonce"
    purpose = "intent"
    expires_at = int(time.time()) + 3600

    # Build intent canonical payload
    payload = "|".join([
        mandate_id, agent_id, "intent",
        "payments,transfers", "1000000", str(expires_at),
    ]).encode()

    full_payload = b"|".join([domain.encode(), nonce.encode(), purpose.encode(), payload])
    sig = sk.sign(full_payload).signature

    intent = IntentMandate(
        mandate_id=mandate_id,
        mandate_type="intent",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at,
        domain=domain,
        purpose=purpose,
        nonce=nonce,
        scope=["payments", "transfers"],
        requested_amount=1000000,
        proof=VCProof(
            verification_method=f"ed25519:{pub_hex}",
            created=str(int(time.time())),
            proof_value=base64.b64encode(sig).decode(),
        ),
    )

    result = verifier.verify(intent)
    assert result.accepted, f"Intent signature should be valid: {result.reason}"


def test_intent_invalid_signature_rejected():
    """Intent with invalid signature must be rejected."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)
    sk, pub_hex = _keypair()

    # Sign WRONG payload
    sig = sk.sign(b"completely wrong data").signature

    intent = IntentMandate(
        mandate_id="test-intent-bad",
        mandate_type="intent",
        subject="agent:test@example.com",
        issuer="agent:test@example.com",
        expires_at=int(time.time()) + 3600,
        domain="example.com",
        purpose="intent",
        nonce="test-nonce",
        scope=["payments"],
        requested_amount=1000000,
        proof=VCProof(
            verification_method=f"ed25519:{pub_hex}",
            created=str(int(time.time())),
            proof_value=base64.b64encode(sig).decode(),
        ),
    )

    result = verifier.verify(intent)
    assert not result.accepted, "Invalid intent signature should be rejected"


def test_cart_signature_verified():
    """Cart mandate signatures must be verified."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)
    sk, pub_hex = _keypair()

    mandate_id = "test-cart"
    agent_id = "agent:test@example.com"
    domain = "example.com"
    nonce = "test-nonce"
    purpose = "cart"
    expires_at = int(time.time()) + 3600
    merchant_domain = "merchant.com"

    line_items = [
        {"item_id": "item1", "name": "Product A", "quantity": 2, "price_minor": 5000},
        {"item_id": "item2", "name": "Product B", "quantity": 1, "price_minor": 3000},
    ]

    sorted_items = sorted(line_items, key=lambda x: (x.get("item_id", ""), x.get("name", "")))
    items_str = ",".join(
        f"{it.get('item_id', '')}:{it.get('name', '')}:{it.get('quantity', 0)}:{it.get('price_minor', 0)}"
        for it in sorted_items
    )
    payload = "|".join([
        mandate_id, agent_id, items_str,
        "13000", "1000", "USD", merchant_domain, str(expires_at),
    ]).encode()

    full_payload = b"|".join([domain.encode(), nonce.encode(), purpose.encode(), payload])
    sig = sk.sign(full_payload).signature

    cart = CartMandate(
        mandate_id=mandate_id,
        mandate_type="cart",
        subject=agent_id,
        issuer=agent_id,
        expires_at=expires_at,
        domain=domain,
        purpose=purpose,
        nonce=nonce,
        line_items=line_items,
        merchant_domain=merchant_domain,
        currency="USD",
        subtotal_minor=13000,
        taxes_minor=1000,
        proof=VCProof(
            verification_method=f"ed25519:{pub_hex}",
            created=str(int(time.time())),
            proof_value=base64.b64encode(sig).decode(),
        ),
    )

    result = verifier.verify(cart)
    assert result.accepted, f"Cart signature should be valid: {result.reason}"


def test_cart_invalid_signature_rejected():
    """Cart with invalid signature must be rejected."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)
    sk, pub_hex = _keypair()

    sig = sk.sign(b"wrong cart data").signature

    cart = CartMandate(
        mandate_id="test-cart-bad",
        mandate_type="cart",
        subject="agent:test@example.com",
        issuer="agent:test@example.com",
        expires_at=int(time.time()) + 3600,
        domain="example.com",
        purpose="cart",
        nonce="test-nonce",
        line_items=[{"item_id": "item1", "name": "Product", "quantity": 1, "price_minor": 1000}],
        merchant_domain="merchant.com",
        currency="USD",
        subtotal_minor=1000,
        taxes_minor=0,
        proof=VCProof(
            verification_method=f"ed25519:{pub_hex}",
            created=str(int(time.time())),
            proof_value=base64.b64encode(sig).decode(),
        ),
    )

    result = verifier.verify(cart)
    assert not result.accepted, "Invalid cart signature should be rejected"


def test_verify_chain_checks_all_signatures():
    """verify_chain must verify signatures for intent, cart, and payment."""
    settings = SardisSettings(allowed_domains=["example.com"])
    verifier = MandateVerifier(settings)
    sk, pub_hex = _keypair()
    verification_method = f"ed25519:{pub_hex}"

    agent_id = "agent:test@example.com"
    expires_at = int(time.time()) + 3600

    # Create intent with INVALID signature
    sig = sk.sign(b"wrong intent payload").signature

    intent_dict = {
        "mandate_id": "bad-intent",
        "mandate_type": "intent",
        "subject": agent_id,
        "issuer": agent_id,
        "expires_at": expires_at,
        "domain": "example.com",
        "purpose": "intent",
        "nonce": "nonce1",
        "scope": ["payments"],
        "requested_amount": 2000000,
        "proof": {
            "verification_method": verification_method,
            "created": str(int(time.time())),
            "proof_value": base64.b64encode(sig).decode(),
        },
    }

    cart_dict = {
        "mandate_id": "test-cart",
        "mandate_type": "cart",
        "subject": agent_id,
        "issuer": agent_id,
        "expires_at": expires_at,
        "domain": "example.com",
        "purpose": "cart",
        "nonce": "nonce2",
        "line_items": [{"item_id": "1", "name": "Item", "quantity": 1, "price_minor": 1000}],
        "merchant_domain": "merchant.com",
        "currency": "USD",
        "subtotal_minor": 1000,
        "taxes_minor": 0,
        "proof": {
            "verification_method": verification_method,
            "created": str(int(time.time())),
            "proof_value": base64.b64encode(b"fake").decode(),
        },
    }

    payment_dict = {
        "mandate_id": "test-payment",
        "mandate_type": "payment",
        "subject": agent_id,
        "issuer": agent_id,
        "expires_at": expires_at,
        "domain": "example.com",
        "purpose": "checkout",
        "nonce": "nonce3",
        "chain": "base",
        "token": "USDC",
        "amount_minor": 1000,
        "destination": "0x1234567890123456789012345678901234567890",
        "audit_hash": "test-hash",
        "merchant_domain": "merchant.com",
        "proof": {
            "verification_method": verification_method,
            "created": str(int(time.time())),
            "proof_value": base64.b64encode(b"fake").decode(),
        },
    }

    bundle = AP2PaymentExecuteRequest(
        intent=intent_dict,
        cart=cart_dict,
        payment=payment_dict,
    )

    result = verifier.verify_chain(bundle)
    assert not result.accepted, "Chain with invalid intent signature should be rejected"
