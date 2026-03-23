"""Merchant Countersignature — verified usage reporting.

Merchants sign usage reports to prevent agents from fabricating
consumption data. Supports HMAC-SHA256 (simple) and Ed25519 (strong).

Usage::

    verifier = MerchantCountersignature(shared_secret="merchant_hmac_key")
    valid = verifier.verify(
        meter_id="meter_abc",
        usage_delta=Decimal("150"),
        timestamp=1711200000,
        signature="a1b2c3...",
    )
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

logger = logging.getLogger("sardis.merchant_countersignature")

# Maximum clock skew allowed (5 minutes)
MAX_TIMESTAMP_DRIFT_SECONDS = 300


class SignatureMethod(str, Enum):
    """Supported signature methods."""
    HMAC_SHA256 = "hmac_sha256"
    ED25519 = "ed25519"


@dataclass
class CountersignaturePayload:
    """The canonical payload that gets signed."""
    meter_id: str
    usage_delta: Decimal
    timestamp: int  # Unix epoch seconds
    merchant_id: str = ""
    nonce: str = ""

    def canonical_bytes(self) -> bytes:
        """Deterministic JSON encoding for signing."""
        data = {
            "merchant_id": self.merchant_id,
            "meter_id": self.meter_id,
            "nonce": self.nonce,
            "timestamp": self.timestamp,
            "usage_delta": str(self.usage_delta),
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":")).encode()


@dataclass
class VerificationResult:
    """Result of a countersignature verification."""
    valid: bool
    method: SignatureMethod
    reason: str | None = None
    verified_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class MerchantCountersignature:
    """Verifies merchant-signed usage reports.

    Prevents agents from fabricating usage data by requiring
    the merchant to countersign each usage delta.
    """

    def __init__(
        self,
        shared_secret: str | None = None,
        public_key: bytes | None = None,
        method: SignatureMethod = SignatureMethod.HMAC_SHA256,
        max_drift_seconds: int = MAX_TIMESTAMP_DRIFT_SECONDS,
    ) -> None:
        self._secret = shared_secret
        self._public_key = public_key
        self._method = method
        self._max_drift = max_drift_seconds

    def sign(self, payload: CountersignaturePayload) -> str:
        """Sign a usage report payload (merchant-side)."""
        data = payload.canonical_bytes()

        if self._method == SignatureMethod.HMAC_SHA256:
            if not self._secret:
                raise ValueError("HMAC signing requires shared_secret")
            sig = hmac.new(
                self._secret.encode(), data, hashlib.sha256
            ).hexdigest()
            return sig

        if self._method == SignatureMethod.ED25519:
            raise NotImplementedError("Ed25519 signing requires nacl library")

        raise ValueError(f"Unsupported method: {self._method}")

    def verify(
        self,
        meter_id: str,
        usage_delta: Decimal,
        timestamp: int,
        signature: str,
        merchant_id: str = "",
        nonce: str = "",
    ) -> VerificationResult:
        """Verify a merchant countersignature on a usage report."""
        # Check timestamp freshness
        now = int(datetime.now(UTC).timestamp())
        drift = abs(now - timestamp)
        if drift > self._max_drift:
            return VerificationResult(
                valid=False,
                method=self._method,
                reason=f"Timestamp drift {drift}s exceeds max {self._max_drift}s",
            )

        payload = CountersignaturePayload(
            meter_id=meter_id,
            usage_delta=usage_delta,
            timestamp=timestamp,
            merchant_id=merchant_id,
            nonce=nonce,
        )
        data = payload.canonical_bytes()

        if self._method == SignatureMethod.HMAC_SHA256:
            if not self._secret:
                return VerificationResult(
                    valid=False, method=self._method,
                    reason="No shared_secret configured",
                )
            expected = hmac.new(
                self._secret.encode(), data, hashlib.sha256
            ).hexdigest()
            valid = hmac.compare_digest(expected, signature)
            return VerificationResult(
                valid=valid,
                method=self._method,
                reason=None if valid else "Signature mismatch",
            )

        if self._method == SignatureMethod.ED25519:
            if not self._public_key:
                return VerificationResult(
                    valid=False, method=self._method,
                    reason="No public_key configured",
                )
            try:
                from nacl.signing import VerifyKey
                vk = VerifyKey(self._public_key)
                vk.verify(data, bytes.fromhex(signature))
                return VerificationResult(valid=True, method=self._method)
            except Exception as e:
                return VerificationResult(
                    valid=False, method=self._method,
                    reason=f"Ed25519 verification failed: {e}",
                )

        return VerificationResult(
            valid=False, method=self._method,
            reason=f"Unsupported method: {self._method}",
        )
