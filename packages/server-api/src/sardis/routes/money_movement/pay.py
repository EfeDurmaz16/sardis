"""Unified payment endpoint — the simplest way to pay with Sardis.

POST /api/v2/pay
    → validates inputs
    → auto-routes to cheapest chain (Phase 2) or uses explicit chain
    → detects cross-currency and auto-swaps (Phase 3)
    → builds a mandate chain
    → calls PaymentOrchestrator.execute_chain()
    → returns a PaymentResult with status enum + route metadata + FX info

Phase 2 additions:
    - `chain` is now optional — omit it to let Sardis pick the cheapest route
    - Auto-routing uses LiquidityRouter.find_best_route() across supported chains
    - Route selection: lowest (gas + bridge_fee + slippage)
    - Fallback: if best route fails, tries next cheapest
    - Response includes `route` field showing selected chain + provider

Phase 3 additions:
    - Cross-currency FX: user sends USD, recipient gets EUR (USDC→EURC)
    - Fiat currency codes mapped to stablecoin tokens (USD→USDC, EUR→EURC)
    - Auto-swap via LiquidityRouter (Tempo DEX or Uniswap V3)
    - 30s quote TTL, 1% (100 bps) slippage tolerance
    - Response includes `fx` field with rate, provider, slippage info
    - Supported: USDC↔EURC, USDC↔USDT (and fiat aliases USD, EUR)
"""
from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sardis_v2_core.mandates import (
    CartMandate,
    IntentMandate,
    MandateChain,
    PaymentMandate,
)
from sardis_v2_core.orchestrator import (
    ChainExecutionError,
    ComplianceViolationError,
    KYAViolationError,
    MandateViolationError,
    PaymentOrchestrator,
    PolicyViolationError,
)
from sardis_v2_core.policy_explainer import explain_denial

from sardis.authz import Principal, require_principal
from sardis.idempotency import get_idempotency_key, run_idempotent

router = APIRouter()
logger = logging.getLogger(__name__)

# Chains to evaluate during auto-routing, ordered by preference.
# The router will quote all of them and pick the cheapest.
AUTO_ROUTE_CHAINS = ["base", "tempo", "ethereum", "arbitrum", "optimism"]

# ---------------------------------------------------------------------------
# Phase 3: Cross-currency FX constants
# ---------------------------------------------------------------------------

# Map fiat currency codes and stablecoin symbols to canonical token symbols.
CURRENCY_TO_TOKEN: dict[str, str] = {
    "USD": "USDC",
    "EUR": "EURC",
    "USDT": "USDT",
    "USDC": "USDC",
    "EURC": "EURC",
}

# Supported cross-currency pairs (from_token, to_token).
SUPPORTED_FX_PAIRS: set[tuple[str, str]] = {
    ("USDC", "EURC"),
    ("EURC", "USDC"),
    ("USDC", "USDT"),
    ("USDT", "USDC"),
}

# FX quote TTL in seconds.
FX_QUOTE_TTL_SECONDS = 30

# Default slippage tolerance in basis points (1% = 100 bps).
FX_SLIPPAGE_TOLERANCE_BPS = 100


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


@dataclass
class PayDependencies:
    orchestrator: PaymentOrchestrator
    chain_mode: str = "live"  # "live" bypasses simulation; anything else triggers sandbox


def get_deps() -> PayDependencies:
    raise NotImplementedError("Must be wired via dependency_overrides")


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class PayStatus(str, Enum):
    pending = "pending"
    confirming = "confirming"
    completed = "completed"
    failed = "failed"
    blocked = "blocked"


class PayRequest(BaseModel):
    to: str = Field(..., description="Recipient address or merchant domain")
    amount: str = Field(..., description="Payment amount (e.g. '25.00')")
    currency: str = Field(default="USDC", description="Token / currency")
    chain: str | None = Field(
        default=None,
        description=(
            "Target blockchain. If omitted, Sardis auto-selects the "
            "cheapest route across supported chains."
        ),
    )
    mandate_id: str | None = Field(default=None, description="Spending mandate ID")


class PolicyExplanationResponse(BaseModel):
    allowed: bool
    summary: str
    checks_passed: list[str] = []
    checks_failed: list[str] = []
    suggested_action: str | None = None
    reason_code: str | None = None


class RouteInfo(BaseModel):
    """Metadata about the route selected for this payment."""
    chain: str
    provider: str
    estimated_fee_bps: int = 0
    route_type: str = "direct"
    auto_routed: bool = False


class FXInfo(BaseModel):
    """FX swap details — only present when a cross-currency swap occurred."""
    from_currency: str
    to_currency: str
    rate: str
    provider: str
    slippage_bps: int
    fee_bps: int = 0
    input_amount: str
    output_amount: str


