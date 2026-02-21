"""Organization API endpoints for multi-tenant management."""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field

from sardis_v2_core.organizations import (
    Organization,
    Team,
    OrgMember,
    OrganizationManager,
    OrganizationPlan,
    MemberRole,
)
from sardis_v2_core.rbac import Permission, RBACEngine
from sardis_api.authz import Principal, require_principal

router = APIRouter(prefix="/api/v2/orgs", tags=["organizations"])


# ========== Request/Response Models ==========

class CreateOrganizationRequest(BaseModel):
    """Request to create a new organization."""
    name: str = Field(..., min_length=1, max_length=100)
    slug: str = Field(..., min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")
    plan: str = Field(default=OrganizationPlan.FREE)
    billing_email: Optional[str] = None
    settings: Optional[dict] = None
    metadata: Optional[dict] = None


class UpdateOrganizationRequest(BaseModel):
    """Request to update organization details."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    plan: Optional[str] = None
    billing_email: Optional[str] = None
    settings: Optional[dict] = None
    metadata: Optional[dict] = None


class OrganizationResponse(BaseModel):
    """Organization details response."""
    id: str
    name: str
    slug: str
    plan: str
    billing_email: Optional[str]
    subscription_status: Optional[str]
    settings: dict
    metadata: dict
    created_at: str
    updated_at: str

    @classmethod
    def from_org(cls, org: Organization) -> "OrganizationResponse":
        return cls(
            id=org.id,
            name=org.name,
            slug=org.slug,
            plan=org.plan,
            billing_email=org.billing_email,
            subscription_status=org.subscription_status,
            settings=org.settings,
            metadata=org.metadata,
            created_at=org.created_at.isoformat(),
            updated_at=org.updated_at.isoformat(),
        )


class CreateTeamRequest(BaseModel):
    """Request to create a new team."""
    name: str = Field(..., min_length=1, max_length=100)
    parent_team_id: Optional[str] = None
    budget_limit: Optional[Decimal] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None


class UpdateTeamRequest(BaseModel):
    """Request to update team details."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    budget_limit: Optional[Decimal] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None


class TeamResponse(BaseModel):
    """Team details response."""
    id: str
    org_id: str
    name: str
    parent_team_id: Optional[str]
    budget_limit: Optional[str]  # Returned as string to preserve precision
    description: Optional[str]
    metadata: dict
    created_at: str
    updated_at: str

    @classmethod
    def from_team(cls, team: Team) -> "TeamResponse":
        return cls(
            id=team.id,
            org_id=team.org_id,
            name=team.name,
            parent_team_id=team.parent_team_id,
            budget_limit=str(team.budget_limit) if team.budget_limit else None,
            description=team.description,
            metadata=team.metadata,
            created_at=team.created_at.isoformat(),
            updated_at=team.updated_at.isoformat(),
        )


class InviteMemberRequest(BaseModel):
    """Request to invite a member to an organization."""
    user_id: str
    role: str = Field(default=MemberRole.VIEWER)
    teams: Optional[List[str]] = None


class UpdateMemberRequest(BaseModel):
    """Request to update member role or team assignments."""
    role: Optional[str] = None
    teams: Optional[List[str]] = None


class MemberResponse(BaseModel):
    """Member details response."""
    id: str
    org_id: str
    user_id: str
    role: str
    teams: List[str]
    invited_by: Optional[str]
    invited_at: str
    joined_at: Optional[str]
    invite_accepted: bool
    metadata: dict

    @classmethod
    def from_member(cls, member: OrgMember) -> "MemberResponse":
        return cls(
            id=member.id,
            org_id=member.org_id,
            user_id=member.user_id,
            role=member.role,
            teams=member.teams,
            invited_by=member.invited_by,
            invited_at=member.invited_at.isoformat(),
            joined_at=member.joined_at.isoformat() if member.joined_at else None,
            invite_accepted=member.invite_accepted,
            metadata=member.metadata,
        )


class SpendingSummaryResponse(BaseModel):
    """Aggregated spending summary for an organization."""
    org_id: str
    total_spent: str  # As string to preserve decimal precision
    transaction_count: int
    agents_count: int


# ========== Dependency: Get OrganizationManager ==========

async def get_org_manager() -> OrganizationManager:
    """Dependency to get OrganizationManager instance."""
    import os
    dsn = os.getenv("DATABASE_URL", "postgresql://localhost/sardis")
    return OrganizationManager(dsn=dsn)


# ========== Dependency: RBAC Enforcement ==========

async def require_org_permission(
    request: Request,
    permission: Permission,
):
    """
    Dependency to enforce RBAC permissions for organization routes.

    This extracts org_member from request.state (set by RBAC middleware)
    and checks if the member has the required permission.
    """
    org_member = getattr(request.state, "org_member", None)
    if not org_member:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )

    if not RBACEngine.check_permission(org_member.role, permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires {permission.value}"
        )


