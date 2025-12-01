"""Agent API routes."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status

from sardis_core.api.schemas import (
    CreateAgentRequest,
    AgentResponse,
    AgentWithWalletResponse,
    WalletResponse,
    VirtualCardResponse,
    AgentInstructionRequest,
    AgentInstructionResponse,
)
from sardis_core.services import WalletService, AgentService
from sardis_core.api.dependencies import get_wallet_service, get_agent_service

from sardis_core.api.auth import get_api_key

router = APIRouter(
    prefix="/agents", 
    tags=["Agents"],
    dependencies=[Depends(get_api_key)]
)


def wallet_to_response(wallet) -> WalletResponse:
    """Convert wallet model to response schema."""
    virtual_card = None
    if wallet.virtual_card:
        virtual_card = VirtualCardResponse(
            card_id=wallet.virtual_card.card_id,
            masked_number=wallet.virtual_card.masked_number,
            is_active=wallet.virtual_card.is_active
        )
    
    return WalletResponse(
        wallet_id=wallet.wallet_id,
        agent_id=wallet.agent_id,
        balance=str(wallet.balance),
        currency=wallet.currency,
        limit_per_tx=str(wallet.limit_per_tx),
        limit_total=str(wallet.limit_total),
        spent_total=str(wallet.spent_total),
        remaining_limit=str(wallet.remaining_limit()),
        virtual_card=virtual_card,
        is_active=wallet.is_active,
        created_at=wallet.created_at
    )


def agent_to_response(agent) -> AgentResponse:
    """Convert agent model to response schema."""
    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        owner_id=agent.owner_id,
        description=agent.description,
        wallet_id=agent.wallet_id,
        is_active=agent.is_active,
        created_at=agent.created_at
    )


@router.post(
    "",
    response_model=AgentWithWalletResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new agent",
    description="Create a new agent and its associated wallet with spending limits."
)
async def create_agent(
    request: CreateAgentRequest,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> AgentWithWalletResponse:
    """Register a new agent with Sardis."""
    try:
        agent, wallet = await wallet_service.register_agent(
            name=request.name,
            owner_id=request.owner_id,
            initial_balance=request.initial_balance,
            limit_per_tx=request.limit_per_tx,
            limit_total=request.limit_total,
            description=request.description
        )
        
        return AgentWithWalletResponse(
            agent=agent_to_response(agent),
            wallet=wallet_to_response(wallet)
        )
    except ValueError as e:
        print(f"ValueError creating agent: {e}")  # Debug logging
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        print(f"Unexpected error creating agent: {type(e).__name__}: {e}")  # Debug logging
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "",
    response_model=list[AgentResponse],
    summary="List agents",
    description="List all registered agents, optionally filtered by owner."
)
async def list_agents(
    owner_id: Optional[str] = None,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> list[AgentResponse]:
    """List registered agents."""
    # Get agents directly from the ledger (database) instead of in-memory cache
    agents = await wallet_service._ledger.list_agents(owner_id=owner_id)
    return [agent_to_response(a) for a in agents]


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID",
    description="Retrieve details of a specific agent."
)
async def get_agent(
    agent_id: str,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> AgentResponse:
    """Get agent details."""
    agent = wallet_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found"
        )
    return agent_to_response(agent)


@router.get(
    "/{agent_id}/wallet",
    response_model=WalletResponse,
    summary="Get agent wallet",
    description="Retrieve the wallet details for an agent including balance and limits."
)
async def get_agent_wallet(
    agent_id: str,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> WalletResponse:
    """Get agent's wallet details."""
    wallet = await wallet_service.get_agent_wallet(agent_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet not found for agent {agent_id}"
        )
    return wallet_to_response(wallet)


@router.post(
    "/{agent_id}/instruct",
    response_model=AgentInstructionResponse,
    summary="Instruct agent",
    description="Send a natural language instruction to the agent."
)
async def instruct_agent(
    agent_id: str,
    request: AgentInstructionRequest,
    agent_service: AgentService = Depends(get_agent_service)
) -> AgentInstructionResponse:
    """Process natural language instruction."""
    result = await agent_service.process_instruction(agent_id, request.instruction)
    
    if "error" in result:
        # If it's a user error (e.g. insufficient funds), we might want 400
        # But for now, let's return 200 with error field to let client handle it
        return AgentInstructionResponse(error=result["error"])
        
    return AgentInstructionResponse(
        response=result.get("response"),
        tool_call=result.get("tool_call"),
        tx_id=result.get("tx_id")
    )
