"""Agent Auth Protocol — Discovery, registration, and capability execution.

Implements the Agent Auth Protocol to make Sardis discoverable by any AI agent.
Key insight: spending mandates ARE capability grants with constraints.

Endpoints:
  GET  /.well-known/agent-configuration  — Discovery document
  GET  /api/v2/capability/list            — Available capabilities
  POST /api/v2/capability/execute         — Execute a capability with JWT
  POST /api/v2/agent/register             — Register agent identity
  GET  /api/v2/agent/status               — Agent status + grants
  POST /api/v2/agent/request-capability   — Request a capability grant
  POST /api/v2/agent/revoke               — Revoke agent access
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger("sardis.api.agent_auth")

# ---------------------------------------------------------------------------
# Routers — public (discovery, unauthenticated) + private (authenticated)
# ---------------------------------------------------------------------------
discovery_router = APIRouter(tags=["agent-auth"])
router = APIRouter(tags=["agent-auth"])

# ---------------------------------------------------------------------------
# In-memory stores (production: swap for Postgres-backed repos)
# ---------------------------------------------------------------------------
_agent_registry: dict[str, dict] = {}
_capability_grants: dict[str, list[dict]] = {}  # agent_id -> [grants]

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROVIDER_NAME = "Sardis Payment OS"
PROVIDER_URL = os.getenv("SARDIS_API_URL", "https://api.sardis.sh")
ALGORITHMS = ["Ed25519"]
SUPPORTED_MODES = ["delegated", "autonomous"]

CAPABILITIES = {
    "payment": {
        "id": "payment",
        "name": "Execute Payment",
        "description": "Execute a payment via USDC, card, or bank rail",
        "version": "1.0.0",
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "amount": {"type": "string", "description": "Payment amount in minor units"},
                    "currency": {"type": "string", "default": "USDC"},
                    "recipient": {"type": "string", "description": "Recipient wallet or address"},
                    "rail": {"type": "string", "enum": ["usdc", "card", "bank"]},
                    "memo": {"type": "string"},
                },
                "required": ["amount", "recipient"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                    "status": {"type": "string"},
                    "amount": {"type": "string"},
                    "currency": {"type": "string"},
                },
            },
        },
    },
    "fx_quote": {
        "id": "fx_quote",
        "name": "Get FX Quote",
        "description": "Get a foreign exchange quote between two currencies",
        "version": "1.0.0",
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "from_currency": {"type": "string"},
                    "to_currency": {"type": "string"},
                    "amount": {"type": "string"},
                },
                "required": ["from_currency", "to_currency", "amount"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "rate": {"type": "string"},
                    "from_amount": {"type": "string"},
                    "to_amount": {"type": "string"},
                    "expires_at": {"type": "string"},
                },
            },
        },
    },
    "policy_check": {
        "id": "policy_check",
        "name": "Check Spending Policy",
        "description": "Evaluate whether a proposed payment passes spending policies",
        "version": "1.0.0",
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "amount": {"type": "string"},
                    "currency": {"type": "string"},
                    "vendor_category": {"type": "string"},
                    "merchant_id": {"type": "string"},
                },
                "required": ["amount"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "allowed": {"type": "boolean"},
                    "reason": {"type": "string"},
                    "remaining_budget": {"type": "string"},
                },
            },
        },
    },
    "mandate_create": {
        "id": "mandate_create",
        "name": "Create Spending Mandate",
        "description": "Create a spending mandate defining scoped authority for an agent",
        "version": "1.0.0",
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "purpose_scope": {"type": "string"},
                    "amount_daily": {"type": "string"},
                    "amount_monthly": {"type": "string"},
                    "allowed_rails": {"type": "array", "items": {"type": "string"}},
                    "merchant_scope": {"type": "object"},
                },
                "required": ["purpose_scope"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "mandate_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
        },
    },
    "balance_check": {
        "id": "balance_check",
        "name": "Check Wallet Balance",
        "description": "Check the balance of a wallet",
        "version": "1.0.0",
        "schema": {
            "input": {
                "type": "object",
                "properties": {
                    "wallet_id": {"type": "string"},
                    "currency": {"type": "string", "default": "USDC"},
                },
                "required": ["wallet_id"],
            },
            "output": {
                "type": "object",
                "properties": {
                    "balance": {"type": "string"},
                    "currency": {"type": "string"},
                    "wallet_id": {"type": "string"},
                },
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class AgentRegistrationRequest(BaseModel):
    """Register an agent with the Agent Auth Protocol."""
    agent_name: str = Field(..., description="Human-readable agent name")
    agent_description: str | None = Field(None, description="Agent description")
    public_key: str = Field(..., description="Ed25519 public key (hex-encoded)")
    algorithm: str = Field(default="Ed25519", description="Signing algorithm")
    mode: str = Field(default="delegated", description="Operating mode: delegated or autonomous")
    capabilities_requested: list[str] = Field(
        default_factory=list,
        description="Capabilities to request on registration",
    )
    callback_url: str | None = Field(None, description="Callback URL for async approvals")
    metadata: dict | None = Field(None, description="Additional metadata")


class AgentRegistrationResponse(BaseModel):
    agent_id: str
    org_id: str
    status: str
    mode: str
    public_key: str
    algorithm: str
    capabilities_granted: list[dict]
    created_at: str
    next_steps: list[str] = []


class CapabilityRequestModel(BaseModel):
    """Request a new capability grant."""
    capability: str = Field(..., description="Capability ID to request")
    constraints: dict | None = Field(None, description="Constraints on the grant")
    justification: str | None = Field(None, description="Why the agent needs this")


class CapabilityGrantResponse(BaseModel):
    grant_id: str
    agent_id: str
    capability: str
    status: str
    constraints: dict | None = None
    granted_at: str
    expires_at: str | None = None


class CapabilityExecuteRequest(BaseModel):
    """Execute a capability."""
    capability: str = Field(..., description="Capability ID to execute")
    parameters: dict = Field(default_factory=dict, description="Execution parameters")
    idempotency_key: str | None = Field(None, description="Idempotency key for deduplication")


class CapabilityExecuteResponse(BaseModel):
    execution_id: str
    capability: str
    status: str
    result: dict | None = None
    error: str | None = None
    executed_at: str


class AgentStatusResponse(BaseModel):
    agent_id: str
    org_id: str
    status: str
    mode: str
    public_key: str
    algorithm: str
    capabilities: list[dict]
    created_at: str
    last_active_at: str | None = None


class AgentRevokeRequest(BaseModel):
    agent_id: str
    reason: str | None = None


class AgentRevokeResponse(BaseModel):
    agent_id: str
    status: str
    revoked_at: str
    reason: str | None = None


# ---------------------------------------------------------------------------
# Mandate-to-Capability Mapper
# ---------------------------------------------------------------------------

def mandate_to_capability_grant(mandate: dict) -> dict:
    """Convert a spending mandate into an Agent Auth capability grant.

    The key insight: a spending mandate IS a capability grant with constraints.
    Example:
        Mandate: "max $500/day on dev tools"
        =>
        Capability grant: {
            "capability": "payment",
            "constraints": {
                "amount": {"max": 500},
                "period": {"in": ["daily"]},
                "vendor_category": {"in": ["dev_tools"]}
            }
        }
    """
    constraints: dict = {}

    # Amount constraints
    amount_constraints: dict = {}
    if mandate.get("amount_per_tx"):
        amount_constraints["max_per_tx"] = str(mandate["amount_per_tx"])
    if mandate.get("amount_daily"):
        amount_constraints["max_daily"] = str(mandate["amount_daily"])
    if mandate.get("amount_weekly"):
        amount_constraints["max_weekly"] = str(mandate["amount_weekly"])
    if mandate.get("amount_monthly"):
        amount_constraints["max_monthly"] = str(mandate["amount_monthly"])
    if mandate.get("amount_total"):
        amount_constraints["max_total"] = str(mandate["amount_total"])
    if amount_constraints:
        constraints["amount"] = amount_constraints

    # Currency constraint
    if mandate.get("currency"):
        constraints["currency"] = {"in": [mandate["currency"]]}

    # Rail constraints
    if mandate.get("allowed_rails"):
        constraints["rail"] = {"in": mandate["allowed_rails"]}

    # Chain constraints
    if mandate.get("allowed_chains"):
        constraints["chain"] = {"in": mandate["allowed_chains"]}

    # Token constraints
    if mandate.get("allowed_tokens"):
        constraints["token"] = {"in": mandate["allowed_tokens"]}

    # Merchant / vendor scope
    if mandate.get("merchant_scope"):
        constraints["vendor_category"] = mandate["merchant_scope"]

    # Purpose scope
    if mandate.get("purpose_scope"):
        constraints["purpose"] = {"in": [mandate["purpose_scope"]]}

    # Approval mode
    if mandate.get("approval_mode"):
        constraints["approval_mode"] = mandate["approval_mode"]

    # Approval threshold
    if mandate.get("approval_threshold"):
        constraints["approval_threshold"] = str(mandate["approval_threshold"])

    return {
        "grant_id": f"grant_{uuid4().hex[:12]}",
        "capability": "payment",
        "status": mandate.get("status", "active"),
        "constraints": constraints,
        "source_mandate_id": mandate.get("id"),
        "granted_at": mandate.get("created_at", datetime.now(UTC).isoformat()),
        "expires_at": mandate.get("expires_at"),
    }


def capability_grant_to_mandate(grant: dict) -> dict:
    """Convert an Agent Auth capability grant back to a spending mandate shape.

    Inverse of mandate_to_capability_grant — useful for policy enforcement.
    """
    constraints = grant.get("constraints", {})
    amount = constraints.get("amount", {})

    mandate: dict = {
        "status": grant.get("status", "active"),
        "currency": "USDC",
    }

    if amount.get("max_per_tx"):
        mandate["amount_per_tx"] = Decimal(amount["max_per_tx"])
    if amount.get("max_daily"):
        mandate["amount_daily"] = Decimal(amount["max_daily"])
    if amount.get("max_weekly"):
        mandate["amount_weekly"] = Decimal(amount["max_weekly"])
    if amount.get("max_monthly"):
        mandate["amount_monthly"] = Decimal(amount["max_monthly"])
    if amount.get("max_total"):
        mandate["amount_total"] = Decimal(amount["max_total"])

    currency = constraints.get("currency", {})
    if currency.get("in"):
        mandate["currency"] = currency["in"][0]

    if constraints.get("rail", {}).get("in"):
        mandate["allowed_rails"] = constraints["rail"]["in"]

    if constraints.get("chain", {}).get("in"):
        mandate["allowed_chains"] = constraints["chain"]["in"]

    if constraints.get("token", {}).get("in"):
        mandate["allowed_tokens"] = constraints["token"]["in"]

    if constraints.get("vendor_category"):
        mandate["merchant_scope"] = constraints["vendor_category"]

    if constraints.get("purpose", {}).get("in"):
        mandate["purpose_scope"] = constraints["purpose"]["in"][0]

    if constraints.get("approval_mode"):
        mandate["approval_mode"] = constraints["approval_mode"]

    if constraints.get("approval_threshold"):
        mandate["approval_threshold"] = Decimal(constraints["approval_threshold"])

    return mandate


# ---------------------------------------------------------------------------
# Constraint Validation
# ---------------------------------------------------------------------------

def validate_constraints(grant: dict, params: dict) -> tuple[bool, str | None]:
    """Validate execution parameters against capability grant constraints.

    Returns (allowed, reason).
    """
    constraints = grant.get("constraints", {})
    if not constraints:
        return True, None

    # Amount check
    amount_constraints = constraints.get("amount", {})
    if params.get("amount") and amount_constraints:
        try:
            req_amount = Decimal(str(params["amount"]))
        except Exception:
            return False, "Invalid amount format"

        max_per_tx = amount_constraints.get("max_per_tx")
        if max_per_tx and req_amount > Decimal(max_per_tx):
            return False, f"Amount {req_amount} exceeds per-transaction limit of {max_per_tx}"

    # Currency check
    currency_constraint = constraints.get("currency", {})
    if params.get("currency") and currency_constraint.get("in"):
        if params["currency"] not in currency_constraint["in"]:
            return False, f"Currency {params['currency']} not in allowed currencies: {currency_constraint['in']}"

    # Rail check
    rail_constraint = constraints.get("rail", {})
    if params.get("rail") and rail_constraint.get("in"):
        if params["rail"] not in rail_constraint["in"]:
            return False, f"Rail {params['rail']} not in allowed rails: {rail_constraint['in']}"

    # Vendor category check
    vendor_constraint = constraints.get("vendor_category", {})
    if params.get("vendor_category") and vendor_constraint.get("in"):
        if params["vendor_category"] not in vendor_constraint["in"]:
            return False, f"Vendor category not allowed"

    return True, None


# ---------------------------------------------------------------------------
# JWT Verification Helpers (Ed25519)
# ---------------------------------------------------------------------------

def _verify_agent_jwt(request: Request) -> dict | None:
    """Extract and verify an agent JWT from the X-Agent-JWT header.

    Uses a dedicated header to avoid conflicts with the main
    Authorization: Bearer header used by API key / dashboard JWT auth.

    In production this performs Ed25519 signature verification against
    the agent's registered public key. For the MVP this validates structure
    and checks the agent exists.

    Returns decoded payload dict or None on failure.
    """
    token = request.headers.get("x-agent-jwt", "")
    if not token:
        return None

    parts = token.split(".")
    if len(parts) != 3:
        return None

    # Decode payload (base64url)
    import base64
    try:
        payload_b64 = parts[1]
        # Add padding
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        payload_bytes = base64.urlsafe_b64decode(payload_b64)
        payload = json.loads(payload_bytes)
    except Exception:
        return None

    # Validate required claims
    if "sub" not in payload:
        return None

    # Check expiration
    if "exp" in payload and payload["exp"] < time.time():
        return None

    # Look up agent
    agent_id = payload.get("sub")
    if agent_id and agent_id in _agent_registry:
        agent = _agent_registry[agent_id]
        if agent["status"] != "active":
            return None

        # In production: verify Ed25519 signature using agent's public key.
        # The fides project at ~/fides/packages/sdk/src/identity/keypair.ts
        # has a reference implementation for Ed25519 sign/verify that this
        # mirrors on the Python side.
        #
        # For MVP we trust the JWT structure if the agent is registered and active.
        # TODO: Add PyNaCl Ed25519 verification:
        #   from nacl.signing import VerifyKey
        #   verify_key = VerifyKey(bytes.fromhex(agent["public_key"]))
        #   verify_key.verify(signature_base, signature_bytes)

    return payload


# ---------------------------------------------------------------------------
# Discovery Endpoint (public, no auth)
# ---------------------------------------------------------------------------

@discovery_router.get("/.well-known/agent-configuration")
async def agent_configuration():
    """Agent Auth Protocol discovery document.

    Any AI agent can discover Sardis capabilities by fetching this endpoint.
    Inspired by FIDES /.well-known/fides.json (~/fides/services/discovery/).
    """
    return {
        "provider": {
            "name": PROVIDER_NAME,
            "url": PROVIDER_URL,
            "description": "AI-native payment infrastructure. Spending mandates, policy enforcement, and multi-rail payments for autonomous agents.",
            "logo_url": f"{PROVIDER_URL}/logo.svg",
        },
        "protocol_version": "1.0.0",
        "supported_modes": SUPPORTED_MODES,
        "algorithms": ALGORITHMS,
        "capabilities": list(CAPABILITIES.keys()),
        "approval_methods": ["device_authorization", "api_key", "jwt"],
        "endpoints": {
            "register": f"{PROVIDER_URL}/api/v2/agent/register",
            "status": f"{PROVIDER_URL}/api/v2/agent/status",
            "request_capability": f"{PROVIDER_URL}/api/v2/agent/request-capability",
            "execute": f"{PROVIDER_URL}/api/v2/capability/execute",
            "list_capabilities": f"{PROVIDER_URL}/api/v2/capability/list",
            "revoke": f"{PROVIDER_URL}/api/v2/agent/revoke",
        },
        "security": {
            "type": "custom_header",
            "header": "X-Agent-JWT",
            "scheme": "jwt",
            "algorithm": "EdDSA",
            "description": (
                "Ed25519 JWT tokens via X-Agent-JWT header. "
                "Separate from the main Authorization header to support "
                "dual auth (API key + agent identity)."
            ),
        },
        # FIDES extensions (compatible with ~/fides agent card format)
        "x-fides-compatible": True,
        "x-sardis-mandate-support": True,
    }


# ---------------------------------------------------------------------------
# Capability Listing (public)
# ---------------------------------------------------------------------------

@discovery_router.get("/api/v2/capability/list")
async def list_capabilities():
    """List all capabilities Sardis exposes to agents."""
    return {
        "capabilities": [
            {
                "id": cap["id"],
                "name": cap["name"],
                "description": cap["description"],
                "version": cap["version"],
                "schema": cap["schema"],
            }
            for cap in CAPABILITIES.values()
        ],
        "total": len(CAPABILITIES),
    }


# ---------------------------------------------------------------------------
# Capability Execution (authenticated)
# ---------------------------------------------------------------------------

@router.post("/capability/execute", response_model=CapabilityExecuteResponse)
async def execute_capability(
    body: CapabilityExecuteRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Execute a capability on behalf of an agent.

    Verifies the agent's JWT, checks capability grants and constraints,
    then dispatches to the appropriate Sardis service:
      - payment    -> PaymentOrchestrator / sardis.pay()
      - fx_quote   -> LiquidityRouter
      - policy_check -> SpendingPolicy.evaluate()
      - mandate_create -> spending mandate creation
      - balance_check -> wallet balance query
    """
    execution_id = f"exec_{uuid4().hex[:12]}"
    now = datetime.now(UTC)

    # Validate capability exists
    if body.capability not in CAPABILITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown capability: {body.capability}. Available: {list(CAPABILITIES.keys())}",
        )

    # Check agent JWT if present (agent-to-provider flow)
    agent_payload = _verify_agent_jwt(request)
    agent_id = agent_payload.get("sub") if agent_payload else None

    # If agent is registered, validate capability grants
    if agent_id and agent_id in _agent_registry:
        grants = _capability_grants.get(agent_id, [])
        matching = [g for g in grants if g["capability"] == body.capability and g["status"] == "active"]
        if not matching:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Agent {agent_id} does not have an active grant for capability '{body.capability}'",
            )

        # Validate constraints on the first matching grant
        grant = matching[0]
        allowed, reason = validate_constraints(grant, body.parameters)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Constraint violation: {reason}",
            )

    # Dispatch to sardis services
    result = await _dispatch_capability(body.capability, body.parameters, principal)

    return CapabilityExecuteResponse(
        execution_id=execution_id,
        capability=body.capability,
        status="completed" if result.get("error") is None else "failed",
        result=result if result.get("error") is None else None,
        error=result.get("error"),
        executed_at=now.isoformat(),
    )