# ========== Organization Endpoints ==========

@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    request: CreateOrganizationRequest,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Create a new organization.

    Requires authentication. The creating user becomes the first org_admin.
    """
    try:
        org = await org_manager.create_org(
            name=request.name,
            slug=request.slug,
            plan=request.plan,
            billing_email=request.billing_email,
            settings=request.settings,
            metadata=request.metadata,
        )

        # Add the creator as an org_admin
        await org_manager.add_member(
            org_id=org.id,
            user_id=principal.user_id,
            role=MemberRole.ORG_ADMIN,
        )

        return OrganizationResponse.from_org(org)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """Get organization details by ID."""
    org = await org_manager.get_org(org_id)
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )

    # Check if user is a member of this org
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    return OrganizationResponse.from_org(org)


@router.put("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    http_request: Request,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Update organization details.

    Requires MANAGE_ORG permission (org_admin only).
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.MANAGE_ORG):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires manage_org"
        )

    org = await org_manager.update_org(
        org_id=org_id,
        name=request.name,
        plan=request.plan,
        billing_email=request.billing_email,
        settings=request.settings,
        metadata=request.metadata,
    )

    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Organization {org_id} not found"
        )

    return OrganizationResponse.from_org(org)


# ========== Team Endpoints ==========

@router.get("/{org_id}/teams", response_model=List[TeamResponse])
async def list_teams(
    org_id: str,
    parent_team_id: Optional[str] = None,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """List all teams in an organization, optionally filtered by parent."""
    # Check membership
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    teams = await org_manager.get_teams(org_id, parent_team_id=parent_team_id)
    return [TeamResponse.from_team(team) for team in teams]


@router.post("/{org_id}/teams", response_model=TeamResponse, status_code=status.HTTP_201_CREATED)
async def create_team(
    org_id: str,
    request: CreateTeamRequest,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Create a new team within an organization.

    Requires MANAGE_TEAM permission (org_admin or team_admin).
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.MANAGE_TEAM):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires manage_team"
        )

    team = await org_manager.create_team(
        org_id=org_id,
        name=request.name,
        parent_team_id=request.parent_team_id,
        budget_limit=request.budget_limit,
        description=request.description,
        metadata=request.metadata,
    )

    return TeamResponse.from_team(team)


@router.put("/{org_id}/teams/{team_id}", response_model=TeamResponse)
async def update_team(
    org_id: str,
    team_id: str,
    request: UpdateTeamRequest,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Update team details.

    Requires MANAGE_TEAM permission.
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.MANAGE_TEAM):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires manage_team"
        )

    # Verify team belongs to org
    team = await org_manager.get_team(team_id)
    if not team or team.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found in organization {org_id}"
        )

    updated_team = await org_manager.update_team(
        team_id=team_id,
        name=request.name,
        budget_limit=request.budget_limit,
        description=request.description,
        metadata=request.metadata,
    )

    if not updated_team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found"
        )

    return TeamResponse.from_team(updated_team)


@router.delete("/{org_id}/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team(
    org_id: str,
    team_id: str,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Delete a team.

    Requires MANAGE_TEAM permission. Note: agents in this team will have
    their team_id set to NULL (not deleted).
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.MANAGE_TEAM):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires manage_team"
        )

    # Verify team belongs to org
    team = await org_manager.get_team(team_id)
    if not team or team.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found in organization {org_id}"
        )

    success = await org_manager.delete_team(team_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team {team_id} not found"
        )


# ========== Member Endpoints ==========

@router.get("/{org_id}/members", response_model=List[MemberResponse])
async def list_members(
    org_id: str,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """List all members of an organization."""
    # Check membership
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    members = await org_manager.get_org_members(org_id)
    return [MemberResponse.from_member(m) for m in members]


@router.post("/{org_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    org_id: str,
    request: InviteMemberRequest,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Invite a new member to the organization.

    Requires INVITE_MEMBERS permission.
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.INVITE_MEMBERS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires invite_members"
        )

    # Check if actor can assign the target role
    if not RBACEngine.can_manage_role(member.role, request.role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot assign role {request.role} with your current role"
        )

    # Check if user is already a member
    existing = await org_manager.get_user_membership(org_id, request.user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User {request.user_id} is already a member"
        )

    new_member = await org_manager.add_member(
        org_id=org_id,
        user_id=request.user_id,
        role=request.role,
        teams=request.teams,
        invited_by=principal.user_id,
    )

    return MemberResponse.from_member(new_member)


@router.put("/{org_id}/members/{member_id}", response_model=MemberResponse)
async def update_member(
    org_id: str,
    member_id: str,
    request: UpdateMemberRequest,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Update member role or team assignments.

    Requires MANAGE_ROLES permission to change roles.
    Requires ASSIGN_TEAM_MEMBERS permission to change team assignments.
    """
    # Check membership and permission
    actor = await org_manager.get_user_membership(org_id, principal.user_id)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    # Get target member
    target = await org_manager.get_member(member_id)
    if not target or target.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {member_id} not found in organization {org_id}"
        )

    # Check role change permission
    if request.role is not None:
        if not RBACEngine.check_permission(actor.role, Permission.MANAGE_ROLES):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: requires manage_roles"
            )

        # Check if actor can assign the new role
        if not RBACEngine.can_manage_role(actor.role, request.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot assign role {request.role} with your current role"
            )

    # Check team assignment permission
    if request.teams is not None:
        if not RBACEngine.check_permission(actor.role, Permission.ASSIGN_TEAM_MEMBERS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: requires assign_team_members"
            )

    updated_member = await org_manager.update_member_role(
        member_id=member_id,
        role=request.role,
        teams=request.teams,
    )

    if not updated_member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {member_id} not found"
        )

    return MemberResponse.from_member(updated_member)


