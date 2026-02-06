"""x402 request schema validation tests."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from sardis_protocol.schemas import X402PaymentExecuteRequest

pytestmark = [pytest.mark.protocol_conformance, pytest.mark.x402]


def test_x402_request_accepts_valid_payload():
    req = X402PaymentExecuteRequest(
        payment_id="pay_x402_1",
        amount="100",
        resource_uri="/v1/weather",
        payer_address="0x1111111111111111111111111111111111111111",
        payer_signature="sig_abc",
        payee_address="0x2222222222222222222222222222222222222222",
    )

    assert req.payment_id == "pay_x402_1"
    assert req.payment_type == "per_request"
    assert req.x402_version == "1.0"


def test_x402_request_rejects_missing_required_fields():
    with pytest.raises(ValidationError):
        X402PaymentExecuteRequest(
            payment_id="pay_x402_2",
            amount="100",
            resource_uri="/v1/weather",
            payer_address="0x1111111111111111111111111111111111111111",
            payee_address="0x2222222222222222222222222222222222222222",
            # Missing payer_signature
        )
