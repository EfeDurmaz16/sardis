"""ERC-8128: Signed HTTP Requests with Ethereum Accounts.

Implements RFC 9421 HTTP Message Signatures using Ethereum secp256k1 keys.
Enables stateless, wallet-based API authentication for AI agents.

Spec: https://eip.tools/eip/8128
Foundation: RFC 9421 (HTTP Message Signatures)
Signing: EIP-191 personal_sign with keccak256

Client side: sign outgoing HTTP requests with agent's Ethereum private key.
Server side: verify incoming requests by recovering the signer's address.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ERC-8128 keyid format: erc8128:<chainId>:<address>
KEYID_PREFIX = "erc8128"
DEFAULT_CHAIN_ID = 1  # Ethereum mainnet
SIGNATURE_LABEL = "sig"
MAX_AGE_SECONDS = 300  # 5 minute default window


@dataclass
class ERC8128SignatureInput:
    """Parsed Signature-Input header fields."""
    keyid: str           # erc8128:<chainId>:<address>
    created: int         # Unix timestamp
    algorithm: str       # Always "erc8128-secp256k1"
    covered_components: list[str]  # e.g. ["@method", "@target-uri", "content-digest"]
    label: str = SIGNATURE_LABEL

    @property
    def chain_id(self) -> int:
        parts = self.keyid.split(":")
        if len(parts) >= 3 and parts[0] == KEYID_PREFIX:
            return int(parts[1])
        return DEFAULT_CHAIN_ID

    @property
    def address(self) -> str:
        parts = self.keyid.split(":")
        if len(parts) >= 3 and parts[0] == KEYID_PREFIX:
            return parts[2]
        return ""


@dataclass
class ERC8128VerificationResult:
    """Result of verifying an ERC-8128 signed request."""
    valid: bool
    signer_address: str | None = None
    chain_id: int | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def build_keyid(address: str, chain_id: int = DEFAULT_CHAIN_ID) -> str:
    """Build ERC-8128 keyid string.

    Args:
        address: Ethereum address (0x-prefixed).
        chain_id: Chain ID (default: 1 for mainnet).

    Returns:
        Keyid string like "erc8128:1:0xABC...def".
    """
    return f"{KEYID_PREFIX}:{chain_id}:{address}"


def compute_content_digest(body: bytes) -> str:
    """Compute SHA-256 Content-Digest header value per RFC 9530.

    Args:
        body: Raw request body bytes.

    Returns:
        Content-Digest header value like "sha-256=:base64hash:".
    """
    digest = hashlib.sha256(body).digest()
    b64 = base64.b64encode(digest).decode("ascii")
    return f"sha-256=:{b64}:"


def build_signature_base(
    method: str,
    target_uri: str,
    headers: dict[str, str],
    covered_components: list[str],
    created: int,
    keyid: str,
) -> str:
    """Build the RFC 9421 signature base string.

    Args:
        method: HTTP method (GET, POST, etc.).
        target_uri: Full request URI.
        headers: Request headers (lowercase keys).
        covered_components: Components to include in signature.
        created: Unix timestamp.
        keyid: ERC-8128 keyid string.

    Returns:
        Signature base string to be signed.
    """
    lines = []

    for component in covered_components:
        if component == "@method":
            lines.append(f'"@method": {method.upper()}')
        elif component == "@target-uri":
            lines.append(f'"@target-uri": {target_uri}')
        elif component == "@authority":
            # Extract authority from URI
            from urllib.parse import urlparse
            parsed = urlparse(target_uri)
            lines.append(f'"@authority": {parsed.netloc}')
        elif component == "@path":
            from urllib.parse import urlparse
            parsed = urlparse(target_uri)
            lines.append(f'"@path": {parsed.path}')
        else:
            # Regular header
            header_key = component.lower()
            value = headers.get(header_key, "")
            lines.append(f'"{header_key}": {value}')

    # Signature params line
    components_str = " ".join(f'"{c}"' for c in covered_components)
    params = f"({components_str});created={created};keyid=\"{keyid}\";alg=\"erc8128-secp256k1\""
    lines.append(f'"@signature-params": {params}')

    return "\n".join(lines)


def build_signature_input_header(
    covered_components: list[str],
    created: int,
    keyid: str,
    label: str = SIGNATURE_LABEL,
) -> str:
    """Build the Signature-Input header value.

    Returns:
        Header value like: sig=("@method" "@target-uri" "content-digest");created=...;keyid="...";alg="..."
    """
    components_str = " ".join(f'"{c}"' for c in covered_components)
    return (
        f'{label}=({components_str});'
        f'created={created};'
        f'keyid="{keyid}";'
        f'alg="erc8128-secp256k1"'
    )


def sign_request(
    method: str,
    target_uri: str,
    body: bytes | None = None,
    headers: dict[str, str] | None = None,
    private_key: str | bytes = b"",
    address: str = "",
    chain_id: int = DEFAULT_CHAIN_ID,
    covered_components: list[str] | None = None,
) -> dict[str, str]:
    """Sign an HTTP request per ERC-8128.

    Uses EIP-191 personal_sign with secp256k1 to sign the RFC 9421
    signature base. Returns headers to add to the request.

    Args:
        method: HTTP method.
        target_uri: Full request URI.
        body: Request body (used for Content-Digest).
        headers: Existing request headers.
        private_key: Ethereum private key (hex string or bytes).
        address: Signer's Ethereum address.
        chain_id: Chain ID for keyid.
        covered_components: Components to sign. Defaults to standard set.

    Returns:
        Dict of headers to add: Content-Digest, Signature-Input, Signature.
    """
    from eth_account import Account
    from eth_account.messages import encode_defunct

    headers = headers or {}
    created = int(time.time())
    keyid = build_keyid(address, chain_id)

    if covered_components is None:
        covered_components = ["@method", "@target-uri"]
        if body:
            covered_components.append("content-digest")

    # Compute content digest if body present
    result_headers: dict[str, str] = {}
    if body:
        content_digest = compute_content_digest(body)
        result_headers["content-digest"] = content_digest
        headers["content-digest"] = content_digest

    # Build signature base
    sig_base = build_signature_base(
        method=method,
        target_uri=target_uri,
        headers=headers,
        covered_components=covered_components,
        created=created,
        keyid=keyid,
    )

    # Sign with EIP-191 (personal_sign)
    message = encode_defunct(text=sig_base)
    if isinstance(private_key, str):
        if private_key.startswith("0x"):
            key_bytes = bytes.fromhex(private_key[2:])
        else:
            key_bytes = bytes.fromhex(private_key)
    else:
        key_bytes = private_key

    signed = Account.sign_message(message, private_key=key_bytes)
    sig_b64 = base64.b64encode(signed.signature).decode("ascii")

    # Build headers
    result_headers["signature-input"] = build_signature_input_header(
        covered_components=covered_components,
        created=created,
        keyid=keyid,
    )
    result_headers["signature"] = f"{SIGNATURE_LABEL}=:{sig_b64}:"

    return result_headers


def parse_signature_input(header_value: str) -> ERC8128SignatureInput | None:
    """Parse a Signature-Input header value.

    Args:
        header_value: Raw Signature-Input header string.

    Returns:
        Parsed ERC8128SignatureInput or None if parsing fails.
    """
    try:
        # Format: sig=("@method" "@target-uri" ...);created=123;keyid="erc8128:1:0x...";alg="..."
        label, rest = header_value.split("=", 1)
        label = label.strip()

        # Extract covered components from parentheses
        paren_start = rest.index("(")
        paren_end = rest.index(")")
        components_str = rest[paren_start + 1:paren_end]
        covered = [c.strip('"') for c in components_str.split() if c.strip('"')]

        # Parse params after closing paren
        params_str = rest[paren_end + 1:]
        params: dict[str, str] = {}
        for part in params_str.split(";"):
            part = part.strip()
            if "=" in part:
                k, v = part.split("=", 1)
                params[k.strip()] = v.strip().strip('"')

        return ERC8128SignatureInput(
            keyid=params.get("keyid", ""),
            created=int(params.get("created", "0")),
            algorithm=params.get("alg", "erc8128-secp256k1"),
            covered_components=covered,
            label=label,
        )
    except (ValueError, IndexError, KeyError) as e:
        logger.warning("Failed to parse Signature-Input: %s", e)
        return None


def extract_signature_bytes(header_value: str, label: str = SIGNATURE_LABEL) -> bytes | None:
    """Extract raw signature bytes from a Signature header.

    Args:
        header_value: Raw Signature header string (e.g. "sig=:base64...:").
        label: Expected signature label.

    Returns:
        Raw signature bytes or None.
    """
    try:
        prefix = f"{label}=:"
        if not header_value.startswith(prefix):
            return None
        b64 = header_value[len(prefix):-1]  # Strip trailing ":"
        return base64.b64decode(b64)
    except Exception as e:
        logger.warning("Failed to extract signature bytes: %s", e)
        return None


def verify_request(
    method: str,
    target_uri: str,
    headers: dict[str, str],
    body: bytes | None = None,
    max_age_seconds: int = MAX_AGE_SECONDS,
) -> ERC8128VerificationResult:
    """Verify an ERC-8128 signed HTTP request.

    Recovers the signer's Ethereum address from the signature and
    validates timestamp freshness and content digest.

    Args:
        method: HTTP method.
        target_uri: Full request URI.
        headers: All request headers (case-insensitive keys).
        body: Request body for Content-Digest verification.
        max_age_seconds: Maximum acceptable signature age.

    Returns:
        ERC8128VerificationResult with validity and recovered address.
    """
    from eth_account import Account
    from eth_account.messages import encode_defunct

    # Normalize header keys to lowercase
    h = {k.lower(): v for k, v in headers.items()}

    # 1. Parse Signature-Input
    sig_input_raw = h.get("signature-input")
    if not sig_input_raw:
        return ERC8128VerificationResult(
            valid=False, error="Missing Signature-Input header"
        )

    sig_input = parse_signature_input(sig_input_raw)
    if not sig_input:
        return ERC8128VerificationResult(
            valid=False, error="Invalid Signature-Input format"
        )

    # 2. Check timestamp freshness
    now = int(time.time())
    age = now - sig_input.created
    if age < 0 or age > max_age_seconds:
        return ERC8128VerificationResult(
            valid=False,
            error=f"Signature expired: age={age}s, max={max_age_seconds}s",
        )

    # 3. Verify Content-Digest if body is present
    if body and "content-digest" in sig_input.covered_components:
        expected_digest = compute_content_digest(body)
        actual_digest = h.get("content-digest", "")
        if expected_digest != actual_digest:
            return ERC8128VerificationResult(
                valid=False, error="Content-Digest mismatch"
            )

    # 4. Extract signature bytes
    sig_raw = h.get("signature")
    if not sig_raw:
        return ERC8128VerificationResult(
            valid=False, error="Missing Signature header"
        )

    sig_bytes = extract_signature_bytes(sig_raw, sig_input.label)
    if not sig_bytes:
        return ERC8128VerificationResult(
            valid=False, error="Invalid Signature format"
        )

    # 5. Reconstruct signature base
    sig_base = build_signature_base(
        method=method,
        target_uri=target_uri,
        headers=h,
        covered_components=sig_input.covered_components,
        created=sig_input.created,
        keyid=sig_input.keyid,
    )

    # 6. Recover signer address via EIP-191
    message = encode_defunct(text=sig_base)
    try:
        recovered_address = Account.recover_message(message, signature=sig_bytes)
    except Exception as e:
        return ERC8128VerificationResult(
            valid=False, error=f"Signature recovery failed: {e}"
        )

    # 7. Compare recovered address with claimed keyid address
    claimed_address = sig_input.address
    if recovered_address.lower() != claimed_address.lower():
        return ERC8128VerificationResult(
            valid=False,
            signer_address=recovered_address,
            error=(
                f"Address mismatch: recovered {recovered_address}, "
                f"claimed {claimed_address}"
            ),
        )

    return ERC8128VerificationResult(
        valid=True,
        signer_address=recovered_address,
        chain_id=sig_input.chain_id,
        metadata={
            "created": sig_input.created,
            "covered_components": sig_input.covered_components,
            "age_seconds": age,
        },
    )