@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: str,
    member_id: str,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Remove a member from the organization.

    Requires REMOVE_MEMBERS permission.
    """
    # Check membership and permission
    actor = await org_manager.get_user_membership(org_id, principal.user_id)
    if not actor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(actor.role, Permission.REMOVE_MEMBERS):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires remove_members"
        )

    # Get target member
    target = await org_manager.get_member(member_id)
    if not target or target.org_id != org_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {member_id} not found in organization {org_id}"
        )

    # Prevent removing yourself if you're the last org_admin
    if target.user_id == principal.user_id and target.role == MemberRole.ORG_ADMIN:
        members = await org_manager.get_org_members(org_id)
        admin_count = sum(1 for m in members if m.role == MemberRole.ORG_ADMIN)
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove the last org_admin"
            )

    success = await org_manager.remove_member(member_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {member_id} not found"
        )


# ========== Spending & Analytics ==========

@router.get("/{org_id}/spending", response_model=SpendingSummaryResponse)
async def get_spending_summary(
    org_id: str,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    Get aggregated spending summary for the organization.

    Requires VIEW_SPENDING permission.
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.VIEW_SPENDING):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires view_spending"
        )

    summary = await org_manager.get_org_spending_summary(org_id)
    return SpendingSummaryResponse(
        org_id=summary["org_id"],
        total_spent=str(summary["total_spent"]),
        transaction_count=summary["transaction_count"],
        agents_count=summary["agents_count"],
    )


@router.get("/{org_id}/agents", response_model=List[str])
async def list_org_agents(
    org_id: str,
    org_manager: OrganizationManager = Depends(get_org_manager),
    principal: Principal = Depends(require_principal),
):
    """
    List all agent IDs belonging to the organization.

    Requires VIEW_AGENT permission.
    """
    # Check membership and permission
    member = await org_manager.get_user_membership(org_id, principal.user_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a member of this organization"
        )

    if not RBACEngine.check_permission(member.role, Permission.VIEW_AGENT):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: requires view_agent"
        )

    agent_ids = await org_manager.get_org_agents(org_id)
    return agent_ids
