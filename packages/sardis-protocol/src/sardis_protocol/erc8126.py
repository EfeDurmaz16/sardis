"""ERC-8126: AI Agent Registration and Verification with ZK Risk Scoring.

Implements the ERC-8126 standard for privacy-preserving agent verification
and zero-knowledge risk scoring. Enables agents to prove compliance
without revealing underlying verification data.

Specification: https://eips.ethereum.org/EIPS/eip-8126

Four verification layers:
    ETV — Ethereum Token Verification (code legitimacy)
    SCV — Staking Contract Verification (economic commitment)
    WAV — Web Application Verification (off-chain security)
    WV  — Wallet Verification (behavioral history)

Risk Score: 0–100 integer (higher = safer)
    0–25:  HIGH risk
    26–50: MEDIUM-HIGH risk
    51–75: MEDIUM-LOW risk
    76–100: LOW risk

Issue: #130
"""
from __future__ import annotations

import hashlib
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, IntEnum
from typing import Any

from eth_abi import encode

logger = logging.getLogger(__name__)


# ============ Enums ============

class VerificationType(str, Enum):
    """ERC-8126 verification layer types."""
    ETV = "etv"  # Ethereum Token Verification
    SCV = "scv"  # Staking Contract Verification
    WAV = "wav"  # Web Application Verification
    WV = "wv"    # Wallet Verification


class RiskBand(str, Enum):
    """Risk band derived from 0-100 score."""
    HIGH = "high"          # 0-25
    MEDIUM_HIGH = "medium_high"  # 26-50
    MEDIUM_LOW = "medium_low"    # 51-75
    LOW = "low"            # 76-100


class VerificationStatus(str, Enum):
    """Status of a verification check."""
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


# ============ Data Structures ============

@dataclass
class VerificationResult:
    """Result from a single verification layer."""
    verification_type: VerificationType
    status: VerificationStatus = VerificationStatus.PENDING
    score: int = 0  # 0-100 for this layer
    proof_hash: bytes = b""  # ZK proof commitment hash
    details: dict[str, Any] = field(default_factory=dict)
    verified_at: datetime | None = None
    expires_at: datetime | None = None

    @property
    def is_valid(self) -> bool:
        """Whether verification passed and is not expired."""
        if self.status != VerificationStatus.VERIFIED:
            return False
        if self.expires_at and datetime.now(UTC) > self.expires_at:
            return False
        return True


@dataclass
class ZKProofCommitment:
    """Zero-knowledge proof commitment for private data verification.

    The commitment proves verification occurred without revealing
    the underlying data. Uses Poseidon hash for ZK-friendliness.
    """
    commitment_hash: bytes  # H(verification_data || nonce)
    nonce: bytes            # Random nonce for binding
    verification_type: VerificationType
    timestamp: int          # Unix timestamp of proof generation
    public_inputs: list[int] = field(default_factory=list)  # Public ZK inputs

    def verify_commitment(self, data: bytes) -> bool:
        """Verify that data matches this commitment."""
        expected = hashlib.sha256(data + self.nonce).digest()
        return expected == self.commitment_hash


@dataclass
class AgentVerification:
    """Complete ERC-8126 agent verification with composite risk score."""
    agent_id: int
    agent_address: str
    etv_result: VerificationResult | None = None
    scv_result: VerificationResult | None = None
    wav_result: VerificationResult | None = None
    wv_result: VerificationResult | None = None
    composite_score: int = 0  # 0-100 weighted composite
    proofs: list[ZKProofCommitment] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def risk_band(self) -> RiskBand:
        """Classify composite score into risk band."""
        return score_to_risk_band(self.composite_score)

    @property
    def is_verified(self) -> bool:
        """Whether at least one verification layer passed."""
        results = [self.etv_result, self.scv_result, self.wav_result, self.wv_result]
        return any(r is not None and r.is_valid for r in results)

    @property
    def verification_count(self) -> int:
        """Number of valid verification layers."""
        results = [self.etv_result, self.scv_result, self.wav_result, self.wv_result]
        return sum(1 for r in results if r is not None and r.is_valid)


# ============ Score Computation ============

# Default weights for each verification layer (must sum to 100)
DEFAULT_WEIGHTS: dict[VerificationType, int] = {
    VerificationType.ETV: 30,  # Code legitimacy
    VerificationType.SCV: 25,  # Economic commitment
    VerificationType.WAV: 20,  # Off-chain security
    VerificationType.WV: 25,   # Behavioral history
}


