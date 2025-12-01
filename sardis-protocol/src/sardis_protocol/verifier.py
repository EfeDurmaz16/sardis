"""Mandate verification pipeline."""
from __future__ import annotations

import base64
import time
from dataclasses import dataclass

from sardis_v2_core import SardisSettings
from sardis_v2_core.identity import AgentIdentity
from sardis_v2_core.mandates import PaymentMandate


@dataclass
class VerificationResult:
    accepted: bool
    reason: str | None = None


class ReplayCache:
    def __init__(self):
        self._seen: dict[str, int] = {}

    def check_and_store(self, mandate_id: str, expires_at: int) -> bool:
        deadline = self._seen.get(mandate_id)
        now = int(time.time())
        if deadline and deadline > now:
            return False
        self._seen[mandate_id] = expires_at
        return True


class MandateVerifier:
    def __init__(self, settings: SardisSettings, replay_cache: ReplayCache | None = None):
        self._settings = settings
        self._replay_cache = replay_cache or ReplayCache()

    def verify(self, mandate: PaymentMandate) -> VerificationResult:
        if mandate.is_expired():
            return VerificationResult(False, "mandate_expired")
        if mandate.domain not in self._settings.allowed_domains:
            return VerificationResult(False, "domain_not_authorized")
        if not self._replay_cache.check_and_store(mandate.mandate_id, mandate.expires_at):
            return VerificationResult(False, "mandate_replayed")

        agent = self._identity_from_proof(mandate)
        if not agent:
            return VerificationResult(False, "identity_not_resolved")

        try:
            signature = base64.b64decode(mandate.proof.proof_value)
        except Exception:  # noqa: BLE001
            return VerificationResult(False, "signature_malformed")

        payload = self._canonical_payment_payload(mandate)
        if not agent.verify(payload, signature=signature, domain=mandate.domain, nonce=mandate.nonce, purpose="checkout"):
            return VerificationResult(False, "signature_invalid")
        return VerificationResult(True)

    def _identity_from_proof(self, mandate: PaymentMandate) -> AgentIdentity | None:
        method = mandate.proof.verification_method
        if "#" not in method:
            return None
        _, fragment = method.split("#", 1)
        try:
            algorithm, key_material = fragment.split(":", 1)
        except ValueError:
            return None
        if algorithm not in {"ed25519", "ecdsa-p256"}:
            return None
        try:
            public_key = bytes.fromhex(key_material)
        except ValueError:
            return None
        return AgentIdentity(
            agent_id=mandate.subject,
            public_key=public_key,
            domain=mandate.domain,
            algorithm="ecdsa-p256" if algorithm == "ecdsa-p256" else "ed25519",
        )

    @staticmethod
    def _canonical_payment_payload(mandate: PaymentMandate) -> bytes:
        fields = [
            mandate.mandate_id,
            mandate.subject,
            str(mandate.amount_minor),
            mandate.token,
            mandate.chain,
            mandate.destination,
            mandate.audit_hash,
        ]
        return "|".join(fields).encode()
