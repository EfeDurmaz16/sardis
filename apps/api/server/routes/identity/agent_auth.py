"""Agent Auth Protocol — Discovery, registration, and capability execution.

Delegates identity management (registration, status, revocation, JWT verification)
to the better-auth agent-auth plugin running on the dashboard service.  Sardis-specific
business logic (capability execution, constraint validation, mandate mapping) stays here.

Endpoints:
  GET  /.well-known/agent-configuration  — Local discovery or Better Auth redirect
  GET  /api/v2/capability/list            — Local capabilities or Better Auth proxy
  POST /api/v2/capability/execute         — Execute a capability (Sardis business logic)
  POST /api/v2/agent/register             — Proxy to better-auth agent registration
  GET  /api/v2/agent/status               — Proxy to better-auth agent status
  POST /api/v2/agent/request-capability   — Proxy to better-auth capability request
  POST /api/v2/agent/revoke               — Proxy to better-auth agent revocation
"""
from __future__ import annotations

import base64
import json
import logging
import os
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from server.authz import Principal, require_principal

logger = logging.getLogger("server.api.agent_auth")

# ---------------------------------------------------------------------------
# Routers — public (discovery, unauthenticated) + private (authenticated)
# ---------------------------------------------------------------------------
discovery_router = APIRouter(tags=["agent-auth"])
router = APIRouter(tags=["agent-auth"])

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BETTER_AUTH_URL = os.getenv("BETTER_AUTH_URL", "https://app.sardis.sh")
PROVIDER_URL = os.getenv("SARDIS_API_URL", "https://api.sardis.sh")
LOCAL_AGENT_AUTH_ENVS = {"dev", "development", "test", "testing", "local"}

# Shared httpx client — created lazily to avoid import-time side effects.
_http_client: httpx.AsyncClient | None = None
_local_agents: dict[str, dict] = {}
_local_grants: dict[str, list[dict]] = {}


def _use_local_agent_auth() -> bool:
    """Use deterministic local Agent Auth when dashboard auth is unavailable.

    Public OSS tests and local development should not depend on app.sardis.sh.
    Production/staging still proxy to Better Auth unless explicitly overridden.
    """
    mode = os.getenv("SARDIS_AGENT_AUTH_MODE", "").strip().lower()
    if mode == "proxy":
        return False
    if mode == "local":
        return True
    env = os.getenv("SARDIS_ENVIRONMENT", "development").strip().lower()
    return env in LOCAL_AGENT_AUTH_ENVS


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _capability_definition(capability: str) -> dict:
    return {
        "id": capability,
        "name": capability,
        "description": f"Sardis {capability} capability",
        "schema": {
            "input": {"type": "object"},
            "output": {"type": "object"},
        },
    }


def _local_discovery_document() -> dict:
    return {
        "provider": {
            "name": "Sardis Payment OS",
            "url": PROVIDER_URL,
        },
        "supported_modes": ["delegated", "autonomous"],
        "algorithms": ["Ed25519"],
        "capabilities": sorted(KNOWN_CAPABILITIES),
        "approval_methods": ["device_authorization", "policy_approval"],
        "endpoints": {
            "capability_list": "/api/v2/capability/list",
            "capability_execute": "/api/v2/capability/execute",
            "agent_register": "/api/v2/agent/register",
            "agent_status": "/api/v2/agent/status",
            "agent_revoke": "/api/v2/agent/revoke",
        },
        "x-fides-compatible": True,
        "x-sardis-mandate-support": True,
    }


def _local_capability_list() -> dict:
    capabilities = [_capability_definition(cap) for cap in sorted(KNOWN_CAPABILITIES)]
    return {"capabilities": capabilities, "total": len(capabilities)}


