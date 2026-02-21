"""Trust Infrastructure API routes."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sardis_v2_core.kya_trust_scoring import (
    TrustScorer,
    KYALevel,
    TransactionRecord,
    ComplianceRecord,
    ReputationRecord,
    BehavioralRecord,
)
from sardis_v2_core.trust_infrastructure import (
    TrustFramework,
    AttestationType,
)
from sardis_v2_core.multi_agent_payments import (
    PaymentOrchestrator,
    PaymentFlowType,
)

router = APIRouter(prefix="/v2/trust", tags=["trust"])

# Singletons
_framework = TrustFramework()
_orchestrator = PaymentOrchestrator()


# ============ Request/Response Models ============


class RegisterAgentRequest(BaseModel):
    agent_id: str
    owner_id: str
    kya_level: str = "none"
    capabilities: List[str] = Field(default_factory=list)


class TrustEvaluationRequest(BaseModel):
    requester: str
    counterparty: str
    amount: str
    operation: str = "payment"


class AttestationRequest(BaseModel):
    agent_id: str
    attestation_type: str
    issuer_id: str
    claim: Dict[str, Any]
    ttl_days: int = 365


class SplitPaymentRequest(BaseModel):
    payer_id: str
    recipients: List[Dict[str, str]]  # [{"id": "agent_x", "share": "0.5"}]
    total_amount: str
    token: str = "USDC"
    chain: str = "base"
    description: Optional[str] = None


class GroupPaymentRequest(BaseModel):
    payers: List[Dict[str, str]]  # [{"id": "agent_x", "amount": "100"}]
    recipient_id: str
    token: str = "USDC"
    chain: str = "base"
    description: Optional[str] = None


class CascadePaymentRequest(BaseModel):
    steps: List[Dict[str, Any]]
    token: str = "USDC"
    chain: str = "base"
    description: Optional[str] = None


# ============ Trust Score Routes ============


@router.post("/agents/register")
async def register_agent(req: RegisterAgentRequest) -> Dict[str, Any]:
    """Register an agent with a trust profile."""
    profile = await _framework.register_agent(
        agent_id=req.agent_id,
        owner_id=req.owner_id,
        kya_level=KYALevel(req.kya_level),
        capabilities=req.capabilities,
    )
    return profile.to_dict()


@router.get("/agents/{agent_id}")
async def get_agent_profile(agent_id: str) -> Dict[str, Any]:
    """Get an agent's trust profile."""
    profile = await _framework.get_profile(agent_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Agent not found")
    return profile.to_dict()


@router.post("/agents/{agent_id}/kya-level")
async def update_kya_level(agent_id: str, level: str) -> Dict[str, Any]:
    """Update an agent's KYA verification level."""
    try:
        profile = await _framework.update_kya_level(agent_id, KYALevel(level))
        return profile.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/evaluate")
async def evaluate_trust(req: TrustEvaluationRequest) -> Dict[str, Any]:
    """Evaluate trust between two agents for a transaction."""
    evaluation = await _framework.evaluate_trust(
        requester=req.requester,
        counterparty=req.counterparty,
        amount=Decimal(req.amount),
        operation=req.operation,
    )
    return evaluation.to_dict()


@router.get("/agents/{agent_id}/score")
async def get_trust_score(agent_id: str) -> Dict[str, Any]:
    """Get an agent's current trust score with breakdown."""
    profile = await _framework.get_profile(agent_id)
    if not profile or not profile.trust_score:
        raise HTTPException(status_code=404, detail="Agent not found")
    return profile.trust_score.to_dict()


@router.get("/agents/{agent_id}/network")
async def get_trust_network(agent_id: str, depth: int = 1) -> Dict[str, Any]:
    """Get the trust network around an agent."""
    return await _framework.get_trust_network(agent_id, depth=min(depth, 3))


# ============ Attestation Routes ============


@router.post("/attestations")
async def issue_attestation(req: AttestationRequest) -> Dict[str, Any]:
    """Issue a trust attestation for an agent."""
    try:
        attestation = await _framework.issue_attestation(
            agent_id=req.agent_id,
            attestation_type=AttestationType(req.attestation_type),
            issuer_id=req.issuer_id,
            claim=req.claim,
            ttl_days=req.ttl_days,
        )
        return attestation.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/attestations/{attestation_id}/verify")
async def verify_attestation(attestation_id: str) -> Dict[str, Any]:
    """Verify an attestation's validity."""
    return await _framework.verify_attestation(attestation_id)


@router.delete("/attestations/{attestation_id}")
async def revoke_attestation(attestation_id: str) -> Dict[str, Any]:
    """Revoke an attestation."""
    success = await _framework.revoke_attestation(attestation_id)
    if not success:
        raise HTTPException(status_code=404, detail="Attestation not found")
    return {"revoked": True, "attestation_id": attestation_id}


@router.get("/agents/{agent_id}/attestations")
async def get_agent_attestations(
    agent_id: str,
    attestation_type: Optional[str] = None,
    valid_only: bool = True,
) -> Dict[str, Any]:
    """Get attestations for an agent."""
    att_type = AttestationType(attestation_type) if attestation_type else None
    attestations = await _framework.get_attestations(
        agent_id, attestation_type=att_type, valid_only=valid_only
    )
    return {
        "agent_id": agent_id,
        "attestations": [a.to_dict() for a in attestations],
        "count": len(attestations),
    }


# ============ Multi-Agent Payment Routes ============


@router.post("/payments/split")
async def create_split_payment(req: SplitPaymentRequest) -> Dict[str, Any]:
    """Create a split payment from one payer to multiple recipients."""
    recipients = [
        (r["id"], Decimal(r["share"]))
        for r in req.recipients
    ]
    flow = await _orchestrator.create_split_payment(
        payer_id=req.payer_id,
        recipients=recipients,
        total_amount=Decimal(req.total_amount),
        token=req.token,
        chain=req.chain,
        description=req.description,
    )
    return flow.to_dict()


@router.post("/payments/group")
async def create_group_payment(req: GroupPaymentRequest) -> Dict[str, Any]:
    """Create a group payment from multiple payers to one recipient."""
    payers = [
        (p["id"], Decimal(p["amount"]))
        for p in req.payers
    ]
    flow = await _orchestrator.create_group_payment(
        payers=payers,
        recipient_id=req.recipient_id,
        token=req.token,
        chain=req.chain,
        description=req.description,
    )
    return flow.to_dict()


@router.post("/payments/cascade")
async def create_cascade_payment(req: CascadePaymentRequest) -> Dict[str, Any]:
    """Create a cascading payment chain."""
    flow = await _orchestrator.create_cascade_payment(
        steps=req.steps,
        token=req.token,
        chain=req.chain,
        description=req.description,
    )
    return flow.to_dict()


@router.post("/payments/{flow_id}/execute")
async def execute_payment_flow(flow_id: str) -> Dict[str, Any]:
    """Execute a payment flow."""
    try:
        flow = await _orchestrator.execute_flow(flow_id)
        return flow.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments/{flow_id}")
async def get_payment_flow(flow_id: str) -> Dict[str, Any]:
    """Get payment flow status."""
    flow = await _orchestrator.get_flow(flow_id)
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return flow.to_dict()


@router.post("/payments/{flow_id}/cancel")
async def cancel_payment_flow(flow_id: str, reason: str = "") -> Dict[str, Any]:
    """Cancel a payment flow."""
    try:
        flow = await _orchestrator.cancel_flow(flow_id, reason)
        return flow.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/payments")
async def list_payment_flows(
    agent_id: Optional[str] = None,
    flow_type: Optional[str] = None,
    state: Optional[str] = None,
) -> Dict[str, Any]:
    """List payment flows with optional filters."""
    ft = PaymentFlowType(flow_type) if flow_type else None
    flows = await _orchestrator.list_flows(agent_id=agent_id, flow_type=ft)
    return {
        "flows": [f.to_dict() for f in flows],
        "count": len(flows),
    }


# ============ Stats ============


@router.get("/stats")
async def get_trust_stats() -> Dict[str, Any]:
    """Get trust infrastructure statistics."""
    return await _framework.get_stats()
