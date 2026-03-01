"""Multi-tenant organization management for Sardis.

This module provides the foundation for organizational hierarchy, team structures,
and member management in Sardis. Organizations can have multiple teams, and each
team can have its own budget limits and agent assignments.

Key concepts:
  - **Organization**: Top-level entity (free/pro/enterprise plans)
  - **Team**: Sub-unit within an org with hierarchy support (parent_team_id)
  - **OrgMember**: User membership with role-based access control
  - **OrganizationManager**: CRUD operations for orgs, teams, and members
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List
from uuid import uuid4

from pydantic import BaseModel, Field


class OrganizationPlan(str):
    """Organization billing plan tiers."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class MemberRole(str):
    """Member roles within an organization."""
    ORG_ADMIN = "org_admin"           # Full org access
    TEAM_ADMIN = "team_admin"         # Manage team agents and policies
    POLICY_ADMIN = "policy_admin"     # Create/edit policies only
    AGENT_OPERATOR = "agent_operator" # Run agents and make payments
    VIEWER = "viewer"                 # Read-only access


@dataclass(slots=True)
class Organization:
    """
    Top-level organizational entity in Sardis.

    An organization represents a company or team using Sardis. It can have
    multiple teams, members, and agents. Organizations are billed based on
    their plan tier (free/pro/enterprise).
    """
    id: str
    name: str
    slug: str  # URL-safe identifier (e.g. "acme-corp")
    plan: str = OrganizationPlan.FREE
    settings: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Optional billing/metadata fields
    billing_email: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    subscription_status: Optional[str] = None  # active, canceled, past_due
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def new(name: str, slug: str, plan: str = OrganizationPlan.FREE) -> "Organization":
        """Create a new organization with generated ID."""
        return Organization(
            id=f"org_{uuid4().hex[:16]}",
            name=name,
            slug=slug,
            plan=plan,
        )


@dataclass(slots=True)
class Team:
    """
    A team within an organization.

    Teams allow organizational hierarchy and budget segmentation. Each team
    can have its own spending limits and can be nested under a parent team.
    Agents belong to teams, and team admins can manage agents within their team.
    """
    id: str
    org_id: str
    name: str
    parent_team_id: Optional[str] = None  # For team hierarchy
    budget_limit: Optional[Decimal] = None  # Team spending cap
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Optional metadata
    description: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def new(org_id: str, name: str, parent_team_id: Optional[str] = None) -> "Team":
        """Create a new team with generated ID."""
        return Team(
            id=f"team_{uuid4().hex[:16]}",
            org_id=org_id,
            name=name,
            parent_team_id=parent_team_id,
        )


@dataclass(slots=True)
class OrgMember:
    """
    A user's membership in an organization.

    Members have roles that determine their permissions (via RBAC). They can
    be assigned to one or more teams within the organization.
    """
    id: str
    org_id: str
    user_id: str
    role: str = MemberRole.VIEWER
    teams: List[str] = field(default_factory=list)  # Team IDs this member belongs to
    invited_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    joined_at: Optional[datetime] = None

    # Invitation/status fields
    invite_accepted: bool = False
    invited_by: Optional[str] = None  # User ID who sent the invitation
    metadata: dict = field(default_factory=dict)

    @staticmethod
    def new(
        org_id: str,
        user_id: str,
        role: str = MemberRole.VIEWER,
        invited_by: Optional[str] = None,
    ) -> "OrgMember":
        """Create a new organization member with generated ID."""
        return OrgMember(
            id=f"member_{uuid4().hex[:16]}",
            org_id=org_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
        )


