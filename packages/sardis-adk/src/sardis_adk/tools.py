"""
Google ADK FunctionTool implementations for Sardis.

Each function follows the ADK convention: plain functions with typed
parameters and detailed docstrings that the LLM reads to decide when
and how to call each tool.  A module-level ``_client`` / ``_wallet_id``
pair is configured at import time by ``SardisToolkit``.
"""
from __future__ import annotations

from sardis import SardisClient

# ---------------------------------------------------------------------------
# Module-level state, configured by SardisToolkit.configure()
# ---------------------------------------------------------------------------

_client: SardisClient | None = None
_wallet_id: str | None = None


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


# ---------------------------------------------------------------------------
# Protocol v1.0 tools
# ---------------------------------------------------------------------------


def sardis_mint_payment_object(
    mandate_id: str,
    merchant_id: str,
    amount: str,
    currency: str = "USDC",
    memo: str = "",
) -> dict:
    """Mint a signed, one-time payment object from a spending mandate.

    Use this tool when the agent needs to create a payment token that
    can be presented to a merchant for verification and settlement.
    Payment objects are the core settlement primitive in Sardis.

    Args:
        mandate_id: Spending mandate to mint from (e.g. "mandate_abc123").
        merchant_id: Merchant this payment is for.
        amount: Exact payment amount (e.g. "25.00").
        currency: Token currency (default: USDC).
        memo: Optional payment memo.

    Returns:
        dict with keys:
            object_id (str): Unique payment object ID.
            mandate_id (str): Source mandate.
            merchant_id (str): Target merchant.
            amount (str): Payment amount.
            status (str): Object status (minted).
            session_hash (str): Replay protection hash.
            expires_at (str): Expiration timestamp.
    """
    client = _get_client()
    result = client._request("POST", "/api/v2/payment-objects/mint", json={
        "mandate_id": mandate_id,
        "merchant_id": merchant_id,
        "amount": amount,
        "currency": currency,
        "memo": memo or None,
    })
    return result


def sardis_get_fx_quote(
    from_currency: str,
    to_currency: str,
    amount: str,
    chain: str = "tempo",
) -> dict:
    """Get an FX quote for a stablecoin swap.

    Use this tool when the agent needs to convert between stablecoins
    (e.g., USDC to EURC). Returns a quote with the exchange rate.

    Args:
        from_currency: Source currency (e.g. "USDC").
        to_currency: Target currency (e.g. "EURC").
        amount: Amount to convert.
        chain: Chain for the swap (default: tempo).

    Returns:
        dict with keys:
            quote_id (str): Quote identifier (use to execute).
            rate (str): Exchange rate.
            from_amount (str): Input amount.
            to_amount (str): Output amount.
            expires_at (str): Quote expiry.
    """
    client = _get_client()
    return client._request("POST", "/api/v2/fx/quote", json={
        "from_currency": from_currency,
        "to_currency": to_currency,
        "from_amount": amount,
        "chain": chain,
    })


def sardis_create_subscription(
    mandate_id: str,
    merchant_id: str,
    amount: str,
    billing_cycle: str = "monthly",
    currency: str = "USDC",
) -> dict:
    """Create a recurring subscription payment.

    Use this tool when the agent needs to set up automatic recurring
    payments to a merchant (e.g., monthly API subscriptions).

    Args:
        mandate_id: Spending mandate backing the subscription.
        merchant_id: Merchant to pay.
        amount: Charge amount per cycle.
        billing_cycle: How often to charge (daily/weekly/monthly/annual).
        currency: Payment currency (default: USDC).

    Returns:
        dict with keys:
            subscription_id (str): Unique subscription ID.
            status (str): Subscription status.
            next_charge_at (str): Next charge date.
            billing_cycle (str): Billing frequency.
    """
    client = _get_client()
    return client._request("POST", "/api/v2/subscriptions", json={
        "mandate_id": mandate_id,
        "merchant_id": merchant_id,
        "charge_amount": amount,
        "billing_cycle": billing_cycle,
        "currency": currency,
    })


def sardis_create_escrow(
    payment_object_id: str,
    merchant_id: str,
    amount: str,
    timelock_hours: int = 72,
) -> dict:
    """Create an escrow hold for a payment.

    Use this tool when the agent needs to hold funds in escrow until
    delivery is confirmed. Supports automatic release after timelock.

    Args:
        payment_object_id: Payment object to escrow.
        merchant_id: Merchant receiving the payment.
        amount: Escrow amount.
        timelock_hours: Auto-release after this many hours (default: 72).

    Returns:
        dict with keys:
            hold_id (str): Escrow hold ID.
            status (str): Hold status.
            timelock_expires_at (str): Auto-release time.
    """
    client = _get_client()
    return client._request("POST", "/api/v2/escrow", json={
        "payment_object_id": payment_object_id,
        "merchant_id": merchant_id,
        "amount": amount,
        "timelock_hours": timelock_hours,
    })