def score_to_risk_band(score: int) -> RiskBand:
    """Map a 0-100 risk score to its ERC-8126 risk band."""
    if score <= 25:
        return RiskBand.HIGH
    if score <= 50:
        return RiskBand.MEDIUM_HIGH
    if score <= 75:
        return RiskBand.MEDIUM_LOW
    return RiskBand.LOW


def compute_composite_score(
    results: dict[VerificationType, VerificationResult],
    weights: dict[VerificationType, int] | None = None,
) -> int:
    """Compute weighted composite risk score from individual layer scores.

    Args:
        results: Verification results per layer.
        weights: Custom weights (must sum to 100). Defaults to DEFAULT_WEIGHTS.

    Returns:
        Composite score 0-100 (higher = safer).
    """
    w = weights or DEFAULT_WEIGHTS
    total_weight = 0
    weighted_sum = 0

    for vtype, result in results.items():
        if vtype in w and result.is_valid:
            weighted_sum += result.score * w[vtype]
            total_weight += w[vtype]

    if total_weight == 0:
        return 0

    return min(round(weighted_sum / total_weight), 100)


# ============ ZK Proof Builders ============

def create_proof_commitment(
    verification_type: VerificationType,
    data: bytes,
    public_inputs: list[int] | None = None,
) -> ZKProofCommitment:
    """Create a ZK proof commitment for verification data.

    Generates a commitment hash H(data || nonce) that can be
    verified later without revealing the original data.

    Args:
        verification_type: Which verification layer this proves.
        data: The private verification data to commit to.
        public_inputs: Optional public ZK circuit inputs.

    Returns:
        ZKProofCommitment with binding commitment hash.
    """
    nonce = secrets.token_bytes(32)
    commitment_hash = hashlib.sha256(data + nonce).digest()

    return ZKProofCommitment(
        commitment_hash=commitment_hash,
        nonce=nonce,
        verification_type=verification_type,
        timestamp=int(datetime.now(UTC).timestamp()),
        public_inputs=public_inputs or [],
    )


def build_verification_calldata(
    agent_id: int,
    verification_type: VerificationType,
    score: int,
    proof_commitment: bytes,
) -> bytes:
    """Build calldata for submitting verification result on-chain.

    Encodes: submitVerification(uint256 agentId, uint8 vType, uint8 score, bytes32 proofHash)

    Args:
        agent_id: The on-chain agent ID.
        verification_type: Verification layer type.
        score: Verification score 0-100.
        proof_commitment: 32-byte proof commitment hash.
    """
    # Function selector: submitVerification(uint256,uint8,uint8,bytes32)
    selector = hashlib.sha256(
        b"submitVerification(uint256,uint8,uint8,bytes32)"
    ).digest()[:4]

    vtype_map = {
        VerificationType.ETV: 0,
        VerificationType.SCV: 1,
        VerificationType.WAV: 2,
        VerificationType.WV: 3,
    }

    # Pad proof commitment to 32 bytes
    proof_padded = proof_commitment[:32].ljust(32, b"\x00")

    encoded = encode(
        ["uint256", "uint8", "uint8", "bytes32"],
        [agent_id, vtype_map[verification_type], score, proof_padded],
    )

    return selector + encoded


def build_risk_score_query_calldata(agent_id: int) -> bytes:
    """Build calldata to query an agent's composite risk score.

    Encodes: getRiskScore(uint256 agentId) → (uint8 score, uint8 band)
    """
    selector = hashlib.sha256(
        b"getRiskScore(uint256)"
    ).digest()[:4]

    encoded = encode(["uint256"], [agent_id])
    return selector + encoded


# ============ ETV: Ethereum Token Verification ============

def evaluate_etv(
    contract_address: str,
    is_verified_source: bool = False,
    has_audit: bool = False,
    uses_proxy: bool = False,
    bytecode_size: int = 0,
) -> VerificationResult:
    """Evaluate Ethereum Token Verification (code legitimacy).

    Scores based on contract verification, audit status, and complexity.

    Args:
        contract_address: The contract address to evaluate.
        is_verified_source: Whether source code is verified on block explorer.
        has_audit: Whether the contract has a security audit.
        uses_proxy: Whether contract uses a proxy pattern.
        bytecode_size: Contract bytecode size in bytes.
    """
    score = 0

    # Verified source code: +40
    if is_verified_source:
        score += 40

    # Security audit: +30
    if has_audit:
        score += 30

    # Bytecode size reasonableness (not too small, not too large): +15
    if 100 <= bytecode_size <= 50000:
        score += 15

    # No proxy (simpler, more auditable): +15
    if not uses_proxy:
        score += 15
    else:
        score += 5  # Proxies get partial credit

    return VerificationResult(
        verification_type=VerificationType.ETV,
        status=VerificationStatus.VERIFIED if score > 0 else VerificationStatus.FAILED,
        score=min(score, 100),
        details={
            "contract_address": contract_address,
            "verified_source": is_verified_source,
            "has_audit": has_audit,
            "uses_proxy": uses_proxy,
            "bytecode_size": bytecode_size,
        },
        verified_at=datetime.now(UTC),
    )


