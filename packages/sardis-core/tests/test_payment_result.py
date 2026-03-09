"""Tests for the unified PaymentResult dataclass."""
from __future__ import annotations

from sardis_v2_core.payment_result import PaymentResult


class TestSuccessFactory:
    def test_success_factory(self) -> None:
        result = PaymentResult.success(
            mandate_id="mnd_abc",
            tx_hash="0xdeadbeef",
            chain="base",
        )
        assert result.status == "success"
        assert result.mandate_id == "mnd_abc"
        assert result.tx_hash == "0xdeadbeef"
        assert result.chain == "base"
        assert result.is_success is True
        assert result.is_rejected is False

    def test_success_with_extra_kwargs(self) -> None:
        result = PaymentResult.success(
            mandate_id="mnd_1",
            tx_hash="0x1",
            chain="polygon",
            ledger_entry_id="led_42",
            attestation_id="att_7",
            policy_evidence={"rule": "passed"},
        )
        assert result.ledger_entry_id == "led_42"
        assert result.attestation_id == "att_7"
        assert result.policy_evidence == {"rule": "passed"}


class TestRejectedFactory:
    def test_rejected_factory(self) -> None:
        result = PaymentResult.rejected(
            reason="over daily limit",
            mandate_id="mnd_xyz",
        )
        assert result.status == "rejected"
        assert result.reason == "over daily limit"
        assert result.mandate_id == "mnd_xyz"
        assert result.is_success is False
        assert result.is_rejected is True

    def test_rejected_without_mandate(self) -> None:
        result = PaymentResult.rejected(reason="blocked merchant")
        assert result.mandate_id == ""
        assert result.reason == "blocked merchant"

    def test_rejected_with_reason_codes(self) -> None:
        result = PaymentResult.rejected(
            reason="policy violation",
            reason_codes=["DAILY_LIMIT", "MCC_BLOCKED"],
        )
        assert result.reason_codes == ["DAILY_LIMIT", "MCC_BLOCKED"]


class TestFailedFactory:
    def test_failed_factory(self) -> None:
        result = PaymentResult.failed(
            reason="chain timeout",
            mandate_id="mnd_fail",
        )
        assert result.status == "failed"
        assert result.reason == "chain timeout"
        assert result.mandate_id == "mnd_fail"
        assert result.is_success is False
        assert result.is_rejected is False

    def test_failed_with_chain_receipt(self) -> None:
        receipt = {"revert_reason": "out of gas"}
        result = PaymentResult.failed(
            reason="tx reverted",
            chain_receipt=receipt,
        )
        assert result.chain_receipt == receipt


class TestIsSuccessProperty:
    def test_true_for_success(self) -> None:
        result = PaymentResult(status="success")
        assert result.is_success is True

    def test_false_for_rejected(self) -> None:
        result = PaymentResult(status="rejected")
        assert result.is_success is False

    def test_false_for_failed(self) -> None:
        result = PaymentResult(status="failed")
        assert result.is_success is False

    def test_false_for_arbitrary_status(self) -> None:
        result = PaymentResult(status="pending")
        assert result.is_success is False


class TestDefaultFields:
    def test_default_fields(self) -> None:
        result = PaymentResult(status="success")
        assert result.mandate_id == ""
        assert result.tx_hash == ""
        assert result.chain == ""
        assert result.reason == ""
        assert result.reason_codes == []
        assert result.policy_evidence == {}
        assert result.compliance_evidence == {}
        assert result.chain_receipt is None
        assert result.ledger_entry_id == ""
        assert result.attestation_id == ""

    def test_mutable_defaults_are_independent(self) -> None:
        """Ensure each instance gets its own list/dict (no shared mutable default)."""
        a = PaymentResult(status="success")
        b = PaymentResult(status="success")
        a.reason_codes.append("X")
        a.policy_evidence["k"] = "v"
        assert b.reason_codes == []
        assert b.policy_evidence == {}