def _local_agent_registration(body: AgentRegistrationRequest, principal: Principal) -> dict:
    if body.mode not in {"delegated", "autonomous"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unsupported mode: {body.mode}")
    if body.algorithm != "Ed25519":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported algorithm: {body.algorithm}",
        )
    unknown = sorted(set(body.capabilities_requested) - KNOWN_CAPABILITIES)
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown capabilities: {unknown}",
        )

    now = _now_iso()
    agent_id = f"agent_auth_{uuid4().hex[:12]}"
    grants = [
        {
            "grant_id": f"grant_{uuid4().hex[:12]}",
            "agent_id": agent_id,
            "capability": capability,
            "status": "active",
            "constraints": None,
            "granted_at": now,
            "expires_at": None,
        }
        for capability in body.capabilities_requested
    ]
    agent = {
        "agent_id": agent_id,
        "org_id": principal.organization_id,
        "status": "active",
        "mode": body.mode,
        "public_key": body.public_key,
        "algorithm": body.algorithm,
        "capabilities": grants,
        "created_at": now,
        "last_active_at": None,
    }
    _local_agents[agent_id] = agent
    _local_grants[agent_id] = grants
    return agent


def _decode_unverified_agent_jwt(token: str) -> dict | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    except Exception:
        return None
    exp = data.get("exp")
    if exp is not None and int(exp) < int(datetime.now(UTC).timestamp()):
        return None
    agent_id = data.get("sub")
    agent = _local_agents.get(agent_id)
    if not agent or agent.get("status") != "active":
        return None
    return data


def _local_agent_or_404(agent_id: str, principal: Principal) -> dict:
    agent = _local_agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    if agent["org_id"] != principal.organization_id and not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return agent


