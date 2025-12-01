"""Risk and authorization API routes."""

from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from sardis_core.services import get_risk_service, RiskService
from sardis_core.services.wallet_service import WalletService
from sardis_core.api.dependencies import get_wallet_service


from sardis_core.api.auth import get_api_key

router = APIRouter(
    prefix="/risk", 
    tags=["Risk"],
    dependencies=[Depends(get_api_key)]
)


# ========== Schemas ==========

class RiskScoreResponse(BaseModel):
    """Risk assessment response."""
    score: float
    level: str
    factors: list[str]
    details: dict
    is_acceptable: bool


class AuthorizeServiceRequest(BaseModel):
    """Request to authorize a service."""
    service_id: str = Field(..., description="The service/merchant ID to authorize")


class AuthorizedServicesResponse(BaseModel):
    """List of authorized services."""
    agent_id: str
    services: list[str]


class RiskProfileResponse(BaseModel):
    """Agent risk profile response."""
    agent_id: str
    current_score: float
    current_level: str
    total_transactions: int
    failed_transactions: int
    total_volume: str
    is_flagged: bool
    flag_reason: Optional[str]
    authorized_services: list[str]


class FlagAgentRequest(BaseModel):
    """Request to flag an agent."""
    reason: str = Field(..., min_length=1, max_length=500)


# ========== Dependencies ==========

def get_service() -> RiskService:
    """Get the risk service."""
    return get_risk_service()


# ========== Routes ==========

@router.get(
    "/agents/{agent_id}/score",
    response_model=RiskScoreResponse,
    summary="Get agent risk score",
    description="Get the current risk assessment for an agent."
)
async def get_agent_risk_score(
    agent_id: str,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> RiskScoreResponse:
    """Get risk score for an agent."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    score = risk_service.assess_agent(agent_id)
    
    return RiskScoreResponse(
        score=score.score,
        level=score.level.value,
        factors=[f.value for f in score.factors],
        details=score.details,
        is_acceptable=score.is_acceptable()
    )


@router.get(
    "/agents/{agent_id}/profile",
    response_model=RiskProfileResponse,
    summary="Get agent risk profile",
    description="Get the full risk profile for an agent including transaction history."
)
async def get_agent_risk_profile(
    agent_id: str,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> RiskProfileResponse:
    """Get full risk profile for an agent."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    profile = risk_service.get_or_create_profile(agent_id)
    
    return RiskProfileResponse(
        agent_id=profile.agent_id,
        current_score=profile.current_score,
        current_level=profile.current_level.value,
        total_transactions=profile.total_transactions,
        failed_transactions=profile.failed_transactions,
        total_volume=str(profile.total_volume),
        is_flagged=profile.is_flagged,
        flag_reason=profile.flag_reason,
        authorized_services=profile.authorized_services
    )


@router.post(
    "/agents/{agent_id}/authorize",
    response_model=AuthorizedServicesResponse,
    summary="Authorize a service",
    description="Authorize a service/merchant for an agent. Payments to authorized services have lower risk scores."
)
async def authorize_service(
    agent_id: str,
    request: AuthorizeServiceRequest,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> AuthorizedServicesResponse:
    """Authorize a service for an agent."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    risk_service.authorize_service(agent_id, request.service_id)
    services = risk_service.list_authorized_services(agent_id)
    
    return AuthorizedServicesResponse(
        agent_id=agent_id,
        services=services
    )


@router.delete(
    "/agents/{agent_id}/authorize/{service_id}",
    response_model=AuthorizedServicesResponse,
    summary="Revoke service authorization",
    description="Revoke a service authorization for an agent."
)
async def revoke_service(
    agent_id: str,
    service_id: str,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> AuthorizedServicesResponse:
    """Revoke a service authorization."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    risk_service.revoke_service(agent_id, service_id)
    services = risk_service.list_authorized_services(agent_id)
    
    return AuthorizedServicesResponse(
        agent_id=agent_id,
        services=services
    )


@router.get(
    "/agents/{agent_id}/authorized-services",
    response_model=AuthorizedServicesResponse,
    summary="List authorized services",
    description="Get the list of services authorized for an agent."
)
async def list_authorized_services(
    agent_id: str,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> AuthorizedServicesResponse:
    """List authorized services for an agent."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    services = risk_service.list_authorized_services(agent_id)
    
    return AuthorizedServicesResponse(
        agent_id=agent_id,
        services=services
    )


@router.post(
    "/agents/{agent_id}/flag",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Flag an agent",
    description="Flag an agent for review. Flagged agents cannot make transactions."
)
async def flag_agent(
    agent_id: str,
    request: FlagAgentRequest,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Flag an agent for review."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    risk_service.flag_agent(agent_id, request.reason)


@router.delete(
    "/agents/{agent_id}/flag",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unflag an agent",
    description="Remove the flag from an agent, allowing transactions again."
)
async def unflag_agent(
    agent_id: str,
    risk_service: RiskService = Depends(get_service),
    wallet_service: WalletService = Depends(get_wallet_service)
):
    """Remove flag from an agent."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    
    risk_service.unflag_agent(agent_id)

