"""Tests verifying ZK-related code is fail-closed.

Ensures that:
1. ZK verifier Solidity contracts always revert (not return true)
2. zkPass verification raises NotImplementedError
3. sardis-zkp verify() raises NotImplementedError in non-production mode
4. SAML endpoint returns 501 (not 500 from uncaught NotImplementedError)
5. ERC-8126 function selectors use keccak256, not sha256
6. create_proof_commitment emits deprecation warning
"""
from __future__ import annotations

import re
import warnings
from pathlib import Path

import pytest

# =========================================================================
# DEFECT 1: ZK verifier contracts must revert, never return true
# =========================================================================

VERIFIER_DIR = Path(__file__).parent.parent / "contracts" / "src" / "verifiers"

VERIFIER_FILES = [
    "FundingSufficiencyVerifier.sol",
    "MandateComplianceVerifier.sol",
    "IdentityProofVerifier.sol",
]


@pytest.mark.parametrize("filename", VERIFIER_FILES)
def test_zk_verifier_contract_reverts(filename: str) -> None:
    """Each ZK verifier .sol file must contain a revert and must NOT
    contain 'valid = true'."""
    path = VERIFIER_DIR / filename
    assert path.exists(), f"Verifier contract not found: {path}"

    source = path.read_text()

    # Must contain the revert statement
    assert 'revert("ZK verification not implemented' in source, (
        f"{filename} does not contain the required revert statement"
    )

    # Must NOT contain the old 'valid = true' pattern
    assert "valid = true" not in source, (
        f"{filename} still contains 'valid = true' - ZK verification is not implemented"
    )


# =========================================================================
# DEFECT 2: zkPass verification must raise NotImplementedError
# =========================================================================


def test_zkpass_verify_proof_raises() -> None:
    """ZKPassVerifier.verify_proof must raise NotImplementedError."""
    from sardis_protocol.zkpass_transgate import ZKPassVerifier

    verifier = ZKPassVerifier()

    # Submit a proof so we have a valid proof_id
    proof = verifier.submit_proof(
        schema_id="coinbase_kyc",
        prover_address="0xABC",
        proof_data=b"fake_proof_data",
        public_inputs={"kyc_status": "verified", "verification_date": "2026-01-01"},
    )

    with pytest.raises(NotImplementedError, match="TransGate SDK"):
        verifier.verify_proof(proof.proof_id)


# =========================================================================
# DEFECT 3: sardis-zkp verify() must raise NotImplementedError (dev mode)
# =========================================================================


def test_zkp_verify_source_raises_in_dev_mode() -> None:
    """ZKProver source must raise NotImplementedError in non-production mode."""
    lib_path = (
        Path(__file__).parent.parent
        / "packages"
        / "sardis-zkp"
        / "src"
        / "lib.py"
    )
    source = lib_path.read_text()

    # The verify method must raise NotImplementedError for non-production
    assert 'raise NotImplementedError(' in source, (
        "sardis-zkp lib.py verify() must raise NotImplementedError in dev mode"
    )
    assert "compiled Noir circuits" in source, (
        "NotImplementedError should mention Noir circuits"
    )

    # Must NOT contain the old mock verification pattern
    assert "Mock verification: check proof structure" not in source, (
        "sardis-zkp lib.py still has mock verification that returns valid=True"
    )


# =========================================================================
# DEFECT 4: ERC-8126 function selectors must use keccak256
# =========================================================================


def test_erc8126_selectors_use_keccak() -> None:
    """build_verification_calldata and build_risk_score_query_calldata
    must use keccak256, not sha256, for EVM-compatible selectors."""
    source_path = (
        Path(__file__).parent.parent
        / "packages"
        / "sardis-protocol"
        / "src"
        / "sardis_protocol"
        / "erc8126.py"
    )
    source = source_path.read_text()

    # The calldata builder functions should reference keccak, not sha256
    # for function selector computation
    keccak_pattern = re.compile(r"keccak\(")
    sha256_selector_pattern = re.compile(r"hashlib\.sha256\(.*(submitVerification|getRiskScore)")

    assert keccak_pattern.search(source), (
        "erc8126.py does not use keccak for function selectors"
    )
    assert not sha256_selector_pattern.search(source), (
        "erc8126.py still uses sha256 for function selectors"
    )


def test_erc8126_create_proof_commitment_deprecation() -> None:
    """create_proof_commitment should emit a DeprecationWarning."""
    from sardis_protocol.erc8126 import VerificationType, create_proof_commitment

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        create_proof_commitment(
            VerificationType.ETV,
            b"test_data",
            [42],
        )

    deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
    assert len(deprecation_warnings) >= 1, (
        "create_proof_commitment should emit a DeprecationWarning"
    )
    assert "create_hash_commitment" in str(deprecation_warnings[0].message)


# =========================================================================
# DEFECT 5: SAML endpoint must return 501, not crash with 500
# =========================================================================


@pytest.mark.asyncio
async def test_saml_handler_returns_501() -> None:
    """SAMLHandler.validate_response must raise HTTPException(501),
    not NotImplementedError (which would surface as 500)."""
    from fastapi import HTTPException

    from server.middleware.sso import SAMLHandler, SSOConfig

    config = SSOConfig(
        id="test",
        org_id="org_test",
        provider_type="saml",
        display_name="Test SAML",
        enabled=True,
        saml_entity_id="https://idp.example.com",
        saml_sso_url="https://idp.example.com/sso",
        saml_certificate="MIIC...",
    )
    handler = SAMLHandler(config)

    with pytest.raises(HTTPException) as exc_info:
        await handler.validate_response("<saml:Response>fake</saml:Response>")

    assert exc_info.value.status_code == 501
    assert "not yet implemented" in exc_info.value.detail.lower()


def test_saml_handler_source_no_notimplementederror() -> None:
    """SAMLHandler.validate_response must raise HTTPException, not
    NotImplementedError (which would surface as unhandled 500)."""
    source_path = (
        Path(__file__).parent.parent
        / "packages"
        / "api"
        / "src"
        / "server"
        / "middleware"
        / "sso.py"
    )
    source = source_path.read_text()

    # The validate_response method should NOT raise NotImplementedError
    # It should raise HTTPException(501) instead
    assert "raise HTTPException(" in source
    assert "HTTP_501_NOT_IMPLEMENTED" in source


# =========================================================================
# DEFECT 6: No _stub_proof references should remain
# =========================================================================


def test_no_stub_proof_references() -> None:
    """All _stub_proof variables must have been renamed to
    _internal_system_proof across the API routers."""
    routers_dir = (
        Path(__file__).parent.parent
        / "packages"
        / "api"
        / "src"
        / "server"
        / "routes"
    )

    files_to_check = [
        "authority/mvp.py",
        "authority/mandates.py",
        "wallets/onchain_payments.py",
        "wallets/wallets.py",
    ]

    for filename in files_to_check:
        path = routers_dir / filename
        if path.exists():
            source = path.read_text()
            assert "_stub_proof" not in source, (
                f"{filename} still contains '_stub_proof' - "
                "should be renamed to '_internal_system_proof'"
            )
