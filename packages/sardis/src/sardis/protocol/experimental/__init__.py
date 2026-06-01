"""Research / experimental protocol adapters — NOT production.

The modules in this package are quarantined per the protocol audit
(``docs/productization/research/PROTOCOL_STRATEGY.md``): in-memory
simulations, draft-EIP sketches with unverified crypto, or unwired schemes
with no production caller. They make NO conformance claims and must not be
depended on from ``core/``, ``routes/``, or ``middleware/``. See README.md.
"""

import contextlib

# ERC-8001: Agent Coordination (experimental — fake crypto, signatures unverified)
with contextlib.suppress(ImportError):
    from .erc8001 import (
        AcceptanceAttestation,
        AgentCoordinationManager,
        AgentIntent,
        BoundedPolicy,
        CoordinationPayload,
        CoordinationStatus,
        CoordinationType,
        create_coordination_manager,
    )
    from .erc8001 import (
        ExecutionResult as CoordinationExecutionResult,
    )

# Kleros dispute resolution (experimental — in-memory, no on-chain interaction)
with contextlib.suppress(ImportError):
    from .kleros import (
        ArbitrationCostEstimate,
        CourtCategory,
        DisputeParty,
        DisputePartyRole,
        DisputeRulingResult,
        DisputeStatus,
        EvidenceType,
        KlerosDisputeResolver,
        Ruling,
        build_appeal_calldata,
        build_create_dispute_calldata,
        build_rule_calldata,
        build_submit_evidence_calldata,
        create_dispute_resolver,
    )
    from .kleros import (
        Dispute as KlerosDispute,
    )
    from .kleros import (
        Evidence as KlerosEvidence,
    )

# Paladin Privacy (experimental — not an ERC; "privacy" is a Python dict)
with contextlib.suppress(ImportError):
    from .paladin_privacy import (
        UTXO,
        NotaryDecision,
        NotaryValidation,
        PaladinPrivacyManager,
        PrivacyConfig,
        PrivacyDomain,
        PrivacyGroup,
        PrivacyLevel,
        PrivateTransfer,
        UTXOState,
        create_privacy_manager,
    )

# zkPass Transgate (experimental — fail-closed stub, verify_proof not implemented)
with contextlib.suppress(ImportError):
    from .zkpass_transgate import (
        PortableKYCResult,
        ProofStatus,
        TransgateConfig,
        TransgateIssuer,
        TransgateProofType,
        TransgateSchema,
        VerificationMethod,
        ZKPassVerifier,
        ZKProof,
        create_zkpass_verifier,
        hash_public_inputs,
    )
    from .zkpass_transgate import (
        VerificationResult as ZKPassVerificationResult,
    )

# x402 upto / streaming (experimental — no production caller, finalize() settles nothing)
with contextlib.suppress(ImportError):
    from .x402_upto import (
        UptoSession,
        build_permit2_typed_data,
    )

__all__ = [
    # ERC-8001
    "AgentCoordinationManager",
    "AgentIntent",
    "AcceptanceAttestation",
    "CoordinationPayload",
    "CoordinationStatus",
    "CoordinationType",
    "CoordinationExecutionResult",
    "BoundedPolicy",
    "create_coordination_manager",
    # Kleros
    "KlerosDisputeResolver",
    "KlerosDispute",
    "KlerosEvidence",
    "DisputeStatus",
    "DisputeParty",
    "DisputePartyRole",
    "DisputeRulingResult",
    "Ruling",
    "EvidenceType",
    "CourtCategory",
    "ArbitrationCostEstimate",
    "build_create_dispute_calldata",
    "build_submit_evidence_calldata",
    "build_appeal_calldata",
    "build_rule_calldata",
    "create_dispute_resolver",
    # Paladin Privacy
    "PaladinPrivacyManager",
    "PrivacyDomain",
    "PrivacyLevel",
    "PrivacyGroup",
    "PrivateTransfer",
    "UTXO",
    "UTXOState",
    "NotaryDecision",
    "NotaryValidation",
    "PrivacyConfig",
    "create_privacy_manager",
    # zkPass Transgate
    "ZKPassVerifier",
    "TransgateProofType",
    "TransgateIssuer",
    "TransgateSchema",
    "ZKProof",
    "ProofStatus",
    "VerificationMethod",
    "ZKPassVerificationResult",
    "PortableKYCResult",
    "TransgateConfig",
    "create_zkpass_verifier",
    "hash_public_inputs",
    # x402 upto (streaming)
    "UptoSession",
    "build_permit2_typed_data",
]
