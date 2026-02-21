"""
Budget Allocation API Routes.

FastAPI routes for managing automated budget allocation cycles and agent budgets.
"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sardis_v2_core.budget_allocator import (
    AllocationStrategy,
    BudgetAllocator,
    BudgetAllocation,
    BudgetCycle,
    BudgetPeriod,
    CycleStatus,
)

router = APIRouter(prefix="/api/v2/budgets", tags=["budgets"])

# Global allocator instance (in production, use dependency injection)
_allocator = BudgetAllocator()


# Request/Response Models


class AgentConfig(BaseModel):
    """Agent configuration for budget allocation."""

    id: str = Field(..., description="Agent identifier")
    name: str | None = Field(None, description="Agent name")
    weight: Decimal | None = Field(None, description="Weight for proportional allocation", ge=0)
    fixed_amount: Decimal | None = Field(None, description="Fixed amount for fixed allocation", ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HistoryRecord(BaseModel):
    """Historical spending/performance record."""

    agent_id: str = Field(..., description="Agent identifier")
    spent: Decimal = Field(..., description="Amount spent", ge=0)
    allocated: Decimal | None = Field(None, description="Amount allocated", ge=0)
    value_generated: Decimal | None = Field(None, description="Value generated (for ROI)", ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateCycleRequest(BaseModel):
    """Request to create a new budget cycle."""

    org_id: str = Field(..., description="Organization identifier")
    period: BudgetPeriod = Field(..., description="Budget period type")
    total_budget: Decimal = Field(..., description="Total budget for the cycle", gt=0)
    currency: str = Field(..., description="Currency code (e.g., USDC)", min_length=3, max_length=10)
    strategy: AllocationStrategy = Field(..., description="Allocation strategy to use")
    agent_configs: list[AgentConfig] = Field(..., description="Agent configurations", min_length=1)
    start_date: datetime | None = Field(None, description="Optional start date (defaults to now)")
    history: list[HistoryRecord] | None = Field(None, description="Historical data for performance allocation")


class BudgetAllocationResponse(BaseModel):
    """Budget allocation response."""

    id: str
    agent_id: str
    amount: str
    currency: str
    period: BudgetPeriod
    strategy: AllocationStrategy
    allocated_at: datetime
    expires_at: datetime
    cycle_id: str
    notes: str | None = None
    metadata: dict[str, Any]

    @classmethod
    def from_allocation(cls, allocation: BudgetAllocation) -> "BudgetAllocationResponse":
        """Convert BudgetAllocation to response model."""
        return cls(
            id=str(allocation.id),
            agent_id=allocation.agent_id,
            amount=str(allocation.amount),
            currency=allocation.currency,
            period=allocation.period,
            strategy=allocation.strategy,
            allocated_at=allocation.allocated_at,
            expires_at=allocation.expires_at,
            cycle_id=str(allocation.cycle_id),
            notes=allocation.notes,
            metadata=allocation.metadata,
        )


class BudgetCycleResponse(BaseModel):
    """Budget cycle response."""

    id: str
    org_id: str
    period: BudgetPeriod
    start_date: datetime
    end_date: datetime
    total_budget: str
    currency: str
    strategy: AllocationStrategy
    allocations: list[BudgetAllocationResponse]
    status: CycleStatus
    created_at: datetime
    closed_at: datetime | None = None
    rollover_from: str | None = None
    rollover_amount: str
    allocated_total: str
    unallocated_amount: str
    metadata: dict[str, Any]

    @classmethod
    def from_cycle(cls, cycle: BudgetCycle) -> "BudgetCycleResponse":
        """Convert BudgetCycle to response model."""
        return cls(
            id=str(cycle.id),
            org_id=cycle.org_id,
            period=cycle.period,
            start_date=cycle.start_date,
            end_date=cycle.end_date,
            total_budget=str(cycle.total_budget),
            currency=cycle.currency,
            strategy=cycle.strategy,
            allocations=[BudgetAllocationResponse.from_allocation(a) for a in cycle.allocations],
            status=cycle.status,
            created_at=cycle.created_at,
            closed_at=cycle.closed_at,
            rollover_from=str(cycle.rollover_from) if cycle.rollover_from else None,
            rollover_amount=str(cycle.rollover_amount),
            allocated_total=str(cycle.allocated_total),
            unallocated_amount=str(cycle.unallocated_amount),
            metadata=cycle.metadata,
        )


class CloseCycleRequest(BaseModel):
    """Request to close a budget cycle."""

    spending_data: list[HistoryRecord] = Field(
        default_factory=list, description="Actual spending data per agent"
    )


class AdjustAllocationRequest(BaseModel):
    """Request to adjust an agent's budget allocation."""

    cycle_id: str = Field(..., description="Cycle identifier")
    new_amount: Decimal = Field(..., description="New allocation amount", gt=0)
    reason: str = Field(..., description="Reason for adjustment", min_length=1)