class OrganizationManager:
    """
    Manager for organization, team, and member CRUD operations.

    This class provides the business logic layer for multi-tenant operations.
    In production, it interfaces with PostgreSQL via the Database class.
    In dev/test, it can fall back to in-memory storage.
    """

    def __init__(self, dsn: str = "memory://"):
        """
        Initialize the organization manager.

        Args:
            dsn: Database connection string. Use "memory://" for in-memory mode.
        """
        self._dsn = dsn
        self._use_postgres = dsn.startswith(("postgresql://", "postgres://"))

        # NOTE: Redis migration — production uses PostgreSQL (self._use_postgres=True).
        # The in-memory dicts below are only used in dev/test mode (memory:// DSN).
        # A full Redis migration of the dev/test path would require serializing
        # Organization, Team, and OrgMember dataclasses (which use slots=True).
        # RedisStateStore(namespace="organizations", ttl=300) is available for future use.
        from sardis_v2_core.redis_state import RedisStateStore
        self._org_cache = RedisStateStore(namespace="organizations")

        # In-memory storage for dev/test
        self._orgs: dict[str, Organization] = {}
        self._teams: dict[str, Team] = {}
        self._members: dict[str, OrgMember] = {}

        # Lookup indexes
        self._slug_to_org_id: dict[str, str] = {}
        self._user_orgs: dict[str, List[str]] = {}  # user_id -> [org_ids]

    # ========== Organization Management ==========

    async def create_org(
        self,
        name: str,
        slug: str,
        plan: str = OrganizationPlan.FREE,
        billing_email: Optional[str] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Organization:
        """
        Create a new organization.

        Args:
            name: Display name of the organization
            slug: URL-safe identifier (must be unique)
            plan: Billing plan tier (free/pro/enterprise)
            billing_email: Email for billing notifications
            settings: Organization-level settings
            metadata: Additional metadata

        Returns:
            Created organization

        Raises:
            ValueError: If slug already exists
        """
        # Check for duplicate slug
        if self._use_postgres:
            from sardis_v2_core.database import Database

            existing = await Database.fetchrow(
                "SELECT id FROM organizations WHERE slug = $1", slug
            )
            if existing:
                raise ValueError(f"Organization with slug '{slug}' already exists")

            org_id = f"org_{uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)

            await Database.execute(
                """
                INSERT INTO organizations (id, name, slug, plan, billing_email, settings, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                org_id,
                name,
                slug,
                plan,
                billing_email,
                settings or {},
                metadata or {},
                now,
                now,
            )

            return Organization(
                id=org_id,
                name=name,
                slug=slug,
                plan=plan,
                billing_email=billing_email,
                settings=settings or {},
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )
        else:
            # In-memory mode
            if slug in self._slug_to_org_id:
                raise ValueError(f"Organization with slug '{slug}' already exists")

            org = Organization.new(name=name, slug=slug, plan=plan)
            if billing_email:
                org.billing_email = billing_email
            if settings:
                org.settings = settings
            if metadata:
                org.metadata = metadata

            self._orgs[org.id] = org
            self._slug_to_org_id[slug] = org.id
            return org

    async def get_org(self, org_id: str) -> Optional[Organization]:
        """Get organization by ID."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            row = await Database.fetchrow(
                "SELECT * FROM organizations WHERE id = $1", org_id
            )
            if not row:
                return None

            return Organization(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                plan=row["plan"],
                billing_email=row.get("billing_email"),
                settings=row.get("settings") or {},
                metadata=row.get("metadata") or {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        else:
            return self._orgs.get(org_id)

    async def get_org_by_slug(self, slug: str) -> Optional[Organization]:
        """Get organization by slug."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            row = await Database.fetchrow(
                "SELECT * FROM organizations WHERE slug = $1", slug
            )
            if not row:
                return None

            return Organization(
                id=row["id"],
                name=row["name"],
                slug=row["slug"],
                plan=row["plan"],
                billing_email=row.get("billing_email"),
                settings=row.get("settings") or {},
                metadata=row.get("metadata") or {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        else:
            org_id = self._slug_to_org_id.get(slug)
            return self._orgs.get(org_id) if org_id else None

    async def update_org(
        self,
        org_id: str,
        name: Optional[str] = None,
        plan: Optional[str] = None,
        billing_email: Optional[str] = None,
        settings: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Organization]:
        """Update organization fields."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            updates = []
            params = [org_id]
            idx = 2

            if name is not None:
                updates.append(f"name = ${idx}")
                params.append(name)
                idx += 1
            if plan is not None:
                updates.append(f"plan = ${idx}")
                params.append(plan)
                idx += 1
            if billing_email is not None:
                updates.append(f"billing_email = ${idx}")
                params.append(billing_email)
                idx += 1
            if settings is not None:
                updates.append(f"settings = ${idx}")
                params.append(settings)
                idx += 1
            if metadata is not None:
                updates.append(f"metadata = ${idx}")
                params.append(metadata)
                idx += 1

            if not updates:
                return await self.get_org(org_id)

            updates.append(f"updated_at = ${idx}")
            params.append(datetime.now(timezone.utc))

            query = f"UPDATE organizations SET {', '.join(updates)} WHERE id = $1"
            await Database.execute(query, *params)

            return await self.get_org(org_id)
        else:
            org = self._orgs.get(org_id)
            if not org:
                return None

            if name is not None:
                org.name = name
            if plan is not None:
                org.plan = plan
            if billing_email is not None:
                org.billing_email = billing_email
            if settings is not None:
                org.settings = settings
            if metadata is not None:
                org.metadata = metadata

            org.updated_at = datetime.now(timezone.utc)
            return org

    async def delete_org(self, org_id: str) -> bool:
        """
        Delete organization and all associated teams/members.

        SECURITY: This is a destructive operation. Should require org_admin role.
        """
        if self._use_postgres:
            from sardis_v2_core.database import Database

            # Cascade delete teams and members
            await Database.execute("DELETE FROM org_members WHERE org_id = $1", org_id)
            await Database.execute("DELETE FROM teams WHERE org_id = $1", org_id)
            result = await Database.execute("DELETE FROM organizations WHERE id = $1", org_id)

            return "DELETE 1" in result
        else:
            if org_id not in self._orgs:
                return False

            org = self._orgs[org_id]

            # Remove from slug index
            if org.slug in self._slug_to_org_id:
                del self._slug_to_org_id[org.slug]

            # Delete teams
            teams_to_delete = [t_id for t_id, t in self._teams.items() if t.org_id == org_id]
            for t_id in teams_to_delete:
                del self._teams[t_id]

            # Delete members
            members_to_delete = [m_id for m_id, m in self._members.items() if m.org_id == org_id]
            for m_id in members_to_delete:
                member = self._members[m_id]
                # Clean up user_orgs index
                if member.user_id in self._user_orgs:
                    self._user_orgs[member.user_id] = [
                        oid for oid in self._user_orgs[member.user_id] if oid != org_id
                    ]
                del self._members[m_id]

            del self._orgs[org_id]
            return True

    # ========== Team Management ==========

    async def create_team(
        self,
        org_id: str,
        name: str,
        parent_team_id: Optional[str] = None,
        budget_limit: Optional[Decimal] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Team:
        """Create a new team within an organization."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            team_id = f"team_{uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)

            await Database.execute(
                """
                INSERT INTO teams (id, org_id, name, parent_team_id, budget_limit, description, metadata, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                """,
                team_id,
                org_id,
                name,
                parent_team_id,
                budget_limit,
                description,
                metadata or {},
                now,
                now,
            )

            return Team(
                id=team_id,
                org_id=org_id,
                name=name,
                parent_team_id=parent_team_id,
                budget_limit=budget_limit,
                description=description,
                metadata=metadata or {},
                created_at=now,
                updated_at=now,
            )
        else:
            team = Team.new(org_id=org_id, name=name, parent_team_id=parent_team_id)
            team.budget_limit = budget_limit
            team.description = description
            if metadata:
                team.metadata = metadata

            self._teams[team.id] = team
            return team

    async def get_team(self, team_id: str) -> Optional[Team]:
        """Get team by ID."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            row = await Database.fetchrow("SELECT * FROM teams WHERE id = $1", team_id)
            if not row:
                return None

            return Team(
                id=row["id"],
                org_id=row["org_id"],
                name=row["name"],
                parent_team_id=row.get("parent_team_id"),
                budget_limit=row.get("budget_limit"),
                description=row.get("description"),
                metadata=row.get("metadata") or {},
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
        else:
            return self._teams.get(team_id)

    async def get_teams(
        self,
        org_id: str,
        parent_team_id: Optional[str] = None,
    ) -> List[Team]:
        """Get all teams in an organization, optionally filtered by parent."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            if parent_team_id is not None:
                rows = await Database.fetch(
                    "SELECT * FROM teams WHERE org_id = $1 AND parent_team_id = $2",
                    org_id,
                    parent_team_id,
                )
            else:
                rows = await Database.fetch(
                    "SELECT * FROM teams WHERE org_id = $1", org_id
                )

            return [
                Team(
                    id=row["id"],
                    org_id=row["org_id"],
                    name=row["name"],
                    parent_team_id=row.get("parent_team_id"),
                    budget_limit=row.get("budget_limit"),
                    description=row.get("description"),
                    metadata=row.get("metadata") or {},
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                )
                for row in rows
            ]
        else:
            teams = [t for t in self._teams.values() if t.org_id == org_id]
            if parent_team_id is not None:
                teams = [t for t in teams if t.parent_team_id == parent_team_id]
            return teams

    async def update_team(
        self,
        team_id: str,
        name: Optional[str] = None,
        budget_limit: Optional[Decimal] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> Optional[Team]:
        """Update team fields."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            updates = []
            params = [team_id]
            idx = 2

            if name is not None:
                updates.append(f"name = ${idx}")
                params.append(name)
                idx += 1
            if budget_limit is not None:
                updates.append(f"budget_limit = ${idx}")
                params.append(budget_limit)
                idx += 1
            if description is not None:
                updates.append(f"description = ${idx}")
                params.append(description)
                idx += 1
            if metadata is not None:
                updates.append(f"metadata = ${idx}")
                params.append(metadata)
                idx += 1

            if not updates:
                return await self.get_team(team_id)

            updates.append(f"updated_at = ${idx}")
            params.append(datetime.now(timezone.utc))

            query = f"UPDATE teams SET {', '.join(updates)} WHERE id = $1"
            await Database.execute(query, *params)

            return await self.get_team(team_id)
        else:
            team = self._teams.get(team_id)
            if not team:
                return None

            if name is not None:
                team.name = name
            if budget_limit is not None:
                team.budget_limit = budget_limit
            if description is not None:
                team.description = description
            if metadata is not None:
                team.metadata = metadata

            team.updated_at = datetime.now(timezone.utc)
            return team

    async def delete_team(self, team_id: str) -> bool:
        """Delete a team."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            result = await Database.execute("DELETE FROM teams WHERE id = $1", team_id)
            return "DELETE 1" in result
        else:
            if team_id in self._teams:
                del self._teams[team_id]
                return True
            return False

    # ========== Member Management ==========

    async def add_member(
        self,
        org_id: str,
        user_id: str,
        role: str = MemberRole.VIEWER,
        teams: Optional[List[str]] = None,
        invited_by: Optional[str] = None,
    ) -> OrgMember:
        """Add a member to an organization."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            member_id = f"member_{uuid4().hex[:16]}"
            now = datetime.now(timezone.utc)

            await Database.execute(
                """
                INSERT INTO org_members (id, org_id, user_id, role, teams, invited_by, invited_at, invite_accepted)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                member_id,
                org_id,
                user_id,
                role,
                teams or [],
                invited_by,
                now,
                False,
            )

            return OrgMember(
                id=member_id,
                org_id=org_id,
                user_id=user_id,
                role=role,
                teams=teams or [],
                invited_by=invited_by,
                invited_at=now,
                invite_accepted=False,
            )
        else:
            member = OrgMember.new(
                org_id=org_id,
                user_id=user_id,
                role=role,
                invited_by=invited_by,
            )
            if teams:
                member.teams = teams

            self._members[member.id] = member

            # Update user_orgs index
            if user_id not in self._user_orgs:
                self._user_orgs[user_id] = []
            if org_id not in self._user_orgs[user_id]:
                self._user_orgs[user_id].append(org_id)

            return member

    async def get_member(self, member_id: str) -> Optional[OrgMember]:
        """Get member by ID."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            row = await Database.fetchrow(
                "SELECT * FROM org_members WHERE id = $1", member_id
            )
            if not row:
                return None

            return OrgMember(
                id=row["id"],
                org_id=row["org_id"],
                user_id=row["user_id"],
                role=row["role"],
                teams=row.get("teams") or [],
                invited_by=row.get("invited_by"),
                invited_at=row["invited_at"],
                joined_at=row.get("joined_at"),
                invite_accepted=row.get("invite_accepted", False),
                metadata=row.get("metadata") or {},
            )
        else:
            return self._members.get(member_id)

    async def get_org_members(self, org_id: str) -> List[OrgMember]:
        """Get all members of an organization."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            rows = await Database.fetch(
                "SELECT * FROM org_members WHERE org_id = $1", org_id
            )

            return [
                OrgMember(
                    id=row["id"],
                    org_id=row["org_id"],
                    user_id=row["user_id"],
                    role=row["role"],
                    teams=row.get("teams") or [],
                    invited_by=row.get("invited_by"),
                    invited_at=row["invited_at"],
                    joined_at=row.get("joined_at"),
                    invite_accepted=row.get("invite_accepted", False),
                    metadata=row.get("metadata") or {},
                )
                for row in rows
            ]
        else:
            return [m for m in self._members.values() if m.org_id == org_id]

    async def get_user_membership(
        self, org_id: str, user_id: str
    ) -> Optional[OrgMember]:
        """Get a user's membership in a specific organization."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            row = await Database.fetchrow(
                "SELECT * FROM org_members WHERE org_id = $1 AND user_id = $2",
                org_id,
                user_id,
            )
            if not row:
                return None

            return OrgMember(
                id=row["id"],
                org_id=row["org_id"],
                user_id=row["user_id"],
                role=row["role"],
                teams=row.get("teams") or [],
                invited_by=row.get("invited_by"),
                invited_at=row["invited_at"],
                joined_at=row.get("joined_at"),
                invite_accepted=row.get("invite_accepted", False),
                metadata=row.get("metadata") or {},
            )
        else:
            for member in self._members.values():
                if member.org_id == org_id and member.user_id == user_id:
                    return member
            return None

    async def update_member_role(
        self,
        member_id: str,
        role: Optional[str] = None,
        teams: Optional[List[str]] = None,
    ) -> Optional[OrgMember]:
        """Update member role or team assignments."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            updates = []
            params = [member_id]
            idx = 2

            if role is not None:
                updates.append(f"role = ${idx}")
                params.append(role)
                idx += 1
            if teams is not None:
                updates.append(f"teams = ${idx}")
                params.append(teams)
                idx += 1

            if not updates:
                return await self.get_member(member_id)

            query = f"UPDATE org_members SET {', '.join(updates)} WHERE id = $1"
            await Database.execute(query, *params)

            return await self.get_member(member_id)
        else:
            member = self._members.get(member_id)
            if not member:
                return None

            if role is not None:
                member.role = role
            if teams is not None:
                member.teams = teams

            return member

    async def remove_member(self, member_id: str) -> bool:
        """Remove a member from an organization."""
        if self._use_postgres:
            from sardis_v2_core.database import Database

            result = await Database.execute(
                "DELETE FROM org_members WHERE id = $1", member_id
            )
            return "DELETE 1" in result
        else:
            if member_id in self._members:
                member = self._members[member_id]

                # Update user_orgs index
                if member.user_id in self._user_orgs:
                    self._user_orgs[member.user_id] = [
                        oid for oid in self._user_orgs[member.user_id]
                        if oid != member.org_id
                    ]

                del self._members[member_id]
                return True
            return False

    # ========== Agent and Spending Queries ==========

    async def get_org_agents(self, org_id: str) -> List[str]:
        """
        Get all agent IDs belonging to an organization.

        This queries agents across all teams in the org.
        Requires agents table to have org_id or team_id column.
        """
        if self._use_postgres:
            from sardis_v2_core.database import Database

            # Try querying by org_id first
            rows = await Database.fetch(
                "SELECT agent_id FROM agents WHERE org_id = $1", org_id
            )
            if rows:
                return [row["agent_id"] for row in rows]

            # Fallback: query by team_id
            team_ids = [t.id for t in await self.get_teams(org_id)]
            if not team_ids:
                return []

            # Use ANY to query by team_id list
            rows = await Database.fetch(
                "SELECT agent_id FROM agents WHERE team_id = ANY($1)", team_ids
            )
            return [row["agent_id"] for row in rows]
        else:
            # In-memory mode: would need access to agent repository
            return []

    async def get_team_agents(self, team_id: str) -> List[str]:
        """
        Get all agent IDs belonging to a specific team.

        Requires agents table to have team_id column.
        """
        if self._use_postgres:
            from sardis_v2_core.database import Database

            rows = await Database.fetch(
                "SELECT agent_id FROM agents WHERE team_id = $1", team_id
            )
            return [row["agent_id"] for row in rows]
        else:
            return []

    async def get_org_spending_summary(self, org_id: str) -> dict:
        """
        Get aggregate spending summary for an organization.

        Returns:
            dict with total_spent, transaction_count, agents_count, etc.
        """
        if self._use_postgres:
            from sardis_v2_core.database import Database

            # Get all agents in org
            agent_ids = await self.get_org_agents(org_id)
            if not agent_ids:
                return {
                    "org_id": org_id,
                    "total_spent": Decimal("0"),
                    "transaction_count": 0,
                    "agents_count": 0,
                }

            # Query spending policy state for total spent
            row = await Database.fetchrow(
                """
                SELECT
                    SUM(spent_total) as total_spent,
                    COUNT(DISTINCT agent_id) as agents_count
                FROM spending_policy_state
                WHERE agent_id = ANY($1)
                """,
                agent_ids,
            )

            # Query transaction count from ledger
            tx_count = await Database.fetchval(
                """
                SELECT COUNT(*) FROM ledger_entries
                WHERE metadata->>'agent_id' = ANY($1)
                """,
                agent_ids,
            ) or 0

            return {
                "org_id": org_id,
                "total_spent": row["total_spent"] or Decimal("0"),
                "transaction_count": tx_count,
                "agents_count": row["agents_count"] or 0,
            }
        else:
            return {
                "org_id": org_id,
                "total_spent": Decimal("0"),
                "transaction_count": 0,
                "agents_count": 0,
            }
