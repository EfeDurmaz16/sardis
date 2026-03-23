"""Sardis payment tools for OpenAI Agents SDK."""
from __future__ import annotations

import os

from sardis import SardisClient


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY")
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    client = SardisClient(api_key=key)
    return client, wid


# Module-level client for decorator-based tools
_default_client: SardisClient | None = None
_default_wallet_id: str | None = None


def configure(api_key: str | None = None, wallet_id: str | None = None):
    """Configure the default Sardis client for tool functions.

    Call this before using the tools, or set SARDIS_API_KEY and SARDIS_WALLET_ID env vars.
    """
    global _default_client, _default_wallet_id
    _default_client, _default_wallet_id = _get_client(api_key, wallet_id)


def _ensure_client():
    global _default_client, _default_wallet_id
    if _default_client is None:
        _default_client, _default_wallet_id = _get_client()
    return _default_client, _default_wallet_id


try:
    from agents import function_tool

    @function_tool
    def sardis_pay(amount: float, merchant: str, purpose: str = "Payment") -> str:
        """Execute a policy-controlled payment from the agent's Sardis wallet. Checks spending limits before executing."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or call configure()."
        result = client.payments.send(wallet_id, to=merchant, amount=amount, purpose=purpose)
        if result.success:
            return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
        return f"BLOCKED by policy: {result.message}"

    @function_tool
    def sardis_check_balance(token: str = "USDC") -> str:
        """Check current wallet balance and spending limits."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id, token=token)
        return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    @function_tool
    def sardis_check_policy(amount: float, merchant: str) -> str:
        """Check if a payment would pass spending policy before executing."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id)
        if amount > balance.remaining:
            return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
        if amount > balance.balance:
            return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
        return f"WOULD BE ALLOWED: ${amount} to {merchant}"

    @function_tool
    def sardis_mint_payment(mandate_id: str, amount: float, token: str = "USDC", recipient: str = "", purpose: str = "") -> str:
        """Mint a payment object from a spending mandate. Returns a portable, verifiable payment instrument."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or call configure()."
        result = client.payment_objects.mint(
            wallet_id, mandate_id=mandate_id, amount=amount, token=token,
            recipient=recipient or None, purpose=purpose or None,
        )
        return f"MINTED: Payment object {result.payment_object_id} for ${amount} {token} (mandate: {mandate_id})"

    @function_tool
    def sardis_get_fx_quote(from_token: str, to_token: str, amount: float) -> str:
        """Get an FX quote for swapping between stablecoins. Does NOT execute the swap."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        quote = client.fx.get_quote(wallet_id, from_token=from_token, to_token=to_token, amount=amount)
        return (
            f"FX Quote {quote.quote_id}: {amount} {from_token} -> {quote.output_amount} {to_token} "
            f"(rate: {quote.exchange_rate}, fee: {quote.fee}, expires: {quote.expires_at})"
        )

    @function_tool
    def sardis_create_subscription(mandate_id: str, recipient: str, amount: float, interval: str = "monthly", token: str = "USDC", purpose: str = "") -> str:
        """Create a recurring payment subscription funded by a spending mandate."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or call configure()."
        result = client.subscriptions.create(
            wallet_id, mandate_id=mandate_id, recipient=recipient, amount=amount,
            token=token, interval=interval, purpose=purpose or None,
        )
        return (
            f"SUBSCRIPTION CREATED: {result.subscription_id} — ${amount} {token} {interval} to {recipient} "
            f"(next: {result.next_payment_at})"
        )

    @function_tool
    def sardis_create_escrow(recipient: str, amount: float, token: str = "USDC", description: str = "", deadline_hours: int = 168, arbiter: str = "") -> str:
        """Create an escrow hold that locks funds until delivery is confirmed or a dispute is resolved."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or call configure()."
        result = client.escrows.create(
            wallet_id, recipient=recipient, amount=amount, token=token,
            description=description or None, deadline_hours=deadline_hours,
            arbiter=arbiter or None,
        )
        return f"ESCROW CREATED: {result.escrow_id} — ${amount} {token} held for {recipient} (deadline: {result.deadline})"

    @function_tool
    def sardis_list_transactions(limit: int = 10) -> str:
        """List recent transactions from the agent's Sardis wallet."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        entries = client.ledger.list(wallet_id=wallet_id, limit=min(limit, 50))
        lines = [f"  {e.tx_id}: ${e.amount} to {e.merchant} ({e.status})" for e in entries]
        return f"Recent transactions ({len(lines)}):\n" + "\n".join(lines) if lines else "No transactions found."

    @function_tool
    def sardis_set_policy(policy_text: str, max_per_tx: float = 0, max_total: float = 0) -> str:
        """Set or update the spending policy using natural language."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.policies.update(wallet_id, policy_text=policy_text,
                                         max_per_tx=max_per_tx or None, max_total=max_total or None)
        return f"Policy updated: per-tx=${result.limit_per_tx}, total=${result.limit_total}"

    @function_tool
    def sardis_create_hold(merchant: str, amount: float, token: str = "USDC") -> str:
        """Create a payment hold (authorization without capture)."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.holds.create(wallet_id, merchant=merchant, amount=amount, token=token)
        return f"Hold created: {result.hold_id} — ${amount} {token} for {merchant}"

    @function_tool
    def sardis_capture_hold(hold_id: str, amount: float = 0) -> str:
        """Capture (settle) a previously created hold."""
        client, _ = _ensure_client()
        result = client.holds.capture(hold_id, amount=amount or None)
        return f"Hold {hold_id} captured: ${result.captured_amount}"

    @function_tool
    def sardis_void_hold(hold_id: str) -> str:
        """Void (cancel) a previously created hold."""
        client, _ = _ensure_client()
        client.holds.void(hold_id)
        return f"Hold {hold_id} voided."

    @function_tool
    def sardis_get_mandate(mandate_id: str) -> str:
        """Get details of a spending mandate."""
        client, _ = _ensure_client()
        result = client._request("GET", f"/api/v2/mandates/{mandate_id}")
        return f"Mandate {mandate_id}: status={result.get('status')}, per_tx=${result.get('amount_per_tx')}, total=${result.get('amount_total')}"

    @function_tool
    def sardis_list_mandates(status: str = "active") -> str:
        """List spending mandates."""
        client, _ = _ensure_client()
        results = client._request("GET", f"/api/v2/mandates?status={status}")
        items = results if isinstance(results, list) else results.get("mandates", [])
        lines = [f"  {m.get('id')}: {m.get('purpose_scope', 'N/A')} (${m.get('amount_total', '?')})" for m in items[:10]]
        return f"Mandates ({len(lines)}):\n" + "\n".join(lines) if lines else "No mandates found."

    @function_tool
    def sardis_get_payment_object(object_id: str) -> str:
        """Get details of a payment object."""
        client, _ = _ensure_client()
        result = client._request("GET", f"/api/v2/payment-objects/{object_id}")
        return f"PaymentObject {object_id}: status={result.get('status')}, amount=${result.get('exact_amount')}, merchant={result.get('merchant_id')}"

