"""FIDES Identity & Trust API — DID linking, trust scores, policy history."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal
from sardis_v2_core import Agent, AgentRepository
from sardis_v2_core.did_bridge import DIDBridge, DIDRegistrationError
from sardis_v2_core.fides_trust_adapter import FidesTrustGraphAdapter
from sardis_v2_core.agit_policy_engine import AgitPolicyEngine
from sardis_v2_core.kya_trust_scoring import KYALevel, TrustScorer
from sardis_v2_core.config import load_settings

logger = logging.getLogger("sardis.api.fides_identity")

router = APIRouter(tags=["fides-identity"])

# Module-level singletons (lazily initialized)
_did_bridge: DIDBridge | None = None
_fides_adapter: FidesTrustGraphAdapter | None = None
_agit_engine: AgitPolicyEngine | None = None
_trust_scorer: TrustScorer | None = None


def _get_did_bridge() -> DIDBridge:
    global _did_bridge
    if _did_bridge is None:
        _did_bridge = DIDBridge()
    return _did_bridge


def _get_fides_adapter() -> FidesTrustGraphAdapter:
    global _fides_adapter
    if _fides_adapter is None:
        settings = load_settings()
        _fides_adapter = FidesTrustGraphAdapter(
            trust_url=settings.fides.trust_url,
            timeout_seconds=settings.fides.request_timeout_seconds,
        )
    return _fides_adapter


def _get_agit_engine() -> AgitPolicyEngine:
    global _agit_engine
    if _agit_engine is None:
        _agit_engine = AgitPolicyEngine()
    return _agit_engine


def _get_trust_scorer() -> TrustScorer:
    global _trust_scorer
    if _trust_scorer is None:
        settings = load_settings()
        adapter = _get_fides_adapter()
        _trust_scorer = TrustScorer(
            trust_graph=adapter,
            platform_did=settings.fides.platform_did,
        )
    return _trust_scorer


def get_agent_repo() -> AgentRepository | None:
    """Optional repository dependency for ownership checks and DID persistence."""
    return None


async def _require_agent_access(
    agent_id: str,
    principal: Principal,
    agent_repo: AgentRepository | None,
) -> Agent | None:
    if agent_repo is None:
        return None

    agent = await agent_repo.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    if not principal.is_admin and agent.owner_id != principal.organization_id:
        raise HTTPException(status_code=403, detail="Access denied")
    return agent


def _metadata_for_agent(agent: Agent | None) -> dict[str, Any]:
    if agent is None or not isinstance(agent.metadata, dict):
        return {}
    return dict(agent.metadata)


def _linked_fides_did(agent: Agent | None) -> str | None:
    if agent is None:
        return None
    if agent.fides_did:
        return agent.fides_did
    metadata = _metadata_for_agent(agent)
    identity_meta = metadata.get("fides_identity")
    if isinstance(identity_meta, dict):
        did_value = identity_meta.get("fides_did")
        if isinstance(did_value, str) and did_value:
            return did_value
    return None


# ============ Request/Response Models ============


class RegisterFidesDIDRequest(BaseModel):
    """Link a FIDES DID to a Sardis agent."""
    fides_did: str = Field(..., description="FIDES DID (did:fides:<base58-pubkey>)")
    signature: str = Field(..., description="Hex-encoded Ed25519 signature over agent_id")
    public_key: str = Field(..., description="Hex-encoded Ed25519 public key")


class TrustAttestationRequest(BaseModel):
    """Issue a trust attestation to the FIDES network."""
    target_did: str = Field(..., description="DID of the agent to attest trust for")
    trust_level: int = Field(default=50, ge=0, le=100, description="Trust level 0-100")
    signature: str = Field(..., description="Hex-encoded signature")
    payload: dict[str, Any] = Field(default_factory=dict)


# ============ DID Registration ============


@router.post("/agents/{agent_id}/fides/register")
async def register_fides_did(
    agent_id: str,
    req: RegisterFidesDIDRequest,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Link a FIDES DID to a Sardis agent with Ed25519 ownership proof."""
    existing_agent = await _require_agent_access(agent_id, principal, agent_repo)
    bridge = _get_did_bridge()

    try:
        mapping = bridge.register_fides_did(
            agent_id=agent_id,
            fides_did=req.fides_did,
            signature=req.signature,
            public_key=req.public_key,
        )
    except DIDRegistrationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if agent_repo is not None and existing_agent is not None:
        merged_metadata = _metadata_for_agent(existing_agent)
        merged_metadata["fides_identity"] = {
            "fides_did": mapping.fides_did,
            "public_key_hex": mapping.public_key_hex,
            "verified_at": mapping.verified_at.isoformat() if mapping.verified_at else None,
        }
        await agent_repo.update(
            agent_id=agent_id,
            fides_did=mapping.fides_did,
            metadata=merged_metadata,
        )

    return {
        "agent_id": mapping.agent_id,
        "fides_did": mapping.fides_did,
        "verified_at": mapping.verified_at.isoformat() if mapping.verified_at else None,
    }