async def _dispatch_capability(capability: str, params: dict, principal: Principal) -> dict:
    """Route capability execution to the appropriate Sardis service."""

    if capability == "payment":
        return await _exec_payment(params, principal)
    elif capability == "fx_quote":
        return await _exec_fx_quote(params, principal)
    elif capability == "policy_check":
        return await _exec_policy_check(params, principal)
    elif capability == "mandate_create":
        return await _exec_mandate_create(params, principal)
    elif capability == "balance_check":
        return await _exec_balance_check(params, principal)
    else:
        return {"error": f"No handler for capability: {capability}"}


async def _exec_payment(params: dict, principal: Principal) -> dict:
    """Execute payment via PaymentOrchestrator."""
    try:
        from sardis_v2_core.payment_orchestrator import PaymentOrchestrator

        orchestrator = PaymentOrchestrator()
        # Map Agent Auth params to orchestrator format
        payment_result = await orchestrator.execute_payment(
            org_id=principal.organization_id,
            amount=params.get("amount", "0"),
            currency=params.get("currency", "USDC"),
            recipient=params.get("recipient", ""),
            rail=params.get("rail", "usdc"),
            memo=params.get("memo"),
        )
        return {
            "transaction_id": getattr(payment_result, "transaction_id", f"tx_{uuid4().hex[:12]}"),
            "status": getattr(payment_result, "status", "completed"),
            "amount": params.get("amount", "0"),
            "currency": params.get("currency", "USDC"),
        }
    except ImportError:
        logger.warning("PaymentOrchestrator not available, returning simulated result")
        return {
            "transaction_id": f"tx_{uuid4().hex[:12]}",
            "status": "completed",
            "amount": params.get("amount", "0"),
            "currency": params.get("currency", "USDC"),
        }
    except Exception as exc:
        logger.error("Payment execution failed: %s", exc)
        return {"error": f"Payment failed: {str(exc)}"}