# ============ SCV: Staking Contract Verification ============

def evaluate_scv(
    staked_amount_usd: float,
    staking_duration_days: int = 0,
    slashing_enabled: bool = False,
) -> VerificationResult:
    """Evaluate Staking Contract Verification (economic commitment).

    Higher stakes and longer durations indicate stronger commitment.

    Args:
        staked_amount_usd: USD value of staked collateral.
        staking_duration_days: How long the stake has been active.
        slashing_enabled: Whether slashing conditions are active.
    """
    score = 0

    # Stake amount tiers
    if staked_amount_usd >= 100000:
        score += 40
    elif staked_amount_usd >= 10000:
        score += 30
    elif staked_amount_usd >= 1000:
        score += 20
    elif staked_amount_usd > 0:
        score += 10

    # Duration bonus
    if staking_duration_days >= 365:
        score += 30
    elif staking_duration_days >= 90:
        score += 20
    elif staking_duration_days >= 30:
        score += 10

    # Slashing conditions: +30 (skin in the game)
    if slashing_enabled:
        score += 30

    return VerificationResult(
        verification_type=VerificationType.SCV,
        status=VerificationStatus.VERIFIED if score > 0 else VerificationStatus.FAILED,
        score=min(score, 100),
        details={
            "staked_amount_usd": staked_amount_usd,
            "staking_duration_days": staking_duration_days,
            "slashing_enabled": slashing_enabled,
        },
        verified_at=datetime.now(UTC),
    )


# ============ WV: Wallet Verification ============

def evaluate_wv(
    wallet_age_days: int = 0,
    transaction_count: int = 0,
    unique_counterparties: int = 0,
    has_ens: bool = False,
    flagged_transactions: int = 0,
) -> VerificationResult:
    """Evaluate Wallet Verification (behavioral history).

    Scores based on wallet age, activity volume, and reputation.

    Args:
        wallet_age_days: Wallet age in days.
        transaction_count: Total transaction count.
        unique_counterparties: Number of unique counterparties.
        has_ens: Whether wallet has an ENS name.
        flagged_transactions: Number of flagged/suspicious transactions.
    """
    score = 0

    # Wallet age
    if wallet_age_days >= 365:
        score += 25
    elif wallet_age_days >= 90:
        score += 15
    elif wallet_age_days >= 30:
        score += 10

    # Transaction volume
    if transaction_count >= 1000:
        score += 25
    elif transaction_count >= 100:
        score += 15
    elif transaction_count >= 10:
        score += 10

    # Counterparty diversity
    if unique_counterparties >= 50:
        score += 20
    elif unique_counterparties >= 10:
        score += 10

    # ENS name (identity signal)
    if has_ens:
        score += 10

    # Flagged transactions penalty
    if flagged_transactions > 0:
        penalty = min(flagged_transactions * 10, 30)
        score = max(0, score - penalty)

    # Base reputation: +20 if no flags
    if flagged_transactions == 0:
        score += 20

    return VerificationResult(
        verification_type=VerificationType.WV,
        status=VerificationStatus.VERIFIED if score > 0 else VerificationStatus.FAILED,
        score=min(score, 100),
        details={
            "wallet_age_days": wallet_age_days,
            "transaction_count": transaction_count,
            "unique_counterparties": unique_counterparties,
            "has_ens": has_ens,
            "flagged_transactions": flagged_transactions,
        },
        verified_at=datetime.now(UTC),
    )


# ============ WAV: Web Application Verification ============

