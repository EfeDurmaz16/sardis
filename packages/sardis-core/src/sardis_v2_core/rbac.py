"""Role-Based Access Control (RBAC) for Sardis organizations.

This module defines the permission system for multi-tenant organizations.
It maps roles to permissions and provides enforcement mechanisms for API routes.

Key concepts:
  - **Permission**: Granular action (CREATE_AGENT, EDIT_POLICY, etc.)
  - **Role**: Named collection of permissions (org_admin, team_admin, etc.)
  - **RBACEngine**: Permission checking and enforcement logic
  - **require_permission**: Decorator for FastAPI route protection
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Set, Optional, Callable
from functools import wraps

from fastapi import HTTPException, status


class Permission(str, Enum):
    """Granular permissions in Sardis organizations."""

    # Agent management
    CREATE_AGENT = "create_agent"
    DELETE_AGENT = "delete_agent"
    UPDATE_AGENT = "update_agent"
    VIEW_AGENT = "view_agent"
    RUN_AGENT = "run_agent"

    # Policy management
    CREATE_POLICY = "create_policy"
    EDIT_POLICY = "edit_policy"
    DELETE_POLICY = "delete_policy"
    VIEW_POLICY = "view_policy"

    # Payment operations
    APPROVE_PAYMENT = "approve_payment"
    VIEW_SPENDING = "view_spending"
    EXPORT_DATA = "export_data"

    # Card management
    MANAGE_CARDS = "manage_cards"
    VIEW_CARDS = "view_cards"

    # Team management
    MANAGE_TEAM = "manage_team"
    VIEW_TEAM = "view_team"
    ASSIGN_TEAM_MEMBERS = "assign_team_members"

    # Organization management
    MANAGE_ORG = "manage_org"
    MANAGE_BILLING = "manage_billing"
    INVITE_MEMBERS = "invite_members"
    REMOVE_MEMBERS = "remove_members"
    MANAGE_ROLES = "manage_roles"

    # Audit and compliance
    VIEW_AUDIT = "view_audit"
    EXPORT_AUDIT = "export_audit"
    VIEW_COMPLIANCE = "view_compliance"

    # API keys
    MANAGE_API_KEYS = "manage_api_keys"
    VIEW_API_KEYS = "view_api_keys"


# Role → Permissions mapping
# Each role is assigned a set of permissions it can exercise
ROLE_PERMISSIONS: Dict[str, Set[Permission]] = {
    "org_admin": {
        # Full access to everything
        Permission.CREATE_AGENT,
        Permission.DELETE_AGENT,
        Permission.UPDATE_AGENT,
        Permission.VIEW_AGENT,
        Permission.RUN_AGENT,
        Permission.CREATE_POLICY,
        Permission.EDIT_POLICY,
        Permission.DELETE_POLICY,
        Permission.VIEW_POLICY,
        Permission.APPROVE_PAYMENT,
        Permission.VIEW_SPENDING,
        Permission.EXPORT_DATA,
        Permission.MANAGE_CARDS,
        Permission.VIEW_CARDS,
        Permission.MANAGE_TEAM,
        Permission.VIEW_TEAM,
        Permission.ASSIGN_TEAM_MEMBERS,
        Permission.MANAGE_ORG,
        Permission.MANAGE_BILLING,
        Permission.INVITE_MEMBERS,
        Permission.REMOVE_MEMBERS,
        Permission.MANAGE_ROLES,
        Permission.VIEW_AUDIT,
        Permission.EXPORT_AUDIT,
        Permission.VIEW_COMPLIANCE,
        Permission.MANAGE_API_KEYS,
        Permission.VIEW_API_KEYS,
    },
    "team_admin": {
        # Manage team agents, policies, and members
        Permission.CREATE_AGENT,
        Permission.DELETE_AGENT,
        Permission.UPDATE_AGENT,
        Permission.VIEW_AGENT,
        Permission.RUN_AGENT,
        Permission.CREATE_POLICY,
        Permission.EDIT_POLICY,
        Permission.DELETE_POLICY,
        Permission.VIEW_POLICY,
        Permission.APPROVE_PAYMENT,
        Permission.VIEW_SPENDING,
        Permission.MANAGE_CARDS,
        Permission.VIEW_CARDS,
        Permission.MANAGE_TEAM,
        Permission.VIEW_TEAM,
        Permission.ASSIGN_TEAM_MEMBERS,
        Permission.VIEW_AUDIT,
        Permission.VIEW_COMPLIANCE,
        Permission.VIEW_API_KEYS,
    },
    "policy_admin": {
        # Create and edit policies only
        Permission.VIEW_AGENT,
        Permission.CREATE_POLICY,
        Permission.EDIT_POLICY,
        Permission.DELETE_POLICY,
        Permission.VIEW_POLICY,
        Permission.VIEW_SPENDING,
        Permission.VIEW_TEAM,
        Permission.VIEW_AUDIT,
        Permission.VIEW_COMPLIANCE,
    },
    "agent_operator": {
        # Run agents and make payments (no policy changes)
        Permission.VIEW_AGENT,
        Permission.RUN_AGENT,
        Permission.VIEW_POLICY,
        Permission.VIEW_SPENDING,
        Permission.VIEW_CARDS,
        Permission.VIEW_TEAM,
        Permission.VIEW_AUDIT,
    },
    "viewer": {
        # Read-only access
        Permission.VIEW_AGENT,
        Permission.VIEW_POLICY,
        Permission.VIEW_SPENDING,
        Permission.VIEW_CARDS,
        Permission.VIEW_TEAM,
        Permission.VIEW_AUDIT,
        Permission.VIEW_COMPLIANCE,
    },
}


class RBACEngine:
    """
    RBAC enforcement engine.

    Provides permission checking and role management for Sardis organizations.
    Used by API middleware to enforce access control on routes.
    """

    @staticmethod
    def get_permissions(role: str) -> Set[Permission]:
        """
        Get all permissions granted to a role.

        Args:
            role: Role name (org_admin, team_admin, etc.)

        Returns:
            Set of Permission enums granted to this role

        Raises:
            ValueError: If role is not recognized
        """
        if role not in ROLE_PERMISSIONS:
            raise ValueError(f"Unknown role: {role}")
        return ROLE_PERMISSIONS[role]

    @staticmethod
    def check_permission(member_role: str, permission: Permission) -> bool:
        """
        Check if a member's role grants a specific permission.

        Args:
            member_role: The member's role (from OrgMember.role)
            permission: Permission to check

        Returns:
            True if the role grants the permission, False otherwise
        """
        try:
            role_perms = RBACEngine.get_permissions(member_role)
            return permission in role_perms
        except ValueError:
            # Unknown role = no permissions
            return False

    @staticmethod
    def require_permission(permission: Permission):
        """
        Decorator factory for FastAPI routes that require a specific permission.

        Usage:
            @router.post("/agents")
            @require_permission(Permission.CREATE_AGENT)
            async def create_agent(...):
                ...

        The decorated route will:
          1. Extract the org_member from request state (set by RBAC middleware)
          2. Check if the member has the required permission
          3. Raise HTTP 403 if permission is denied
        """
        def decorator(func: Callable):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request from kwargs (FastAPI dependency injection)
                from fastapi import Request
                request: Optional[Request] = kwargs.get("request")

                if not request:
                    # Try to find Request in args
                    for arg in args:
                        if isinstance(arg, Request):
                            request = arg
                            break

                if not request:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="RBAC middleware error: request not found"
                    )

                # Check if org_member was set by RBAC middleware
                org_member = getattr(request.state, "org_member", None)
                if not org_member:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )

                # Check permission
                if not RBACEngine.check_permission(org_member.role, permission):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: requires {permission.value}"
                    )

                # Permission granted, call the wrapped function
                return await func(*args, **kwargs)

            return wrapper
        return decorator

    @staticmethod
    def has_any_permission(member_role: str, permissions: Set[Permission]) -> bool:
        """
        Check if a member has any of the specified permissions.

        Args:
            member_role: The member's role
            permissions: Set of permissions to check

        Returns:
            True if the role grants at least one of the permissions
        """
        try:
            role_perms = RBACEngine.get_permissions(member_role)
            return bool(role_perms.intersection(permissions))
        except ValueError:
            return False

    @staticmethod
    def has_all_permissions(member_role: str, permissions: Set[Permission]) -> bool:
        """
        Check if a member has all of the specified permissions.

        Args:
            member_role: The member's role
            permissions: Set of permissions to check

        Returns:
            True if the role grants all of the permissions
        """
        try:
            role_perms = RBACEngine.get_permissions(member_role)
            return permissions.issubset(role_perms)
        except ValueError:
            return False

    @staticmethod
    def can_manage_role(actor_role: str, target_role: str) -> bool:
        """
        Check if an actor can assign/modify a target role.

        Business rules:
          - org_admin can manage all roles
          - team_admin can manage agent_operator, policy_admin, viewer
          - Other roles cannot manage roles

        Args:
            actor_role: The role of the member performing the action
            target_role: The role being assigned/modified

        Returns:
            True if the actor can manage the target role
        """
        if actor_role == "org_admin":
            return True

        if actor_role == "team_admin":
            # team_admin can manage lower-privilege roles
            return target_role in {"agent_operator", "policy_admin", "viewer"}

        # Other roles cannot manage roles
        return False

    @staticmethod
    def get_manageable_roles(actor_role: str) -> Set[str]:
        """
        Get the set of roles that an actor can assign to others.

        Args:
            actor_role: The role of the member performing role assignment

        Returns:
            Set of role names that can be assigned
        """
        if actor_role == "org_admin":
            return {"org_admin", "team_admin", "policy_admin", "agent_operator", "viewer"}

        if actor_role == "team_admin":
            return {"team_admin", "policy_admin", "agent_operator", "viewer"}

        return set()


def require_role(required_role: str):
    """
    Decorator factory for FastAPI routes that require a specific role.

    This is a coarser-grained alternative to require_permission().
    Use this when you want to restrict a route to a specific role tier.

    Usage:
        @router.delete("/orgs/{org_id}")
        @require_role("org_admin")
        async def delete_organization(...):
            ...

    Args:
        required_role: Minimum role required (org_admin, team_admin, etc.)
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from fastapi import Request
            request: Optional[Request] = kwargs.get("request")

            if not request:
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break

            if not request:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="RBAC middleware error: request not found"
                )

            org_member = getattr(request.state, "org_member", None)
            if not org_member:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )

            # Simple role match (could be enhanced with role hierarchy)
            if org_member.role != required_role and org_member.role != "org_admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Role denied: requires {required_role}"
                )

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ========== Permission Groups (for convenience) ==========