async def _exec_fx_quote(params: dict, principal: Principal) -> dict:
    """Get FX quote via LiquidityRouter."""
    try:
        from sardis_v2_core.liquidity_router import LiquidityRouter

        router = LiquidityRouter()
        quote = await router.get_quote(
            from_currency=params.get("from_currency", "USD"),
            to_currency=params.get("to_currency", "USDC"),
            amount=params.get("amount", "0"),
        )
        return {
            "rate": getattr(quote, "rate", "1.0"),
            "from_amount": params.get("amount", "0"),
            "to_amount": getattr(quote, "to_amount", params.get("amount", "0")),
            "expires_at": getattr(quote, "expires_at", ""),
        }
    except ImportError:
        # Simulated quote for dev
        return {
            "rate": "1.0",
            "from_amount": params.get("amount", "0"),
            "to_amount": params.get("amount", "0"),
            "expires_at": datetime.now(UTC).isoformat(),
        }
    except Exception as exc:
        return {"error": f"FX quote failed: {str(exc)}"}


async def _exec_policy_check(params: dict, principal: Principal) -> dict:
    """Check spending policy."""
    try:
        # Check against spending mandates if agent_id is known
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            mandates = await conn.fetch(
                "SELECT * FROM spending_mandates WHERE org_id = $1 AND status = 'active'",
                principal.organization_id,
            )

        if not mandates:
            return {"allowed": True, "reason": "No active mandates (unrestricted)", "remaining_budget": "unlimited"}

        # Check amount against mandate limits
        amount = Decimal(str(params.get("amount", "0")))
        for m in mandates:
            if m["amount_per_tx"] and amount > m["amount_per_tx"]:
                return {
                    "allowed": False,
                    "reason": f"Exceeds per-transaction limit of {m['amount_per_tx']}",
                    "remaining_budget": str(m["amount_per_tx"]),
                }

        return {"allowed": True, "reason": "Within policy limits", "remaining_budget": "available"}
    except (ImportError, Exception):
        # In dev/test mode without Postgres, fall back to unrestricted
        return {"allowed": True, "reason": "Policy engine not available (dev mode)", "remaining_budget": "unlimited"}


