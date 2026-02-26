"""Secure checkout executor endpoints (PAN-safe orchestration)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import inspect
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core.policy_attestation import build_signed_policy_snapshot, verify_signed_policy_snapshot

logger = logging.getLogger(__name__)
_PAN_LIKE_DIGITS_RE = re.compile(r"\b\d{12,19}\b")
_PAN_WITH_SEPARATORS_RE = re.compile(r"\b(?:\d[ -]?){12,19}\b")
_CVV_INLINE_RE = re.compile(r"(?i)\b(cvv|cvc)\b\s*[:=]?\s*\d{3,4}\b")
_SENSITIVE_AUDIT_KEYS = {
    "pan",
    "cvv",
    "cvc",
    "card_number",
    "full_number",
    "track_data",
    "secret_ref",
}
_DEFAULT_PAN_BOUNDARY_MODE = "issuer_hosted_iframe_plus_enclave_break_glass"
_SUPPORTED_PAN_BOUNDARY_MODES = {
    _DEFAULT_PAN_BOUNDARY_MODE,
    "issuer_hosted_iframe_only",
    "enclave_break_glass_only",
}
_BOUNDARY_MODE_STRICTNESS = {
    "issuer_hosted_iframe_only": 0,
    "enclave_break_glass_only": 1,
    "issuer_hosted_iframe_plus_enclave_break_glass": 2,
}
_DEFAULT_PROVIDER_BOUNDARY_MATRIX = {
    # conservative default for fiat-first issuers
    "stripe_issuing": "issuer_hosted_iframe_only",
    "stripe": "issuer_hosted_iframe_only",
    # PCI-minimized default: hosted-only until provider contract/reveal model is certified.
    "lithic": "issuer_hosted_iframe_only",
    "rain": "issuer_hosted_iframe_only",
    # funding/ramp rails default to hosted-only profile
    "bridge": "issuer_hosted_iframe_only",
    "coinbase_cdp": "issuer_hosted_iframe_only",
}


class MerchantExecutionMode(str, Enum):
    TOKENIZED_API = "tokenized_api"
    EMBEDDED_IFRAME = "embedded_iframe"
    PAN_ENTRY = "pan_entry"
    BLOCKED = "blocked"


class SecureCheckoutJobStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    READY = "ready"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class SecurityIncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecureCheckoutDependencies:
    wallet_repo: Any
    agent_repo: Any
    card_repo: Any
    card_provider: Any
    policy_store: Any | None = None
    approval_service: Any | None = None
    audit_sink: Any | None = None
    cache_service: Any | None = None
    store: "InMemorySecureCheckoutStore | None" = None


class SecureExecutionOptions(BaseModel):
    """Execution safety flags for external browser workers."""

    trace: bool = False
    screenshot: bool = False
    video: bool = False
    strict_origin_check: bool = True


class CreateSecureCheckoutJobRequest(BaseModel):
    """Create a secure checkout job from an approved intent."""

    wallet_id: str
    card_id: str
    merchant_url: str
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    purpose: str = "agent_checkout"
    intent_id: str = Field(default_factory=lambda: f"intent_{uuid.uuid4().hex[:16]}")
    approval_id: Optional[str] = None
    approval_ids: list[str] = Field(default_factory=list)
    options: SecureExecutionOptions = Field(default_factory=SecureExecutionOptions)


class ExecuteSecureCheckoutJobRequest(BaseModel):
    """Dispatch an already created secure checkout job."""

    approval_id: Optional[str] = None
    approval_ids: list[str] = Field(default_factory=list)


class CompleteSecureCheckoutJobRequest(BaseModel):
    status: str = Field(pattern="^(completed|failed)$")
    executor_ref: Optional[str] = None
    failure_reason: Optional[str] = None


class MerchantCapabilityRequest(BaseModel):
    merchant_url: str
    amount: Optional[Decimal] = Field(default=None, gt=0)
    currency: str = "USD"


class MerchantCapabilityResponse(BaseModel):
    merchant_origin: str
    merchant_host: str
    merchant_mode: MerchantExecutionMode
    mode_reason: str
    approval_likely_required: bool
    pan_execution_enabled: bool
    pan_allowed_for_merchant: bool
    pan_compliance_ready: bool
    pan_compliance_reason: str


class SecureCheckoutSecurityPolicyResponse(BaseModel):
    pan_execution_enabled: bool
    require_shared_secret_store: bool
    shared_secret_store_configured: bool
    pan_entry_allowlist: list[str] = Field(default_factory=list)
    production_pan_entry_requires_allowlist: bool
    pan_entry_break_glass_only: bool
    pan_boundary_mode: str
    pan_provider: str
    pan_provider_boundary_mode: Optional[str] = None
    pan_boundary_mode_locked: bool = False
    issuer_hosted_reveal_preferred: bool
    supported_merchant_modes: list[str] = Field(default_factory=list)
    recommended_default_mode: str
    auto_freeze_on_security_incident: bool
    auto_rotate_on_security_incident: bool
    auto_rotate_severities: list[str] = Field(default_factory=list)
    auto_unfreeze_on_security_incident: bool
    auto_unfreeze_ops_approved: bool
    auto_unfreeze_allowed_severities: list[str] = Field(default_factory=list)
    min_approvals: int
    pan_min_approvals: int
    require_distinct_approval_reviewers: bool
    incident_cooldown_seconds: dict[str, int] = Field(default_factory=dict)


class SecureCheckoutJobResponse(BaseModel):
    job_id: str
    intent_id: str
    wallet_id: str
    card_id: str
    merchant_origin: str
    merchant_mode: MerchantExecutionMode
    status: SecureCheckoutJobStatus
    amount: str
    currency: str
    approval_required: bool
    approval_id: Optional[str] = None
    approval_ids: list[str] = Field(default_factory=list)
    approval_quorum_required: int = 0
    policy_reason: str = "OK"
    executor_ref: Optional[str] = None
    secret_ref: Optional[str] = None
    secret_expires_at: Optional[str] = None
    redacted_card: dict[str, Any] = Field(default_factory=dict)
    options: SecureExecutionOptions
    created_at: str
    updated_at: str
    error_code: Optional[str] = None
    error: Optional[str] = None


class ConsumeExecutorSecretResponse(BaseModel):
    """One-time payload for isolated executor runtime."""

    pan: str
    cvv: str
    exp_month: int
    exp_year: int
    merchant_origin: str
    amount: str
    currency: str
    purpose: str


class SecureCheckoutApprovalEvidence(BaseModel):
    approval_id: str
    status: str
    reviewed_by: Optional[str] = None
    wallet_id: Optional[str] = None
    organization_id: Optional[str] = None
    reviewed_at: Optional[str] = None


class SecureCheckoutPolicyEvidence(BaseModel):
    policy_present: bool
    policy_reason: str
    policy_hash: Optional[str] = None
    policy_snapshot_id: Optional[str] = None
    policy_snapshot_chain_hash: Optional[str] = None
    policy_snapshot_signer_kid: Optional[str] = None
    max_per_tx: Optional[str] = None
    max_daily: Optional[str] = None
    max_monthly: Optional[str] = None
    approval_threshold: Optional[str] = None


class SecureCheckoutAttestationEvidence(BaseModel):
    dispatch_required: bool
    dispatch_url_configured: bool
    executor_attestation_enabled: bool
    executor_attestation_ttl_seconds: int
    shared_secret_store_required: bool
    shared_secret_store_configured: bool


class SecureCheckoutEvidenceIntegrity(BaseModel):
    digest_sha256: str
    hash_chain_tail: Optional[str] = None
    hash_chain_entries: int = 0
    event_count: int = 0


class SecureCheckoutEvidenceExportResponse(BaseModel):
    job: SecureCheckoutJobResponse
    approvals: list[SecureCheckoutApprovalEvidence] = Field(default_factory=list)
    policy: SecureCheckoutPolicyEvidence
    attestation: SecureCheckoutAttestationEvidence
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    integrity: SecureCheckoutEvidenceIntegrity
    generated_at: str
    scope_window: dict[str, Optional[str]] = Field(default_factory=dict)
    verifier_hints: list[str] = Field(default_factory=list)


def get_deps() -> SecureCheckoutDependencies:
    raise NotImplementedError("Dependency override required")


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    return os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower() in {"prod", "production"}


def _checkout_signed_policy_snapshot_required() -> bool:
    raw = (os.getenv("SARDIS_CHECKOUT_REQUIRE_SIGNED_POLICY_SNAPSHOT", "") or "").strip()
    if raw:
        return _is_truthy(raw)
    return _is_production_env()


def _checkout_policy_signer_secret() -> str:
    return (os.getenv("SARDIS_CHECKOUT_POLICY_SIGNER_SECRET", "") or "").strip()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def _host_matches(patterns: list[str], host: str) -> bool:
    host = (host or "").strip().lower()
    for pattern in patterns:
        if pattern.startswith("*."):
            suffix = pattern[1:]
            if host.endswith(suffix):
                return True
        elif host == pattern:
            return True
    return False


def _normalize_merchant_origin(merchant_url: str) -> tuple[str, str]:
    parsed = urlparse(merchant_url)
    scheme = (parsed.scheme or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    if scheme not in {"https", "http"}:
        raise ValueError("merchant_url must include http/https scheme")
    if not host:
        raise ValueError("merchant_url missing hostname")
    port = parsed.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        origin = f"{scheme}://{host}:{port}"
    else:
        origin = f"{scheme}://{host}"
    return origin, host


def _resolve_merchant_mode(host: str) -> tuple[MerchantExecutionMode, str]:
    blocked = _parse_csv_env("SARDIS_CHECKOUT_BLOCKED_MERCHANTS")
    if _host_matches(blocked, host):
        return MerchantExecutionMode.BLOCKED, "merchant_blocked"

    tokenized = _parse_csv_env("SARDIS_CHECKOUT_TOKENIZED_MERCHANTS")
    if _host_matches(tokenized, host):
        return MerchantExecutionMode.TOKENIZED_API, "merchant_supports_tokenized_api"

    embedded = _parse_csv_env("SARDIS_CHECKOUT_EMBEDDED_IFRAME_MERCHANTS")
    if _host_matches(embedded, host):
        return MerchantExecutionMode.EMBEDDED_IFRAME, "merchant_supports_embedded_iframe"

    return MerchantExecutionMode.PAN_ENTRY, "merchant_requires_pan_entry"


def _sanitize_options(options: SecureExecutionOptions) -> SecureExecutionOptions:
    allow_trace = _is_truthy(os.getenv("SARDIS_CHECKOUT_ALLOW_EXECUTOR_TRACING", "0"))
    if allow_trace:
        return options
    return SecureExecutionOptions(
        trace=False,
        screenshot=False,
        video=False,
        strict_origin_check=options.strict_origin_check,
    )


def _redacted_card_summary(card: dict[str, Any] | None) -> dict[str, Any]:
    if not card:
        return {}
    last4 = str(card.get("card_number_last4") or "")
    expiry_month = card.get("expiry_month")
    expiry_year = card.get("expiry_year")
    return {
        "last4": last4,
        "expiry_month": expiry_month,
        "expiry_year": expiry_year,
        "provider": card.get("provider"),
    }


def _approval_threshold() -> Decimal:
    raw = os.getenv("SARDIS_CHECKOUT_APPROVAL_THRESHOLD_USD", "500")
    try:
        return Decimal(raw)
    except Exception:
        return Decimal("500")


def _require_approval_for_pan() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1"))


def _bounded_int_env(name: str, default: int, *, min_value: int = 1, max_value: int = 5) -> int:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return max(min_value, min(default, max_value))
    try:
        value = int(raw)
    except ValueError:
        value = default
    return max(min_value, min(value, max_value))


def _checkout_min_approvals() -> int:
    return _bounded_int_env("SARDIS_CHECKOUT_MIN_APPROVALS", 1)


def _checkout_pan_min_approvals() -> int:
    default = 2 if _is_production_env() else 1
    configured = _bounded_int_env("SARDIS_CHECKOUT_PAN_MIN_APPROVALS", default)
    return max(_checkout_min_approvals(), configured)


def _checkout_require_distinct_approval_reviewers() -> bool:
    raw = (os.getenv("SARDIS_CHECKOUT_REQUIRE_DISTINCT_APPROVAL_REVIEWERS", "") or "").strip()
    if raw:
        return _is_truthy(raw)
    return _is_production_env() and _checkout_pan_min_approvals() > 1


def _required_checkout_approvals(
    *,
    approval_required: bool,
    merchant_mode: MerchantExecutionMode | str,
) -> int:
    if not approval_required:
        return 0
    mode_value = (
        merchant_mode.value
        if isinstance(merchant_mode, MerchantExecutionMode)
        else str(merchant_mode or "").strip().lower()
    )
    if mode_value == MerchantExecutionMode.PAN_ENTRY.value:
        return _checkout_pan_min_approvals()
    return _checkout_min_approvals()


def _pan_execution_enabled() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "0"))
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1"))


def _pan_boundary_mode() -> str:
    resolved, _, _ = _resolve_pan_boundary_mode()
    return resolved


def _pan_provider() -> str:
    configured = (os.getenv("SARDIS_CHECKOUT_PAN_PROVIDER", "") or "").strip().lower()
    if configured:
        return configured
    return (os.getenv("SARDIS_CARDS_PRIMARY_PROVIDER", "") or "").strip().lower()


def _pan_provider_boundary_matrix() -> dict[str, str]:
    matrix = dict(_DEFAULT_PROVIDER_BOUNDARY_MATRIX)
    raw = (os.getenv("SARDIS_CHECKOUT_PAN_PROVIDER_BOUNDARY_MATRIX_JSON", "") or "").strip()
    if not raw:
        return matrix
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Invalid SARDIS_CHECKOUT_PAN_PROVIDER_BOUNDARY_MATRIX_JSON; using defaults")
        return matrix
    if not isinstance(parsed, dict):
        logger.warning("SARDIS_CHECKOUT_PAN_PROVIDER_BOUNDARY_MATRIX_JSON must be an object; using defaults")
        return matrix
    for key, value in parsed.items():
        provider = str(key or "").strip().lower()
        mode = str(value or "").strip().lower()
        if provider and mode in _SUPPORTED_PAN_BOUNDARY_MODES:
            matrix[provider] = mode
    return matrix


def _provider_boundary_mode(provider: str) -> Optional[str]:
    provider_key = str(provider or "").strip().lower()
    if not provider_key:
        return None
    return _pan_provider_boundary_matrix().get(provider_key)


def _resolve_pan_boundary_mode() -> tuple[str, Optional[str], bool]:
    configured = os.getenv(
        "SARDIS_CHECKOUT_PAN_BOUNDARY_MODE",
        _DEFAULT_PAN_BOUNDARY_MODE,
    ).strip().lower()
    if configured not in _SUPPORTED_PAN_BOUNDARY_MODES:
        if _is_production_env():
            logger.warning(
                "Invalid SARDIS_CHECKOUT_PAN_BOUNDARY_MODE=%s in production; forcing issuer_hosted_iframe_only",
                configured,
            )
            configured = "issuer_hosted_iframe_only"
        else:
            configured = _DEFAULT_PAN_BOUNDARY_MODE

    provider = _pan_provider()
    provider_mode = _provider_boundary_mode(provider)
    if not (_is_production_env() and provider_mode):
        return configured, provider_mode, False

    configured_rank = _BOUNDARY_MODE_STRICTNESS.get(configured, 99)
    provider_rank = _BOUNDARY_MODE_STRICTNESS.get(provider_mode, 99)
    if configured_rank <= provider_rank:
        return configured, provider_mode, False
    logger.info(
        "PAN boundary mode %s is looser than provider profile %s for provider=%s; locking to provider profile",
        configured,
        provider_mode,
        provider or "unknown",
    )
    return provider_mode, provider_mode, True


def _require_tokenized_in_prod() -> bool:
    if not _is_production_env():
        return False
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_REQUIRE_TOKENIZED_IN_PROD", "1"))


def _pan_entry_allowed_for_host(host: str) -> bool:
    allowlist = _parse_csv_env("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS")
    return _host_matches(allowlist, host)


def _pan_entry_policy_decision(host: str) -> tuple[bool, str]:
    boundary_mode, provider_mode, locked = _resolve_pan_boundary_mode()
    if boundary_mode == "issuer_hosted_iframe_only":
        if locked and provider_mode == "issuer_hosted_iframe_only":
            return False, "pan_provider_profile_disallows_pan_entry"
        return False, "pan_boundary_mode_disallows_pan_entry"

    if not _pan_execution_enabled():
        return False, "pan_execution_disabled"
    if _is_production_env():
        if not _is_truthy(os.getenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", "0")):
            return False, "pan_compliance_not_attested"
        if not os.getenv("SARDIS_CHECKOUT_QSA_CONTACT", "").strip():
            return False, "pan_qsa_contact_missing"
    if _require_tokenized_in_prod() and not _pan_entry_allowed_for_host(host):
        return False, "pan_entry_not_allowlisted"
    return True, "pan_entry_allowed"


def _secret_ttl_seconds() -> int:
    raw = os.getenv("SARDIS_CHECKOUT_SECRET_TTL_SECONDS", "60").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 60
    return max(10, min(value, 300))


def _redact_sensitive_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    text = _CVV_INLINE_RE.sub(lambda match: f"{match.group(1).lower()}=[REDACTED_CVV]", text)
    text = _PAN_WITH_SEPARATORS_RE.sub("[REDACTED_PAN]", text)
    return _PAN_LIKE_DIGITS_RE.sub("[REDACTED_PAN]", text)


def _sanitize_audit_payload(payload: dict[str, Any]) -> dict[str, Any]:
    def _sanitize_value(key: str, value: Any) -> Any:
        key_lower = (key or "").strip().lower()
        if key_lower in _SENSITIVE_AUDIT_KEYS:
            return "[REDACTED]"
        if isinstance(value, dict):
            return {k: _sanitize_value(str(k), v) for k, v in value.items()}
        if isinstance(value, list):
            return [_sanitize_value("", item) for item in value]
        if isinstance(value, str):
            return _redact_sensitive_text(value)
        return value

    return {k: _sanitize_value(str(k), v) for k, v in (payload or {}).items()}


def _pan_executor_runtime_ready() -> tuple[bool, str]:
    if not _is_production_env():
        return True, "ok"
    if not _executor_dispatch_url():
        return False, "executor_dispatch_url_not_configured"
    if not _dispatch_required():
        return False, "executor_dispatch_required_in_production"
    if not os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip():
        return False, "executor_token_not_configured"
    if _executor_attestation_enabled() and not _executor_attestation_key():
        return False, "executor_attestation_key_not_configured"
    return True, "ok"


def _build_secret_payload_from_reveal(
    *,
    details: dict[str, Any],
    merchant_origin: str,
    amount: Any,
    currency: str,
    purpose: str,
) -> dict[str, Any]:
    pan = str(details.get("pan") or "").strip().replace(" ", "")
    cvv = str(details.get("cvv") or details.get("cvc") or "").strip()
    exp_month = int(details.get("exp_month") or 0)
    exp_year = int(details.get("exp_year") or 0)
    if exp_year < 100:
        exp_year += 2000

    if not pan or not pan.isdigit() or len(pan) < 12 or len(pan) > 19:
        raise ValueError("invalid_pan")
    if not cvv or not cvv.isdigit() or len(cvv) not in {3, 4}:
        raise ValueError("invalid_cvv")
    if exp_month < 1 or exp_month > 12:
        raise ValueError("invalid_exp_month")
    current_year = _now_utc().year
    if exp_year < current_year or exp_year > current_year + 30:
        raise ValueError("invalid_exp_year")

    return {
        "pan": pan,
        "cvv": cvv,
        "exp_month": exp_month,
        "exp_year": exp_year,
        "merchant_origin": merchant_origin,
        "amount": str(amount),
        "currency": currency,
        "purpose": purpose,
    }


def _executor_dispatch_url() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_URL", "").strip()


def _dispatch_required() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_DISPATCH_REQUIRED", "0"))


def _dispatch_timeout_seconds() -> float:
    raw = os.getenv("SARDIS_CHECKOUT_DISPATCH_TIMEOUT_SECONDS", "5").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 5.0
    return max(1.0, min(value, 30.0))


def _dispatch_signing_key() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_SIGNING_KEY", "").strip()


def _executor_attestation_enabled() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "1"))
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "0"))


def _executor_attestation_key() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY", "").strip()


def _executor_attestation_ttl_seconds() -> int:
    raw = os.getenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_TTL_SECONDS", "120").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 120
    return max(30, min(value, 900))


def _hash_payload_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    return str(value)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default).encode("utf-8")


def _hash_chain_tail(events: list[dict[str, Any]]) -> tuple[Optional[str], int]:
    if not events:
        return None, 0
    previous = hashlib.sha256(b"secure_checkout_evidence_v1").hexdigest()
    for item in events:
        event_hash = hashlib.sha256(_canonical_json_bytes(item)).hexdigest()
        previous = hashlib.sha256(f"{previous}:{event_hash}".encode("utf-8")).hexdigest()
    return previous, len(events)


def _compute_executor_signature(
    *,
    key: str,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    payload_hash: str,
) -> str:
    canonical = "\n".join([method.upper(), path, timestamp, nonce, payload_hash])
    return hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


async def _dispatch_to_executor(
    *,
    job: dict[str, Any],
    secret_ref: Optional[str] = None,
    secret_expires_at: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Dispatch metadata-only execution request to an isolated worker.

    Never includes PAN/CVV in payload. Worker must consume secret_ref separately.
    """
    dispatch_url = _executor_dispatch_url()
    if not dispatch_url:
        return True, None, None

    token = (
        os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_TOKEN", "").strip()
        or os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip()
    )
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "job_id": job["job_id"],
        "intent_id": job["intent_id"],
        "wallet_id": job["wallet_id"],
        "card_id": job["card_id"],
        "merchant_origin": job["merchant_origin"],
        "merchant_mode": job["merchant_mode"],
        "amount": str(job["amount"]),
        "currency": job["currency"],
        "purpose": job["purpose"],
        "options": job.get("options") or {},
        "secret_ref": secret_ref,
        "secret_expires_at": secret_expires_at,
    }

    timeout = _dispatch_timeout_seconds()
    signing_key = _dispatch_signing_key()
    if signing_key:
        now_ts = str(int(time.time()))
        nonce = uuid.uuid4().hex
        payload_hash = _hash_payload_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        dispatch_path = urlparse(dispatch_url).path or "/"
        headers["X-Sardis-Timestamp"] = now_ts
        headers["X-Sardis-Nonce"] = nonce
        headers["X-Sardis-Signature"] = _compute_executor_signature(
            key=signing_key,
            method="POST",
            path=dispatch_path,
            timestamp=now_ts,
            nonce=nonce,
            payload_hash=payload_hash,
        )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(dispatch_url, json=payload, headers=headers)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"executor_dispatch_failed:{exc}"

    if response.status_code >= 400:
        return False, None, f"executor_dispatch_http_{response.status_code}"

    executor_ref: Optional[str] = None
    try:
        body = response.json()
        if isinstance(body, dict):
            candidate = body.get("execution_id") or body.get("executor_ref") or body.get("job_id")
            if candidate:
                executor_ref = str(candidate)
    except Exception:
        executor_ref = None
    return True, executor_ref, None


