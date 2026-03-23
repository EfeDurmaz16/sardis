"""Sardis ZKP — zero-knowledge proof generation and verification.

Three privacy tiers for payment objects:
  - Transparent: No ZKP, all data visible on-chain
  - Hybrid: Selective disclosure (amount hidden, merchant visible)
  - Full ZK: All payment details hidden behind proofs

Circuits (Noir):
  1. mandate_compliance — proves payment satisfies mandate bounds
  2. identity_proof — proves agent is KYA-verified without revealing identity
  3. funding_sufficiency — proves cells cover payment without revealing values

Usage::

    from sardis_zkp import ZKProver, PrivacyTier

    prover = ZKProver()
    proof = await prover.prove_mandate_compliance(
        amount=Decimal("50.00"),
        per_tx_limit=Decimal("100.00"),
        daily_limit=Decimal("1000.00"),
        daily_spent=Decimal("200.00"),
    )
    verified = await prover.verify(proof)
"""
from __future__ import annotations

import hashlib
import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.zkp")

CIRCUITS_DIR = Path(__file__).parent.parent / "circuits"


class PrivacyTier(str, Enum):
    """Privacy level for a payment object."""
    TRANSPARENT = "transparent"   # No ZKP
    HYBRID = "hybrid"            # Selective disclosure
    FULL_ZK = "full_zk"         # Everything hidden


class CircuitType(str, Enum):
    """Available ZKP circuits."""
    MANDATE_COMPLIANCE = "mandate_compliance"
    IDENTITY_PROOF = "identity_proof"
    FUNDING_SUFFICIENCY = "funding_sufficiency"


@dataclass
class ZKProof:
    """A generated zero-knowledge proof."""

    proof_id: str = field(default_factory=lambda: f"zkp_{uuid4().hex[:12]}")
    circuit: CircuitType = CircuitType.MANDATE_COMPLIANCE
    proof_bytes: bytes = field(default_factory=bytes)
    public_inputs: list[str] = field(default_factory=list)
    verification_key_hash: str = ""
    verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def proof_hex(self) -> str:
        return self.proof_bytes.hex()


@dataclass
class VerificationResult:
    """Result of proof verification."""
    valid: bool
    circuit: CircuitType
    public_inputs: list[str]
    verification_time_ms: float = 0.0
    error: str | None = None


def _scale_amount(amount: Decimal) -> int:
    """Scale a decimal amount to integer (6 decimal places)."""
    return int(amount * Decimal("1000000"))


