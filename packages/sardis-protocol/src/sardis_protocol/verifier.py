"""Mandate verification pipeline."""
from __future__ import annotations

import base64
import logging
import os
import time
from dataclasses import MISSING, dataclass, fields
from typing import Any, Dict, Optional, Type

from sardis_v2_core import SardisSettings
from sardis_v2_core.identity import AgentIdentity, IdentityRegistry
from sardis_v2_core.mandates import CartMandate, IntentMandate, MandateBase, MandateChain, PaymentMandate, VCProof
from .schemas import AP2PaymentExecuteRequest
from .storage import MandateArchive, ReplayCache
from .rate_limiter import AgentRateLimiter, RateLimitConfig, get_rate_limiter
from .reason_codes import ProtocolReasonCode, map_legacy_reason_to_code

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Raised when verification requirements are not met."""
    pass


@dataclass
class VerificationResult:
    accepted: bool
    reason: str | None = None
    sd_jwt_detected: bool = False
    reason_code: ProtocolReasonCode | None = None


@dataclass
class MandateChainVerification:
    accepted: bool
    reason: str | None = None
    chain: MandateChain | None = None
    sd_jwt_detected: bool = False
    reason_code: ProtocolReasonCode | None = None


class MandateVerifier:
    def __init__(
        self,
        settings: SardisSettings,
        replay_cache: ReplayCache | None = None,
        archive: MandateArchive | None = None,
        rate_limiter: AgentRateLimiter | None = None,
        rate_limit_config: RateLimitConfig | None = None,
        identity_registry: IdentityRegistry | None = None,
    ):
        self._settings = settings
        self._replay_cache = replay_cache or ReplayCache()
        self._archive = archive
        self._rate_limiter = rate_limiter or get_rate_limiter(rate_limit_config)
        self._identity_registry = identity_registry

    @staticmethod
    def _detect_sd_jwt(data: dict) -> bool:
        """Detect SD-JWT indicators in mandate data.

        Args:
            data: Mandate payload dictionary

        Returns:
            True if SD-JWT indicators found, False otherwise
        """
        # Check for SD-JWT selective disclosure key
        if "_sd" in data:
            return True

        # Check for SD-JWT algorithm declaration
        if "_sd_alg" in data:
            return True

        # Check for SD-JWT disclosure separator in proof
        proof = data.get("proof")
        if isinstance(proof, dict):
            proof_value = proof.get("proof_value", "")
            if "~" in proof_value:
                return True

        return False

    @staticmethod
    def _jcs_canonicalize(obj: dict) -> bytes:
        """RFC 8785 JSON Canonicalization Scheme.

        Rules:
        - Object keys sorted lexicographically (Unicode code point order)
        - No whitespace between tokens
        - Numbers: no leading zeros, no trailing zeros after decimal, no positive sign
        - Strings: minimal escape sequences
        - Recursive for nested objects/arrays
        """
        import json

        def _sort_recursive(value):
            if isinstance(value, dict):
                return {k: _sort_recursive(v) for k, v in sorted(value.items())}
            if isinstance(value, list):
                return [_sort_recursive(item) for item in value]
            return value

        sorted_obj = _sort_recursive(obj)
        return json.dumps(sorted_obj, separators=(",", ":"), ensure_ascii=False, sort_keys=True).encode("utf-8")

    def verify(self, mandate: IntentMandate | CartMandate | PaymentMandate, *, use_jcs: bool = False) -> VerificationResult:
        if mandate.is_expired():
            reason = "mandate_expired"
            return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))
        if mandate.domain not in self._settings.allowed_domains:
            reason = "domain_not_authorized"
            return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))
        if not self._replay_cache.check_and_store(mandate.mandate_id, mandate.expires_at):
            reason = "mandate_replayed"
            return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))

        agent = self._identity_from_proof(mandate)
        if not agent:
            reason = "identity_not_resolved"
            return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))

        try:
            signature = base64.b64decode(mandate.proof.proof_value)
        except Exception:  # noqa: BLE001
            reason = "signature_malformed"
            return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))

        # Get canonical payload based on mandate type and canonicalization mode
        if use_jcs:
            if isinstance(mandate, PaymentMandate):
                payload = self._jcs_payment_payload(mandate)
            elif isinstance(mandate, CartMandate):
                payload = self._jcs_cart_payload(mandate)
            elif isinstance(mandate, IntentMandate):
                payload = self._jcs_intent_payload(mandate)
            else:
                reason = "unknown_mandate_type"
                return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))
        else:
            if isinstance(mandate, PaymentMandate):
                payload = self._canonical_payment_payload(mandate)
            elif isinstance(mandate, CartMandate):
                payload = self._canonical_cart_payload(mandate)
            elif isinstance(mandate, IntentMandate):
                payload = self._canonical_intent_payload(mandate)
            else:
                reason = "unknown_mandate_type"
                return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))

        if not agent.verify(payload, signature=signature, domain=mandate.domain, nonce=mandate.nonce, purpose=mandate.purpose):
            reason = "signature_invalid"
            return VerificationResult(False, reason, reason_code=map_legacy_reason_to_code(reason))
        return VerificationResult(True, reason_code=None)

    def verify_chain(self, bundle: AP2PaymentExecuteRequest, *, canonicalization_mode: str = "pipe") -> MandateChainVerification:
        try:
            intent = self._parse_mandate(bundle.intent, IntentMandate)
            cart = self._parse_mandate(bundle.cart, CartMandate)
            payment = self._parse_mandate(bundle.payment, PaymentMandate)
        except (KeyError, TypeError, ValueError) as exc:
            reason = f"invalid_payload: {exc}"
            return MandateChainVerification(False, reason, reason_code=map_legacy_reason_to_code(str(exc)))

        # Check if any mandate uses SD-JWT
        sd_jwt_detected = (
            self._detect_sd_jwt(bundle.intent)
            or self._detect_sd_jwt(bundle.cart)
            or self._detect_sd_jwt(bundle.payment)
        )

        # Check agent rate limits
        agent_id = payment.subject
        rate_result = self._rate_limiter.check_and_increment(agent_id)
        if not rate_result.allowed:
            reason = rate_result.reason
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        if intent.mandate_type != "intent" or intent.purpose != "intent":
            reason = "intent_invalid_type"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        if cart.mandate_type != "cart" or cart.purpose != "cart":
            reason = "cart_invalid_type"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        if payment.mandate_type != "payment" or payment.purpose != "checkout":
            reason = "payment_invalid_type"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        if payment.ai_agent_presence is not True:
            reason = "payment_agent_presence_required"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        if payment.transaction_modality not in {"human_present", "human_not_present"}:
            reason = "payment_invalid_modality"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        for mandate in (intent, cart, payment):
            if mandate.is_expired():
                reason = "mandate_expired"
                return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        if len({intent.subject, cart.subject, payment.subject}) != 1:
            reason = "subject_mismatch"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        if not payment.merchant_domain:
            reason = "payment_missing_merchant_domain"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        if cart.merchant_domain != payment.merchant_domain:
            reason = "merchant_domain_mismatch"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        # Validate payment amount does not exceed cart total
        cart_total = cart.subtotal_minor + cart.taxes_minor
        if payment.amount_minor > cart_total:
            reason = "payment_exceeds_cart_total"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        # Validate intent amount bounds if specified
        if intent.requested_amount is not None and payment.amount_minor > intent.requested_amount:
            reason = "payment_exceeds_intent_amount"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        # Verify signatures for all mandates in the chain with specified canonicalization mode
        use_jcs = (canonicalization_mode == "jcs")
        intent_result = self.verify(intent, use_jcs=use_jcs)
        if not intent_result.accepted:
            reason = f"intent_{intent_result.reason}"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        cart_result = self.verify(cart, use_jcs=use_jcs)
        if not cart_result.accepted:
            reason = f"cart_{cart_result.reason}"
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))

        payment_result = self.verify(payment, use_jcs=use_jcs)
        if not payment_result.accepted:
            reason = payment_result.reason
            return MandateChainVerification(False, reason, sd_jwt_detected=sd_jwt_detected, reason_code=map_legacy_reason_to_code(reason))
        chain = MandateChain(intent=intent, cart=cart, payment=payment)
        if self._archive:
            self._archive.store(chain)
        return MandateChainVerification(True, chain=chain, sd_jwt_detected=sd_jwt_detected, reason_code=None)

    def _parse_mandate(self, data: Dict[str, Any], model: Type[MandateBase]) -> MandateBase:
        proof_payload = data.get("proof")
        if not isinstance(proof_payload, dict):
            raise ValueError("mandate_missing_proof")

        # Check for SD-JWT indicators (awareness only, does not fail)
        if self._detect_sd_jwt(data):
            logger.info(f"SD-JWT detected in {model.__name__} mandate")

        proof = VCProof(**proof_payload)
        init_values: Dict[str, Any] = {}
        for field in fields(model):
            if field.name == "proof":
                continue
            if field.name in data:
                init_values[field.name] = data[field.name]
                continue
            if field.default is not MISSING:
                init_values[field.name] = field.default
                continue
            if field.default_factory is not MISSING:  # type: ignore[comparison-overlap]
                init_values[field.name] = field.default_factory()  # type: ignore[misc]
                continue
            raise ValueError(f"mandate_missing_field:{field.name}")
        return model(proof=proof, **init_values)

    def _identity_from_proof(self, mandate: IntentMandate | CartMandate | PaymentMandate) -> AgentIdentity | None:
        method = mandate.proof.verification_method
        try:
            algorithm, public_key = IdentityRegistry.parse_verification_method(method)
        except ValueError:
            return None

        if self._identity_registry:
            if not self._identity_registry.verify_binding(
                agent_id=mandate.subject,
                domain=mandate.domain,
                public_key=public_key,
                algorithm=algorithm,
            ):
                return None
        else:
            # Fail-closed in production: identity registry must be configured.
            # Support both legacy SARDIS_ENV and canonical SARDIS_ENVIRONMENT names.
            raw_env = (os.getenv("SARDIS_ENVIRONMENT") or os.getenv("SARDIS_ENV") or "dev").strip().lower()
            is_production = raw_env in {"prod", "production"}
            if is_production:
                raise VerificationError("Identity registry required in production")
            logger.warning("Identity registry not configured - skipping identity binding verification (dev mode)")

        return AgentIdentity(
            agent_id=mandate.subject,
            public_key=public_key,
            domain=mandate.domain,
            algorithm=algorithm,
        )

    @staticmethod
    def _canonical_intent_payload(mandate: IntentMandate) -> bytes:
        """Create canonical payload for Intent mandate signature verification."""
        fields = [
            mandate.mandate_id,
            mandate.subject,
            mandate.mandate_type,
            ",".join(sorted(mandate.scope)) if mandate.scope else "",
            str(mandate.requested_amount) if mandate.requested_amount is not None else "",
            str(mandate.expires_at),
        ]
        return "|".join(fields).encode()

    @staticmethod
    def _canonical_cart_payload(mandate: CartMandate) -> bytes:
        """Create canonical payload for Cart mandate signature verification."""
        # Sort line items by a stable key to ensure consistent ordering
        sorted_items = sorted(mandate.line_items, key=lambda x: (x.get("item_id", ""), x.get("name", "")))
        items_str = ",".join(
            f"{item.get('item_id', '')}:{item.get('name', '')}:{item.get('quantity', 0)}:{item.get('price_minor', 0)}"
            for item in sorted_items
        )
        fields = [
            mandate.mandate_id,
            mandate.subject,
            items_str,
            str(mandate.subtotal_minor),
            str(mandate.taxes_minor),
            mandate.currency,
            mandate.merchant_domain,
            str(mandate.expires_at),
        ]
        return "|".join(fields).encode()

    @staticmethod
    def _canonical_payment_payload(mandate: PaymentMandate) -> bytes:
        """Create canonical payload for Payment mandate signature verification."""
        fields = [
            mandate.mandate_id,
            mandate.subject,
            str(mandate.amount_minor),
            mandate.token,
            mandate.chain,
            mandate.destination,
            mandate.merchant_domain or "",
            mandate.audit_hash,
            "1" if mandate.ai_agent_presence else "0",
            mandate.transaction_modality,
        ]
        return "|".join(fields).encode()

    @staticmethod
    def _jcs_intent_payload(mandate: IntentMandate) -> bytes:
        """Create JCS canonical payload for Intent mandate signature verification."""
        mandate_dict = {
            "mandate_id": mandate.mandate_id,
            "subject": mandate.subject,
            "mandate_type": mandate.mandate_type,
            "scope": sorted(mandate.scope) if mandate.scope else [],
            "requested_amount": mandate.requested_amount,
            "expires_at": mandate.expires_at,
        }
        return MandateVerifier._jcs_canonicalize(mandate_dict)

    @staticmethod
    def _jcs_cart_payload(mandate: CartMandate) -> bytes:
        """Create JCS canonical payload for Cart mandate signature verification."""
        # Sort line items by a stable key to ensure consistent ordering
        sorted_items = sorted(mandate.line_items, key=lambda x: (x.get("item_id", ""), x.get("name", "")))
        mandate_dict = {
            "mandate_id": mandate.mandate_id,
            "subject": mandate.subject,
            "line_items": sorted_items,
            "subtotal_minor": mandate.subtotal_minor,
            "taxes_minor": mandate.taxes_minor,
            "currency": mandate.currency,
            "merchant_domain": mandate.merchant_domain,
            "expires_at": mandate.expires_at,
        }
        return MandateVerifier._jcs_canonicalize(mandate_dict)

    @staticmethod
    def _jcs_payment_payload(mandate: PaymentMandate) -> bytes:
        """Create JCS canonical payload for Payment mandate signature verification."""
        mandate_dict = {
            "mandate_id": mandate.mandate_id,
            "subject": mandate.subject,
            "amount_minor": mandate.amount_minor,
            "token": mandate.token,
            "chain": mandate.chain,
            "destination": mandate.destination,
            "merchant_domain": mandate.merchant_domain or "",
            "audit_hash": mandate.audit_hash,
            "ai_agent_presence": mandate.ai_agent_presence,
            "transaction_modality": mandate.transaction_modality,
        }
        return MandateVerifier._jcs_canonicalize(mandate_dict)
