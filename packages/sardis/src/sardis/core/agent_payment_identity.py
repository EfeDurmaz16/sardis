"""Canonical agent payment identity models shared across rails and APIs."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class SpendAuthorityTier(str, Enum):
    NONE = "none"
    BASIC = "basic"
    VERIFIED = "verified"
    ATTESTED = "attested"
    RUNTIME_ATTESTED = "runtime_attested"
    INSTITUTION_TRUSTED = "institution_trusted"


class IdentityAttestation(BaseModel):
    kind: str
    reference: str
    issuer: str | None = None
    status: str = "active"


class ProvenanceAttestation(BaseModel):
    repo_hash: str | None = None
    commit_hash: str | None = None
    signer_did: str | None = None
    chain_verified: bool | None = None
    source: str | None = None


class CounterpartyTrustProfile(BaseModel):
    did: str | None = None
    overall_score: float | None = None
    trust_tier: str | None = None


class EvidencePack(BaseModel):
    policy_ref: str
    reason_codes: list[str] = Field(default_factory=list)
    attestation_refs: list[str] = Field(default_factory=list)
    trust_score: float | None = None
    signature_scheme: str = "hmac-sha256"


class AgentPaymentIdentity(BaseModel):
    agent_id: str
    organization_id: str
    wallet_id: str | None = None
    payment_identity_id: str | None = None
    did: str
    fides_did: str | None = None
    spend_authority_tier: SpendAuthorityTier
    kya_level: str
    kya_status: str
    policy_ref: str
    mode: str = "live"
    chain: str
    trust_score: float | None = None
    trust_tier: str | None = None
    identity_attestations: list[IdentityAttestation] = Field(default_factory=list)
    provenance: ProvenanceAttestation | None = None
    issued_at: str | None = None
    expires_at: str | None = None


class AgentPaymentEnvelope(BaseModel):
    payment_identity_id: str
    agent_payment_identity: AgentPaymentIdentity
    evidence: EvidencePack


def spend_authority_tier_for_agent(
    kya_level: str,
    *,
    has_runtime_provenance: bool = False,
    institution_trusted: bool = False,
) -> SpendAuthorityTier:
    normalized = (kya_level or "none").strip().lower()
    if institution_trusted:
        return SpendAuthorityTier.INSTITUTION_TRUSTED
    if normalized == "attested":
        if has_runtime_provenance:
            return SpendAuthorityTier.RUNTIME_ATTESTED
        return SpendAuthorityTier.ATTESTED
    if normalized == "verified":
        return SpendAuthorityTier.VERIFIED
    if normalized == "basic":
        return SpendAuthorityTier.BASIC
    return SpendAuthorityTier.NONE


def trust_tier_from_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 0.9:
        return "sovereign"
    if score >= 0.7:
        return "high"
    if score >= 0.5:
        return "medium"
    if score >= 0.3:
        return "low"
    return "untrusted"