except ImportError:
    # openai-agents not installed - provide plain function versions
    def sardis_pay(amount: float, merchant: str, purpose: str = "Payment") -> str:
        """Execute a policy-controlled payment from the agent's Sardis wallet."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.payments.send(wallet_id, to=merchant, amount=amount, purpose=purpose)
        if result.success:
            return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
        return f"BLOCKED by policy: {result.message}"

    def sardis_check_balance(token: str = "USDC") -> str:
        """Check current wallet balance and spending limits."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id, token=token)
        return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    def sardis_check_policy(amount: float, merchant: str) -> str:
        """Check if a payment would pass spending policy before executing."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id)
        if amount > balance.remaining:
            return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
        if amount > balance.balance:
            return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
        return f"WOULD BE ALLOWED: ${amount} to {merchant}"

    def sardis_mint_payment(mandate_id: str, amount: float, token: str = "USDC", recipient: str = "", purpose: str = "") -> str:
        """Mint a payment object from a spending mandate."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.payment_objects.mint(
            wallet_id, mandate_id=mandate_id, amount=amount, token=token,
            recipient=recipient or None, purpose=purpose or None,
        )
        return f"MINTED: Payment object {result.payment_object_id} for ${amount} {token} (mandate: {mandate_id})"

    def sardis_get_fx_quote(from_token: str, to_token: str, amount: float) -> str:
        """Get an FX quote for swapping between stablecoins."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        quote = client.fx.get_quote(wallet_id, from_token=from_token, to_token=to_token, amount=amount)
        return (
            f"FX Quote {quote.quote_id}: {amount} {from_token} -> {quote.output_amount} {to_token} "
            f"(rate: {quote.exchange_rate}, fee: {quote.fee}, expires: {quote.expires_at})"
        )

    def sardis_create_subscription(mandate_id: str, recipient: str, amount: float, interval: str = "monthly", token: str = "USDC", purpose: str = "") -> str:
        """Create a recurring payment subscription funded by a spending mandate."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.subscriptions.create(
            wallet_id, mandate_id=mandate_id, recipient=recipient, amount=amount,
            token=token, interval=interval, purpose=purpose or None,
        )
        return (
            f"SUBSCRIPTION CREATED: {result.subscription_id} — ${amount} {token} {interval} to {recipient} "
            f"(next: {result.next_payment_at})"
        )

    def sardis_create_escrow(recipient: str, amount: float, token: str = "USDC", description: str = "", deadline_hours: int = 168, arbiter: str = "") -> str:
        """Create an escrow hold that locks funds until delivery is confirmed."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.escrows.create(
            wallet_id, recipient=recipient, amount=amount, token=token,
            description=description or None, deadline_hours=deadline_hours,
            arbiter=arbiter or None,
        )
        return f"ESCROW CREATED: {result.escrow_id} — ${amount} {token} held for {recipient} (deadline: {result.deadline})"


def get_sardis_tools() -> list:
    """Get all 15 Sardis tools for an OpenAI Agent."""
    return [
        sardis_pay,
        sardis_check_balance,
        sardis_check_policy,
        sardis_list_transactions,
        sardis_set_policy,
        sardis_create_hold,
        sardis_capture_hold,
        sardis_void_hold,
        sardis_get_mandate,
        sardis_list_mandates,
        sardis_mint_payment,
        sardis_get_fx_quote,
        sardis_create_subscription,
        sardis_create_escrow,
        sardis_get_payment_object,
    ]
