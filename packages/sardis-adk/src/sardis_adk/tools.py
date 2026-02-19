"""
Google ADK FunctionTool implementations for Sardis.

Each function follows the ADK convention: plain functions with typed
parameters and detailed docstrings that the LLM reads to decide when
and how to call each tool.  A module-level ``_client`` / ``_wallet_id``
pair is configured at import time by ``SardisToolkit``.
"""
from __future__ import annotations

from typing import Optional

from sardis import SardisClient

# ---------------------------------------------------------------------------
# Module-level state, configured by SardisToolkit.configure()
# ---------------------------------------------------------------------------

_client: Optional[SardisClient] = None
_wallet_id: Optional[str] = None


def configure(client: SardisClient, wallet_id: str) -> None:
    """Bind a SardisClient and default wallet to the tool functions."""
    global _client, _wallet_id
    _client = client
    _wallet_id = wallet_id


def _get_client() -> SardisClient:
    if _client is None:
        raise RuntimeError(
            "Sardis tools have not been configured. "
            "Call SardisToolkit(...).get_tools() or tools.configure() first."
        )
    return _client


def _get_wallet_id() -> str:
    if _wallet_id is None:
        raise RuntimeError(
            "No default wallet_id configured. "
            "Pass wallet_id to SardisToolkit or call tools.configure()."
        )
    return _wallet_id


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------


def sardis_pay(
    to: str,
    amount: str,
    token: str = "USDC",
    purpose: str = "",
) -> dict:
    """Execute a payment through Sardis with automatic policy enforcement.

    Use this tool when the user asks you to send money, pay a merchant,
    transfer funds, or make any kind of payment.  Sardis enforces the
    wallet's spending policy automatically -- if the payment violates a
    limit the transaction will be rejected and the response will explain
    why.

    Args:
        to: Recipient address or merchant identifier (e.g. "openai.com",
            "0xabc...", "anthropic:api").
        amount: Payment amount in token units (e.g. "25.00").
        token: Token to pay with. Defaults to USDC.  Supported:
            USDC, USDT, PYUSD, EURC.
        purpose: Human-readable reason for the payment (e.g. "Monthly
            API subscription").  Some policies require a purpose.

    Returns:
        dict with keys:
            success (bool): Whether the payment went through.
            tx_id (str): Unique transaction identifier.
            status (str): Transaction status (executed, rejected, etc.).
            amount (str): Amount that was sent.
            to (str): Recipient.
            token (str): Token used.
            message (str): Human-readable status message.
            balance_after (float): Wallet balance after the payment.
    """
    client = _get_client()
    wallet_id = _get_wallet_id()

    result = client.payments.send(
        wallet_id=wallet_id,
        to=to,
        amount=amount,
        token=token,
        memo=purpose or None,
    )

    wallet = client.wallets.get(wallet_id)
    return {
        "success": result.success,
        "tx_id": result.tx_id,
        "status": result.status.value,
        "amount": str(result.amount),
        "to": result.to,
        "token": token,
        "message": result.message or "",
        "balance_after": float(wallet.balance),
    }


def sardis_check_balance(
    token: str = "USDC",
    chain: str = "base",
) -> dict:
    """Check the current wallet balance and spending limits.

    Use this tool when the user asks about their balance, how much they
    can still spend, remaining limits, or anything related to wallet
    funds.

    Args:
        token: Token to query (default: USDC).
        chain: Blockchain network (default: base).

    Returns:
        dict with keys:
            wallet_id (str): The wallet identifier.
            balance (float): Current balance in token units.
            token (str): Token type.
            chain (str): Blockchain network.
            spent_total (float): Total amount spent so far.
            limit_per_tx (float): Maximum per-transaction limit.
            limit_total (float): Maximum total spending limit.
            remaining (float): How much more can be spent.
    """
    client = _get_client()
    wallet_id = _get_wallet_id()

    info = client.wallets.get_balance(wallet_id, chain=chain, token=token)
    return {
        "wallet_id": info.wallet_id,
        "balance": info.balance,
        "token": info.token,
        "chain": info.chain,
        "spent_total": info.spent_total,
        "limit_per_tx": info.limit_per_tx,
        "limit_total": info.limit_total,
        "remaining": info.remaining,
    }


