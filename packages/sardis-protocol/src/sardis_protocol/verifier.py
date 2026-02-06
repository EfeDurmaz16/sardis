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

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    """Raised when verification requirements are not met."""
    pass


@dataclass
class VerificationResult:
    accepted: bool
    reason: str | None = None


@dataclass
class MandateChainVerification:
    accepted: bool
    reason: str | None = None
    chain: MandateChain | None = None


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

    def verify(self, mandate: IntentMandate | CartMandate | PaymentMandate) -> VerificationResult:
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

        # Get canonical payload based on mandate type
        if isinstance(mandate, PaymentMandate):
            payload = self._canonical_payment_payload(mandate)
        elif isinstance(mandate, CartMandate):
            payload = self._canonical_cart_payload(mandate)
        elif isinstance(mandate, IntentMandate):
            payload = self._canonical_intent_payload(mandate)
        else:
            return VerificationResult(False, "unknown_mandate_type")

        if not agent.verify(payload, signature=signature, domain=mandate.domain, nonce=mandate.nonce, purpose=mandate.purpose):
            return VerificationResult(False, "signature_invalid")
        return VerificationResult(True)

    def verify_chain(self, bundle: AP2PaymentExecuteRequest) -> MandateChainVerification:
        try:
            intent = self._parse_mandate(bundle.intent, IntentMandate)
            cart = self._parse_mandate(bundle.cart, CartMandate)
            payment = self._parse_mandate(bundle.payment, PaymentMandate)
        except (KeyError, TypeError, ValueError) as exc:
            return MandateChainVerification(False, f"invalid_payload: {exc}")
        
        # Check agent rate limits
        agent_id = payment.subject
        rate_result = self._rate_limiter.check_and_increment(agent_id)
        if not rate_result.allowed:
            return MandateChainVerification(False, rate_result.reason)

        if intent.mandate_type != "intent" or intent.purpose != "intent":
            return MandateChainVerification(False, "intent_invalid_type")
        if cart.mandate_type != "cart" or cart.purpose != "cart":
            return MandateChainVerification(False, "cart_invalid_type")
        if payment.mandate_type != "payment" or payment.purpose != "checkout":
            return MandateChainVerification(False, "payment_invalid_type")
        if payment.ai_agent_presence is not True:
            return MandateChainVerification(False, "payment_agent_presence_required")
        if payment.transaction_modality not in {"human_present", "human_not_present"}:
            return MandateChainVerification(False, "payment_invalid_modality")

        for mandate in (intent, cart, payment):
            if mandate.is_expired():
                return MandateChainVerification(False, "mandate_expired")

        if len({intent.subject, cart.subject, payment.subject}) != 1:
            return MandateChainVerification(False, "subject_mismatch")
        if not payment.merchant_domain:
            return MandateChainVerification(False, "payment_missing_merchant_domain")
        if cart.merchant_domain != payment.merchant_domain:
            return MandateChainVerification(False, "merchant_domain_mismatch")

        # Validate payment amount does not exceed cart total
        cart_total = cart.subtotal_minor + cart.taxes_minor
        if payment.amount_minor > cart_total:
            return MandateChainVerification(False, "payment_exceeds_cart_total")
        
        # Validate intent amount bounds if specified
        if intent.requested_amount is not None and payment.amount_minor > intent.requested_amount:
            return MandateChainVerification(False, "payment_exceeds_intent_amount")

        # Verify signatures for all mandates in the chain
        intent_result = self.verify(intent)
        if not intent_result.accepted:
            return MandateChainVerification(False, f"intent_{intent_result.reason}")

        cart_result = self.verify(cart)
        if not cart_result.accepted:
            return MandateChainVerification(False, f"cart_{cart_result.reason}")

        payment_result = self.verify(payment)
        if not payment_result.accepted:
            return MandateChainVerification(False, payment_result.reason)
        chain = MandateChain(intent=intent, cart=cart, payment=payment)
        if self._archive:
            self._archive.store(chain)
        return MandateChainVerification(True, chain=chain)

    def _parse_mandate(self, data: Dict[str, Any], model: Type[MandateBase]) -> MandateBase:
        proof_payload = data.get("proof")
        if not isinstance(proof_payload, dict):
            raise ValueError("mandate_missing_proof")
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
