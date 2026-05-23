"""RFC 9421 HTTP Message Signatures for FIDES-authenticated A2A payments.

Implements HTTP message signing and verification using Ed25519 keys,
following RFC 9421 (HTTP Message Signatures) format.

Signature format:
    sig1=("@method" "@target-uri" "@authority" "content-type");
    created=UNIX;expires=UNIX;nonce="UUID";keyid="did:fides:...";alg="ed25519"

Content-Digest:
    sha-256=:BASE64_HASH: (SHA-256 of body, base64-encoded)
"""
from __future__ import annotations

import base64
import hashlib
import time
import uuid
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse


@dataclass(frozen=True)
class VerifyResult:
    """Result of verifying an RFC 9421 signature."""
    valid: bool
    error: str | None = None
    keyid: str | None = None
    created: int | None = None
    expires: int | None = None


# Default signature validity window (seconds)
DEFAULT_SIGNATURE_TTL = 300
# Maximum clock skew allowed (seconds)
MAX_CLOCK_SKEW = 30


def _compute_content_digest(body: bytes | str) -> str:
    """Compute SHA-256 Content-Digest header value.

    Format: sha-256=:BASE64_HASH:
    """
    if isinstance(body, str):
        body = body.encode()
    digest = hashlib.sha256(body).digest()
    b64 = base64.b64encode(digest).decode()
    return f"sha-256=:{b64}:"


def _build_signature_base(
    method: str,
    url: str,
    headers: dict[str, str],
    covered_components: list[str],
) -> str:
    """Build the signature base string per RFC 9421 Section 2.5.

    Each component is rendered as:
        "@method": GET
        "@target-uri": https://example.com/path
        "content-type": application/json
    """
    parsed = urlparse(url)
    lines = []

    for component in covered_components:
        if component == "@method":
            lines.append(f'"@method": {method.upper()}')
        elif component == "@target-uri":
            lines.append(f'"@target-uri": {url}')
        elif component == "@authority":
            authority = parsed.netloc or parsed.hostname or ""
            lines.append(f'"@authority": {authority}')
        else:
            # Regular header field
            header_value = headers.get(component, headers.get(component.lower(), ""))
            lines.append(f'"{component}": {header_value}')

    return "\n".join(lines)


def _build_signature_params(
    covered_components: list[str],
    created: int,
    expires: int,
    nonce: str,
    keyid: str,
    alg: str = "ed25519",
) -> str:
    """Build Signature-Input parameter string."""
    components = " ".join(f'"{c}"' for c in covered_components)
    return (
        f"sig1=({components});"
        f"created={created};"
        f"expires={expires};"
        f'nonce="{nonce}";'
        f'keyid="{keyid}";'
        f'alg="{alg}"'
    )


def sign_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | str,
    private_key: bytes,
    keyid: str,
    ttl: int = DEFAULT_SIGNATURE_TTL,
) -> dict[str, str]:
    """Sign an HTTP request per RFC 9421.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: Full request URL
        headers: Request headers (will be augmented with signature headers)
        body: Request body (for Content-Digest)
        private_key: Ed25519 private key (32 or 64 bytes)
        keyid: Key identifier (typically did:fides:...)
        ttl: Signature validity in seconds

    Returns:
        Dict of signature headers to add: Content-Digest, Signature-Input, Signature
    """
    try:
        from nacl.signing import SigningKey
    except ImportError:
        raise ImportError("PyNaCl is required for RFC 9421 signing: pip install pynacl")

    now = int(time.time())
    nonce = uuid.uuid4().hex

    # Compute content digest
    content_digest = _compute_content_digest(body)

    # Covered components
    covered = ["@method", "@target-uri", "@authority", "content-type", "content-digest"]

    # Build headers with content-digest
    sign_headers = dict(headers)
    sign_headers["content-digest"] = content_digest

    # Build signature base
    sig_base = _build_signature_base(method, url, sign_headers, covered)

    # Build signature params
    sig_params = _build_signature_params(
        covered, created=now, expires=now + ttl, nonce=nonce, keyid=keyid,
    )

    # Append params line to signature base
    full_base = f"{sig_base}\n\"@signature-params\": {sig_params}"

    # Sign with Ed25519
    if len(private_key) == 64:
        signing_key = SigningKey(private_key[:32])
    else:
        signing_key = SigningKey(private_key)

    signed = signing_key.sign(full_base.encode())
    signature_b64 = base64.b64encode(signed.signature).decode()

    return {
        "Content-Digest": content_digest,
        "Signature-Input": sig_params,
        "Signature": f"sig1=:{signature_b64}:",
    }


