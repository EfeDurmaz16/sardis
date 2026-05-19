"""Credential-free checks for the experimental Sardis ZKP package."""

from __future__ import annotations

import json
import tomllib
from decimal import Decimal
from pathlib import Path

import pytest
from sardis_zkp import CircuitType, PrivacyTier, ZKProver
from sardis_zkp.lib import CIRCUITS_DIR

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_nargo_manifest_declares_experimental_circuit_package():
    data = tomllib.loads((PACKAGE_ROOT / "Nargo.toml").read_text(encoding="utf-8"))

    assert data["package"]["name"] == "sardis_zkp"
    assert data["package"]["type"] == "bin"
    assert data["package"]["compiler_version"] == ">=0.30.0"


def test_circuit_files_document_public_and_private_inputs():
    expected = {
        "identity_proof.nr",
        "funding_sufficiency.nr",
        "mandate_compliance.nr",
    }
    files = {path.name for path in (PACKAGE_ROOT / "circuits").glob("*.nr")}

    assert files == expected
    for path in (PACKAGE_ROOT / "circuits").glob("*.nr"):
        text = path.read_text(encoding="utf-8")
        assert "Public inputs" in text
        assert "Private inputs" in text
        assert "#[test]" in text


def test_python_wrapper_uses_real_circuit_directory():
    assert CIRCUITS_DIR == PACKAGE_ROOT / "circuits"
    assert (CIRCUITS_DIR / "mandate_compliance.nr").is_file()


@pytest.mark.asyncio
async def test_mock_mandate_proof_generation_is_marked_unverified():
    proof = await ZKProver().prove_mandate_compliance(
        amount=Decimal("50"),
        per_tx_limit=Decimal("100"),
        daily_limit=Decimal("1000"),
        daily_spent=Decimal("200"),
        merchant_id="merchant.example",
        nonce=42,
    )

    payload = json.loads(proof.proof_bytes.decode())
    assert proof.circuit == CircuitType.MANDATE_COMPLIANCE
    assert proof.verified is False
    assert payload["circuit"] == "mandate_compliance"
    assert proof.metadata == {
        "amount_hidden": True,
        "limits_hidden": True,
        "merchant_hidden": True,
    }


@pytest.mark.asyncio
async def test_mock_verification_is_not_available_without_nargo():
    with pytest.raises(NotImplementedError, match="nargo"):
        await ZKProver().verify(
            await ZKProver().prove_funding_sufficiency(
                payment_amount=Decimal("10"),
                cell_values=[Decimal("5"), Decimal("5")],
            )
        )


def test_public_enums_are_stable():
    assert PrivacyTier.FULL_ZK.value == "full_zk"
    assert CircuitType.FUNDING_SUFFICIENCY.value == "funding_sufficiency"