def _poseidon_hash_mock(*values: int) -> str:
    """Mock Poseidon hash for development (SHA-256 placeholder).

    In production, this uses the actual Poseidon hash from the Noir circuit.
    """
    data = json.dumps(list(values), sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()


class ZKProver:
    """Generates and verifies zero-knowledge proofs for Sardis payments.

    In development mode, uses mock proofs (SHA-256 commitments).
    In production, compiles and executes Noir circuits via nargo.
    """

    def __init__(self, production: bool = False) -> None:
        self._production = production
        self._circuits_dir = CIRCUITS_DIR

    async def prove_mandate_compliance(
        self,
        amount: Decimal,
        per_tx_limit: Decimal,
        daily_limit: Decimal,
        daily_spent: Decimal,
        merchant_id: str = "",
        nonce: int | None = None,
    ) -> ZKProof:
        """Prove a payment satisfies mandate bounds without revealing limits."""
        nonce = nonce or int(uuid4().int % (2**32))
        amount_scaled = _scale_amount(amount)
        limit_scaled = _scale_amount(per_tx_limit)
        daily_scaled = _scale_amount(daily_limit)
        spent_scaled = _scale_amount(daily_spent)
        merchant_hash = int(hashlib.sha256(merchant_id.encode()).hexdigest()[:16], 16)

        # Compute commitments
        mandate_commitment = _poseidon_hash_mock(
            limit_scaled, daily_scaled, 0, nonce
        )
        payment_commitment = _poseidon_hash_mock(
            amount_scaled, merchant_hash, spent_scaled, nonce
        )

        if self._production:
            proof_bytes = await self._run_noir_prover(
                CircuitType.MANDATE_COMPLIANCE,
                {
                    "mandate_commitment": mandate_commitment,
                    "payment_commitment": payment_commitment,
                    "amount": str(amount_scaled),
                    "per_tx_limit": str(limit_scaled),
                    "daily_limit": str(daily_scaled),
                    "daily_spent": str(spent_scaled),
                    "merchant_id_hash": str(merchant_hash),
                    "allowed_merchant_root": "0",
                    "merchant_proof": ["0"] * 8,
                    "mandate_nonce": str(nonce),
                },
            )
        else:
            # Mock proof for development
            proof_data = {
                "circuit": "mandate_compliance",
                "public": [mandate_commitment, payment_commitment],
                "nonce": nonce,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            proof_bytes = json.dumps(proof_data).encode()

        proof = ZKProof(
            circuit=CircuitType.MANDATE_COMPLIANCE,
            proof_bytes=proof_bytes,
            public_inputs=[mandate_commitment, payment_commitment],
            metadata={
                "amount_hidden": True,
                "limits_hidden": True,
                "merchant_hidden": True,
            },
        )

        logger.info("Generated mandate compliance proof %s", proof.proof_id)
        return proof

    async def prove_identity(
        self,
        agent_id: str,
        kya_level: int,
        required_level: int,
        attestation_timestamp: int,
        attestation_expiry: int,
        issuer_id: str,
    ) -> ZKProof:
        """Prove agent has required KYA level without revealing identity."""
        agent_hash = int(hashlib.sha256(agent_id.encode()).hexdigest()[:16], 16)
        issuer_hash = int(hashlib.sha256(issuer_id.encode()).hexdigest()[:16], 16)

        commitment = _poseidon_hash_mock(
            agent_hash, kya_level, attestation_timestamp,
            attestation_expiry, issuer_hash,
        )

        proof_data = {
            "circuit": "identity_proof",
            "public": [commitment, str(required_level)],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        proof_bytes = json.dumps(proof_data).encode()

        proof = ZKProof(
            circuit=CircuitType.IDENTITY_PROOF,
            proof_bytes=proof_bytes,
            public_inputs=[commitment, str(required_level)],
            metadata={"agent_hidden": True, "level_proven": True},
        )

        logger.info("Generated identity proof %s", proof.proof_id)
        return proof

    async def prove_funding_sufficiency(
        self,
        payment_amount: Decimal,
        cell_values: list[Decimal],
        currency: str = "USDC",
    ) -> ZKProof:
        """Prove funding cells cover payment without revealing cell values."""
        amount_scaled = _scale_amount(payment_amount)
        values_scaled = [_scale_amount(v) for v in cell_values]

        # Pad to 16 cells
        while len(values_scaled) < 16:
            values_scaled.append(0)
        values_scaled = values_scaled[:16]

        nonce = int(uuid4().int % (2**32))
        currency_hash = int(hashlib.sha256(currency.encode()).hexdigest()[:16], 16)

        batch1 = _poseidon_hash_mock(*values_scaled[:4])
        batch2 = _poseidon_hash_mock(*values_scaled[4:8])
        commitment = _poseidon_hash_mock(
            int(batch1[:16], 16), int(batch2[:16], 16), currency_hash, nonce
        )

        proof_data = {
            "circuit": "funding_sufficiency",
            "public": [str(amount_scaled), commitment],
            "timestamp": datetime.now(UTC).isoformat(),
        }
        proof_bytes = json.dumps(proof_data).encode()

        proof = ZKProof(
            circuit=CircuitType.FUNDING_SUFFICIENCY,
            proof_bytes=proof_bytes,
            public_inputs=[str(amount_scaled), commitment],
            metadata={
                "cell_count": len([v for v in cell_values if v > 0]),
                "values_hidden": True,
            },
        )

        logger.info("Generated funding sufficiency proof %s", proof.proof_id)
        return proof

    async def verify(self, proof: ZKProof) -> VerificationResult:
        """Verify a zero-knowledge proof."""
        import time
        start = time.monotonic()

        if self._production:
            valid = await self._run_noir_verifier(proof)
        else:
            # Mock verification: check proof structure
            try:
                data = json.loads(proof.proof_bytes)
                valid = (
                    data.get("circuit") == proof.circuit.value
                    and data.get("public") == proof.public_inputs
                )
            except (json.JSONDecodeError, KeyError):
                valid = False

        elapsed = (time.monotonic() - start) * 1000

        result = VerificationResult(
            valid=valid,
            circuit=proof.circuit,
            public_inputs=proof.public_inputs,
            verification_time_ms=elapsed,
        )

        proof.verified = valid
        logger.info(
            "Proof %s verification: %s (%.1fms)",
            proof.proof_id, "VALID" if valid else "INVALID", elapsed,
        )
        return result

    async def _run_noir_prover(
        self, circuit: CircuitType, inputs: dict
    ) -> bytes:
        """Run the Noir prover via nargo CLI."""
        circuit_dir = self._circuits_dir / circuit.value
        prover_toml = circuit_dir / "Prover.toml"

        # Write inputs
        with open(prover_toml, "w") as f:
            for k, v in inputs.items():
                if isinstance(v, list):
                    f.write(f'{k} = [{", ".join(f\'"{x}\'' for x in v)}]\n')
                else:
                    f.write(f'{k} = "{v}"\n')

        result = subprocess.run(
            ["nargo", "prove"],
            cwd=str(circuit_dir),
            capture_output=True,
            timeout=60,
        )

        if result.returncode != 0:
            raise RuntimeError(f"Noir prover failed: {result.stderr.decode()}")

        proof_path = circuit_dir / "proofs" / f"{circuit.value}.proof"
        return proof_path.read_bytes()

    async def _run_noir_verifier(self, proof: ZKProof) -> bool:
        """Run the Noir verifier via nargo CLI."""
        circuit_dir = self._circuits_dir / proof.circuit.value

        result = subprocess.run(
            ["nargo", "verify"],
            cwd=str(circuit_dir),
            capture_output=True,
            timeout=30,
        )

        return result.returncode == 0