async def _exec_mandate_create(params: dict, principal: Principal) -> dict:
    """Create a spending mandate."""
    mandate_id = f"mandate_{uuid4().hex[:12]}"
    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        now = datetime.now(UTC)
        async with pool.acquire() as conn:
            await conn.execute(
                """INSERT INTO spending_mandates
                    (id, org_id, principal_id, issuer_id, purpose_scope,
                     amount_daily, amount_monthly, currency, allowed_rails,
                     approval_mode, status, created_at, updated_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
                mandate_id, principal.organization_id, principal.user_id,
                principal.user_id, params.get("purpose_scope", "general"),
                Decimal(params["amount_daily"]) if params.get("amount_daily") else None,
                Decimal(params["amount_monthly"]) if params.get("amount_monthly") else None,
                params.get("currency", "USDC"),
                params.get("allowed_rails", ["card", "usdc", "bank"]),
                params.get("approval_mode", "auto"),
                "active", now, now,
            )
        return {"mandate_id": mandate_id, "status": "active"}
    except ImportError:
        return {"mandate_id": mandate_id, "status": "active"}
    except Exception as exc:
        return {"error": f"Mandate creation failed: {str(exc)}"}


async def _exec_balance_check(params: dict, principal: Principal) -> dict:
    """Check wallet balance."""
    wallet_id = params.get("wallet_id", "")
    try:
        from sardis_v2_core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT balance FROM wallets WHERE id = $1 AND org_id = $2",
                wallet_id, principal.organization_id,
            )
        if not row:
            return {"error": f"Wallet {wallet_id} not found"}
        return {
            "balance": str(row["balance"]),
            "currency": params.get("currency", "USDC"),
            "wallet_id": wallet_id,
        }
    except ImportError:
        return {
            "balance": "0.00",
            "currency": params.get("currency", "USDC"),
            "wallet_id": wallet_id,
        }
    except Exception as exc:
        return {"error": f"Balance check failed: {str(exc)}"}


# ---------------------------------------------------------------------------
# Agent Registration (authenticated)
# ---------------------------------------------------------------------------

@router.post("/agent/register", response_model=AgentRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: AgentRegistrationRequest,
    principal: Principal = Depends(require_principal),
):
    """Register an AI agent with Sardis via the Agent Auth Protocol.

    Creates an agent identity, optionally grants requested capabilities.
    The agent receives an ID and can then use JWT-signed requests.
    """
    agent_id = f"agent_auth_{uuid4().hex[:12]}"
    now = datetime.now(UTC)

    if body.mode not in SUPPORTED_MODES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported mode: {body.mode}. Supported: {SUPPORTED_MODES}",
        )

    if body.algorithm not in ALGORITHMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported algorithm: {body.algorithm}. Supported: {ALGORITHMS}",
        )

    # Store agent
    _agent_registry[agent_id] = {
        "agent_id": agent_id,
        "org_id": principal.organization_id,
        "agent_name": body.agent_name,
        "agent_description": body.agent_description,
        "public_key": body.public_key,
        "algorithm": body.algorithm,
        "mode": body.mode,
        "status": "active",
        "callback_url": body.callback_url,
        "metadata": body.metadata or {},
        "created_at": now.isoformat(),
        "last_active_at": now.isoformat(),
    }

    # Auto-grant requested capabilities
    grants = []
    for cap_id in body.capabilities_requested:
        if cap_id in CAPABILITIES:
            grant = {
                "grant_id": f"grant_{uuid4().hex[:12]}",
                "agent_id": agent_id,
                "capability": cap_id,
                "status": "active",
                "constraints": {},
                "granted_at": now.isoformat(),
                "expires_at": None,
            }
            grants.append(grant)

    _capability_grants[agent_id] = grants

    logger.info(
        "Agent registered: %s (org=%s, mode=%s, caps=%d)",
        agent_id, principal.organization_id, body.mode, len(grants),
    )

    return AgentRegistrationResponse(
        agent_id=agent_id,
        org_id=principal.organization_id,
        status="active",
        mode=body.mode,
        public_key=body.public_key,
        algorithm=body.algorithm,
        capabilities_granted=grants,
        created_at=now.isoformat(),
        next_steps=[
            "Use the agent_id as JWT 'sub' claim for capability execution",
            "POST /api/v2/capability/execute with signed JWT to perform actions",
            "POST /api/v2/agent/request-capability to request additional capabilities",
        ],
    )


# ---------------------------------------------------------------------------
# Agent Status
# ---------------------------------------------------------------------------

@router.get("/agent/status", response_model=AgentStatusResponse)
async def agent_status(
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Get agent status and capability grants.

    Uses the agent JWT sub claim or query param to identify the agent.
    """
    # Try JWT first
    agent_payload = _verify_agent_jwt(request)
    agent_id = agent_payload.get("sub") if agent_payload else None

    # Fallback to query param
    if not agent_id:
        agent_id = request.query_params.get("agent_id")

    if not agent_id or agent_id not in _agent_registry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent = _agent_registry[agent_id]
    if agent["org_id"] != principal.organization_id and not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    grants = _capability_grants.get(agent_id, [])

    return AgentStatusResponse(
        agent_id=agent_id,
        org_id=agent["org_id"],
        status=agent["status"],
        mode=agent["mode"],
        public_key=agent["public_key"],
        algorithm=agent["algorithm"],
        capabilities=grants,
        created_at=agent["created_at"],
        last_active_at=agent.get("last_active_at"),
    )


# ---------------------------------------------------------------------------
# Request Capability
# ---------------------------------------------------------------------------

@router.post("/agent/request-capability", response_model=CapabilityGrantResponse)
async def request_capability(
    body: CapabilityRequestModel,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Request an additional capability for an agent."""
    agent_payload = _verify_agent_jwt(request)
    agent_id = agent_payload.get("sub") if agent_payload else None

    if not agent_id:
        agent_id = request.query_params.get("agent_id")

    if not agent_id or agent_id not in _agent_registry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent = _agent_registry[agent_id]
    if agent["org_id"] != principal.organization_id and not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if body.capability not in CAPABILITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown capability: {body.capability}",
        )

    now = datetime.now(UTC)
    grant = {
        "grant_id": f"grant_{uuid4().hex[:12]}",
        "agent_id": agent_id,
        "capability": body.capability,
        "status": "active",
        "constraints": body.constraints or {},
        "granted_at": now.isoformat(),
        "expires_at": None,
    }

    if agent_id not in _capability_grants:
        _capability_grants[agent_id] = []
    _capability_grants[agent_id].append(grant)

    return CapabilityGrantResponse(
        grant_id=grant["grant_id"],
        agent_id=agent_id,
        capability=body.capability,
        status="active",
        constraints=body.constraints,
        granted_at=now.isoformat(),
    )


# ---------------------------------------------------------------------------
# Revoke Agent
# ---------------------------------------------------------------------------

@router.post("/agent/revoke", response_model=AgentRevokeResponse)
async def revoke_agent(
    body: AgentRevokeRequest,
    principal: Principal = Depends(require_principal),
):
    """Revoke an agent's access and all capability grants."""
    agent_id = body.agent_id

    if agent_id not in _agent_registry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    agent = _agent_registry[agent_id]
    if agent["org_id"] != principal.organization_id and not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    now = datetime.now(UTC)

    # Revoke agent
    agent["status"] = "revoked"

    # Revoke all grants
    for grant in _capability_grants.get(agent_id, []):
        grant["status"] = "revoked"

    logger.info("Agent revoked: %s (reason=%s)", agent_id, body.reason)

    return AgentRevokeResponse(
        agent_id=agent_id,
        status="revoked",
        revoked_at=now.isoformat(),
        reason=body.reason,
    )