class BudgetUtilizationResponse(BaseModel):
    """Budget utilization response."""

    agent_id: str
    cycle_id: str
    allocated: str
    spent: str
    remaining: str
    utilization_pct: str
    currency: str
    expires_at: datetime


class RolloverRequest(BaseModel):
    """Request to trigger automatic rollover."""

    org_id: str = Field(..., description="Organization identifier")
    new_total_budget: Decimal = Field(..., description="Fresh budget for new cycle", gt=0)
    currency: str = Field(..., description="Currency code", min_length=3, max_length=10)
    agent_configs: list[AgentConfig] = Field(..., description="Agent configurations", min_length=1)
    spending_data: list[HistoryRecord] = Field(..., description="Spending data from current cycle")


class StrategyInfo(BaseModel):
    """Allocation strategy information."""

    name: str
    description: str


# API Routes


@router.post("/cycles", response_model=BudgetCycleResponse, status_code=status.HTTP_201_CREATED)
async def create_budget_cycle(request: CreateCycleRequest) -> BudgetCycleResponse:
    """
    Create a new budget allocation cycle.

    Allocates budget to agents based on the specified strategy and configuration.
    """
    try:
        # Convert agent configs to dicts
        agent_dicts = [
            {
                "id": config.id,
                "name": config.name,
                "weight": config.weight,
                "fixed_amount": config.fixed_amount,
                **config.metadata,
            }
            for config in request.agent_configs
        ]

        # Convert history if provided
        history_dicts = None
        if request.history:
            history_dicts = [
                {
                    "agent_id": rec.agent_id,
                    "spent": rec.spent,
                    "allocated": rec.allocated,
                    "value_generated": rec.value_generated,
                    **rec.metadata,
                }
                for rec in request.history
            ]

        cycle = _allocator.create_cycle(
            org_id=request.org_id,
            period=request.period,
            total_budget=request.total_budget,
            currency=request.currency,
            strategy=request.strategy,
            agent_configs=agent_dicts,
            start_date=request.start_date,
            history=history_dicts,
        )

        return BudgetCycleResponse.from_cycle(cycle)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cycles/current", response_model=BudgetCycleResponse | None)
async def get_current_cycle(org_id: str) -> BudgetCycleResponse | None:
    """
    Get the current active budget cycle for an organization.

    Returns None if no active cycle exists.
    """
    try:
        cycle = _allocator.get_current_cycle(org_id)
        if not cycle:
            return None
        return BudgetCycleResponse.from_cycle(cycle)

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/cycles/{cycle_id}", response_model=BudgetCycleResponse)
async def get_cycle(cycle_id: UUID) -> BudgetCycleResponse:
    """Get detailed information about a specific budget cycle."""
    try:
        cycle = _allocator.get_cycle(cycle_id)
        if not cycle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Cycle not found: {cycle_id}"
            )

        return BudgetCycleResponse.from_cycle(cycle)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/cycles/{cycle_id}/close", response_model=BudgetCycleResponse)