class PayResponse(BaseModel):
    status: PayStatus
    tx_hash: str | None = None
    ledger_tx_id: str | None = None
    chain: str | None = None
    message: str | None = None
    mandate_id: str | None = None
    route: RouteInfo | None = None
    fx: FXInfo | None = None
    policy_explanation: PolicyExplanationResponse | None = None
    simulated: bool = False


# ---------------------------------------------------------------------------
# Phase 3: Cross-currency FX helpers
# ---------------------------------------------------------------------------


def _resolve_token(currency: str) -> str | None:
    """Map a fiat currency code or token symbol to its canonical token.

    Returns None if the currency is unsupported.
    """
    return CURRENCY_TO_TOKEN.get(currency.upper())


def _is_cross_currency(request_currency: str, sender_token: str) -> bool:
    """Detect whether a payment requires an FX swap.

    ``request_currency`` is what the caller asked for (e.g. "EUR").
    ``sender_token`` is the canonical token the sender holds (e.g. "USDC").
    """
    target_token = _resolve_token(request_currency)
    if target_token is None:
        return False
    return target_token != sender_token


async def _get_fx_quote(
    from_token: str,
    to_token: str,
    amount: Decimal,
    chain: str | None = None,
) -> dict[str, Any]:
    """Get an FX quote from the LiquidityRouter.

    Returns a dict with rate, output, provider, fee_bps, slippage_bps,
    and a ``quoted_at`` epoch timestamp (TTL = 30 s).

    Raises ``HTTPException(422)`` for unsupported pairs and
    ``HTTPException(503)`` when no adapter can produce a quote.
    """
    pair = (from_token, to_token)
    if pair not in SUPPORTED_FX_PAIRS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Unsupported currency pair: {from_token} -> {to_token}. "
                f"Supported: {', '.join(f'{a}->{b}' for a, b in sorted(SUPPORTED_FX_PAIRS))}"
            ),
        )

    try:
        from sardis_chain.liquidity_router import LiquidityRouter
        router_instance = LiquidityRouter()
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FX infrastructure (LiquidityRouter) is not available",
        )

    target_chain = chain or "base"
    try:
        route = await router_instance.find_best_route(
            from_token=from_token,
            to_token=to_token,
            amount=amount,
            from_chain=target_chain,
        )
    except Exception as exc:
        logger.error("FX quote failed for %s->%s: %s", from_token, to_token, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"FX quote unavailable: {exc}",
        )

    return {
        "rate": route.estimated_rate,
        "output": route.estimated_output,
        "provider": route.provider,
        "fee_bps": route.estimated_fee_bps,
        "slippage_bps": FX_SLIPPAGE_TOLERANCE_BPS,
        "chain": route.chain,
        "quoted_at": time.time(),
    }


def _check_slippage(
    quote: dict[str, Any],
    actual_output: Decimal,
    expected_output: Decimal,
) -> str | None:
    """Return an error message if slippage exceeds tolerance, else None."""
    if expected_output <= 0:
        return None
    actual_bps = int(
        (1 - actual_output / expected_output) * 10000
    )
    if actual_bps > FX_SLIPPAGE_TOLERANCE_BPS:
        return (
            f"Slippage {actual_bps} bps exceeds tolerance "
            f"{FX_SLIPPAGE_TOLERANCE_BPS} bps. "
            f"Expected {expected_output}, got {actual_output}. "
            f"Request a fresh quote."
        )
    return None


# ---------------------------------------------------------------------------
# Auto-routing helpers
# ---------------------------------------------------------------------------


async def _find_best_chain(
    currency: str, amount: Decimal
) -> list[dict[str, Any]]:
    """Rank chains by total cost (gas + bridge fee + slippage).

    Returns a list of dicts sorted by estimated cost, each containing:
      - chain: str
      - provider: str
      - estimated_fee_bps: int
      - route_type: str
    """
    try:
        from sardis_chain.liquidity_router import LiquidityRouter

        router_instance = LiquidityRouter()
    except ImportError:
        logger.warning("LiquidityRouter not available — defaulting to base")
        return [{"chain": "base", "provider": "default", "estimated_fee_bps": 0, "route_type": "direct"}]

    candidates: list[dict[str, Any]] = []
    for chain in AUTO_ROUTE_CHAINS:
        try:
            route = await router_instance.find_best_route(
                from_token=currency,
                to_token=currency,
                amount=amount,
                from_chain=chain,
                to_chain=chain,
            )
            candidates.append({
                "chain": route.chain,
                "provider": route.provider,
                "estimated_fee_bps": route.estimated_fee_bps,
                "route_type": route.route_type,
            })
        except Exception as e:
            logger.debug("Auto-route quote failed for %s: %s", chain, e)

    if not candidates:
        # Absolute fallback
        candidates.append({
            "chain": "base",
            "provider": "fallback",
            "estimated_fee_bps": 0,
            "route_type": "direct",
        })

    # Sort by fee (lowest first)
    candidates.sort(key=lambda c: c["estimated_fee_bps"])
    return candidates


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "",
    response_model=PayResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute a payment",
    description=(
        "Unified payment endpoint. Validates inputs, enforces policy, "
        "and executes on-chain. If `chain` is omitted, Sardis auto-selects "
        "the cheapest route across supported chains. If the requested currency "
        "differs from the sender's token, Sardis auto-swaps via the best "
        "FX adapter (Tempo DEX or Uniswap V3) before transferring."
    ),
    tags=["pay"],
)
async def pay(
    body: PayRequest,
    request: Request,
    principal: Principal = Depends(require_principal),
    deps: PayDependencies = Depends(get_deps),
) -> PayResponse:
    idem_key = get_idempotency_key(request)
    if idem_key:
        async def _execute_idempotent() -> tuple[int, Any]:
            response = await _execute_pay(body=body, principal=principal, deps=deps)
            return status.HTTP_200_OK, response.model_dump(mode="json")

        return await run_idempotent(
            request=request,
            principal=principal,
            operation="pay.execute",
            key=idem_key,
            payload=body.model_dump(mode="json"),
            fn=_execute_idempotent,
        )

    return await _execute_pay(body=body, principal=principal, deps=deps)


