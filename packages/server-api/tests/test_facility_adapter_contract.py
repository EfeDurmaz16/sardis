from __future__ import annotations

import pytest
from sardis_v2_core.facility_gate import (
    DisabledProviderFacilityAdapter,
    Facility,
    FacilityDecision,
    FacilityEvidenceRef,
    FacilityRequest,
    LiabilityAssignment,
    MockProviderFacilityAdapter,
    SimulatedFacilityAdapter,
    build_facility_decision,
)


def _approved_request_and_decision():
    request = FacilityRequest(
        request_id="fac_req_contract",
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
        sponsor_repayment_status="current",
        agent_trust_tier="trusted",
    )
    assert decision.verdict == FacilityDecision.APPROVED
    return request, decision


@pytest.mark.asyncio
async def test_simulated_adapter_contract_executes_only_approved_authorizations() -> None:
    request, decision = _approved_request_and_decision()
    adapter = SimulatedFacilityAdapter()

    credential = await adapter.execute_authorization(request=request, decision=decision)

    assert credential.provider == "simulated"
    assert credential.authorization_id == decision.decision_id
    assert credential.merchant == request.merchant
    assert credential.amount_minor == request.amount_minor


@pytest.mark.asyncio
async def test_simulated_adapter_contract_rejects_unapproved_authorizations() -> None:
    request, decision = _approved_request_and_decision()
    decision.verdict = FacilityDecision.STEP_UP_REQUIRED
    adapter = SimulatedFacilityAdapter()

    with pytest.raises(ValueError, match="facility_authorization_not_approved"):
        await adapter.execute_authorization(request=request, decision=decision)


@pytest.mark.asyncio
async def test_simulated_adapter_contract_revokes_authorization() -> None:
    request, decision = _approved_request_and_decision()
    adapter = SimulatedFacilityAdapter()
    credential = await adapter.execute_authorization(request=request, decision=decision)

    revoked = await adapter.revoke_authorization(decision.decision_id, "operator revoked")

    assert revoked is True
    assert credential.status == "revoked"


def test_simulated_adapter_declares_required_capabilities() -> None:
    capabilities = SimulatedFacilityAdapter.capabilities

    assert capabilities.contract_version == "facility_adapter_v1"
    assert capabilities.supports_execute is True
    assert capabilities.supports_revoke is True
    assert capabilities.supports_merchant_lock is True
    assert capabilities.supports_amount_limit is True


@pytest.mark.asyncio
async def test_mock_provider_adapter_passes_pre_provider_contract() -> None:
    request, decision = _approved_request_and_decision()
    adapter = MockProviderFacilityAdapter()

    credential = await adapter.execute_authorization(request=request, decision=decision)
    revoked = await adapter.revoke_authorization(decision.decision_id, "operator revoked")

    assert adapter.capabilities.provider == "mock_provider"
    assert adapter.capabilities.supports_webhooks is True
    assert credential.provider == "mock_provider"
    assert credential.last4 == "1111"
    assert revoked is True
    assert credential.status == "revoked"


@pytest.mark.asyncio
async def test_disabled_provider_adapter_skeleton_cannot_execute_or_revoke() -> None:
    request, decision = _approved_request_and_decision()
    adapter = DisabledProviderFacilityAdapter(provider="candidate")

    assert adapter.capabilities.provider == "candidate"
    assert adapter.capabilities.supports_webhooks is True
    with pytest.raises(RuntimeError, match="facility_provider_adapter_disabled"):
        await adapter.execute_authorization(request=request, decision=decision)
    with pytest.raises(RuntimeError, match="facility_provider_adapter_disabled"):
        await adapter.revoke_authorization(decision.decision_id, "operator revoked")