def verify_request(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | str,
    public_key: bytes,
) -> VerifyResult:
    """Verify an RFC 9421 signed HTTP request.

    Args:
        method: HTTP method
        url: Full request URL
        headers: Request headers (must include Signature, Signature-Input, Content-Digest)
        body: Request body
        public_key: Ed25519 public key (32 bytes)

    Returns:
        VerifyResult with validity status
    """
    try:
        from nacl.exceptions import BadSignatureError
        from nacl.signing import VerifyKey
    except ImportError:
        return VerifyResult(valid=False, error="PyNaCl not installed")

    # Normalize header keys to lowercase for lookup
    norm_headers = {k.lower(): v for k, v in headers.items()}

    # Extract signature components
    sig_input = norm_headers.get("signature-input", "")
    sig_value = norm_headers.get("signature", "")
    content_digest = norm_headers.get("content-digest", "")

    if not sig_input or not sig_value:
        return VerifyResult(valid=False, error="Missing Signature or Signature-Input headers")
    if not content_digest:
        return VerifyResult(valid=False, error="Missing Content-Digest header")

    # Verify content digest
    expected_digest = _compute_content_digest(body)
    if content_digest != expected_digest:
        return VerifyResult(valid=False, error="Content-Digest mismatch")

    # Parse signature parameters
    params = _parse_signature_params(sig_input)
    if params is None:
        return VerifyResult(valid=False, error="Failed to parse Signature-Input")

    # Check expiry
    now = int(time.time())
    created = params.get("created", 0)
    expires = params.get("expires", 0)

    if created > now + MAX_CLOCK_SKEW:
        return VerifyResult(
            valid=False, error="Signature created in the future",
            keyid=params.get("keyid"), created=created, expires=expires,
        )
    if expires and now > expires + MAX_CLOCK_SKEW:
        return VerifyResult(
            valid=False, error="Signature expired",
            keyid=params.get("keyid"), created=created, expires=expires,
        )

    # Reconstruct signature base
    covered = params.get("components", [])
    sig_base = _build_signature_base(method, url, norm_headers, covered)
    full_base = f"{sig_base}\n\"@signature-params\": {sig_input}"

    # Extract raw signature bytes
    sig_b64 = sig_value
    if sig_b64.startswith("sig1=:") and sig_b64.endswith(":"):
        sig_b64 = sig_b64[6:-1]
    elif sig_b64.startswith("sig1="):
        sig_b64 = sig_b64[5:]

    try:
        signature_bytes = base64.b64decode(sig_b64)
    except Exception:
        return VerifyResult(valid=False, error="Invalid signature encoding")

    # Verify Ed25519 signature
    try:
        verify_key = VerifyKey(public_key)
        verify_key.verify(full_base.encode(), signature_bytes)
    except BadSignatureError:
        return VerifyResult(
            valid=False, error="Signature verification failed",
            keyid=params.get("keyid"), created=created, expires=expires,
        )
    except Exception as e:
        return VerifyResult(valid=False, error=f"Verification error: {e}")

    return VerifyResult(
        valid=True,
        keyid=params.get("keyid"),
        created=created,
        expires=expires,
    )


def _parse_signature_params(sig_input: str) -> dict[str, Any] | None:
    """Parse RFC 9421 Signature-Input into components dict.

    Example input:
        sig1=("@method" "@target-uri" "@authority" "content-type");created=1234;expires=5678;nonce="abc";keyid="did:fides:...";alg="ed25519"
    """
    try:
        # Remove sig1= prefix if present
        s = sig_input
        if s.startswith("sig1="):
            s = s[5:]

        result: dict[str, Any] = {}

        # Extract covered components from parentheses
        if "(" in s and ")" in s:
            paren_start = s.index("(")
            paren_end = s.index(")")
            components_str = s[paren_start + 1 : paren_end]
            result["components"] = [
                c.strip('"') for c in components_str.split() if c.strip('"')
            ]
            s = s[paren_end + 1 :]

        # Parse key=value pairs after components
        for part in s.split(";"):
            part = part.strip()
            if not part or "=" not in part:
                continue
            key, value = part.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"')
            if key in ("created", "expires"):
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = value
            else:
                result[key] = value

        return result
    except Exception:
        return None