def sardis_check_policy(
    to: str,
    amount: str,
    token: str = "USDC",
    purpose: str = "",
) -> dict:
    """Check whether a payment would be allowed by the wallet's policy.

    Use this tool BEFORE making a payment if the user wants to verify
    whether a transaction will succeed, or when they ask "can I pay X?"
    or "would this be allowed?".  This does NOT execute the payment.

    Args:
        to: Recipient address or merchant identifier.
        amount: Payment amount to validate.
        token: Token type (default: USDC).
        purpose: Payment purpose (some policies require this).

    Returns:
        dict with keys:
            allowed (bool): Whether the policy would approve this payment.
            reason (str): Explanation of the decision.
            checks_passed (list[str]): Which policy checks passed.
            checks_failed (list[str]): Which policy checks failed.
            requires_approval (bool): Whether human approval is needed.
    """
    from sardis import Policy

    client = _get_client()
    wallet_id = _get_wallet_id()

    wallet = client.wallets.get(wallet_id)

    # Use the wallet's built-in policy limits to construct a policy
    policy = Policy(
        max_per_tx=float(wallet.limit_per_tx),
        max_total=float(wallet.limit_total),
    )
    result = policy.check(
        amount=float(amount),
        wallet=wallet,
        destination=to,
        token=token,
        purpose=purpose or None,
    )
    return {
        "allowed": result.approved,
        "reason": result.reason or "",
        "checks_passed": result.checks_passed,
        "checks_failed": result.checks_failed,
        "requires_approval": result.requires_approval,
    }


def sardis_set_policy(
    policy_text: str,
    max_per_tx: str = "",
    max_total: str = "",
) -> dict:
    """Set or update the spending policy on the wallet using natural language.

    Use this tool when the user says things like "set my limit to $50
    per transaction", "change daily budget to $500", or gives any
    natural-language spending rule.

    The policy_text is parsed for limits.  You can also pass explicit
    numeric overrides via max_per_tx / max_total.

    Args:
        policy_text: Natural language policy description (e.g.
            "Max $50 per transaction, daily limit $500").
        max_per_tx: Optional explicit per-transaction limit override.
        max_total: Optional explicit total spending limit override.

    Returns:
        dict with keys:
            success (bool): Whether the policy was applied.
            wallet_id (str): The wallet that was updated.
            limit_per_tx (float): New per-transaction limit.
            limit_total (float): New total spending limit.
            policy_text (str): The natural language policy stored.
    """
    import re
    from decimal import Decimal

    client = _get_client()
    wallet_id = _get_wallet_id()

    wallet = client.wallets.get(wallet_id)

    # Parse natural language for limits
    parsed_per_tx = None
    parsed_total = None
    text_lower = policy_text.lower()

    # Per-transaction patterns
    m = re.search(
        r'(?:max\s+)?\$?([\d,]+(?:\.\d+)?)\s*(?:per\s+(?:transaction|tx)|/tx)',
        text_lower,
    )
    if m:
        parsed_per_tx = float(m.group(1).replace(",", ""))

    # Daily / total patterns
    m = re.search(
        r'(?:daily\s+limit|max\s*/\s*day)\s*\$?([\d,]+(?:\.\d+)?)',
        text_lower,
    )
    if m:
        parsed_total = float(m.group(1).replace(",", ""))
    if parsed_total is None:
        m = re.search(r'max\s+\$?([\d,]+(?:\.\d+)?)\s*/\s*day', text_lower)
        if m:
            parsed_total = float(m.group(1).replace(",", ""))
    if parsed_total is None:
        m = re.search(r'daily\s+limit\s+\$?([\d,]+(?:\.\d+)?)', text_lower)
        if m:
            parsed_total = float(m.group(1).replace(",", ""))

    # Explicit overrides take precedence
    new_per_tx = float(max_per_tx) if max_per_tx else parsed_per_tx
    new_total = float(max_total) if max_total else parsed_total

    if new_per_tx is not None:
        wallet.limit_per_tx = Decimal(str(new_per_tx))
    if new_total is not None:
        wallet.limit_total = Decimal(str(new_total))

    # Store the policy text if wallet supports it
    if hasattr(wallet, "_policy_text"):
        wallet._policy_text = policy_text

    return {
        "success": True,
        "wallet_id": wallet_id,
        "limit_per_tx": float(wallet.limit_per_tx),
        "limit_total": float(wallet.limit_total),
        "policy_text": policy_text,
    }


def sardis_list_transactions(
    limit: int = 10,
) -> dict:
    """List recent transactions from the wallet's ledger.

    Use this tool when the user asks to see their transaction history,
    recent payments, spending activity, or audit trail.

    Args:
        limit: Maximum number of transactions to return (default: 10,
            max: 50).

    Returns:
        dict with keys:
            wallet_id (str): The wallet queried.
            count (int): Number of transactions returned.
            transactions (list[dict]): Each entry has tx_id, amount,
                to, status, currency, timestamp, and purpose.
    """
    client = _get_client()
    wallet_id = _get_wallet_id()

    capped_limit = min(limit, 50)
    entries = client.ledger.list(wallet_id=wallet_id, limit=capped_limit)

    txns = []
    for entry in entries:
        txns.append({
            "tx_id": entry.tx_id,
            "amount": str(entry.amount),
            "to": entry.merchant,
            "status": entry.status,
            "currency": entry.currency,
            "timestamp": entry.timestamp.isoformat(),
            "purpose": entry.purpose or "",
        })

    return {
        "wallet_id": wallet_id,
        "count": len(txns),
        "transactions": txns,
    }
