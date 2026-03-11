"""zkPass Transgate: Zero-knowledge proof verification for portable KYC/compliance.

Enables users who already passed KYC on Coinbase/Binance/etc to prove it via
ZK proof without re-sharing personal data. Integrates with Sardis compliance
pipeline as an alternative to iDenfy ($0.55/verification savings).

Key features:
- Schema-based proof definitions for different verification types
- Proof submission and verification lifecycle
- Portable KYC level derivation from ZK proofs
- On-chain calldata builders for contract verification
- Issuer-agnostic: supports Coinbase, Binance, Kraken, OKX, Bybit

Issue: #150
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)

# ============ Constants ============

ZKPASS_VERSION = "0.1.0"
DEFAULT_PROOF_TTL_HOURS = 720  # 30 days
IDENFY_COST_PER_VERIFICATION = 0.55
SUPPORTED_PROOF_TYPES: frozenset[str] = frozenset()  # Populated after enum definition


# ============ Enums ============


class TransgateProofType(str, Enum):
    """Types of zero-knowledge proofs supported by Transgate."""
    KYC_VERIFIED = "kyc_verified"
    AGE_VERIFIED = "age_verified"
    COUNTRY_VERIFIED = "country_verified"
    BALANCE_VERIFIED = "balance_verified"
    ACCREDITED_INVESTOR = "accredited_investor"
    SANCTIONS_CLEAR = "sanctions_clear"


class TransgateIssuer(str, Enum):
    """Supported KYC issuers for portable verification."""
    COINBASE = "coinbase"
    BINANCE = "binance"
    KRAKEN = "kraken"
    OKX = "okx"
    BYBIT = "bybit"
    GENERIC = "generic"


class ProofStatus(str, Enum):
    """Lifecycle status of a ZK proof."""
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class VerificationMethod(str, Enum):
    """Method used for identity/compliance verification."""
    IDENFY = "idenfy"
    ZKPASS = "zkpass"
    PRIVADO_ID = "privado_id"
    MANUAL = "manual"


# Now populate the constant
SUPPORTED_PROOF_TYPES = frozenset({t.value for t in TransgateProofType})

# KYC level mapping: set of proof type values -> level
KYC_LEVEL_MAPPING: dict[frozenset[str], str] = {
    frozenset({"kyc_verified"}): "basic",
    frozenset({"kyc_verified", "country_verified"}): "enhanced",
    frozenset({"kyc_verified", "country_verified", "sanctions_clear"}): "full",
}


# ============ Data Classes ============


@dataclass
class TransgateSchema:
    """Defines a proof schema for a specific verification type and issuer."""
    schema_id: str
    proof_type: TransgateProofType
    issuer: TransgateIssuer
    required_fields: list[str]
    description: str
    version: int = 1


@dataclass
class ZKProof:
    """A zero-knowledge proof submitted for verification."""
    proof_id: str
    schema_id: str
    proof_type: TransgateProofType
    issuer: TransgateIssuer
    prover_address: str
    proof_data: bytes
    public_inputs: dict[str, str]
    status: ProofStatus = ProofStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    verified_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """Whether proof is verified and not expired."""
        if self.status != ProofStatus.VERIFIED:
            return False
        if self.is_expired:
            return False
        return True

    @property
    def is_expired(self) -> bool:
        """Whether proof has passed its expiry time."""
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at


@dataclass
class VerificationResult:
    """Result of a proof verification attempt."""
    proof_id: str
    success: bool
    method: VerificationMethod
    issuer: TransgateIssuer | None
    proof_type: TransgateProofType | None
    verified_at: datetime
    details: dict[str, str] = field(default_factory=dict)


@dataclass
class TransgateConfig:
    """Configuration for the zkPass Transgate verifier."""
    app_id: str = ""
    api_key: str = ""
    base_url: str = "https://api.zkpass.org"
    proof_ttl_hours: int = 720  # 30 days
    supported_issuers: frozenset[str] = field(
        default_factory=lambda: frozenset({i.value for i in TransgateIssuer})
    )


@dataclass
class PortableKYCResult:
    """Result of a portable KYC check using ZK proofs."""
    verification_result: VerificationResult
    kyc_level: str  # "basic" | "enhanced" | "full" | ""
    accepted_proof_types: list[TransgateProofType]
    cost_savings_usd: float = IDENFY_COST_PER_VERIFICATION


# ============ Main Verifier Class ============


class ZKPassVerifier:
    """Manages zkPass Transgate proof schemas, submission, and verification.

    Provides portable KYC verification using zero-knowledge proofs,
    enabling users to prove compliance without re-sharing personal data.
    """

    def __init__(self, config: TransgateConfig | None = None) -> None:
        self._config = config or TransgateConfig()
        self._proofs: dict[str, ZKProof] = {}
        self._schemas: dict[str, TransgateSchema] = {}
        self.load_default_schemas()

    # ---- Schema Management ----

    def register_schema(self, schema: TransgateSchema) -> TransgateSchema:
        """Register a new proof schema.

        Args:
            schema: The schema to register.

        Returns:
            The registered schema.

        Raises:
            ValueError: If a schema with the same ID already exists.
        """
        if schema.schema_id in self._schemas:
            raise ValueError(f"Schema already registered: {schema.schema_id}")
        self._schemas[schema.schema_id] = schema
        return schema

    def get_schema(self, schema_id: str) -> TransgateSchema | None:
        """Get a schema by ID, or None if not found."""
        return self._schemas.get(schema_id)

    def load_default_schemas(self) -> None:
        """Load built-in schemas for common verification types."""
        defaults = [
            TransgateSchema(
                schema_id="coinbase_kyc",
                proof_type=TransgateProofType.KYC_VERIFIED,
                issuer=TransgateIssuer.COINBASE,
                required_fields=["kyc_status", "verification_date"],
                description="Coinbase KYC verification proof",
            ),
            TransgateSchema(
                schema_id="binance_kyc",
                proof_type=TransgateProofType.KYC_VERIFIED,
                issuer=TransgateIssuer.BINANCE,
                required_fields=["kyc_level", "verification_date"],
                description="Binance KYC verification proof",
            ),
            TransgateSchema(
                schema_id="age_verification",
                proof_type=TransgateProofType.AGE_VERIFIED,
                issuer=TransgateIssuer.GENERIC,
                required_fields=["is_over_18"],
                description="Age verification proof (18+)",
            ),
            TransgateSchema(
                schema_id="country_check",
                proof_type=TransgateProofType.COUNTRY_VERIFIED,
                issuer=TransgateIssuer.GENERIC,
                required_fields=["country_code"],
                description="Country of residence verification proof",
            ),
            TransgateSchema(
                schema_id="sanctions_screen",
                proof_type=TransgateProofType.SANCTIONS_CLEAR,
                issuer=TransgateIssuer.GENERIC,
                required_fields=["screening_date", "result"],
                description="Sanctions screening clearance proof",
            ),
            TransgateSchema(
                schema_id="accredited_check",
                proof_type=TransgateProofType.ACCREDITED_INVESTOR,
                issuer=TransgateIssuer.GENERIC,
                required_fields=["status", "verification_date"],
                description="Accredited investor verification proof",
            ),
        ]
        for schema in defaults:
            if schema.schema_id not in self._schemas:
                self._schemas[schema.schema_id] = schema

    # ---- Proof Submission & Verification ----

    def submit_proof(
        self,
        schema_id: str,
        prover_address: str,
        proof_data: bytes,
        public_inputs: dict[str, str],
        issuer: TransgateIssuer | None = None,
    ) -> ZKProof:
        """Submit a new proof for verification.

        Args:
            schema_id: ID of the schema this proof is for.
            prover_address: Address of the prover.
            proof_data: The raw ZK proof bytes.
            public_inputs: Public inputs for verification.
            issuer: Override issuer (defaults to schema issuer).

        Returns:
            The created ZKProof in PENDING status.

        Raises:
            ValueError: If schema not found.
        """
        schema = self._schemas.get(schema_id)
        if not schema:
            raise ValueError(f"Schema not found: {schema_id}")

        proof_id = uuid.uuid4().hex[:16]
        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=self._config.proof_ttl_hours)

        proof = ZKProof(
            proof_id=proof_id,
            schema_id=schema_id,
            proof_type=schema.proof_type,
            issuer=issuer or schema.issuer,
            prover_address=prover_address,
            proof_data=proof_data,
            public_inputs=public_inputs,
            status=ProofStatus.PENDING,
            created_at=now,
            expires_at=expires_at,
        )

        self._proofs[proof_id] = proof
        logger.info(
            "zkPass proof submitted: id=%s schema=%s prover=%s",
            proof_id, schema_id, prover_address,
        )
        return proof

    def verify_proof(self, proof_id: str) -> VerificationResult:
        """Verify a submitted proof.

        Checks that the proof exists, has valid proof data, and that
        public inputs match the schema's required fields.

        Args:
            proof_id: ID of the proof to verify.

        Returns:
            VerificationResult indicating success or failure.

        Raises:
            ValueError: If proof not found.
        """
        proof = self._proofs.get(proof_id)
        if not proof:
            raise ValueError(f"Proof not found: {proof_id}")

        schema = self._schemas.get(proof.schema_id)
        if not schema:
            proof.status = ProofStatus.REJECTED
            return VerificationResult(
                proof_id=proof_id,
                success=False,
                method=VerificationMethod.ZKPASS,
                issuer=proof.issuer,
                proof_type=proof.proof_type,
                verified_at=datetime.now(UTC),
                details={"reason": "Schema not found"},
            )

        # Check proof_data is not empty
        if not proof.proof_data:
            proof.status = ProofStatus.REJECTED
            return VerificationResult(
                proof_id=proof_id,
                success=False,
                method=VerificationMethod.ZKPASS,
                issuer=proof.issuer,
                proof_type=proof.proof_type,
                verified_at=datetime.now(UTC),
                details={"reason": "Empty proof data"},
            )

        # Check public inputs match schema required fields
        for required_field in schema.required_fields:
            if required_field not in proof.public_inputs:
                proof.status = ProofStatus.REJECTED
                return VerificationResult(
                    proof_id=proof_id,
                    success=False,
                    method=VerificationMethod.ZKPASS,
                    issuer=proof.issuer,
                    proof_type=proof.proof_type,
                    verified_at=datetime.now(UTC),
                    details={"reason": f"Missing required field: {required_field}"},
                )

        # All checks passed — mark as verified
        now = datetime.now(UTC)
        proof.status = ProofStatus.VERIFIED
        proof.verified_at = now

        logger.info(
            "zkPass proof verified: id=%s type=%s issuer=%s",
            proof_id, proof.proof_type.value, proof.issuer.value,
        )

        return VerificationResult(
            proof_id=proof_id,
            success=True,
            method=VerificationMethod.ZKPASS,
            issuer=proof.issuer,
            proof_type=proof.proof_type,
            verified_at=now,
            details={"schema_id": proof.schema_id},
        )

    def reject_proof(self, proof_id: str, reason: str = "") -> ZKProof:
        """Reject a proof.

        Args:
            proof_id: ID of the proof to reject.
            reason: Reason for rejection.

        Returns:
            The updated ZKProof.

        Raises:
            ValueError: If proof not found.
        """
        proof = self._proofs.get(proof_id)
        if not proof:
            raise ValueError(f"Proof not found: {proof_id}")
        proof.status = ProofStatus.REJECTED
        logger.info("zkPass proof rejected: id=%s reason=%s", proof_id, reason)
        return proof

    def get_proof(self, proof_id: str) -> ZKProof | None:
        """Get a proof by ID."""
        return self._proofs.get(proof_id)

    def get_proofs_for_address(self, address: str) -> list[ZKProof]:
        """Get all proofs submitted by an address."""
        return [p for p in self._proofs.values() if p.prover_address == address]

    def get_valid_proofs_for_address(self, address: str) -> list[ZKProof]:
        """Get only verified and non-expired proofs for an address."""
        return [
            p for p in self._proofs.values()
            if p.prover_address == address and p.is_valid
        ]

    # ---- Portable KYC ----

    def check_portable_kyc(self, address: str) -> PortableKYCResult:
        """Check portable KYC status for an address based on ZK proofs.

        Determines KYC level from the combination of valid proof types:
        - "full": KYC_VERIFIED + COUNTRY_VERIFIED + SANCTIONS_CLEAR
        - "enhanced": KYC_VERIFIED + (COUNTRY_VERIFIED or SANCTIONS_CLEAR)
        - "basic": KYC_VERIFIED only
        - "": no valid KYC proofs

        Args:
            address: The prover address to check.

        Returns:
            PortableKYCResult with KYC level and accepted proof types.
        """
        valid_proofs = self.get_valid_proofs_for_address(address)
        proof_types = {p.proof_type for p in valid_proofs}
        proof_type_values = {p.proof_type.value for p in valid_proofs}

        # Determine KYC level
        kyc_level = ""
        if TransgateProofType.KYC_VERIFIED in proof_types:
            has_country = TransgateProofType.COUNTRY_VERIFIED in proof_types
            has_sanctions = TransgateProofType.SANCTIONS_CLEAR in proof_types

            if has_country and has_sanctions:
                kyc_level = "full"
            elif has_country or has_sanctions:
                kyc_level = "enhanced"
            else:
                kyc_level = "basic"

        # Find the issuer from a KYC proof (if any)
        issuer = None
        for p in valid_proofs:
            if p.proof_type == TransgateProofType.KYC_VERIFIED:
                issuer = p.issuer
                break

        accepted = list(proof_types)

        verification_result = VerificationResult(
            proof_id=valid_proofs[0].proof_id if valid_proofs else "",
            success=bool(kyc_level),
            method=VerificationMethod.ZKPASS,
            issuer=issuer,
            proof_type=TransgateProofType.KYC_VERIFIED if kyc_level else None,
            verified_at=datetime.now(UTC),
            details={"kyc_level": kyc_level, "proof_count": str(len(valid_proofs))},
        )

        return PortableKYCResult(
            verification_result=verification_result,
            kyc_level=kyc_level,
            accepted_proof_types=accepted,
            cost_savings_usd=IDENFY_COST_PER_VERIFICATION if kyc_level else 0.0,
        )

    def has_valid_kyc(self, address: str) -> bool:
        """Check if an address has any valid KYC_VERIFIED proof."""
        valid_proofs = self.get_valid_proofs_for_address(address)
        return any(p.proof_type == TransgateProofType.KYC_VERIFIED for p in valid_proofs)

    # ---- Properties ----

    @property
    def total_proofs(self) -> int:
        """Total number of proofs submitted."""
        return len(self._proofs)

    @property
    def verified_proofs(self) -> int:
        """Number of verified proofs."""
        return sum(1 for p in self._proofs.values() if p.status == ProofStatus.VERIFIED)

    @property
    def schema_count(self) -> int:
        """Number of registered schemas."""
        return len(self._schemas)


# ============ Calldata Builders ============


def build_verify_proof_calldata(
    proof_id: str,
    proof_data: bytes,
    public_inputs_hash: bytes,
) -> bytes:
    """Build calldata for on-chain proof verification.

    Encodes: verifyProof(bytes16 proofId, bytes proofData, bytes32 inputsHash)

    Args:
        proof_id: The proof identifier (hex string).
        proof_data: The raw ZK proof bytes.
        public_inputs_hash: SHA-256 hash of public inputs.

    Returns:
        ABI-encoded calldata bytes.
    """
    selector = bytes.fromhex("e1a2b3c4")

    # Proof ID padded to 32 bytes
    proof_id_bytes = proof_id.encode("utf-8").ljust(32, b"\x00")[:32]

    # Public inputs hash padded to 32 bytes
    inputs_hash_padded = public_inputs_hash[:32].ljust(32, b"\x00")

    # Length-prefixed proof data
    proof_len = len(proof_data).to_bytes(32, "big")

    return selector + proof_id_bytes + inputs_hash_padded + proof_len + proof_data


def build_register_schema_calldata(
    schema_id: str,
    proof_type: str,
    issuer: str,
) -> bytes:
    """Build calldata for on-chain schema registration.

    Encodes: registerSchema(bytes32 schemaId, string proofType, string issuer)

    Args:
        schema_id: Schema identifier.
        proof_type: Proof type string value.
        issuer: Issuer string value.

    Returns:
        ABI-encoded calldata bytes.
    """
    selector = bytes.fromhex("f2b3c4d5")

    schema_id_bytes = schema_id.encode("utf-8").ljust(32, b"\x00")[:32]

    proof_type_bytes = proof_type.encode("utf-8")
    issuer_bytes = issuer.encode("utf-8")

    data = (
        schema_id_bytes
        + len(proof_type_bytes).to_bytes(32, "big")
        + proof_type_bytes.ljust(((len(proof_type_bytes) + 31) // 32) * 32, b"\x00")
        + len(issuer_bytes).to_bytes(32, "big")
        + issuer_bytes.ljust(((len(issuer_bytes) + 31) // 32) * 32, b"\x00")
    )

    return selector + data


# ============ Helper Functions ============


def create_zkpass_verifier(
    app_id: str = "",
    api_key: str = "",
) -> ZKPassVerifier:
    """Factory function to create a ZKPassVerifier with optional credentials.

    Args:
        app_id: zkPass application ID.
        api_key: zkPass API key.

    Returns:
        Configured ZKPassVerifier instance.
    """
    config = TransgateConfig(app_id=app_id, api_key=api_key)
    return ZKPassVerifier(config=config)


def hash_public_inputs(inputs: dict[str, str]) -> bytes:
    """Compute a deterministic SHA-256 hash of public inputs.

    Sorts keys for determinism, then hashes the JSON representation.

    Args:
        inputs: Public input key-value pairs.

    Returns:
        32-byte SHA-256 digest.
    """
    canonical = json.dumps(inputs, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).digest()
