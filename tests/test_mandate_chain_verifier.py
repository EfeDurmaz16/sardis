import base64
import time
from uuid import uuid4

from nacl import signing

from sardis_protocol.schemas import AP2PaymentExecuteRequest
from sardis_protocol.verifier import MandateVerifier
from sardis_v2_core import SardisSettings
from sardis_v2_core.identity import AgentIdentity
from sardis_v2_core.mandates import VCProof


def _settings() -> SardisSettings:
    return SardisSettings(
        allowed_domains=["merchant.example"],
        chains=[
            {
                "name": "base",
                "rpc_url": "https://base.example",
                "chain_id": 84532,
                "stablecoins": ["USDC"],
                "settlement_vault": "0x0000000000000000000000000000000000000000",
            }
        ],
        mpc={"name": "turnkey", "api_base": "https://turnkey.example", "credential_id": "cred"},
    )


def _make_bundle():
    identity, seed = AgentIdentity.generate()
    signer = signing.SigningKey(seed)
    now = int(time.time())
    expires = now + 600
    subject = identity.agent_id
    domain = "merchant.example"

    intent = {
        "mandate_id": f"intent-{uuid4().hex}",
        "mandate_type": "intent",
        "issuer": "did:sardis:issuer",
        "subject": subject,
        "expires_at": expires,
        "nonce": "nonce-intent",
        "proof": {
            "type": "DataIntegrityProof",
            "verification_method": f"did:agent#{identity.algorithm}:{identity.agent_id}",
            "created": "2024-01-01T00:00:00Z",
            "proof_value": base64.b64encode(b"intent-proof").decode(),
        },
        "domain": domain,
        "purpose": "intent",
        "scope": ["digital"],
        "requested_amount": 100_00,
        "issuer_policy": "standard",
    }

    cart = {
        "mandate_id": f"cart-{uuid4().hex}",
        "mandate_type": "cart",
        "issuer": "did:sardis:issuer",
        "subject": subject,
        "expires_at": expires,
        "nonce": "nonce-cart",
        "proof": {
            "type": "DataIntegrityProof",
            "verification_method": f"did:agent#{identity.algorithm}:{identity.agent_id}",
            "created": "2024-01-01T00:00:00Z",
            "proof_value": base64.b64encode(b"cart-proof").decode(),
        },
        "domain": domain,
        "purpose": "cart",
        "merchant_domain": domain,
        "line_items": [{"sku": "sku-1", "description": "Test", "amount_minor": 100_00}],
        "currency": "USD",
        "subtotal_minor": 100_00,
        "taxes_minor": 0,
    }

    payment_amount = 100_00
    payment = {
        "mandate_id": f"payment-{uuid4().hex}",
        "mandate_type": "payment",
        "issuer": "did:sardis:issuer",
        "subject": subject,
        "expires_at": expires,
        "nonce": "nonce-pay",
        "proof": {
            "type": "DataIntegrityProof",
            "verification_method": f"did:agent#ed25519:{identity.agent_id}",
            "created": "2024-01-01T00:00:00Z",
            "proof_value": "",
        },
        "domain": domain,
        "purpose": "checkout",
        "chain": "base",
        "token": "USDC",
        "amount_minor": payment_amount,
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
    proof_value = base64.b64encode(signer.sign(payload).signature).decode()
    payment["proof"]["proof_value"] = proof_value

    return AP2PaymentExecuteRequest(intent=intent, cart=cart, payment=payment)


def test_verify_chain_success():
    verifier = MandateVerifier(settings=_settings())
    bundle = _make_bundle()
    result = verifier.verify_chain(bundle)
    assert result.accepted
    assert result.chain is not None
    assert result.chain.payment.mandate_id.startswith("payment-")


def test_verify_chain_subject_mismatch_fails():
    verifier = MandateVerifier(settings=_settings())
    bundle = _make_bundle()
    bundle.cart["subject"] = "someone-else"
    result = verifier.verify_chain(bundle)
    assert not result.accepted
    assert result.reason == "subject_mismatch"