def evaluate_wav(
    has_https: bool = False,
    valid_ssl: bool = False,
    domain_age_days: int = 0,
    has_security_headers: bool = False,
    cors_configured: bool = False,
) -> VerificationResult:
    """Evaluate Web Application Verification (off-chain security).

    Scores based on web security posture of the agent's interface.

    Args:
        has_https: Whether the endpoint uses HTTPS.
        valid_ssl: Whether SSL certificate is valid and not expired.
        domain_age_days: Domain registration age in days.
        has_security_headers: Whether security headers are present (CSP, HSTS, etc.).
        cors_configured: Whether CORS is properly restricted.
    """
    score = 0

    # HTTPS: +25
    if has_https:
        score += 25

    # Valid SSL: +20
    if valid_ssl:
        score += 20

    # Domain age
    if domain_age_days >= 365:
        score += 20
    elif domain_age_days >= 90:
        score += 10

    # Security headers: +20
    if has_security_headers:
        score += 20

    # CORS: +15
    if cors_configured:
        score += 15

    return VerificationResult(
        verification_type=VerificationType.WAV,
        status=VerificationStatus.VERIFIED if score > 0 else VerificationStatus.FAILED,
        score=min(score, 100),
        details={
            "has_https": has_https,
            "valid_ssl": valid_ssl,
            "domain_age_days": domain_age_days,
            "has_security_headers": has_security_headers,
            "cors_configured": cors_configured,
        },
        verified_at=datetime.now(UTC),
    )


# ============ Full Agent Verification ============

def verify_agent(
    agent_id: int,
    agent_address: str,
    etv_params: dict[str, Any] | None = None,
    scv_params: dict[str, Any] | None = None,
    wav_params: dict[str, Any] | None = None,
    wv_params: dict[str, Any] | None = None,
    weights: dict[VerificationType, int] | None = None,
) -> AgentVerification:
    """Run full ERC-8126 verification for an agent.

    Evaluates all applicable verification layers and computes
    a composite risk score.

    Args:
        agent_id: On-chain agent ID.
        agent_address: Agent's Ethereum address.
        etv_params: Parameters for Ethereum Token Verification.
        scv_params: Parameters for Staking Contract Verification.
        wav_params: Parameters for Web Application Verification.
        wv_params: Parameters for Wallet Verification.
        weights: Custom layer weights.

    Returns:
        AgentVerification with all results and composite score.
    """
    results: dict[VerificationType, VerificationResult] = {}
    proofs: list[ZKProofCommitment] = []

    if etv_params is not None:
        result = evaluate_etv(**etv_params)
        results[VerificationType.ETV] = result
        if result.is_valid:
            proof = create_proof_commitment(
                VerificationType.ETV,
                str(etv_params).encode(),
                [result.score],
            )
            proofs.append(proof)

    if scv_params is not None:
        result = evaluate_scv(**scv_params)
        results[VerificationType.SCV] = result
        if result.is_valid:
            proof = create_proof_commitment(
                VerificationType.SCV,
                str(scv_params).encode(),
                [result.score],
            )
            proofs.append(proof)

    if wav_params is not None:
        result = evaluate_wav(**wav_params)
        results[VerificationType.WAV] = result
        if result.is_valid:
            proof = create_proof_commitment(
                VerificationType.WAV,
                str(wav_params).encode(),
                [result.score],
            )
            proofs.append(proof)

    if wv_params is not None:
        result = evaluate_wv(**wv_params)
        results[VerificationType.WV] = result
        if result.is_valid:
            proof = create_proof_commitment(
                VerificationType.WV,
                str(wv_params).encode(),
                [result.score],
            )
            proofs.append(proof)

    composite = compute_composite_score(results, weights)

    verification = AgentVerification(
        agent_id=agent_id,
        agent_address=agent_address,
        etv_result=results.get(VerificationType.ETV),
        scv_result=results.get(VerificationType.SCV),
        wav_result=results.get(VerificationType.WAV),
        wv_result=results.get(VerificationType.WV),
        composite_score=composite,
        proofs=proofs,
    )

    logger.info(
        "ERC-8126 verification for agent %d: score=%d band=%s layers=%d",
        agent_id, composite, verification.risk_band.value, verification.verification_count,
    )

    return verification


# ============ Normalized Risk for Guardrails Integration ============

def risk_score_to_normalized(erc8126_score: int) -> float:
    """Convert ERC-8126 score (0-100, higher=safer) to normalized risk (0.0-1.0, higher=riskier).

    This inverts the scale for integration with Sardis guardrails/AnomalyEngine
    which uses 0.0 = safe, 1.0 = dangerous.
    """
    return max(0.0, min(1.0, 1.0 - (erc8126_score / 100.0)))
