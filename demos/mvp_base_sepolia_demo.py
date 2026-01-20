"""
MVP demo: TAP issuance -> AP2 mandate sign -> validate -> execute USDC on Base Sepolia -> deterministic receipt.

Prereqs:
- Run Sardis API locally: uvicorn sardis_api.main:create_app --factory
- Set env:
    SARDIS_CHAIN_MODE=live
    SARDIS_CHAINS__0__NAME=base_sepolia
    SARDIS_CHAINS__0__RPC_URL=<your Base Sepolia RPC>
    SARDIS_EOA_PRIVATE_KEY=<funded testnet key>
    SARDIS_EOA_ADDRESS=<same address>
- Fund the EOA with Base Sepolia ETH + USDC (testnet faucet).
"""
from __future__ import annotations

import base64
import os
import time
import uuid

import requests
from nacl import signing
from nacl.encoding import HexEncoder

BASE_URL = os.getenv("SARDIS_API_BASE_URL", "http://localhost:8000/api/v2/mvp")


def issue_identity(domain: str = "example.com"):
    resp = requests.post(f"{BASE_URL}/tap/issue", json={"domain": domain})
    resp.raise_for_status()
    return resp.json()


def sign_payment_mandate(agent, secret_key_hex: str, destination: str) -> dict:
    mandate_id = f"mandate_{uuid.uuid4().hex[:12]}"
    nonce = str(int(time.time() * 1000))
    expires_at = int(time.time()) + 300
    amount_minor = 5_000_000  # 5 USDC with 6 decimals
    audit_hash = f"audit::{mandate_id}"

    canonical = "|".join(
        [
            mandate_id,
            agent["agent_id"],
            str(amount_minor),
            "USDC",
            "base_sepolia",
            destination,
            audit_hash,
        ]
    ).encode()

    payload = b"|".join(
        [
            agent["domain"].encode(),
            nonce.encode(),
            b"checkout",
            canonical,
        ]
    )

    signing_key = signing.SigningKey(bytes.fromhex(secret_key_hex))
    signature = signing_key.sign(payload).signature
    proof_value = base64.b64encode(signature).decode()

    return {
        "mandate_id": mandate_id,
        "mandate_type": "payment",
        "issuer": agent["agent_id"],
        "subject": agent["agent_id"],
        "expires_at": expires_at,
        "nonce": nonce,
        "domain": agent["domain"],
        "purpose": "checkout",
        "chain": "base_sepolia",
        "token": "USDC",
        "amount_minor": amount_minor,
        "destination": destination,
        "audit_hash": audit_hash,
        "proof": {
            "type": "DataIntegrityProof",
            "verification_method": agent["verification_method"],
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "proof_purpose": "assertionMethod",
            "proof_value": proof_value,
        },
    }


def validate(mandate: dict):
    resp = requests.post(f"{BASE_URL}/mandates/validate", json={"mandate": mandate})
    resp.raise_for_status()
    return resp.json()


def execute(mandate: dict):
    resp = requests.post(f"{BASE_URL}/payments/execute", json={"mandate": mandate})
    resp.raise_for_status()
    return resp.json()


def main():
    print("Issuing TAP identity...")
    identity = issue_identity()
    print(identity)

    # NOTE: private_key is returned only for sandbox/demo. Secure key mgmt required for production.
    secret_key = identity.get("private_key")
    if not secret_key:
        raise SystemExit("No private key returned; provide your own and set private_key in request.")

    destination = os.getenv("DESTINATION_ADDRESS", identity["agent_id"][:42])
    mandate = sign_payment_mandate(identity, secret_key, destination)

    print("Validating mandate...")
    validation = validate(mandate)
    print(validation)
    if not validation["accepted"]:
        raise SystemExit("Mandate rejected")

    print("Executing payment on Base Sepolia...")
    execution = execute(mandate)
    print(execution)

    print("Receipt:")
    print(execution["receipt"])


if __name__ == "__main__":
    main()