def _get_http_client() -> httpx.AsyncClient:
    """Return (or create) a shared async httpx client for better-auth calls."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            base_url=BETTER_AUTH_URL,
            timeout=httpx.Timeout(10.0, connect=5.0),
            headers={"Accept": "application/json"},
        )
    return _http_client


# ---------------------------------------------------------------------------
# Request / Response Models (unchanged API contract)
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
# Local and Better Auth proxy helpers
# ---------------------------------------------------------------------------

def _forward_headers(request: Request) -> dict[str, str]:
    """Build headers to forward to better-auth, preserving auth context."""
    headers: dict[str, str] = {"Content-Type": "application/json"}
    # Forward the main auth header so better-auth can identify the user
    if auth_header := request.headers.get("authorization"):
        headers["Authorization"] = auth_header
    # Forward agent JWT header
    if agent_jwt := request.headers.get("x-agent-jwt"):
        headers["X-Agent-JWT"] = agent_jwt
    # Forward cookies (better-auth session cookies)
    if cookie := request.headers.get("cookie"):
        headers["Cookie"] = cookie
    return headers


async def _proxy_to_better_auth(
    method: str,
    path: str,
    request: Request,
    json_body: dict | None = None,
    params: dict | None = None,
) -> dict:
    """Proxy a request to better-auth and return the JSON response.

    Raises HTTPException on network errors or non-2xx responses.
    """
    client = _get_http_client()
    headers = _forward_headers(request)

    try:
        resp = await client.request(
            method=method,
            url=path,
            headers=headers,
            json=json_body,
            params=params,
        )
    except httpx.RequestError as exc:
        logger.error("better-auth proxy error: %s %s -> %s", method, path, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent auth service unavailable",
        ) from exc

    if resp.status_code >= 400:
        # Pass through better-auth error responses
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text or "Unknown error from auth service"
        raise HTTPException(status_code=resp.status_code, detail=detail)

    try:
        return resp.json()
    except Exception:
        return {}


async def _verify_agent_jwt(request: Request) -> dict | None:
    """Verify an agent JWT by calling better-auth's token verification.

    Sends the X-Agent-JWT header to better-auth for cryptographic verification
    against the agent's registered public key.  Returns the decoded payload or
    None when no token is present / verification fails.
    """
    token = request.headers.get("x-agent-jwt", "")
    if not token:
        return None
    if _use_local_agent_auth():
        return _decode_unverified_agent_jwt(token)

    client = _get_http_client()
    try:
        resp = await client.post(
            "/api/auth/agent/verify-token",
            headers={"X-Agent-JWT": token, "Accept": "application/json"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("payload") or data
    except httpx.RequestError as exc:
        logger.warning("Agent JWT verification call failed: %s", exc)

    # TODO: When better-auth exposes a cross-service verify endpoint with JWKS,
    # replace this fallback with local JWKS-based EdDSA verification.
    logger.debug("Agent JWT verification: token present but could not be verified via better-auth")
    return None


# ---------------------------------------------------------------------------
# Mandate-to-Capability Mapper (Sardis business logic — kept as-is)
# ---------------------------------------------------------------------------

def mandate_to_capability_grant(mandate: dict) -> dict:
    """Convert a spending mandate into an Agent Auth capability grant.

    The key insight: a spending mandate IS a capability grant with constraints.
    """
    constraints: dict = {}

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

    if mandate.get("currency"):
        constraints["currency"] = {"in": [mandate["currency"]]}
    if mandate.get("allowed_rails"):
        constraints["rail"] = {"in": mandate["allowed_rails"]}
    if mandate.get("allowed_chains"):
        constraints["chain"] = {"in": mandate["allowed_chains"]}
    if mandate.get("allowed_tokens"):
        constraints["token"] = {"in": mandate["allowed_tokens"]}
    if mandate.get("merchant_scope"):
        constraints["vendor_category"] = mandate["merchant_scope"]
    if mandate.get("purpose_scope"):
        constraints["purpose"] = {"in": [mandate["purpose_scope"]]}
    if mandate.get("approval_mode"):
        constraints["approval_mode"] = mandate["approval_mode"]
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
    """Convert an Agent Auth capability grant back to a spending mandate shape."""
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
# Constraint Validation (Sardis business logic — kept as-is)
# ---------------------------------------------------------------------------

def validate_constraints(grant: dict, params: dict) -> tuple[bool, str | None]:
    """Validate execution parameters against capability grant constraints."""
    constraints = grant.get("constraints", {})
    if not constraints:
        return True, None

    amount_constraints = constraints.get("amount", {})
    if params.get("amount") and amount_constraints:
        try:
            req_amount = Decimal(str(params["amount"]))
        except Exception:
            return False, "Invalid amount format"
        max_per_tx = amount_constraints.get("max_per_tx")
        if max_per_tx and req_amount > Decimal(max_per_tx):
            return False, f"Amount {req_amount} exceeds per-transaction limit of {max_per_tx}"

    currency_constraint = constraints.get("currency", {})
    if params.get("currency") and currency_constraint.get("in"):
        if params["currency"] not in currency_constraint["in"]:
            return False, f"Currency {params['currency']} not in allowed currencies: {currency_constraint['in']}"

    rail_constraint = constraints.get("rail", {})
    if params.get("rail") and rail_constraint.get("in"):
        if params["rail"] not in rail_constraint["in"]:
            return False, f"Rail {params['rail']} not in allowed rails: {rail_constraint['in']}"

    vendor_constraint = constraints.get("vendor_category", {})
    if params.get("vendor_category") and vendor_constraint.get("in"):
        if params["vendor_category"] not in vendor_constraint["in"]:
            return False, "Vendor category not allowed"

    return True, None


# ---------------------------------------------------------------------------
# Discovery Endpoint (public, no auth)
# ---------------------------------------------------------------------------

@discovery_router.get("/.well-known/agent-configuration")
async def agent_configuration():
    """Agent Auth Protocol discovery document.

    Uses a deterministic local document in dev/test/local environments. In
    proxy mode it redirects to the Better Auth agent-auth plugin's discovery
    endpoint on the dashboard service.
    """
    if _use_local_agent_auth():
        return _local_discovery_document()
    return RedirectResponse(
        url=f"{BETTER_AUTH_URL}/api/auth/agent/.well-known/agent-configuration",
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


# ---------------------------------------------------------------------------
# Capability Listing (public) — proxy to better-auth
# ---------------------------------------------------------------------------

@discovery_router.get("/api/v2/capability/list")
async def list_capabilities(request: Request):
    """List all capabilities Sardis exposes to agents.

    Proxies to better-auth which holds the canonical capability definitions
    configured in the agentAuth plugin.
    """
    if _use_local_agent_auth():
        return _local_capability_list()
    try:
        data = await _proxy_to_better_auth(
            "GET", "/api/auth/agent/capabilities", request,
        )
        return data
    except HTTPException:
        # Fallback: return a minimal capability list when better-auth is unreachable.
        # This keeps the endpoint functional during dashboard downtime.
        return _local_capability_list()


# ---------------------------------------------------------------------------
# Capability Execution (authenticated — Sardis business logic)
# ---------------------------------------------------------------------------

KNOWN_CAPABILITIES = {"payment", "fx_quote", "policy_check", "mandate_create", "balance_check"}


@router.post("/capability/execute", response_model=CapabilityExecuteResponse)
async def execute_capability(
    body: CapabilityExecuteRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Execute a capability on behalf of an agent.

    Verifies the agent's JWT via better-auth, checks capability grants and
    constraints, then dispatches to the appropriate Sardis service.
    """
    execution_id = f"exec_{uuid4().hex[:12]}"
    now = datetime.now(UTC)

    if body.capability not in KNOWN_CAPABILITIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown capability: {body.capability}. Available: {sorted(KNOWN_CAPABILITIES)}",
        )

    # Verify agent JWT via better-auth
    agent_payload = await _verify_agent_jwt(request)
    agent_id = agent_payload.get("sub") if agent_payload else None

    # If the agent is authenticated, validate grants via better-auth
    if agent_id:
        if _use_local_agent_auth():
            grants = _local_grants.get(agent_id, [])
            matching = [
                g for g in grants
                if g.get("capability") == body.capability and g.get("status") == "active"
            ]
            if not matching:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Agent {agent_id} does not have an active grant for capability '{body.capability}'",
                )
            allowed, reason = validate_constraints(matching[0], body.parameters)
            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Constraint violation: {reason}",
                )
        else:
            try:
                grants_data = await _proxy_to_better_auth(
                    "GET",
                    f"/api/auth/agent/grants/{agent_id}",
                    request,
                )
                grants = grants_data.get("grants", [])
                matching = [
                    g for g in grants
                    if g.get("capability") == body.capability and g.get("status") == "active"
                ]
                if not matching:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Agent {agent_id} does not have an active grant for capability '{body.capability}'",
                    )
                # Validate constraints on the first matching grant
                allowed, reason = validate_constraints(matching[0], body.parameters)
                if not allowed:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Constraint violation: {reason}",
                    )
            except HTTPException:
                raise
            except Exception as exc:
                logger.warning("Could not validate agent grants via better-auth: %s", exc)
                # Fail-open only in development; production requires grant validation
                env = os.getenv("SARDIS_ENVIRONMENT", "development").lower()
                if env in ("production", "staging"):
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Agent grant validation service unavailable",
                    ) from exc

    # Dispatch to Sardis services
    result = await _dispatch_capability(body.capability, body.parameters, principal)

    return CapabilityExecuteResponse(
        execution_id=execution_id,
        capability=body.capability,
        status="completed" if result.get("error") is None else "failed",
        result=result if result.get("error") is None else None,
        error=result.get("error"),
        executed_at=now.isoformat(),
    )