async def close_cycle(cycle_id: UUID, request: CloseCycleRequest) -> BudgetCycleResponse:
    """
    Close a budget cycle and calculate rollover amounts.

    Requires actual spending data to calculate unused budget.
    """
    try:
        # Convert spending data
        spending_dicts = None
        if request.spending_data:
            spending_dicts = [
                {
                    "agent_id": rec.agent_id,
                    "spent": rec.spent,
                    "allocated": rec.allocated,
                    **rec.metadata,
                }
                for rec in request.spending_data
            ]

        cycle = _allocator.close_cycle(cycle_id, spending_dicts)
        return BudgetCycleResponse.from_cycle(cycle)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents/{agent_id}", response_model=BudgetAllocationResponse)
async def get_agent_budget(agent_id: str, cycle_id: UUID | None = None) -> BudgetAllocationResponse:
    """
    Get budget allocation for a specific agent.

    If cycle_id is not provided, returns allocation from current active cycle.
    """
    try:
        allocation = _allocator.get_agent_budget(agent_id, cycle_id)
        if not allocation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No budget allocation found for agent {agent_id}",
            )

        return BudgetAllocationResponse.from_allocation(allocation)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/agents/{agent_id}/utilization", response_model=BudgetUtilizationResponse)
async def get_budget_utilization(
    agent_id: str, cycle_id: UUID, spent_amount: Decimal
) -> BudgetUtilizationResponse:
    """
    Get budget utilization metrics for an agent.

    Shows allocated amount, spent amount, remaining budget, and utilization percentage.
    """
    try:
        utilization = _allocator.get_budget_utilization(agent_id, cycle_id, spent_amount)

        return BudgetUtilizationResponse(
            agent_id=utilization["agent_id"],
            cycle_id=str(utilization["cycle_id"]),
            allocated=str(utilization["allocated"]),
            spent=str(utilization["spent"]),
            remaining=str(utilization["remaining"]),
            utilization_pct=str(utilization["utilization_pct"]),
            currency=utilization["currency"],
            expires_at=utilization["expires_at"],
        )

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/agents/{agent_id}/adjust", response_model=BudgetAllocationResponse)
async def adjust_allocation(agent_id: str, request: AdjustAllocationRequest) -> BudgetAllocationResponse:
    """
    Adjust an agent's budget allocation.

    Can only adjust allocations in active cycles. Records adjustment history.
    """
    try:
        cycle_id = UUID(request.cycle_id)
        allocation = _allocator.adjust_allocation(
            agent_id=agent_id, cycle_id=cycle_id, new_amount=request.new_amount, reason=request.reason
        )

        return BudgetAllocationResponse.from_allocation(allocation)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/rollover", response_model=BudgetCycleResponse, status_code=status.HTTP_201_CREATED)
async def auto_rollover(request: RolloverRequest) -> BudgetCycleResponse:
    """
    Automatically create a new budget cycle with rollover from current cycle.

    Closes the current cycle and creates a new one with unused budget carried over
    (subject to rollover cap).
    """
    try:
        # Convert agent configs
        agent_dicts = [
            {
                "id": config.id,
                "name": config.name,
                "weight": config.weight,
                "fixed_amount": config.fixed_amount,
                **config.metadata,
            }
            for config in request.agent_configs
        ]

        # Convert spending data
        spending_dicts = [
            {
                "agent_id": rec.agent_id,
                "spent": rec.spent,
                "allocated": rec.allocated,
                **rec.metadata,
            }
            for rec in request.spending_data
        ]

        cycle = _allocator.auto_rollover(
            org_id=request.org_id,
            new_total_budget=request.new_total_budget,
            currency=request.currency,
            agent_configs=agent_dicts,
            spending_data=spending_dicts,
        )

        return BudgetCycleResponse.from_cycle(cycle)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/strategies", response_model=list[StrategyInfo])
async def get_strategies() -> list[StrategyInfo]:
    """
    List all available budget allocation strategies.

    Returns strategy names and descriptions.
    """
    try:
        strategies = _allocator.get_available_strategies()
        return [StrategyInfo(name=s["name"], description=s["description"]) for s in strategies]

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
