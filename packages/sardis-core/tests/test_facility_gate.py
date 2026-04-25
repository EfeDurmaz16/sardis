from __future__ import annotations

from decimal import Decimal

from sardis_v2_core.facility_gate import (
    Facility,
    FacilityDecision,
    FacilityEvidenceRef,
    FacilityRepaymentMirror,
    FacilityRepaymentStatus,
    FacilityRequest,
    LiabilityAssignment,
    build_decision_packet,
    build_facility_decision,
)
from sardis_v2_core.spending_mandate import SpendingMandate


def test_spending_mandate_does_not_imply_facility_authority() -> None:
    mandate = SpendingMandate(
        principal_id="principal_1",
        issuer_id="principal_1",
        agent_id="agent_1",
        amount_per_tx=Decimal("5000"),
        allowed_rails=["simulated_card"],
    )

    result = mandate.check_facility_draw(
        amount=Decimal("2400"),
        facility_id="fac_1",
        merchant="aws.amazon.com",
        category="cloud",
        rail="simulated_card",
    )

    assert result.approved is False
    assert result.error_code == "MANDATE_FACILITY_AUTHORITY_REQUIRED"


def test_facility_decision_steps_up_when_evidence_is_missing() -> None:
    mandate = SpendingMandate(
        principal_id="principal_1",
        issuer_id="principal_1",
        agent_id="agent_1",
        amount_per_tx=Decimal("5000"),
        allowed_rails=["simulated_card"],
        facility_authority_allowed=True,
        allowed_facility_ids=["fac_1"],
        facility_max_draw=Decimal("5000"),
        facility_scope={"allowed_categories": ["cloud"]},
    )
    request = FacilityRequest(
        request_id="fac_req_1",
        organization_id="org_1",
        agent_id="agent_1",
        sponsor_id="sponsor_1",
        facility_id="fac_1",
        mandate_id=mandate.id,
        merchant="aws.amazon.com",
        amount_minor=240_000,
        category="cloud",
        purpose="cloud infrastructure",
    )

    decision = build_facility_decision(
        request=request,
        facility=Facility(facility_id="fac_1", organization_id="org_1", sponsor_id="sponsor_1"),
        mandate_check=mandate.check_facility_draw(
            amount=Decimal("2400"),
            facility_id="fac_1",
            merchant="aws.amazon.com",
            category="cloud",
            rail="simulated_card",
        ),
        liability=LiabilityAssignment(
            repayment_obligor="sponsor_1",
            settlement_responsible_party="simulated",
            loss_owner="simulated",
        ),
    )

    assert decision.verdict == FacilityDecision.STEP_UP_REQUIRED
    assert "facility_evidence_required" in decision.reason_codes


def test_facility_decision_approves_low_risk_evidenced_request() -> None:
    mandate = SpendingMandate(
        principal_id="principal_1",
        issuer_id="principal_1",
        agent_id="agent_1",
        amount_per_tx=Decimal("900"),
        allowed_rails=["simulated_card"],
        facility_authority_allowed=True,
        allowed_facility_ids=["fac_1"],
        facility_max_draw=Decimal("900"),
        facility_scope={"allowed_categories": ["cloud"]},
    )
    request = FacilityRequest(
        request_id="fac_req_1",
        organization_id="org_1",
        agent_id="agent_1",
        sponsor_id="sponsor_1",
        facility_id="fac_1",
        mandate_id=mandate.id,
        merchant="aws.amazon.com",
        amount_minor=75_000,
        category="cloud",
        purpose="cloud infrastructure",
        task_graph_hash="sha256:task",
        evidence=[
            FacilityEvidenceRef(
                evidence_id="evd_1",
                evidence_type="invoice",
                content_hash="sha256:invoice",
            )
        ],
    )

    decision = build_facility_decision(
        request=request,
        facility=Facility(facility_id="fac_1", organization_id="org_1", sponsor_id="sponsor_1"),
        mandate_check=mandate.check_facility_draw(
            amount=Decimal("750"),
            facility_id="fac_1",
            merchant="aws.amazon.com",
            category="cloud",
            rail="simulated_card",
        ),
        liability=LiabilityAssignment(
            repayment_obligor="sponsor_1",
            settlement_responsible_party="simulated",
            loss_owner="simulated",
        ),
        merchant_is_novel=False,
        sponsor_repayment_status="current",
        agent_trust_tier="trusted",
    )

    assert decision.verdict == FacilityDecision.APPROVED
    assert "facility_authorization_approved" in decision.reason_codes