# Common permission sets for easier checking
AGENT_WRITE_PERMISSIONS = {
    Permission.CREATE_AGENT,
    Permission.UPDATE_AGENT,
    Permission.DELETE_AGENT,
}

POLICY_WRITE_PERMISSIONS = {
    Permission.CREATE_POLICY,
    Permission.EDIT_POLICY,
    Permission.DELETE_POLICY,
}

TEAM_MANAGEMENT_PERMISSIONS = {
    Permission.MANAGE_TEAM,
    Permission.ASSIGN_TEAM_MEMBERS,
}

ORG_MANAGEMENT_PERMISSIONS = {
    Permission.MANAGE_ORG,
    Permission.MANAGE_BILLING,
    Permission.INVITE_MEMBERS,
    Permission.REMOVE_MEMBERS,
    Permission.MANAGE_ROLES,
}


def validate_role(role: str) -> bool:
    """
    Validate that a role name is recognized.

    Args:
        role: Role name to validate

    Returns:
        True if role is valid, False otherwise
    """
    return role in ROLE_PERMISSIONS


def get_all_roles() -> Set[str]:
    """Get all defined role names."""
    return set(ROLE_PERMISSIONS.keys())


def get_role_hierarchy() -> Dict[str, int]:
    """
    Get role hierarchy levels (higher number = more privileges).

    This can be used for role comparison and elevation checks.

    Returns:
        Dict mapping role name to privilege level (0-100)
    """
    return {
        "viewer": 10,
        "agent_operator": 20,
        "policy_admin": 30,
        "team_admin": 50,
        "org_admin": 100,
    }


def is_role_elevated(current_role: str, target_role: str) -> bool:
    """
    Check if target_role has higher privileges than current_role.

    Args:
        current_role: Current role
        target_role: Target role to compare

    Returns:
        True if target_role is more privileged
    """
    hierarchy = get_role_hierarchy()
    current_level = hierarchy.get(current_role, 0)
    target_level = hierarchy.get(target_role, 0)
    return target_level > current_level