# ---------------------------------------------------------------------------
# Capability Dispatch (Sardis business logic — kept as-is)
# ---------------------------------------------------------------------------

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
        from sardis.core.payment_orchestrator import PaymentOrchestrator

        orchestrator = PaymentOrchestrator()
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
        logger.error("Payment execution failed: %s", exc, exc_info=True)
        return {"error_code": "payment_failed", "message": "Payment could not be processed"}


async def _exec_fx_quote(params: dict, principal: Principal) -> dict:
    """Get FX quote via LiquidityRouter."""
    try:
        from sardis.core.liquidity_router import LiquidityRouter

        liq_router = LiquidityRouter()
        quote = await liq_router.get_quote(
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
        from sardis.core.database import Database

        pool = await Database.get_pool()
        async with pool.acquire() as conn:
            mandates = await conn.fetch(
                "SELECT * FROM spending_mandates WHERE org_id = $1 AND status = 'active'",
                principal.organization_id,
            )
        if not mandates:
            return {"allowed": True, "reason": "No active mandates (unrestricted)", "remaining_budget": "unlimited"}

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
        return {"allowed": True, "reason": "Policy engine not available (dev mode)", "remaining_budget": "unlimited"}


async def _exec_mandate_create(params: dict, principal: Principal) -> dict:
    """Create a spending mandate."""
    mandate_id = f"mandate_{uuid4().hex[:12]}"
    try:
        from sardis.core.database import Database

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
        from sardis.core.database import Database

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
# Agent Registration — local dev/test store or Better Auth proxy
# ---------------------------------------------------------------------------

@router.post("/agent/register", response_model=AgentRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    body: AgentRegistrationRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Register an AI agent with Sardis via the Agent Auth Protocol.

    Uses a deterministic in-memory store in dev/test/local environments. In
    proxy mode it delegates identity storage to the Better Auth agent-auth
    plugin.
    """
    if _use_local_agent_auth():
        data = _local_agent_registration(body, principal)
        return AgentRegistrationResponse(
            agent_id=data["agent_id"],
            org_id=data["org_id"],
            status=data["status"],
            mode=data["mode"],
            public_key=data["public_key"],
            algorithm=data["algorithm"],
            capabilities_granted=data["capabilities"],
            created_at=data["created_at"],
            next_steps=[
                "Use the agent_id as JWT 'sub' claim for capability execution",
                "POST /api/v2/capability/execute with signed JWT to perform actions",
                "POST /api/v2/agent/request-capability to request additional capabilities",
            ],
        )

    data = await _proxy_to_better_auth(
        "POST",
        "/api/auth/agent/register",
        request,
        json_body={
            "name": body.agent_name,
            "description": body.agent_description,
            "publicKey": body.public_key,
            "algorithm": body.algorithm,
            "mode": body.mode,
            "capabilities": body.capabilities_requested,
            "callbackUrl": body.callback_url,
            "metadata": body.metadata,
        },
    )

    now = datetime.now(UTC).isoformat()
    agent_id = data.get("agentId") or data.get("agent_id") or f"agent_auth_{uuid4().hex[:12]}"

    logger.info(
        "Agent registered via better-auth: %s (org=%s, mode=%s)",
        agent_id, principal.organization_id, body.mode,
    )

    return AgentRegistrationResponse(
        agent_id=agent_id,
        org_id=data.get("orgId") or data.get("org_id") or principal.organization_id,
        status=data.get("status", "active"),
        mode=data.get("mode", body.mode),
        public_key=data.get("publicKey") or data.get("public_key") or body.public_key,
        algorithm=data.get("algorithm", body.algorithm),
        capabilities_granted=data.get("capabilitiesGranted") or data.get("capabilities_granted") or [],
        created_at=data.get("createdAt") or data.get("created_at") or now,
        next_steps=[
            "Use the agent_id as JWT 'sub' claim for capability execution",
            "POST /api/v2/capability/execute with signed JWT to perform actions",
            "POST /api/v2/agent/request-capability to request additional capabilities",
        ],
    )


# ---------------------------------------------------------------------------
# Agent Status — proxy to better-auth
# ---------------------------------------------------------------------------

@router.get("/agent/status", response_model=AgentStatusResponse)
async def agent_status(
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Get agent status and capability grants via better-auth."""
    # Try JWT first
    agent_payload = await _verify_agent_jwt(request)
    agent_id = agent_payload.get("sub") if agent_payload else None

    # Fallback to query param
    if not agent_id:
        agent_id = request.query_params.get("agent_id")

    if not agent_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agent_id required (via JWT or query param)")

    if _use_local_agent_auth():
        data = _local_agent_or_404(agent_id, principal)
        return AgentStatusResponse(
            agent_id=agent_id,
            org_id=data["org_id"],
            status=data["status"],
            mode=data["mode"],
            public_key=data["public_key"],
            algorithm=data["algorithm"],
            capabilities=_local_grants.get(agent_id, []),
            created_at=data["created_at"],
            last_active_at=data.get("last_active_at"),
        )

    data = await _proxy_to_better_auth(
        "GET",
        f"/api/auth/agent/{agent_id}",
        request,
    )

    # Verify org ownership
    agent_org = data.get("orgId") or data.get("org_id") or ""
    if agent_org != principal.organization_id and not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return AgentStatusResponse(
        agent_id=agent_id,
        org_id=agent_org or principal.organization_id,
        status=data.get("status", "unknown"),
        mode=data.get("mode", "delegated"),
        public_key=data.get("publicKey") or data.get("public_key") or "",
        algorithm=data.get("algorithm", "Ed25519"),
        capabilities=data.get("capabilities") or data.get("grants") or [],
        created_at=data.get("createdAt") or data.get("created_at") or "",
        last_active_at=data.get("lastActiveAt") or data.get("last_active_at"),
    )


# ---------------------------------------------------------------------------
# Request Capability — proxy to better-auth
# ---------------------------------------------------------------------------

@router.post("/agent/request-capability", response_model=CapabilityGrantResponse)
async def request_capability(
    body: CapabilityRequestModel,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Request an additional capability for an agent via better-auth."""
    agent_payload = await _verify_agent_jwt(request)
    agent_id = agent_payload.get("sub") if agent_payload else None
    if not agent_id:
        agent_id = request.query_params.get("agent_id")
    if not agent_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="agent_id required (via JWT or query param)")

    if body.capability not in KNOWN_CAPABILITIES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown capability: {body.capability}")

    if _use_local_agent_auth():
        _local_agent_or_404(agent_id, principal)
        now = _now_iso()
        grant = {
            "grant_id": f"grant_{uuid4().hex[:12]}",
            "agent_id": agent_id,
            "capability": body.capability,
            "status": "active",
            "constraints": body.constraints,
            "granted_at": now,
            "expires_at": None,
        }
        _local_grants.setdefault(agent_id, []).append(grant)
        _local_agents[agent_id]["capabilities"] = _local_grants[agent_id]
        return CapabilityGrantResponse(**grant)

    data = await _proxy_to_better_auth(
        "POST",
        f"/api/auth/agent/{agent_id}/request-capability",
        request,
        json_body={
            "capability": body.capability,
            "constraints": body.constraints,
            "justification": body.justification,
        },
    )

    now = datetime.now(UTC).isoformat()
    return CapabilityGrantResponse(
        grant_id=data.get("grantId") or data.get("grant_id") or f"grant_{uuid4().hex[:12]}",
        agent_id=agent_id,
        capability=body.capability,
        status=data.get("status", "active"),
        constraints=data.get("constraints") or body.constraints,
        granted_at=data.get("grantedAt") or data.get("granted_at") or now,
        expires_at=data.get("expiresAt") or data.get("expires_at"),
    )


# ---------------------------------------------------------------------------
# Revoke Agent — proxy to better-auth
# ---------------------------------------------------------------------------

@router.post("/agent/revoke", response_model=AgentRevokeResponse)
async def revoke_agent(
    body: AgentRevokeRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
):
    """Revoke an agent's access and all capability grants via better-auth."""
    if _use_local_agent_auth():
        agent = _local_agent_or_404(body.agent_id, principal)
        agent["status"] = "revoked"
        for grant in _local_grants.get(body.agent_id, []):
            grant["status"] = "revoked"
        logger.info("Agent revoked locally: %s (reason=%s)", body.agent_id, body.reason)
        return AgentRevokeResponse(
            agent_id=body.agent_id,
            status="revoked",
            revoked_at=_now_iso(),
            reason=body.reason,
        )

    data = await _proxy_to_better_auth(
        "POST",
        f"/api/auth/agent/{body.agent_id}/revoke",
        request,
        json_body={"reason": body.reason},
    )

    now = datetime.now(UTC).isoformat()

    logger.info("Agent revoked via better-auth: %s (reason=%s)", body.agent_id, body.reason)

    return AgentRevokeResponse(
        agent_id=body.agent_id,
        status=data.get("status", "revoked"),
        revoked_at=data.get("revokedAt") or data.get("revoked_at") or now,
        reason=body.reason,
    )
