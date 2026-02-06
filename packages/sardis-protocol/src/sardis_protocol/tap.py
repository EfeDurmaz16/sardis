"""TAP (Trusted Agent Protocol) request validation helpers.

Implements the baseline checks described by TAP merchant guidance:
- RFC 9421-like Signature-Input/Signature structure checks
- required fields and tag semantics
- timestamp validity + max window (default 8 minutes)
- nonce replay prevention hook
- linked object checks for agentic consumer/payment containers
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import time
from typing import Any, Mapping, MutableSet, Sequence


TAP_ALLOWED_TAGS = {"agent-browser-auth", "agent-payer-auth"}
TAP_MAX_TIME_WINDOW_SECONDS = 8 * 60
TAP_ALLOWED_MESSAGE_ALGS = {"ed25519", "ecdsa-p256"}
TAP_ALLOWED_OBJECT_ALGS = {"ed25519", "ps256", "rs256"}
TAP_PROTOCOL_VERSION = "1.0"
TAP_SUPPORTED_VERSIONS = ["1.0"]


@dataclass(slots=True)
class TapSignatureInput:
    label: str
    components: list[str]
    created: int
    expires: int
    keyid: str
    alg: str
    nonce: str
    tag: str

    def signature_params(self) -> str:
        components_str = " ".join(f'"{component}"' for component in self.components)
        return (
            f'{self.label}=({components_str});'
            f"created={self.created};"
            f'keyid="{self.keyid}";'
            f'alg="{self.alg}";'
            f"expires={self.expires};"
            f'nonce="{self.nonce}";'
            f'tag="{self.tag}"'
        )


@dataclass(slots=True)
class TapVerificationResult:
    accepted: bool
    reason: str | None = None
    signature_input: TapSignatureInput | None = None
    signature_b64: str | None = None
    signature_base: str | None = None
    tap_version: str | None = None


_SIG_INPUT_RE = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z0-9_-]*)=\((?P<components>[^)]*)\)\s*;(?P<params>.+)$")
_SIG_RE = re.compile(r"^\s*(?P<label>[A-Za-z][A-Za-z0-9_-]*)=:(?P<sig>[A-Za-z0-9+/=_-]+):\s*$")
_COMPONENT_RE = re.compile(r'"([^"]+)"')
_PARAM_RE = re.compile(r"^\s*(?P<key>[A-Za-z0-9_-]+)\s*=\s*(?P<value>.+?)\s*$")


def validate_tap_version(version: str) -> tuple[bool, str | None]:
    """Validate a TAP protocol version string."""
    if not version:
        return True, None  # Missing version defaults to current
    if version in TAP_SUPPORTED_VERSIONS:
        return True, None
    major = version.split(".")[0] if "." in version else version
    supported_majors = {v.split(".")[0] for v in TAP_SUPPORTED_VERSIONS}
    if major not in supported_majors:
        return False, f"tap_version_unsupported:{version}"
    return True, None  # Known major, unknown minor - accept with warning


def parse_signature_input(header_value: str) -> TapSignatureInput:
    """
    Parse a TAP Signature-Input header.

    Expected shape (single signature):
      sig2=("@authority" "@path");created=...;keyid="...";alg="...";expires=...;nonce="...";tag="..."
    """
    match = _SIG_INPUT_RE.match(header_value or "")
    if not match:
        raise ValueError("invalid_signature_input_format")

    label = match.group("label")
    components_raw = match.group("components")
    params_raw = match.group("params")

    components = _COMPONENT_RE.findall(components_raw)
    if not components:
        raise ValueError("signature_input_missing_components")

    parsed_params: dict[str, str] = {}
    for chunk in params_raw.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        p = _PARAM_RE.match(chunk)
        if not p:
            raise ValueError("invalid_signature_input_param")
        key = p.group("key").lower()
        value = p.group("value").strip()
        if value.startswith('"') and value.endswith('"') and len(value) >= 2:
            value = value[1:-1]
        parsed_params[key] = value

    required = ("created", "expires", "keyid", "alg", "nonce", "tag")
    for field_name in required:
        if field_name not in parsed_params:
            raise ValueError(f"signature_input_missing_{field_name}")

    try:
        created = int(parsed_params["created"])
        expires = int(parsed_params["expires"])
    except ValueError as exc:
        raise ValueError("invalid_signature_input_timestamps") from exc

    return TapSignatureInput(
        label=label,
        components=components,
        created=created,
        expires=expires,
        keyid=parsed_params["keyid"],
        alg=parsed_params["alg"],
        nonce=parsed_params["nonce"],
        tag=parsed_params["tag"],
    )


def parse_signature_header(header_value: str) -> tuple[str, str]:
    """Parse a TAP Signature header (single signature dictionary member)."""
    match = _SIG_RE.match(header_value or "")
    if not match:
        raise ValueError("invalid_signature_header_format")
    return match.group("label"), match.group("sig")


def build_signature_base(authority: str, path: str, signature_input: TapSignatureInput) -> str:
    """
    Build signature base string for @authority/@path TAP usage.

    This follows the canonical structure in TAP merchant guidance examples.
    """
    return (
        f"@authority: {authority}\n"
        f"@path: {path}\n"
        f"\"@signature-params\": {signature_input.signature_params()}"
    )


def validate_tap_headers(
    *,
    signature_input_header: str,
    signature_header: str,
    authority: str,
    path: str,
    now: int | None = None,
    max_time_window_seconds: int = TAP_MAX_TIME_WINDOW_SECONDS,
    allowed_tags: Sequence[str] = tuple(TAP_ALLOWED_TAGS),
    allowed_algs: Sequence[str] = tuple(TAP_ALLOWED_MESSAGE_ALGS),
    nonce_cache: MutableSet[str] | None = None,
    verify_signature_fn: Any | None = None,
    tap_version: str | None = None,
) -> TapVerificationResult:
    """
    Validate TAP message-signature headers.

    This performs structural and semantic checks. Cryptographic verification can
    be optionally injected via verify_signature_fn(signature_base, signature_b64, keyid, alg).
    """
    if tap_version is not None:
        version_valid, version_reason = validate_tap_version(tap_version)
        if not version_valid:
            return TapVerificationResult(False, version_reason)

    try:
        signature_input = parse_signature_input(signature_input_header)
    except ValueError as exc:
        return TapVerificationResult(False, f"tap_signature_input_invalid:{exc}")

    try:
        signature_label, signature_b64 = parse_signature_header(signature_header)
    except ValueError as exc:
        return TapVerificationResult(False, f"tap_signature_invalid:{exc}")

    if signature_label != signature_input.label:
        return TapVerificationResult(False, "tap_signature_label_mismatch")

    required_components = {"@authority", "@path"}
    if not required_components.issubset(set(signature_input.components)):
        return TapVerificationResult(False, "tap_required_components_missing")

    if signature_input.tag not in set(allowed_tags):
        return TapVerificationResult(False, "tap_tag_invalid")
    if signature_input.alg.lower() not in {alg.lower() for alg in allowed_algs}:
        return TapVerificationResult(False, "tap_alg_invalid")

    current = now if now is not None else int(time.time())
    if signature_input.created >= current:
        return TapVerificationResult(False, "tap_created_not_in_past")
    if signature_input.expires <= current:
        return TapVerificationResult(False, "tap_expired")
    if signature_input.expires - signature_input.created > max_time_window_seconds:
        return TapVerificationResult(False, "tap_window_too_large")

    if nonce_cache is not None:
        if signature_input.nonce in nonce_cache:
            return TapVerificationResult(False, "tap_nonce_replayed")
        nonce_cache.add(signature_input.nonce)

    signature_base = build_signature_base(authority, path, signature_input)
    if verify_signature_fn is not None:
        try:
            verified = bool(
                verify_signature_fn(
                    signature_base.encode(),
                    signature_b64,
                    signature_input.keyid,
                    signature_input.alg,
                )
            )
        except Exception:
            verified = False
        if not verified:
            return TapVerificationResult(False, "tap_signature_verification_failed")

    return TapVerificationResult(
        True,
        signature_input=signature_input,
        signature_b64=signature_b64,
        signature_base=signature_base,
        tap_version=tap_version,
    )


def build_object_signature_base(obj: Mapping[str, Any]) -> str:
    """
    Build TAP linked-object signature base.

    Canonicalization rule:
    - include all fields in received order except `signature`
    - compact JSON encoding to avoid whitespace variance
    """
    ordered: dict[str, Any] = {}
    for key, value in obj.items():
        if key == "signature":
            continue
        ordered[str(key)] = value
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=True)


def validate_agentic_consumer_object(
    obj: Mapping[str, Any],
    *,
    header_nonce: str | None = None,
    allowed_algs: Sequence[str] = tuple(TAP_ALLOWED_OBJECT_ALGS),
    verify_signature_fn: Any | None = None,
) -> TapVerificationResult:
    """
    Validate structure of the agentic consumer object.

    Required fields from TAP merchant guidance:
      nonce, idToken, contextualData, kid, alg, signature
    """
    required_fields = ("nonce", "idToken", "contextualData", "kid", "alg", "signature")
    for field_name in required_fields:
        if field_name not in obj:
            return TapVerificationResult(False, f"agentic_consumer_missing_{field_name}")

    nonce = str(obj.get("nonce", ""))
    if not nonce:
        return TapVerificationResult(False, "agentic_consumer_nonce_empty")
    alg = str(obj.get("alg", ""))
    if alg.lower() not in {a.lower() for a in allowed_algs}:
        return TapVerificationResult(False, "agentic_consumer_alg_invalid")

    if header_nonce is not None and nonce != header_nonce:
        return TapVerificationResult(False, "agentic_consumer_nonce_mismatch")

    signature_base = build_object_signature_base(obj)
    if verify_signature_fn is not None:
        try:
            verified = bool(
                verify_signature_fn(
                    signature_base.encode(),
                    str(obj.get("signature", "")),
                    str(obj.get("kid", "")),
                    alg,
                )
            )
        except Exception:
            verified = False
        if not verified:
            return TapVerificationResult(False, "agentic_consumer_signature_invalid")

    return TapVerificationResult(True)


def validate_agentic_payment_container(
    obj: Mapping[str, Any],
    *,
    header_nonce: str | None = None,
    require_nonce_match: bool = True,
    allowed_algs: Sequence[str] = tuple(TAP_ALLOWED_OBJECT_ALGS),
    verify_signature_fn: Any | None = None,
) -> TapVerificationResult:
    """
    Validate structure of the agentic payment container.

    Minimum required TAP fields:
      nonce, kid, alg, signature
    """
    required_fields = ("nonce", "kid", "alg", "signature")
    for field_name in required_fields:
        if field_name not in obj:
            return TapVerificationResult(False, f"agentic_payment_missing_{field_name}")

    nonce = str(obj.get("nonce", ""))
    if not nonce:
        return TapVerificationResult(False, "agentic_payment_nonce_empty")
    alg = str(obj.get("alg", ""))
    if alg.lower() not in {a.lower() for a in allowed_algs}:
        return TapVerificationResult(False, "agentic_payment_alg_invalid")

    if require_nonce_match and header_nonce is not None and nonce != header_nonce:
        return TapVerificationResult(False, "agentic_payment_nonce_mismatch")

    signature_base = build_object_signature_base(obj)
    if verify_signature_fn is not None:
        try:
            verified = bool(
                verify_signature_fn(
                    signature_base.encode(),
                    str(obj.get("signature", "")),
                    str(obj.get("kid", "")),
                    alg,
                )
            )
        except Exception:
            verified = False
        if not verified:
            return TapVerificationResult(False, "agentic_payment_signature_invalid")

    return TapVerificationResult(True)


__all__ = [
    "TAP_ALLOWED_TAGS",
    "TAP_MAX_TIME_WINDOW_SECONDS",
    "TAP_ALLOWED_MESSAGE_ALGS",
    "TAP_ALLOWED_OBJECT_ALGS",
    "TAP_PROTOCOL_VERSION",
    "TAP_SUPPORTED_VERSIONS",
    "TapSignatureInput",
    "TapVerificationResult",
    "validate_tap_version",
    "parse_signature_input",
    "parse_signature_header",
    "build_signature_base",
    "build_object_signature_base",
    "validate_tap_headers",
    "validate_agentic_consumer_object",
    "validate_agentic_payment_container",
]