def test_facility_decision_packet_is_stable_and_exportable() -> None:
    request = FacilityRequest(
        request_id="fac_req_packet",
        organization_id="org_1",
        agent_id="agent_1",
        sponsor_id="sponsor_1",
        facility_id="fac_1",
        mandate_id="mandate_1",
        merchant="aws.amazon.com",
        amount_minor=75_000,
        task_graph_hash="sha256:task",
        evidence=[
            FacilityEvidenceRef(
                evidence_id="evd_1",
                evidence_type="invoice",
                content_hash="sha256:invoice",
            )
        ],
        request_payload_hash="sha256:request",
    )
    decision = build_facility_decision(
        request=request,
        facility=Facility(facility_id="fac_1", organization_id="org_1", sponsor_id="sponsor_1"),
        mandate_check=type("MandateCheck", (), {"approved": True, "mandate_version": 7})(),
        liability=LiabilityAssignment(
            repayment_obligor="sponsor_1",
            settlement_responsible_party="simulated",
            loss_owner="simulated",
        ),
        merchant_is_novel=False,
        sponsor_repayment_status="current",
        agent_trust_tier="trusted",
    )

    first = build_decision_packet(
        request=request,
        decision=decision,
        mandate_snapshot_hash="sha256:mandate",
        facility_snapshot_hash="sha256:facility",
        policy_snapshot_hash="sha256:policy",
    )
    second = build_decision_packet(
        request=request,
        decision=decision,
        mandate_snapshot_hash="sha256:mandate",
        facility_snapshot_hash="sha256:facility",
        policy_snapshot_hash="sha256:policy",
    )

    assert first == second
    assert first["schema_version"] == "facility_decision_packet_v1"
    assert first["mandate"]["mandate_version"] == 7
    assert first["considered_evidence_ids"] == ["evd_1"]
    assert first["decision_packet_hash"]


def test_repayment_mirror_is_considered_in_risk_and_decision_packet() -> None:
    request = FacilityRequest(
        request_id="fac_req_repayment",
        organization_id="org_1",
        agent_id="agent_1",
        sponsor_id="sponsor_1",
        facility_id="fac_1",
        mandate_id="mandate_1",
        merchant="aws.amazon.com",
        amount_minor=75_000,
        task_graph_hash="sha256:task",
        evidence=[
            FacilityEvidenceRef(
                evidence_id="evd_1",
                evidence_type="invoice",
                content_hash="sha256:invoice",
            )
        ],
    )
    mirror = FacilityRepaymentMirror(
        facility_id="fac_1",
        sponsor_id="sponsor_1",
        status=FacilityRepaymentStatus.DELINQUENT,
        source="provider_snapshot",
        days_past_due=45,
    )
    decision = build_facility_decision(
        request=request,
        facility=Facility(facility_id="fac_1", organization_id="org_1", sponsor_id="sponsor_1"),
        mandate_check=type("MandateCheck", (), {"approved": True, "mandate_version": 1})(),
        liability=LiabilityAssignment(
            repayment_obligor="sponsor_1",
            settlement_responsible_party="simulated",
            loss_owner="simulated",
        ),
        merchant_is_novel=False,
        agent_trust_tier="trusted",
        repayment_mirror=mirror,
    )
    packet = build_decision_packet(request=request, decision=decision, repayment_mirror=mirror)

    assert "sponsor_repayment_delinquent" in decision.risk.reason_codes
    assert packet["repayment_mirror"]["status"] == "delinquent"
    assert packet["repayment_mirror"]["days_past_due"] == 45
