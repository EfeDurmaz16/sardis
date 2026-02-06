"""AP2 negative interop test runner.

Loads negative test cases from fixtures and validates rejection behavior.
"""
import json
import pytest
from pathlib import Path

from sardis_v2_core import SardisSettings
from sardis_protocol.verifier import MandateVerifier, MandateChainVerification
from sardis_protocol.schemas import AP2PaymentExecuteRequest

FIXTURES_PATH = Path(__file__).parent / "fixtures" / "ap2_negative_interop.json"


def load_fixtures():
    """Load negative test cases from JSON fixture file."""
    with FIXTURES_PATH.open() as f:
        data = json.load(f)
    return data


pytestmark = [pytest.mark.protocol_conformance, pytest.mark.ap2]


@pytest.mark.parametrize("fixture", load_fixtures(), ids=lambda f: f["id"])
def test_ap2_negative_interop(fixture):
    """Test that mandate verifier correctly rejects malformed AP2 mandates.

    This test validates that the MandateVerifier properly detects and rejects
    various protocol violations as specified in the AP2 specification.

    Args:
        fixture: Test case containing invalid mandate data and expected error
    """
    # Setup verifier with permissive settings for testing
    settings = SardisSettings(
        allowed_domains=["example.com", "shop.example.com"],
        postgres_url="postgresql://test:test@localhost/test",
    )
    verifier = MandateVerifier(settings=settings)

    # Construct AP2 payment request from fixture input
    request = AP2PaymentExecuteRequest(
        intent=fixture["input"]["intent"],
        cart=fixture["input"]["cart"],
        payment=fixture["input"]["payment"],
    )

    # Run verification through the mandate chain verifier
    result: MandateChainVerification = verifier.verify_chain(request)

    # Assert that verification was rejected
    assert not result.accepted, (
        f"Test {fixture['id']}: Expected rejection but mandate was accepted. "
        f"Description: {fixture['description']}"
    )

    # Assert that the rejection reason matches the expected error
    expected_error = fixture["expected_error"]
    assert result.reason is not None, (
        f"Test {fixture['id']}: Verification was rejected but no reason provided"
    )

    # The reason may be prefixed with mandate type (e.g., "intent_mandate_expired")
    # or exact match (e.g., "subject_mismatch")
    assert expected_error in result.reason, (
        f"Test {fixture['id']}: Expected error '{expected_error}' but got '{result.reason}'. "
        f"Description: {fixture['description']}. "
        f"Spec reference: {fixture['spec_reference']}"
    )