@router.get("/agents/{agent_id}/fides/identity")
async def get_fides_identity(
    agent_id: str,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Get the linked FIDES identity for an agent."""
    agent = await _require_agent_access(agent_id, principal, agent_repo)
    bridge = _get_did_bridge()
    mapping = bridge.get_mapping(agent_id)

    if mapping is None:
        metadata = _metadata_for_agent(agent)
        identity_meta = metadata.get("fides_identity") if metadata else None
        public_key_hex = identity_meta.get("public_key_hex") if isinstance(identity_meta, dict) else None
        return {
            "agent_id": agent_id,
            "fides_did": _linked_fides_did(agent),
            "verified_at": identity_meta.get("verified_at") if isinstance(identity_meta, dict) else None,
            "public_key_hex": public_key_hex,
        }

    return {
        "agent_id": mapping.agent_id,
        "fides_did": mapping.fides_did,
        "verified_at": mapping.verified_at.isoformat() if mapping.verified_at else None,
        "public_key_hex": mapping.public_key_hex,
    }


# ============ Trust Score ============


@router.get("/agents/{agent_id}/trust-score")
async def get_trust_score(
    agent_id: str,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Get current trust score for an agent (calls TrustScorer with FIDES adapter)."""
    scorer = _get_trust_scorer()
    bridge = _get_did_bridge()
    agent = await _require_agent_access(agent_id, principal, agent_repo)

    fides_did = bridge.resolve_to_fides(agent_id) or _linked_fides_did(agent)
    try:
        kya_level = KYALevel((agent.kya_level if agent is not None else KYALevel.NONE.value).lower())
    except ValueError:
        kya_level = KYALevel.NONE

    score = await scorer.calculate_trust(
        agent_id=agent_id,
        agent_did=fides_did,
        kya_level=kya_level,
        use_cache=True,
    )

    return score.to_dict()


@router.get("/agents/{agent_id}/trust-path/{target_did:path}")
async def get_trust_path(
    agent_id: str,
    target_did: str,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Find trust path from agent to target DID via FIDES network."""
    agent = await _require_agent_access(agent_id, principal, agent_repo)
    bridge = _get_did_bridge()
    adapter = _get_fides_adapter()

    agent_fides_did = bridge.resolve_to_fides(agent_id) or _linked_fides_did(agent)
    if not agent_fides_did:
        raise HTTPException(
            status_code=404,
            detail=f"Agent {agent_id} has no linked FIDES DID",
        )

    path_result = await adapter.find_path(agent_fides_did, target_did)

    return {
        "from_did": path_result.from_did,
        "to_did": path_result.to_did,
        "found": path_result.found,
        "hops": path_result.hops,
        "cumulative_trust": round(path_result.cumulative_trust, 4),
        "reason": path_result.reason,
        "path": [
            {"did": node.did, "trust_level": node.trust_level}
            for node in path_result.path
        ],
    }


# ============ Trust Attestation ============


@router.post("/agents/{agent_id}/trust/attest")
async def issue_trust_attestation(
    agent_id: str,
    req: TrustAttestationRequest,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Issue a trust attestation to the FIDES network."""
    agent = await _require_agent_access(agent_id, principal, agent_repo)
    bridge = _get_did_bridge()
    adapter = _get_fides_adapter()

    issuer_did = bridge.resolve_to_fides(agent_id) or _linked_fides_did(agent)
    if not issuer_did:
        raise HTTPException(
            status_code=400,
            detail=f"Agent {agent_id} must register a FIDES DID first",
        )

    result = await adapter.submit_attestation(
        issuer_did=issuer_did,
        subject_did=req.target_did,
        trust_level=req.trust_level,
        signature=req.signature,
        payload=req.payload,
    )

    if not result.success:
        raise HTTPException(status_code=502, detail=result.error or "Attestation failed")

    return {
        "success": True,
        "attestation_id": result.attestation_id,
        "issuer_did": issuer_did,
        "subject_did": req.target_did,
        "trust_level": req.trust_level,
    }


# ============ Policy History (AGIT) ============


@router.get("/agents/{agent_id}/policy-history")
async def get_policy_history(
    agent_id: str,
    limit: int = 20,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Get AGIT-signed policy commit log for an agent."""
    await _require_agent_access(agent_id, principal, agent_repo)
    engine = _get_agit_engine()
    commits = engine.get_chain_history(agent_id, limit=min(limit, 100))

    return {
        "agent_id": agent_id,
        "commits": commits,
        "count": len(commits),
    }


@router.get("/agents/{agent_id}/policy-history/{commit_hash}")
async def get_policy_at_commit(
    agent_id: str,
    commit_hash: str,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Get policy snapshot at a specific AGIT commit."""
    await _require_agent_access(agent_id, principal, agent_repo)
    engine = _get_agit_engine()
    history = engine.get_chain_history(agent_id, limit=1000)
    if not any(entry.get("commit_hash") == commit_hash for entry in history):
        raise HTTPException(status_code=404, detail="Commit not found")
    policy = engine.get_policy_at(commit_hash)

    if policy is None:
        raise HTTPException(status_code=404, detail="Commit not found")

    return {
        "agent_id": agent_id,
        "commit_hash": commit_hash,
        "policy": policy,
    }


@router.post("/agents/{agent_id}/policy-history/verify")
async def verify_policy_chain(
    agent_id: str,
    principal: Principal = Depends(require_principal),
    agent_repo: AgentRepository | None = Depends(get_agent_repo),
) -> dict[str, Any]:
    """Verify integrity of the AGIT policy hash chain."""
    await _require_agent_access(agent_id, principal, agent_repo)
    engine = _get_agit_engine()
    verification = engine.verify_policy_chain(agent_id)

    return {
        "agent_id": agent_id,
        "valid": verification.valid,
        "chain_length": verification.chain_length,
        "broken_at": verification.broken_at,
        "error": verification.error,
    }