async def _execute_pay(
    *,
    body: PayRequest,
    principal: Principal,
    deps: PayDependencies,
) -> PayResponse:
    # Parse amount
    try:
        amount = Decimal(body.amount)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid amount: {body.amount!r}",
        )

    # ── Phase 3: resolve currency & detect cross-currency ───────────
    # Map fiat codes to stablecoin tokens (USD→USDC, EUR→EURC, etc.)
    target_token = _resolve_token(body.currency)
    if target_token is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=(
                f"Unsupported currency: {body.currency!r}. "
                f"Supported: {', '.join(sorted(CURRENCY_TO_TOKEN.keys()))}"
            ),
        )

    # ── Sandbox / simulated mode short-circuit ─────────────────────
    # When chain_mode is not "live", return a simulated payment instead
    # of hitting the orchestrator (which requires funded wallets and
    # on-chain infrastructure).  All input validation above still runs,
    # so callers see real 422 errors for bad amounts/currencies.
    if deps.chain_mode != "live":
        selected_chain = body.chain or "base"
        mandate_id = body.mandate_id or f"pay_{principal.user_id}"
        sim_tx_hash = f"0xsim_{uuid.uuid4().hex}"
        sim_ledger_id = f"sim_ledger_{uuid.uuid4().hex[:12]}"

        logger.info(
            "Simulated payment: %s %s from %s to %s on %s (chain_mode=%s)",
            body.amount, body.currency, principal.user_id, body.to,
            selected_chain, deps.chain_mode,
        )

        return PayResponse(
            status=PayStatus.completed,
            tx_hash=sim_tx_hash,
            ledger_tx_id=sim_ledger_id,
            chain=selected_chain,
            message=f"Simulated payment of {body.amount} {body.currency} to {body.to}",
            mandate_id=mandate_id,
            route=RouteInfo(
                chain=selected_chain,
                provider="simulated",
                estimated_fee_bps=0,
                route_type="simulated",
                auto_routed=body.chain is None,
            ),
            simulated=True,
        )

    # The sender's token defaults to USDC (the base stablecoin).
    # In the future this could be resolved from the sender's wallet balance.
    sender_token = "USDC"

    cross_currency = _is_cross_currency(body.currency, sender_token)
    fx_info: FXInfo | None = None
    fx_quote: dict[str, Any] | None = None

    if cross_currency:
        # Get FX quote — raises 422 for unsupported pairs, 503 if unavailable
        fx_quote = await _get_fx_quote(
            from_token=sender_token,
            to_token=target_token,
            amount=amount,
            chain=body.chain,
        )

        logger.info(
            "Cross-currency detected: %s (%s) -> %s at rate %s via %s",
            sender_token, body.currency, target_token,
            fx_quote["rate"], fx_quote["provider"],
        )

        fx_info = FXInfo(
            from_currency=sender_token,
            to_currency=target_token,
            rate=str(fx_quote["rate"]),
            provider=fx_quote["provider"],
            slippage_bps=fx_quote["slippage_bps"],
            fee_bps=fx_quote["fee_bps"],
            input_amount=str(amount),
            output_amount=str(fx_quote["output"]),
        )

    # Determine the token to use for the on-chain transfer.
    # For cross-currency, the mandate uses the *target* token (e.g. EURC).
    transfer_token = target_token
    transfer_amount = amount
    if cross_currency and fx_quote:
        transfer_amount = fx_quote["output"]

    # ── Phase 2: resolve chain ──────────────────────────────────────
    # Iron rule: explicit chain always wins.
    auto_routed = body.chain is None
    if auto_routed:
        ranked_chains = await _find_best_chain(transfer_token, transfer_amount)
    else:
        ranked_chains = [{
            "chain": body.chain,
            "provider": "explicit",
            "estimated_fee_bps": 0,
            "route_type": "direct",
        }]

    # Build a minimal mandate chain for the orchestrator
    mandate_id = body.mandate_id or f"pay_{principal.user_id}"

    # Try each candidate chain in order (cheapest first).
    last_error: Exception | None = None
    for candidate in ranked_chains:
        selected_chain = candidate["chain"]

        intent = IntentMandate(
            mandate_id=f"intent_{mandate_id}",
            from_agent=principal.user_id,
            to_merchant=body.to,
            amount_minor=int(transfer_amount * 100),
            currency=transfer_token,
            purpose=f"sardis.pay to {body.to}",
        )
        cart = CartMandate(
            mandate_id=f"cart_{mandate_id}",
            items=[{
                "merchant": body.to,
                "amount_minor": int(transfer_amount * 100),
                "currency": transfer_token,
            }],
            total_minor=int(transfer_amount * 100),
            currency=transfer_token,
        )
        payment = PaymentMandate(
            mandate_id=mandate_id,
            from_agent=principal.user_id,
            to_merchant=body.to,
            amount_minor=int(transfer_amount * 100),
            currency=transfer_token,
            chain=selected_chain,
            token=transfer_token,
        )
        chain = MandateChain(intent=intent, cart=cart, payment=payment)

        route_info = RouteInfo(
            chain=selected_chain,
            provider=candidate["provider"],
            estimated_fee_bps=candidate["estimated_fee_bps"],
            route_type="fx_swap" if cross_currency else candidate["route_type"],
            auto_routed=auto_routed,
        )

        try:
            result = await deps.orchestrator.execute_chain(chain)

            # Phase 3: validate slippage if cross-currency
            if cross_currency and fx_quote:
                slippage_err = _check_slippage(
                    fx_quote, fx_quote["output"], amount * fx_quote["rate"],
                )
                if slippage_err:
                    # Slippage exceeded — get a fresh quote for the error message
                    try:
                        fresh_quote = await _get_fx_quote(
                            from_token=sender_token,
                            to_token=target_token,
                            amount=amount,
                            chain=selected_chain,
                        )
                        fresh_rate = str(fresh_quote["rate"])
                    except Exception:
                        fresh_rate = "unavailable"

                    return PayResponse(
                        status=PayStatus.failed,
                        message=f"{slippage_err} Fresh rate: {fresh_rate}",
                        mandate_id=mandate_id,
                        route=route_info,
                        fx=fx_info,
                    )

            return PayResponse(
                status=PayStatus.completed,
                tx_hash=result.chain_tx_hash,
                ledger_tx_id=result.ledger_tx_id,
                chain=result.chain or selected_chain,
                mandate_id=result.mandate_id,
                route=route_info,
                fx=fx_info,
            )
        except (PolicyViolationError, MandateViolationError, KYAViolationError, ComplianceViolationError) as exc:
            # Policy / compliance errors are not retryable on a different chain
            _reason_attr = {
                PolicyViolationError: "rule_id",
                MandateViolationError: "error_code",
                KYAViolationError: "reason",
                ComplianceViolationError: "rule_id",
            }
            default_code = type(exc).__name__.replace("Error", "").lower() + "_violation"
            reason = getattr(exc, _reason_attr.get(type(exc), "rule_id"), None) or default_code
            explanation = explain_denial(reason)
            return PayResponse(
                status=PayStatus.blocked,
                message=str(exc),
                mandate_id=mandate_id,
                route=route_info,
                fx=fx_info,
                policy_explanation=PolicyExplanationResponse(**explanation.to_dict()),
            )
        except ChainExecutionError as exc:
            last_error = exc
            if auto_routed:
                logger.warning(
                    "Chain execution failed on %s (provider=%s), trying next route: %s",
                    selected_chain, candidate["provider"], exc,
                )
                continue
            # Explicit chain — no fallback
            return PayResponse(
                status=PayStatus.failed,
                message=str(exc),
                mandate_id=mandate_id,
                route=route_info,
                fx=fx_info,
            )
        except Exception as exc:
            last_error = exc
            logger.exception("Unexpected error in /pay on chain %s: %s", selected_chain, exc)
            if auto_routed:
                continue
            return PayResponse(
                status=PayStatus.failed,
                message="Internal error",
                mandate_id=mandate_id,
                route=route_info,
                fx=fx_info,
            )

    # All candidates exhausted (auto-routing only reaches here)
    return PayResponse(
        status=PayStatus.failed,
        message=f"All routes exhausted. Last error: {last_error}" if last_error else "No viable route found",
        mandate_id=mandate_id,
        fx=fx_info,
    )
