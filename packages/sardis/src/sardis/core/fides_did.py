"""FIDES DID utilities for agent identity.

Ported from fides/packages/sdk/src/identity/did.ts.

DID format: did:fides:<base58-ed25519-pubkey>
"""
from __future__ import annotations

from nacl import signing

DID_PREFIX = "did:fides:"
ED25519_PUBLIC_KEY_LENGTH = 32

# Base58 alphabet (Bitcoin variant)
_B58_ALPHABET = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(data: bytes) -> str:
    """Base58 encode (Bitcoin alphabet)."""
    n = int.from_bytes(data, "big")
    result = []
    while n > 0:
        n, remainder = divmod(n, 58)
        result.append(_B58_ALPHABET[remainder:remainder + 1])
    # Preserve leading zero bytes
    for byte in data:
        if byte == 0:
            result.append(b"1")
        else:
            break
    return b"".join(reversed(result)).decode("ascii")


def _b58decode(s: str) -> bytes:
    """Base58 decode (Bitcoin alphabet)."""
    n = 0
    for char in s:
        n = n * 58 + _B58_ALPHABET.index(char.encode("ascii"))
    # Calculate byte length
    result = n.to_bytes((n.bit_length() + 7) // 8, "big") if n else b""
    # Restore leading zero bytes
    pad = 0
    for char in s:
        if char == "1":
            pad += 1
        else:
            break
    return b"\x00" * pad + result


def is_valid_did(did: str) -> bool:
    """Validate a FIDES DID string."""
    if not did.startswith(DID_PREFIX):
        return False
    encoded = did[len(DID_PREFIX):]
    if not encoded:
        return False
    try:
        decoded = _b58decode(encoded)
        return len(decoded) == ED25519_PUBLIC_KEY_LENGTH
    except Exception:
        return False


def generate_did(public_key: bytes) -> str:
    """Generate a FIDES DID from a 32-byte Ed25519 public key."""
    if len(public_key) != ED25519_PUBLIC_KEY_LENGTH:
        raise ValueError(f"Public key must be {ED25519_PUBLIC_KEY_LENGTH} bytes, got {len(public_key)}")
    return f"{DID_PREFIX}{_b58encode(public_key)}"


def parse_did(did: str) -> bytes:
    """Parse a FIDES DID and extract the Ed25519 public key."""
    if not is_valid_did(did):
        raise ValueError(f"Invalid FIDES DID format: expected {DID_PREFIX}<valid-base58-pubkey>")
    encoded = did[len(DID_PREFIX):]
    return _b58decode(encoded)


def generate_did_keypair() -> tuple[str, bytes, bytes]:
    """Generate a new Ed25519 keypair and return (did, public_key, private_key)."""
    signer = signing.SigningKey.generate()
    public_key = bytes(signer.verify_key)
    did = generate_did(public_key)
    return did, public_key, bytes(signer)


def sardis_did_to_fides_did(sardis_did: str, public_key: bytes) -> str | None:
    """Convert a did:sardis:<agent_id> to did:fides:<base58-pubkey>.

    Returns None if the public key is not a valid Ed25519 key.
    """
    if len(public_key) != ED25519_PUBLIC_KEY_LENGTH:
        return None
    return generate_did(public_key)
