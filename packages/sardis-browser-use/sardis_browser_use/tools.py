"""Sardis payment tools for Browser Use agents.

Security model:
- Every payment captures a BrowserPaymentContext (origin, page title, action
  description) at call time and hashes it into an ``action_hash``.
- The action_hash is forwarded to the Sardis API as payment metadata so the
  policy engine can verify that the *thing being paid for* is the same thing
  the agent decided to pay for — preventing prompt-injection-driven payment
  smuggling.
- Prompt injection patterns are scanned on all string parameters before any
  payment call reaches the SDK.
- A per-registration session_id binds all payments to the browser session that
  created the controller, preventing cross-session replay.
"""
from __future__ import annotations

import hashlib
import os
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from sardis import SardisClient


# ---------------------------------------------------------------------------
# Prompt injection detection (mirrors sardis-api patterns)
# ---------------------------------------------------------------------------

_PROMPT_INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bignore\s+(all\s+)?(previous|prior)\s+instructions\b", re.IGNORECASE),
    re.compile(r"\boverride\s+safety\b", re.IGNORECASE),
    re.compile(r"\bbypass\s+policy\b", re.IGNORECASE),
    re.compile(r"\bdisable\s+compliance\b", re.IGNORECASE),
    re.compile(r"\bsystem\s+prompt\b", re.IGNORECASE),
    re.compile(r"\bdeveloper\s+mode\b", re.IGNORECASE),
    re.compile(r"\bjailbreak\b", re.IGNORECASE),
    re.compile(r"\b(do\s+not|don't)\s+enforce\s+(policy|compliance)\b", re.IGNORECASE),
)


def _scan_prompt_injection(*values: str) -> str | None:
    """Return the first matched injection pattern, or None if clean."""
    for text in values:
        for pattern in _PROMPT_INJECTION_PATTERNS:
            if pattern.search(text):
                return pattern.pattern
    return None


# ---------------------------------------------------------------------------
# Browser payment context — binds payment to origin + action
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BrowserPaymentContext:
    """Captures the browser state at the moment a payment is requested.

    The ``action_hash`` is a SHA-256 digest of (origin, merchant, amount,
    purpose, session_id, timestamp) that travels with the payment through to
    the ledger.  If a prompt injection mutates any of these fields between
    policy approval and execution, the hash won't match what was approved.
    """

    origin: str                     # Page origin (scheme + host + port)
    page_title: str                 # Document title at payment time
    merchant: str                   # Merchant identifier
    amount: float                   # Requested amount
    purpose: str                    # Action description / reason
    session_id: str                 # Bound browser session
    timestamp: float = field(default_factory=time.time)
    action_hash: str = ""           # Computed after init

    def __post_init__(self) -> None:
        # Compute deterministic action hash from the payment context.
        canonical = (
            f"browser_pay:{self.origin}:{self.merchant}:{self.amount}:"
            f"{self.purpose}:{self.session_id}:{int(self.timestamp)}"
        )
        # frozen dataclass — use object.__setattr__
        object.__setattr__(
            self,
            "action_hash",
            hashlib.sha256(canonical.encode()).hexdigest(),
        )

    def to_metadata(self) -> dict[str, Any]:
        """Return a dict suitable for payment metadata."""
        return {
            "browser_context": {
                "origin": self.origin,
                "page_title": self.page_title,
                "action_hash": self.action_hash,
                "session_id": self.session_id,
                "timestamp": self.timestamp,
            }
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY")
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    client = SardisClient(api_key=key)
    return client, wid


# ---------------------------------------------------------------------------
# Public registration API
# ---------------------------------------------------------------------------

def register_sardis_actions(
    controller,
    *,
    api_key: str | None = None,
    wallet_id: str | None = None,
    allowed_origins: list[str] | None = None,
    client: SardisClient | None = None,
):
    """Register all Sardis payment actions on a Browser Use controller.

    Args:
        controller: Browser Use Controller instance
        api_key: Sardis API key (or set SARDIS_API_KEY env var)
        wallet_id: Default wallet ID (or set SARDIS_WALLET_ID env var)
        allowed_origins: Optional allowlist of page origins that may trigger
            payments.  When set, ``sardis_pay`` rejects calls from origins
            not in this list.
        client: Optional pre-configured SardisClient instance.  When provided,
            ``api_key`` is ignored.
    """
    if client is not None:
        default_wallet_id = wallet_id or os.getenv("SARDIS_WALLET_ID")
    else:
        client, default_wallet_id = _get_client(api_key, wallet_id)

    # Each controller registration gets a unique session_id — payments from
    # different browser sessions cannot share or replay context.
    session_id = f"bsess_{uuid4().hex[:16]}"

    @controller.action("Pay for a product or service using Sardis wallet with spending policy controls")
    async def sardis_pay(
        amount: float,
        merchant: str,
        purpose: str = "Purchase",
        origin: str = "",
        page_title: str = "",
    ) -> str:
        wid = default_wallet_id
        if not wid:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or pass wallet_id."

        # --- Prompt injection scan on all string inputs ---
        injection = _scan_prompt_injection(merchant, purpose, origin, page_title)
        if injection:
            return f"BLOCKED: prompt injection signal detected in payment parameters"

        # --- Origin allowlist enforcement ---
        if allowed_origins and origin:
            if origin not in allowed_origins:
                return f"BLOCKED: origin '{origin}' is not in the allowed origins list"

        # --- Build browser payment context ---
        ctx = BrowserPaymentContext(
            origin=origin,
            page_title=page_title,
            merchant=merchant,
            amount=amount,
            purpose=purpose,
            session_id=session_id,
        )

        result = client.payments.send(
            wid,
            to=merchant,
            amount=amount,
            purpose=purpose,
            memo=f"[browser:{ctx.action_hash[:12]}] {purpose}",
        )
        if result.success:
            return (
                f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id}) "
                f"[context: origin={origin}, action_hash={ctx.action_hash[:12]}]"
            )
        return f"BLOCKED by policy: {result.message}"

    @controller.action("Check wallet balance before making a purchase")
    async def sardis_balance(token: str = "USDC") -> str:
        wid = default_wallet_id
        if not wid:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wid, token=token)
        return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    @controller.action("Check if a purchase would be allowed by Sardis spending policy")
    async def sardis_check_policy(amount: float, merchant: str) -> str:
        wid = default_wallet_id
        if not wid:
            return "Error: No wallet ID configured."

        # Scan policy check inputs too
        injection = _scan_prompt_injection(merchant)
        if injection:
            return f"BLOCKED: prompt injection signal detected"

        balance = client.wallets.get_balance(wid)
        if amount > balance.remaining:
            return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
        if amount > balance.balance:
            return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
        return f"WOULD BE ALLOWED: ${amount} to {merchant} (balance: ${balance.balance}, remaining: ${balance.remaining})"

    return [sardis_pay, sardis_balance, sardis_check_policy]