class InMemorySecureCheckoutStore:
    """In-memory state for secure checkout jobs and one-time secret refs."""

    def __init__(self) -> None:
        self.is_persistent = False
        self.is_shared_secret_store = False
        self._jobs_by_id: dict[str, dict[str, Any]] = {}
        self._jobs_by_intent_id: dict[str, str] = {}
        self._secrets: dict[str, dict[str, Any]] = {}
        self._completion_receipts: dict[str, dict[str, Any]] = {}
        self._used_executor_nonces: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def upsert_job(self, job: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            existing_id = self._jobs_by_intent_id.get(job["intent_id"])
            if existing_id:
                existing = self._jobs_by_id[existing_id]
                return dict(existing)
            self._jobs_by_id[job["job_id"]] = dict(job)
            self._jobs_by_intent_id[job["intent_id"]] = job["job_id"]
            return dict(job)

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            return dict(job) if job else None

    async def update_job(self, job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            if not job:
                return None
            updated = dict(job)
            updated.update(fields)
            updated["updated_at"] = _now_utc()
            self._jobs_by_id[job_id] = updated
            return dict(updated)

    async def put_secret(self, secret_ref: str, payload: dict[str, Any], expires_at: datetime) -> None:
        async with self._lock:
            self._secrets[secret_ref] = {
                "payload": dict(payload),
                "expires_at": expires_at,
                "consumed": False,
            }

    async def drop_secret(self, secret_ref: str) -> None:
        async with self._lock:
            self._secrets.pop(secret_ref, None)

    async def consume_secret(self, secret_ref: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            secret = self._secrets.get(secret_ref)
            if not secret:
                return None
            if secret["consumed"]:
                return None
            if _now_utc() > secret["expires_at"]:
                self._secrets.pop(secret_ref, None)
                return None
            secret["consumed"] = True
            payload = dict(secret["payload"])
            self._secrets.pop(secret_ref, None)
            return payload

    async def get_completion_receipt(self, idempotency_key: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            item = self._completion_receipts.get(idempotency_key)
            return dict(item) if item else None

    async def put_completion_receipt(self, idempotency_key: str, job: dict[str, Any]) -> None:
        async with self._lock:
            self._completion_receipts[idempotency_key] = dict(job)

    async def mark_executor_nonce_used(self, nonce: str, *, ttl_seconds: int) -> bool:
        now = time.time()
        expires_at = now + float(ttl_seconds)
        async with self._lock:
            expired = [n for n, exp in self._used_executor_nonces.items() if exp <= now]
            for n in expired:
                self._used_executor_nonces.pop(n, None)
            if nonce in self._used_executor_nonces:
                return False
            self._used_executor_nonces[nonce] = expires_at
            return True


_DEFAULT_STORE = InMemorySecureCheckoutStore()


def _resolve_store(deps: SecureCheckoutDependencies) -> InMemorySecureCheckoutStore:
    return deps.store or _DEFAULT_STORE


class RepositoryBackedSecureCheckoutStore(InMemorySecureCheckoutStore):
    """Persistent job storage + in-memory one-time secret storage."""

    def __init__(self, job_repository: Any, cache_service: Any | None = None):
        super().__init__()
        self.is_persistent = True
        self.is_shared_secret_store = bool(cache_service)
        self._job_repository = job_repository
        self._cache = cache_service

    async def upsert_job(self, job: dict[str, Any]) -> dict[str, Any]:
        if not self._job_repository:
            return await super().upsert_job(job)
        return await self._job_repository.upsert_job(job)

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        if not self._job_repository:
            return await super().get_job(job_id)
        return await self._job_repository.get_job(job_id)

    async def update_job(self, job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        if not self._job_repository:
            return await super().update_job(job_id, **fields)
        return await self._job_repository.update_job(job_id, **fields)

    def _secret_key(self, secret_ref: str) -> str:
        return f"sardis:checkout:secret:{secret_ref}"

    def _consume_lock_resource(self, secret_ref: str) -> str:
        return f"checkout:secret:consume:{secret_ref}"

    def _completion_key(self, idempotency_key: str) -> str:
        return f"sardis:checkout:completion:{idempotency_key}"

    async def put_secret(self, secret_ref: str, payload: dict[str, Any], expires_at: datetime) -> None:
        if not self._cache:
            await super().put_secret(secret_ref, payload, expires_at=expires_at)
            return
        ttl = int((expires_at - _now_utc()).total_seconds())
        if ttl <= 0:
            return
        body = {
            "payload": dict(payload),
            "expires_at": expires_at.isoformat(),
        }
        await self._cache.set(self._secret_key(secret_ref), json.dumps(body), ttl=ttl)

    async def drop_secret(self, secret_ref: str) -> None:
        if not self._cache:
            await super().drop_secret(secret_ref)
            return
        await self._cache.delete(self._secret_key(secret_ref))

    async def consume_secret(self, secret_ref: str) -> Optional[dict[str, Any]]:
        if not self._cache:
            return await super().consume_secret(secret_ref)

        lock_resource = self._consume_lock_resource(secret_ref)
        try:
            async with self._cache.lock(lock_resource, ttl_seconds=5, max_retries=3):
                raw = await self._cache.get(self._secret_key(secret_ref))
                if not raw:
                    return None
                await self._cache.delete(self._secret_key(secret_ref))
        except TimeoutError:
            return None

        try:
            body = json.loads(raw)
            expires_at_raw = str(body.get("expires_at") or "").strip()
            expires_at = datetime.fromisoformat(expires_at_raw) if expires_at_raw else _now_utc()
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if _now_utc() > expires_at:
                return None
            payload = body.get("payload")
            if isinstance(payload, dict):
                return payload
            return None
        except Exception:
            return None

    async def get_completion_receipt(self, idempotency_key: str) -> Optional[dict[str, Any]]:
        if not self._cache:
            return await super().get_completion_receipt(idempotency_key)
        raw = await self._cache.get(self._completion_key(idempotency_key))
        if not raw:
            return None
        try:
            item = json.loads(raw)
            return item if isinstance(item, dict) else None
        except Exception:
            return None

    async def put_completion_receipt(self, idempotency_key: str, job: dict[str, Any]) -> None:
        if not self._cache:
            await super().put_completion_receipt(idempotency_key, job)
            return
        await self._cache.set(
            self._completion_key(idempotency_key),
            json.dumps(dict(job), default=str),
            ttl=86400,
        )


def _allow_inmemory_store_in_prod() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "0"))


def _allow_inmemory_secret_store_in_prod() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_SECRET_STORE", "0"))


def _require_persistent_job_store() -> bool:
    return _is_production_env() and not _allow_inmemory_store_in_prod()


def _is_persistent_store(store: Any) -> bool:
    return bool(getattr(store, "is_persistent", False))


def _require_shared_secret_store() -> bool:
    return _is_production_env() and not _allow_inmemory_secret_store_in_prod()


def _has_shared_secret_store(store: Any) -> bool:
    return bool(getattr(store, "is_shared_secret_store", False))


def _auto_freeze_on_security_incident_enabled() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_CHECKOUT_AUTO_FREEZE_ON_SECURITY_INCIDENT", "1"))
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_AUTO_FREEZE_ON_SECURITY_INCIDENT", "0"))


def _dispatch_security_alert_enabled() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_DISPATCH_SECURITY_ALERTS", "1"))


def _parse_int_env(name: str, default: int, *, min_value: int, max_value: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw)
    except ValueError:
        parsed = default
    return max(min_value, min(parsed, max_value))


def _security_incident_severity(code: str) -> SecurityIncidentSeverity:
    normalized = (code or "").strip().lower()
    severity_overrides = {
        "policy_denied": SecurityIncidentSeverity.MEDIUM,
        "approval_required": SecurityIncidentSeverity.MEDIUM,
        "merchant_anomaly": SecurityIncidentSeverity.HIGH,
        "decline_burst": SecurityIncidentSeverity.HIGH,
        "executor_auth_failed": SecurityIncidentSeverity.CRITICAL,
        "attestation_replay": SecurityIncidentSeverity.CRITICAL,
    }
    return severity_overrides.get(normalized, SecurityIncidentSeverity.HIGH)


def _security_incident_cooldown_seconds(severity: SecurityIncidentSeverity) -> int:
    defaults = {
        SecurityIncidentSeverity.LOW: 300,
        SecurityIncidentSeverity.MEDIUM: 900,
        SecurityIncidentSeverity.HIGH: 3600,
        SecurityIncidentSeverity.CRITICAL: 21600,
    }
    env_name = f"SARDIS_CHECKOUT_INCIDENT_COOLDOWN_{severity.value.upper()}_SECONDS"
    return _parse_int_env(env_name, defaults[severity], min_value=30, max_value=86400)


def _security_incident_severity_set_env(name: str, default_csv: str) -> set[str]:
    raw = os.getenv(name, default_csv)
    return {part.strip().lower() for part in raw.split(",") if part.strip()}


def _auto_rotate_on_security_incident_enabled() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_CHECKOUT_AUTO_ROTATE_ON_SECURITY_INCIDENT", "0"))
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_AUTO_ROTATE_ON_SECURITY_INCIDENT", "0"))


def _auto_rotate_severities() -> set[str]:
    return _security_incident_severity_set_env(
        "SARDIS_CHECKOUT_AUTO_ROTATE_SEVERITIES",
        "high,critical",
    )


def _auto_unfreeze_on_security_incident_enabled() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_ON_SECURITY_INCIDENT", "0"))


def _auto_unfreeze_ops_approved() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_AUTO_UNFREEZE_OPS_APPROVED", "0"))


def _auto_unfreeze_allowed_severities() -> set[str]:
    return _security_incident_severity_set_env(
        "SARDIS_CHECKOUT_AUTO_UNFREEZE_ALLOWED_SEVERITIES",
        "low,medium",
    )


def _auto_unfreeze_allowed_for_severity(severity: SecurityIncidentSeverity) -> bool:
    return severity.value in _auto_unfreeze_allowed_severities()


async def _emit_audit_event(
    deps: SecureCheckoutDependencies,
    *,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    sink = deps.audit_sink
    if not sink:
        return
    sanitized_payload = _sanitize_audit_payload(payload)
    event = {
        "event_type": event_type,
        "ts": _now_utc().isoformat(),
        "payload": sanitized_payload,
    }
    record_callable = None
    if hasattr(sink, "record_event"):
        record_callable = getattr(sink, "record_event")
    elif hasattr(sink, "write_event"):
        record_callable = getattr(sink, "write_event")
    elif hasattr(sink, "append"):
        try:
            from sardis_compliance.checks import ComplianceAuditEntry
        except Exception:
            ComplianceAuditEntry = None  # type: ignore[assignment]

        if ComplianceAuditEntry is not None:
            entry = ComplianceAuditEntry(
                mandate_id=str(payload.get("intent_id") or payload.get("job_id") or ""),
                subject=str(sanitized_payload.get("wallet_id") or ""),
                allowed=event_type != "secure_checkout.job_failed",
                reason=str(sanitized_payload.get("error_code") or sanitized_payload.get("status") or event_type),
                rule_id=event_type,
                provider="secure_checkout",
                metadata=dict(sanitized_payload),
            )
            record_callable = getattr(sink, "append")
            result = record_callable(entry)
            if inspect.isawaitable(result):
                await result
            return
    elif callable(sink):
        record_callable = sink

    if record_callable is None:
        return

    result = record_callable(event)
    if inspect.isawaitable(result):
        await result


def _iso_or_none(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _to_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()  # type: ignore[call-arg]
        if isinstance(dumped, dict):
            return dumped
    if hasattr(value, "dict"):
        dumped = value.dict()  # type: ignore[call-arg]
        if isinstance(dumped, dict):
            return dumped
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    return {}


def _policy_snapshot(policy: Any) -> dict[str, Any]:
    raw = _to_plain_dict(policy)
    if not raw:
        for key in ("max_per_tx", "max_daily", "max_monthly", "approval_threshold"):
            if hasattr(policy, key):
                raw[key] = getattr(policy, key)
    snapshot = {
        "max_per_tx": raw.get("max_per_tx"),
        "max_daily": raw.get("max_daily"),
        "max_monthly": raw.get("max_monthly"),
        "approval_threshold": raw.get("approval_threshold"),
    }
    return {k: v for k, v in snapshot.items() if v is not None}


def _build_signed_checkout_policy_snapshot(policy: Any) -> tuple[Optional[dict[str, Any]], Optional[str]]:
    secret = _checkout_policy_signer_secret()
    if not secret:
        if _checkout_signed_policy_snapshot_required():
            return None, "policy_snapshot_signer_not_configured"
        return None, None

    try:
        snapshot = build_signed_policy_snapshot(
            policy=policy,
            signer_secret=secret,
            source_text="secure_checkout_policy",
            signer_kid="checkout-policy-signer",
        )
    except Exception:
        logger.exception("Failed to build signed checkout policy snapshot")
        return None, "policy_snapshot_signing_failed"

    verified, verify_reason = verify_signed_policy_snapshot(
        snapshot=snapshot,
        signer_secret=secret,
        expected_prev_chain_hash=snapshot.prev_chain_hash,
    )
    if not verified:
        return None, f"policy_snapshot_verification_failed:{verify_reason}"
    return snapshot.to_dict(), None


async def _collect_job_audit_events(
    deps: SecureCheckoutDependencies,
    *,
    job_id: str,
    intent_id: str,
) -> list[dict[str, Any]]:
    sink = deps.audit_sink
    if not sink:
        return []

    events: list[Any] = []
    if hasattr(sink, "events"):
        raw_events = getattr(sink, "events")
        if isinstance(raw_events, list):
            events.extend(raw_events)
    elif hasattr(sink, "list_events"):
        try:
            result = sink.list_events()  # type: ignore[attr-defined]
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, list):
                events.extend(result)
        except Exception:
            events = []

    filtered: list[dict[str, Any]] = []
    for entry in events:
        item = _to_plain_dict(entry)
        if not item:
            continue
        payload = _to_plain_dict(item.get("payload"))
        entry_job_id = str(payload.get("job_id") or "").strip()
        entry_intent_id = str(payload.get("intent_id") or "").strip()
        if entry_job_id != job_id and entry_intent_id != intent_id:
            continue
        filtered.append(
            {
                "event_type": str(item.get("event_type") or ""),
                "ts": _iso_or_none(item.get("ts")),
                "payload": payload,
            }
        )
    filtered.sort(key=lambda e: str(e.get("ts") or ""))
    return filtered


async def _collect_approval_evidence(
    deps: SecureCheckoutDependencies,
    approval_ids: list[str],
) -> list[SecureCheckoutApprovalEvidence]:
    if not approval_ids:
        return []
    evidence: list[SecureCheckoutApprovalEvidence] = []
    for approval_id in approval_ids:
        status_value = "unknown"
        reviewed_by = None
        wallet_id = None
        organization_id = None
        reviewed_at = None
        if deps.approval_service:
            try:
                approval = await deps.approval_service.get_approval(approval_id)
            except Exception:
                approval = None
            if approval is None:
                status_value = "not_found"
            else:
                status_value = str(getattr(approval, "status", "") or "found")
                reviewed_by = _iso_or_none(getattr(approval, "reviewed_by", None))
                wallet_id = _iso_or_none(getattr(approval, "wallet_id", None))
                organization_id = _iso_or_none(getattr(approval, "organization_id", None))
                reviewed_at = _iso_or_none(getattr(approval, "reviewed_at", None))
        evidence.append(
            SecureCheckoutApprovalEvidence(
                approval_id=approval_id,
                status=status_value,
                reviewed_by=reviewed_by,
                wallet_id=wallet_id,
                organization_id=organization_id,
                reviewed_at=reviewed_at,
            )
        )
    return evidence


async def _collect_policy_evidence(
    deps: SecureCheckoutDependencies,
    *,
    wallet: Any,
    policy_reason: str,
) -> SecureCheckoutPolicyEvidence:
    if not deps.policy_store or wallet is None:
        return SecureCheckoutPolicyEvidence(policy_present=False, policy_reason=policy_reason)

    try:
        policy = await deps.policy_store.fetch_policy(wallet.agent_id)
    except Exception:
        policy = None
    if policy is None:
        return SecureCheckoutPolicyEvidence(policy_present=False, policy_reason=policy_reason)

    signed_snapshot, snapshot_error = _build_signed_checkout_policy_snapshot(policy)
    if snapshot_error:
        return SecureCheckoutPolicyEvidence(
            policy_present=True,
            policy_reason=snapshot_error,
        )

    snapshot = _policy_snapshot(policy)
    snapshot_hash = hashlib.sha256(_canonical_json_bytes(snapshot)).hexdigest() if snapshot else None
    return SecureCheckoutPolicyEvidence(
        policy_present=True,
        policy_reason=policy_reason,
        policy_hash=snapshot_hash,
        policy_snapshot_id=_iso_or_none((signed_snapshot or {}).get("snapshot_id")),
        policy_snapshot_chain_hash=_iso_or_none((signed_snapshot or {}).get("chain_hash")),
        policy_snapshot_signer_kid=_iso_or_none((signed_snapshot or {}).get("signer_kid")),
        max_per_tx=_iso_or_none(snapshot.get("max_per_tx")),
        max_daily=_iso_or_none(snapshot.get("max_daily")),
        max_monthly=_iso_or_none(snapshot.get("max_monthly")),
        approval_threshold=_iso_or_none(snapshot.get("approval_threshold")),
    )


async def _dispatch_security_alert(
    *,
    job: Optional[dict[str, Any]],
    code: str,
    detail: str,
) -> None:
    if not _dispatch_security_alert_enabled():
        return
    try:
        from sardis_api.routers.alerts import dispatch_alert
        from sardis_v2_core.alert_rules import Alert, AlertSeverity, AlertType

        alert = Alert(
            alert_type=AlertType.POLICY_VIOLATION,
            severity=AlertSeverity.CRITICAL,
            message=f"Secure checkout security incident: {code}",
            agent_id=None,
            organization_id=None,
            data={
                "job_id": (job or {}).get("job_id"),
                "wallet_id": (job or {}).get("wallet_id"),
                "card_id": (job or {}).get("card_id"),
                "merchant_origin": (job or {}).get("merchant_origin"),
                "code": code,
                "detail": detail,
                "channels": ["websocket", "slack"],
            },
        )
        await dispatch_alert(alert)
    except Exception:
        logger.exception("Failed to dispatch secure checkout security alert")


async def _try_rotate_incident_card(
    *,
    deps: SecureCheckoutDependencies,
    job: dict[str, Any],
    compromised_card: dict[str, Any],
    reason_code: str,
) -> None:
    if not deps.card_provider or not deps.card_repo:
        return

    provider_card_id = str(compromised_card.get("provider_card_id") or "").strip()
    if not provider_card_id:
        return

    try:
        await deps.card_provider.cancel_card(provider_card_id=provider_card_id)
        if hasattr(deps.card_repo, "update_status"):
            await deps.card_repo.update_status(str(compromised_card.get("card_id") or ""), "cancelled")
    except Exception:
        logger.exception("Failed to cancel compromised card for rotation")
        return

    replacement_card_id = f"card_{uuid.uuid4().hex[:16]}"
    wallet_id = str(job.get("wallet_id") or compromised_card.get("wallet_id") or "").strip()
    if not wallet_id:
        return

    limit_per_tx = Decimal(str(compromised_card.get("limit_per_tx") or "500"))
    limit_daily = Decimal(str(compromised_card.get("limit_daily") or "2000"))
    limit_monthly = Decimal(str(compromised_card.get("limit_monthly") or "10000"))
    card_type_raw = str(compromised_card.get("card_type") or "multi_use").strip().lower()
    locked_merchant_id = compromised_card.get("locked_merchant_id")

    try:
        replacement = await deps.card_provider.create_card(
            wallet_id=wallet_id,
            card_type=card_type_raw,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            locked_merchant_id=locked_merchant_id,
        )
    except Exception:
        # Compatibility: some provider adapters still expect CardType enum.
        try:
            from sardis_cards.models import CardType

            fallback_card_type = CardType(card_type_raw) if card_type_raw in {item.value for item in CardType} else CardType.MULTI_USE
            replacement = await deps.card_provider.create_card(
                wallet_id=wallet_id,
                card_type=fallback_card_type,
                limit_per_tx=limit_per_tx,
                limit_daily=limit_daily,
                limit_monthly=limit_monthly,
                locked_merchant_id=locked_merchant_id,
            )
        except Exception:
            logger.exception("Failed to create replacement card during rotation")
            return

    if isinstance(replacement, dict):
        replacement_provider_card_id = str(replacement.get("provider_card_id") or "").strip()
    else:
        replacement_provider_card_id = str(getattr(replacement, "provider_card_id", "") or "").strip()
    if not replacement_provider_card_id:
        return

    try:
        if hasattr(deps.card_provider, "activate_card"):
            await deps.card_provider.activate_card(provider_card_id=replacement_provider_card_id)
    except Exception:
        logger.exception("Failed to activate replacement card during rotation")

    if hasattr(deps.card_repo, "create"):
        try:
            await deps.card_repo.create(
                card_id=replacement_card_id,
                wallet_id=wallet_id,
                provider=str(compromised_card.get("provider") or getattr(deps.card_provider, "name", "unknown")),
                provider_card_id=replacement_provider_card_id,
                card_type=card_type_raw,
                limit_per_tx=float(limit_per_tx),
                limit_daily=float(limit_daily),
                limit_monthly=float(limit_monthly),
            )
            if hasattr(deps.card_repo, "update_status"):
                await deps.card_repo.update_status(replacement_card_id, "active")
        except Exception:
            logger.exception("Failed to persist replacement card during rotation")

    await _emit_audit_event(
        deps,
        event_type="secure_checkout.card_auto_rotated",
        payload={
            "job_id": job.get("job_id"),
            "reason": reason_code,
            "compromised_card_id": compromised_card.get("card_id"),
            "replacement_card_id": replacement_card_id,
            "replacement_provider_card_id": replacement_provider_card_id,
        },
    )


def _schedule_auto_unfreeze_after_cooldown(
    *,
    deps: SecureCheckoutDependencies,
    job: dict[str, Any],
    card_id: str,
    provider_card_id: str,
    severity: SecurityIncidentSeverity,
    cooldown_seconds: int,
) -> None:
    if not deps.card_provider or not deps.card_repo:
        return
    if not _auto_unfreeze_on_security_incident_enabled():
        return
    if not _auto_unfreeze_allowed_for_severity(severity):
        return
    if not _auto_unfreeze_ops_approved():
        return

    async def _runner() -> None:
        await asyncio.sleep(cooldown_seconds)
        try:
            await deps.card_provider.unfreeze_card(provider_card_id=provider_card_id)
            if hasattr(deps.card_repo, "update_status"):
                await deps.card_repo.update_status(card_id, "active")
            await _emit_audit_event(
                deps,
                event_type="secure_checkout.card_auto_unfrozen",
                payload={
                    "job_id": job.get("job_id"),
                    "card_id": card_id,
                    "provider_card_id": provider_card_id,
                    "severity": severity.value,
                    "cooldown_seconds": cooldown_seconds,
                },
            )
        except Exception:
            logger.exception("Failed to auto-unfreeze card after cooldown")

    asyncio.create_task(_runner())


async def _handle_security_incident(
    *,
    deps: SecureCheckoutDependencies,
    job: Optional[dict[str, Any]],
    code: str,
    detail: str,
    secret_ref: Optional[str] = None,
) -> None:
    severity = _security_incident_severity(code)
    cooldown_seconds = _security_incident_cooldown_seconds(severity)
    actions: list[str] = ["append_audit", "dispatch_alert"]
    if _auto_freeze_on_security_incident_enabled():
        actions.append("freeze_card")
    if _auto_rotate_on_security_incident_enabled() and severity.value in _auto_rotate_severities():
        actions.append("rotate_card")
    if _auto_unfreeze_on_security_incident_enabled():
        if _auto_unfreeze_allowed_for_severity(severity):
            if _auto_unfreeze_ops_approved():
                actions.append(f"auto_unfreeze_after_{cooldown_seconds}s")
            else:
                actions.append("auto_unfreeze_blocked_missing_ops_approval")
        else:
            actions.append("auto_unfreeze_not_allowed_for_severity")

    safe_detail = _redact_sensitive_text(detail)
    payload: dict[str, Any] = {
        "code": code,
        "severity": severity.value,
        "detail": safe_detail,
        "secret_ref": secret_ref,
        "cooldown_seconds": cooldown_seconds,
        "planned_actions": actions,
    }
    if job:
        payload.update(
            {
                "job_id": job.get("job_id"),
                "intent_id": job.get("intent_id"),
                "wallet_id": job.get("wallet_id"),
                "card_id": job.get("card_id"),
                "merchant_origin": job.get("merchant_origin"),
            }
        )
    await _emit_audit_event(
        deps,
        event_type="secure_checkout.security_incident",
        payload=payload,
    )
    await _dispatch_security_alert(job=job, code=code, detail=safe_detail)

    if not _auto_freeze_on_security_incident_enabled():
        return
    if not job or not deps.card_repo or not deps.card_provider:
        return

    card_id = str(job.get("card_id") or "").strip()
    if not card_id:
        return
    try:
        card = await deps.card_repo.get_by_card_id(card_id)
        provider_card_id = str((card or {}).get("provider_card_id") or "").strip()
        if not provider_card_id:
            return
        await deps.card_provider.freeze_card(provider_card_id=provider_card_id)
        if hasattr(deps.card_repo, "update_status"):
            await deps.card_repo.update_status(card_id, "frozen")
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.card_auto_frozen",
            payload={
                "job_id": job.get("job_id"),
                "card_id": card_id,
                "provider_card_id": provider_card_id,
                "reason": code,
                "severity": severity.value,
            },
        )

        if _auto_rotate_on_security_incident_enabled() and severity.value in _auto_rotate_severities():
            await _try_rotate_incident_card(
                deps=deps,
                job=job,
                compromised_card=card or {"card_id": card_id},
                reason_code=code,
            )

        if _auto_unfreeze_on_security_incident_enabled() and not _auto_unfreeze_ops_approved():
            await _emit_audit_event(
                deps,
                event_type="secure_checkout.card_unfreeze_pending_ops_approval",
                payload={
                    "job_id": job.get("job_id"),
                    "card_id": card_id,
                    "provider_card_id": provider_card_id,
                    "severity": severity.value,
                    "cooldown_seconds": cooldown_seconds,
                },
            )

        _schedule_auto_unfreeze_after_cooldown(
            deps=deps,
            job=job,
            card_id=card_id,
            provider_card_id=provider_card_id,
            severity=severity,
            cooldown_seconds=cooldown_seconds,
        )
    except Exception:
        logger.exception("Failed to auto-freeze card for security incident")


async def _verify_executor_auth(
    *,
    deps: SecureCheckoutDependencies,
    request: Request,
    token: Optional[str],
    timestamp: Optional[str],
    nonce: Optional[str],
    signature: Optional[str],
    payload_bytes: bytes,
) -> None:
    expected = os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip()
    if expected:
        presented = (token or "").strip()
        if not presented or not hmac.compare_digest(presented, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_executor_token")
    elif _is_production_env():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="executor_token_not_configured",
        )

    if not _executor_attestation_enabled():
        return

    key = _executor_attestation_key()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="executor_attestation_key_not_configured",
        )

    ts = (timestamp or "").strip()
    nonce_value = (nonce or "").strip()
    signature_value = (signature or "").strip()
    if not ts or not nonce_value or not signature_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_missing")

    try:
        ts_value = int(ts)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_invalid_ts") from exc

    ttl_seconds = _executor_attestation_ttl_seconds()
    now = int(time.time())
    if abs(now - ts_value) > ttl_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_expired")

    payload_hash = _hash_payload_bytes(payload_bytes)
    expected_sig = _compute_executor_signature(
        key=key,
        method=request.method,
        path=request.url.path,
        timestamp=ts,
        nonce=nonce_value,
        payload_hash=payload_hash,
    )
    if not hmac.compare_digest(signature_value, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_invalid_signature")

    store = _resolve_store(deps)
    first_seen = await store.mark_executor_nonce_used(nonce_value, ttl_seconds=ttl_seconds)
    if not first_seen:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_replay")


def _serialize_job(job: dict[str, Any]) -> SecureCheckoutJobResponse:
    approval_ids = list(job.get("approval_ids") or [])
    approval_id = job.get("approval_id")
    if approval_id and approval_id not in approval_ids:
        approval_ids.insert(0, str(approval_id))
    approval_quorum_required = int(
        job.get("approval_quorum_required")
        or _required_checkout_approvals(
            approval_required=bool(job.get("approval_required")),
            merchant_mode=str(job.get("merchant_mode") or ""),
        )
    )
    return SecureCheckoutJobResponse(
        job_id=job["job_id"],
        intent_id=job["intent_id"],
        wallet_id=job["wallet_id"],
        card_id=job["card_id"],
        merchant_origin=job["merchant_origin"],
        merchant_mode=MerchantExecutionMode(job["merchant_mode"]),
        status=SecureCheckoutJobStatus(job["status"]),
        amount=str(job["amount"]),
        currency=job["currency"],
        approval_required=bool(job["approval_required"]),
        approval_id=approval_id,
        approval_ids=approval_ids,
        approval_quorum_required=approval_quorum_required,
        policy_reason=job.get("policy_reason", "OK"),
        executor_ref=job.get("executor_ref"),
        secret_ref=job.get("secret_ref"),
        secret_expires_at=job.get("secret_expires_at"),
        redacted_card=job.get("redacted_card") or {},
        options=SecureExecutionOptions(**(job.get("options") or {})),
        created_at=job["created_at"].isoformat(),
        updated_at=job["updated_at"].isoformat(),
        error_code=job.get("error_code"),
        error=job.get("error"),
    )


async def _require_wallet_access(
    *,
    deps: SecureCheckoutDependencies,
    principal: Principal,
    wallet_id: str,
) -> Any:
    if not deps.wallet_repo or not deps.agent_repo:
        if _is_production_env():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="wallet_or_agent_repository_not_configured",
            )
        return None

    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not principal.is_admin and getattr(agent, "owner_id", None) != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return wallet


async def _evaluate_policy(
    *,
    deps: SecureCheckoutDependencies,
    wallet: Any,
    amount: Decimal,
) -> tuple[bool, str]:
    if not deps.policy_store:
        if _is_production_env():
            return False, "policy_store_not_configured"
        return True, "OK"

    policy = await deps.policy_store.fetch_policy(wallet.agent_id)
    if not policy:
        return True, "OK"

    _, snapshot_error = _build_signed_checkout_policy_snapshot(policy)
    if snapshot_error:
        return False, snapshot_error

    allowed, reason = policy.validate_payment(
        amount=amount,
        fee=Decimal("0"),
        mcc_code=None,
        merchant_category=None,
    )
    return bool(allowed), str(reason or "policy_denied")


async def _validate_approved_token(
    *,
    deps: SecureCheckoutDependencies,
    approval_id: Optional[str],
    approval_ids: Optional[list[str]],
    principal: Principal,
    wallet_id: str,
    min_approvals: int = 1,
    require_distinct_reviewers: bool = False,
) -> tuple[bool, str, list[str]]:
    requested_ids: list[str] = []
    if approval_id:
        requested_ids.append(str(approval_id).strip())
    requested_ids.extend(str(item).strip() for item in (approval_ids or []) if str(item).strip())
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in requested_ids:
        if candidate and candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)

    required = max(0, int(min_approvals))
    if required == 0:
        return True, "approval_not_required", []
    if not deduped:
        return False, "approval_required", []
    if len(deduped) < required:
        return False, f"approval_quorum_not_met:{len(deduped)}/{required}", []
    if not deps.approval_service:
        return False, "approval_service_not_configured", []

    validated: list[str] = []
    reviewers: set[str] = set()
    for candidate in deduped:
        approval = await deps.approval_service.get_approval(candidate)
        if not approval:
            return False, "approval_not_found", validated
        if str(getattr(approval, "status", "") or "").strip().lower() != "approved":
            return False, "approval_not_approved", validated
        approval_wallet_id = str(getattr(approval, "wallet_id", "") or "").strip()
        if approval_wallet_id and approval_wallet_id != wallet_id:
            return False, "approval_wallet_mismatch", validated
        approval_org_id = str(getattr(approval, "organization_id", "") or "").strip()
        if approval_org_id and approval_org_id != principal.organization_id and not principal.is_admin:
            return False, "approval_org_mismatch", validated
        reviewer = str(getattr(approval, "reviewed_by", "") or "").strip().lower()
        if require_distinct_reviewers and not reviewer:
            return False, "approval_missing_reviewer", validated
        if reviewer:
            reviewers.add(reviewer)
        validated.append(candidate)

    if len(validated) < required:
        return False, f"approval_quorum_not_met:{len(validated)}/{required}", validated
    if require_distinct_reviewers and len(reviewers) < required:
        return False, f"approval_distinct_reviewer_quorum_not_met:{len(reviewers)}/{required}", validated
    return True, "approval_valid", validated


def create_secure_checkout_router() -> APIRouter:
    """Create secure checkout router."""
    router = APIRouter(dependencies=[Depends(require_principal)])

    @router.get("/secure/security-policy", response_model=SecureCheckoutSecurityPolicyResponse)
    async def get_security_policy(
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        if not principal.is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
        store = _resolve_store(deps)
        pan_allowlist = _parse_csv_env("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS")
        boundary_mode, provider_boundary_mode, boundary_locked = _resolve_pan_boundary_mode()
        return SecureCheckoutSecurityPolicyResponse(
            pan_execution_enabled=_pan_execution_enabled(),
            require_shared_secret_store=_require_shared_secret_store(),
            shared_secret_store_configured=_has_shared_secret_store(store),
            pan_entry_allowlist=sorted(pan_allowlist),
            production_pan_entry_requires_allowlist=_require_tokenized_in_prod(),
            pan_entry_break_glass_only=_require_tokenized_in_prod(),
            pan_boundary_mode=boundary_mode,
            pan_provider=_pan_provider() or "unknown",
            pan_provider_boundary_mode=provider_boundary_mode,
            pan_boundary_mode_locked=boundary_locked,
            issuer_hosted_reveal_preferred=True,
            supported_merchant_modes=[mode.value for mode in MerchantExecutionMode],
            recommended_default_mode=MerchantExecutionMode.EMBEDDED_IFRAME.value,
            auto_freeze_on_security_incident=_auto_freeze_on_security_incident_enabled(),
            auto_rotate_on_security_incident=_auto_rotate_on_security_incident_enabled(),
            auto_rotate_severities=sorted(_auto_rotate_severities()),
            auto_unfreeze_on_security_incident=_auto_unfreeze_on_security_incident_enabled(),
            auto_unfreeze_ops_approved=_auto_unfreeze_ops_approved(),
            auto_unfreeze_allowed_severities=sorted(_auto_unfreeze_allowed_severities()),
            min_approvals=_checkout_min_approvals(),
            pan_min_approvals=_checkout_pan_min_approvals(),
            require_distinct_approval_reviewers=_checkout_require_distinct_approval_reviewers(),
            incident_cooldown_seconds={
                level.value: _security_incident_cooldown_seconds(level)
                for level in SecurityIncidentSeverity
            },
        )

    @router.post("/secure/merchant-capability", response_model=MerchantCapabilityResponse)
    async def get_merchant_capability(
        payload: MerchantCapabilityRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        # Keep the same wallet/org auth surface by requiring principal even for preflight.
        _ = deps
        _ = principal
        try:
            merchant_origin, merchant_host = _normalize_merchant_origin(payload.merchant_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        merchant_mode, mode_reason = _resolve_merchant_mode(merchant_host)
        pan_allowed_for_merchant = True
        pan_compliance_ready = True
        pan_compliance_reason = "ok"
        if merchant_mode == MerchantExecutionMode.PAN_ENTRY:
            pan_allowed_for_merchant, pan_mode_reason = _pan_entry_policy_decision(merchant_host)
            pan_compliance_ready = pan_mode_reason in {"pan_entry_allowed", "pan_entry_not_allowlisted"}
            pan_compliance_reason = "ok" if pan_compliance_ready else pan_mode_reason
            if not pan_allowed_for_merchant:
                mode_reason = pan_mode_reason
        threshold = _approval_threshold()
        amount = payload.amount or Decimal("0")
        approval_likely_required = (
            (merchant_mode == MerchantExecutionMode.PAN_ENTRY and _require_approval_for_pan())
            or (payload.amount is not None and amount >= threshold)
        )
        return MerchantCapabilityResponse(
            merchant_origin=merchant_origin,
            merchant_host=merchant_host,
            merchant_mode=merchant_mode,
            mode_reason=mode_reason,
            approval_likely_required=approval_likely_required,
            pan_execution_enabled=_pan_execution_enabled(),
            pan_allowed_for_merchant=pan_allowed_for_merchant,
            pan_compliance_ready=pan_compliance_ready,
            pan_compliance_reason=pan_compliance_reason,
        )

    @router.post("/secure/jobs", response_model=SecureCheckoutJobResponse, status_code=status.HTTP_201_CREATED)
    async def create_secure_job(
        payload: CreateSecureCheckoutJobRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        if _require_persistent_job_store() and not _is_persistent_store(store):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="secure_checkout_persistent_store_required",
            )
        wallet = await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=payload.wallet_id,
        )

        if not deps.card_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="card_repository_not_configured",
            )

        card = await deps.card_repo.get_by_card_id(payload.card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        if str(card.get("wallet_id") or "") != payload.wallet_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Card does not belong to wallet")

        card_status = str(card.get("status") or "").strip().lower()
        if card_status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is not active")

        try:
            merchant_origin, merchant_host = _normalize_merchant_origin(payload.merchant_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        merchant_mode, mode_reason = _resolve_merchant_mode(merchant_host)
        if merchant_mode == MerchantExecutionMode.BLOCKED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mode_reason)
        if merchant_mode == MerchantExecutionMode.PAN_ENTRY:
            pan_allowed_for_merchant, pan_mode_reason = _pan_entry_policy_decision(merchant_host)
            if not pan_allowed_for_merchant:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=pan_mode_reason)

        if wallet is None:
            policy_ok, policy_reason = (True, "OK")
        else:
            policy_ok, policy_reason = await _evaluate_policy(
                deps=deps,
                wallet=wallet,
                amount=payload.amount,
            )
        if not policy_ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=policy_reason)

        approval_required = (
            policy_reason == "requires_approval"
            or payload.amount >= _approval_threshold()
            or (merchant_mode == MerchantExecutionMode.PAN_ENTRY and _require_approval_for_pan())
        )
        required_approvals = _required_checkout_approvals(
            approval_required=approval_required,
            merchant_mode=merchant_mode,
        )
        approval_ok, _, validated_approval_ids = await _validate_approved_token(
            deps=deps,
            approval_id=payload.approval_id,
            approval_ids=payload.approval_ids,
            principal=principal,
            wallet_id=payload.wallet_id,
            min_approvals=required_approvals,
            require_distinct_reviewers=_checkout_require_distinct_approval_reviewers(),
        )
        job_status = SecureCheckoutJobStatus.READY
        if approval_required and not approval_ok:
            job_status = SecureCheckoutJobStatus.PENDING_APPROVAL

        now = _now_utc()
        options = _sanitize_options(payload.options)
        job = {
            "job_id": f"scj_{uuid.uuid4().hex[:16]}",
            "intent_id": payload.intent_id,
            "wallet_id": payload.wallet_id,
            "card_id": payload.card_id,
            "merchant_origin": merchant_origin,
            "merchant_mode": merchant_mode.value,
            "status": job_status.value,
            "amount": payload.amount,
            "currency": payload.currency.upper(),
            "purpose": payload.purpose,
            "approval_required": approval_required,
            "approval_id": validated_approval_ids[0] if approval_ok and validated_approval_ids else None,
            "approval_ids": validated_approval_ids if approval_ok else [],
            "approval_quorum_required": required_approvals,
            "policy_reason": policy_reason,
            "executor_ref": None,
            "secret_ref": None,
            "secret_expires_at": None,
            "redacted_card": _redacted_card_summary(card),
            "options": options.model_dump(),
            "created_at": now,
            "updated_at": now,
            "error_code": None,
            "error": None,
        }
        saved = await store.upsert_job(job)
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.job_created",
            payload={
                "job_id": saved["job_id"],
                "intent_id": saved["intent_id"],
                "wallet_id": saved["wallet_id"],
                "merchant_origin": saved["merchant_origin"],
                "merchant_mode": saved["merchant_mode"],
                "status": saved["status"],
                "approval_required": saved["approval_required"],
                "approval_quorum_required": saved.get("approval_quorum_required", required_approvals),
                "approval_count": len(saved.get("approval_ids") or validated_approval_ids),
                "policy_reason": saved.get("policy_reason"),
            },
        )
        saved["approval_ids"] = saved.get("approval_ids") or validated_approval_ids
        saved["approval_quorum_required"] = saved.get("approval_quorum_required") or required_approvals
        return _serialize_job(saved)

    @router.get("/secure/jobs/{job_id}", response_model=SecureCheckoutJobResponse)
    async def get_secure_job(
        job_id: str,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=job["wallet_id"],
        )
        return _serialize_job(job)

    @router.get("/secure/jobs/{job_id}/evidence", response_model=SecureCheckoutEvidenceExportResponse)
    async def get_secure_job_evidence(
        job_id: str,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        wallet = await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=job["wallet_id"],
        )

        job_payload = _serialize_job(job)
        approval_ids = list(job_payload.approval_ids or [])
        approvals = await _collect_approval_evidence(deps, approval_ids)
        policy = await _collect_policy_evidence(
            deps,
            wallet=wallet,
            policy_reason=str(job.get("policy_reason") or "OK"),
        )
        store_has_shared_secrets = _has_shared_secret_store(store)
        attestation = SecureCheckoutAttestationEvidence(
            dispatch_required=_dispatch_required(),
            dispatch_url_configured=bool(_executor_dispatch_url()),
            executor_attestation_enabled=_executor_attestation_enabled(),
            executor_attestation_ttl_seconds=_executor_attestation_ttl_seconds(),
            shared_secret_store_required=_require_shared_secret_store(),
            shared_secret_store_configured=store_has_shared_secrets,
        )
        events = await _collect_job_audit_events(
            deps,
            job_id=job_payload.job_id,
            intent_id=job_payload.intent_id,
        )
        digest_material = {
            "job": job_payload.model_dump(),
            "approvals": [item.model_dump() for item in approvals],
            "policy": policy.model_dump(),
            "attestation": attestation.model_dump(),
            "audit_events": events,
        }
        digest_sha256 = hashlib.sha256(_canonical_json_bytes(digest_material)).hexdigest()
        chain_tail, chain_entries = _hash_chain_tail(events)
        integrity = SecureCheckoutEvidenceIntegrity(
            digest_sha256=digest_sha256,
            hash_chain_tail=chain_tail,
            hash_chain_entries=chain_entries,
            event_count=len(events),
        )
        scope_window = {
            "job_created_at": job_payload.created_at,
            "job_updated_at": job_payload.updated_at,
            "first_event_at": events[0]["ts"] if events else None,
            "last_event_at": events[-1]["ts"] if events else None,
        }
        return SecureCheckoutEvidenceExportResponse(
            job=job_payload,
            approvals=approvals,
            policy=policy,
            attestation=attestation,
            audit_events=events,
            integrity=integrity,
            generated_at=_now_utc().isoformat(),
            scope_window=scope_window,
            verifier_hints=[
                "Recompute digest_sha256 from canonical JSON of job/approvals/policy/attestation/audit_events.",
                "Rebuild hash_chain_tail by replaying audit_events in timestamp order.",
                "Cross-check approval_id values against approvals service records.",
            ],
        )

    @router.post("/secure/jobs/{job_id}/execute", response_model=SecureCheckoutJobResponse)
    async def execute_secure_job(
        job_id: str,
        payload: ExecuteSecureCheckoutJobRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        if _require_persistent_job_store() and not _is_persistent_store(store):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="secure_checkout_persistent_store_required",
            )
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=job["wallet_id"],
        )

        if job["status"] == SecureCheckoutJobStatus.PENDING_APPROVAL.value:
            required_approvals = int(
                job.get("approval_quorum_required")
                or _required_checkout_approvals(
                    approval_required=bool(job.get("approval_required")),
                    merchant_mode=str(job.get("merchant_mode") or ""),
                )
            )
            approval_ok, approval_reason, validated_approval_ids = await _validate_approved_token(
                deps=deps,
                approval_id=payload.approval_id,
                approval_ids=payload.approval_ids,
                principal=principal,
                wallet_id=job["wallet_id"],
                min_approvals=required_approvals,
                require_distinct_reviewers=_checkout_require_distinct_approval_reviewers(),
            )
            if not approval_ok:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=approval_reason)
            updated_job = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.READY.value,
                approval_id=validated_approval_ids[0] if validated_approval_ids else payload.approval_id,
            )
            job = updated_job or job
            job["approval_ids"] = validated_approval_ids
            job["approval_quorum_required"] = required_approvals

        if job["status"] != SecureCheckoutJobStatus.READY.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"job_not_ready:{job['status']}")

        if job["merchant_mode"] in {
            MerchantExecutionMode.TOKENIZED_API.value,
            MerchantExecutionMode.EMBEDDED_IFRAME.value,
        }:
            dispatch_ok, executor_ref, dispatch_error = await _dispatch_to_executor(job=job)
            if not dispatch_ok and _dispatch_required():
                updated = await store.update_job(
                    job_id,
                    status=SecureCheckoutJobStatus.FAILED.value,
                    error_code="executor_dispatch_failed",
                    error=dispatch_error or "executor_dispatch_failed",
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(updated or job).get("error_code"),
                )
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.DISPATCHED.value,
                executor_ref=executor_ref
                or (
                    f"embedded_iframe:{job_id}"
                    if job["merchant_mode"] == MerchantExecutionMode.EMBEDDED_IFRAME.value
                    else f"tokenized:{job_id}"
                ),
            )
            dispatched = updated or job
            await _emit_audit_event(
                deps,
                event_type="secure_checkout.job_dispatched",
                payload={
                    "job_id": dispatched["job_id"],
                    "intent_id": dispatched["intent_id"],
                    "wallet_id": dispatched["wallet_id"],
                    "merchant_mode": dispatched["merchant_mode"],
                    "executor_ref": dispatched.get("executor_ref"),
                    "secret_ref": None,
                },
            )
            serialized_job = dict(updated or job)
            if job.get("approval_ids"):
                serialized_job["approval_ids"] = list(job.get("approval_ids") or [])
            if job.get("approval_quorum_required"):
                serialized_job["approval_quorum_required"] = job.get("approval_quorum_required")
            return _serialize_job(serialized_job)

        merchant_host = urlparse(job["merchant_origin"]).hostname or ""
        pan_allowed_for_merchant, pan_mode_reason = _pan_entry_policy_decision(merchant_host)
        if not pan_allowed_for_merchant:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code=pan_mode_reason,
                error=f"PAN execution rejected: {pan_mode_reason}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(updated or job).get("error_code"),
            )

        if _require_shared_secret_store() and not _has_shared_secret_store(store):
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="secure_secret_store_not_configured",
                error="secure_secret_store_not_configured",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(updated or job).get("error_code"),
            )

        runtime_ready, runtime_reason = _pan_executor_runtime_ready()
        if not runtime_ready:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code=runtime_reason,
                error=runtime_reason,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(updated or job).get("error_code"),
            )

        if not deps.card_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="card_provider_not_configured",
            )

        try:
            details = await deps.card_provider.reveal_card_details(
                card_id=job["card_id"],
                reason="secure_checkout_executor",
            )
        except Exception as exc:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="card_details_reveal_failed",
                error=_redact_sensitive_text(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(updated or job).get("error_code"),
            ) from exc

        secret_ref = f"sec_{uuid.uuid4().hex[:18]}"
        expires_at = _now_utc() + timedelta(seconds=_secret_ttl_seconds())
        try:
            secret_payload = _build_secret_payload_from_reveal(
                details=details if isinstance(details, dict) else {},
                merchant_origin=job["merchant_origin"],
                amount=job["amount"],
                currency=job["currency"],
                purpose=job["purpose"],
            )
        except ValueError as exc:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="card_details_invalid",
                error=_redact_sensitive_text(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(updated or job).get("error_code"),
            ) from exc
        await store.put_secret(secret_ref, secret_payload, expires_at=expires_at)
        dispatch_ok, executor_ref, dispatch_error = await _dispatch_to_executor(
            job=job,
            secret_ref=secret_ref,
            secret_expires_at=expires_at.isoformat(),
        )
        if not dispatch_ok and _dispatch_required():
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="executor_dispatch_failed",
                error=dispatch_error or "executor_dispatch_failed",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(updated or job).get("error_code"),
            )
        updated = await store.update_job(
            job_id,
            status=SecureCheckoutJobStatus.DISPATCHED.value,
            secret_ref=secret_ref,
            secret_expires_at=expires_at.isoformat(),
            executor_ref=executor_ref or f"secret_ref:{secret_ref}",
        )
        dispatched = updated or job
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.job_dispatched",
            payload={
                "job_id": dispatched["job_id"],
                "intent_id": dispatched["intent_id"],
                "wallet_id": dispatched["wallet_id"],
                "merchant_mode": dispatched["merchant_mode"],
                "executor_ref": dispatched.get("executor_ref"),
                "secret_ref_present": bool(dispatched.get("secret_ref")),
                "secret_expires_at": dispatched.get("secret_expires_at"),
            },
        )
        serialized_job = dict(updated or job)
        if job.get("approval_ids"):
            serialized_job["approval_ids"] = list(job.get("approval_ids") or [])
        if job.get("approval_quorum_required"):
            serialized_job["approval_quorum_required"] = job.get("approval_quorum_required")
        return _serialize_job(serialized_job)

    @router.post(
        "/secure/secrets/{secret_ref}/consume",
        response_model=ConsumeExecutorSecretResponse,
        include_in_schema=False,
    )
    async def consume_executor_secret(
        secret_ref: str,
        request: Request,
        x_sardis_executor_token: Optional[str] = Header(default=None),
        x_sardis_executor_timestamp: Optional[str] = Header(default=None),
        x_sardis_executor_nonce: Optional[str] = Header(default=None),
        x_sardis_executor_signature: Optional[str] = Header(default=None),
        deps: SecureCheckoutDependencies = Depends(get_deps),
    ):
        store = _resolve_store(deps)
        body = await request.body()
        try:
            await _verify_executor_auth(
                deps=deps,
                request=request,
                token=x_sardis_executor_token,
                timestamp=x_sardis_executor_timestamp,
                nonce=x_sardis_executor_nonce,
                signature=x_sardis_executor_signature,
                payload_bytes=body,
            )
        except HTTPException as exc:
            await _handle_security_incident(
                deps=deps,
                job=None,
                code="executor_auth_failed",
                detail=str(exc.detail),
                secret_ref=secret_ref,
            )
            raise

        payload = await store.consume_secret(secret_ref)
        if not payload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="secret_not_found_or_expired")
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.secret_consumed",
            payload={
                "secret_ref": secret_ref,
                "merchant_origin": payload.get("merchant_origin"),
                "amount": payload.get("amount"),
                "currency": payload.get("currency"),
                "purpose": payload.get("purpose"),
            },
        )
        return ConsumeExecutorSecretResponse(**payload)

    @router.post(
        "/secure/jobs/{job_id}/complete",
        response_model=SecureCheckoutJobResponse,
        include_in_schema=False,
    )
    async def complete_executor_job(
        job_id: str,
        payload: CompleteSecureCheckoutJobRequest,
        request: Request,
        x_sardis_executor_token: Optional[str] = Header(default=None),
        x_sardis_completion_idempotency_key: Optional[str] = Header(default=None),
        x_sardis_executor_timestamp: Optional[str] = Header(default=None),
        x_sardis_executor_nonce: Optional[str] = Header(default=None),
        x_sardis_executor_signature: Optional[str] = Header(default=None),
        deps: SecureCheckoutDependencies = Depends(get_deps),
    ):
        store = _resolve_store(deps)
        job_for_incident = await store.get_job(job_id)
        body = await request.body()
        try:
            await _verify_executor_auth(
                deps=deps,
                request=request,
                token=x_sardis_executor_token,
                timestamp=x_sardis_executor_timestamp,
                nonce=x_sardis_executor_nonce,
                signature=x_sardis_executor_signature,
                payload_bytes=body,
            )
        except HTTPException as exc:
            await _handle_security_incident(
                deps=deps,
                job=job_for_incident,
                code="executor_auth_failed",
                detail=str(exc.detail),
            )
            raise

        completion_key = (x_sardis_completion_idempotency_key or "").strip()
        if completion_key:
            existing_receipt = await store.get_completion_receipt(completion_key)
            if existing_receipt:
                return _serialize_job(existing_receipt)

        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        if job["status"] != SecureCheckoutJobStatus.DISPATCHED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"job_not_dispatched:{job['status']}",
            )

        desired_status = SecureCheckoutJobStatus.COMPLETED.value
        error_code = None
        error = None
        if payload.status == "failed":
            desired_status = SecureCheckoutJobStatus.FAILED.value
            error_code = "executor_failed"
            error = payload.failure_reason or "executor_failed"

        secret_ref = job.get("secret_ref")
        if secret_ref:
            await store.drop_secret(secret_ref)

        updated = await store.update_job(
            job_id,
            status=desired_status,
            executor_ref=payload.executor_ref or job.get("executor_ref"),
            error_code=error_code,
            error=error,
            secret_ref=None,
            secret_expires_at=None,
        )
        finalized = updated or job
        if completion_key:
            await store.put_completion_receipt(completion_key, finalized)
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.job_finalized",
            payload={
                "job_id": finalized["job_id"],
                "intent_id": finalized["intent_id"],
                "wallet_id": finalized["wallet_id"],
                "status": finalized["status"],
                "executor_ref": finalized.get("executor_ref"),
                "error_code": finalized.get("error_code"),
            },
        )
        return _serialize_job(updated or job)

    return router


router = create_secure_checkout_router()
