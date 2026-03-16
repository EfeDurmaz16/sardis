"""Sardis Telegram Bot — manage agent payments from Telegram.

Commands:
  /start     — Connect Sardis account
  /balance   — Check wallet balance
  /pay       — Execute a payment
  /history   — Recent transactions
  /mandate   — Show active spending mandates
  /revoke    — Emergency revoke a mandate
  /status    — API health check
  /help      — Show available commands

Setup:
  1. Create a bot via @BotFather on Telegram
  2. Set TELEGRAM_BOT_TOKEN env var
  3. Set SARDIS_API_URL and SARDIS_API_KEY env vars
  4. Run: python -m sardis_telegram_bot.bot

This bot is a thin client over the Sardis REST API. All financial
operations go through the same policy enforcement pipeline.
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sardis.telegram")

API_URL = os.getenv("SARDIS_API_URL", "https://api.sardis.sh")
API_KEY = os.getenv("SARDIS_API_KEY", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


async def api_get(path: str) -> dict | list | None:
    """GET request to Sardis API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(f"{API_URL}{path}", headers=HEADERS)
            return r.json() if r.status_code == 200 else None
    except Exception as e:
        logger.error("API GET %s failed: %s", path, e)
        return None


async def api_post(path: str, data: dict | None = None) -> dict | None:
    """POST request to Sardis API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{API_URL}{path}", headers=HEADERS, json=data or {})
            return r.json() if r.status_code in (200, 201, 202) else None
    except Exception as e:
        logger.error("API POST %s failed: %s", path, e)
        return None


# ── Command Handlers ──────────────────────────────────────────────────

async def cmd_start(update, context):
    """Welcome message and connection instructions."""
    await update.message.reply_text(
        "Welcome to Sardis — Payment OS for the Agent Economy.\n\n"
        "Commands:\n"
        "/balance — Check wallet balance\n"
        "/pay <to> <amount> — Execute a payment\n"
        "/history — Recent transactions\n"
        "/mandate — Show active spending mandates\n"
        "/revoke <mandate_id> — Emergency revoke\n"
        "/status — API health check\n"
        "/help — Show this message\n\n"
        f"API: {API_URL}\n"
        f"Connected: {'Yes' if API_KEY else 'No (set SARDIS_API_KEY)'}"
    )


async def cmd_help(update, context):
    """Show help."""
    await cmd_start(update, context)


async def cmd_balance(update, context):
    """Check wallet balance."""
    wallets = await api_get("/api/v2/wallets")
    if not wallets or not isinstance(wallets, list):
        await update.message.reply_text("Could not fetch wallets. Check API connection.")
        return

    if not wallets:
        await update.message.reply_text("No wallets found. Create one in the dashboard.")
        return

    lines = []
    for w in wallets[:5]:
        name = w.get("name", w.get("id", "?"))
        balance = w.get("balance", "?")
        currency = w.get("currency", "USDC")
        status = w.get("status", "?")
        lines.append(f"💰 {name}: {balance} {currency} [{status}]")

    await update.message.reply_text("Wallet Balances:\n\n" + "\n".join(lines))


async def cmd_pay(update, context):
    """Execute a payment: /pay <to> <amount> [purpose]"""
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Usage: /pay <destination> <amount> [purpose]\nExample: /pay openai.com 25 API credits")
        return

    to = args[0]
    try:
        amount = float(args[1])
    except ValueError:
        await update.message.reply_text("Invalid amount. Use a number: /pay openai.com 25")
        return

    purpose = " ".join(args[2:]) if len(args) > 2 else None

    # Confirmation
    msg = f"Confirm payment:\n\n💸 ${amount:.2f} → {to}"
    if purpose:
        msg += f"\nPurpose: {purpose}"
    msg += "\n\nSend /confirm to proceed or /cancel to abort."

    # Store pending payment in context
    context.user_data["pending_payment"] = {"to": to, "amount": amount, "purpose": purpose}
    await update.message.reply_text(msg)


async def cmd_confirm(update, context):
    """Confirm pending payment."""
    payment = context.user_data.pop("pending_payment", None)
    if not payment:
        await update.message.reply_text("No pending payment to confirm.")
        return

    result = await api_post("/api/v2/payments", {
        "destination": payment["to"],
        "amount": str(payment["amount"]),
        "currency": "USDC",
        "purpose": payment.get("purpose"),
    })

    if result:
        status = result.get("status", "unknown")
        tx_id = result.get("tx_id", result.get("id", "?"))
        await update.message.reply_text(
            f"Payment result: {status}\n"
            f"TX ID: {tx_id}\n"
            f"Amount: ${payment['amount']:.2f} → {payment['to']}"
        )
    else:
        await update.message.reply_text("Payment failed. Check API logs for details.")


async def cmd_cancel(update, context):
    """Cancel pending payment."""
    context.user_data.pop("pending_payment", None)
    await update.message.reply_text("Payment cancelled.")


async def cmd_history(update, context):
    """Show recent transactions."""
    data = await api_get("/api/v2/ledger/recent?limit=5")
    if not data or not isinstance(data, list):
        await update.message.reply_text("Could not fetch transactions.")
        return

    if not data:
        await update.message.reply_text("No transactions yet.")
        return

    lines = []
    for tx in data[:5]:
        amount = tx.get("amount", "?")
        currency = tx.get("currency", "USDC")
        status = tx.get("status", "?")
        to = tx.get("to_wallet", tx.get("destination", "?"))
        lines.append(f"{'✅' if status == 'completed' else '❌'} ${amount} {currency} → {to} [{status}]")

    await update.message.reply_text("Recent Transactions:\n\n" + "\n".join(lines))


async def cmd_mandate(update, context):
    """Show active spending mandates."""
    mandates = await api_get("/api/v2/spending-mandates?status_filter=active")
    if not mandates or not isinstance(mandates, list):
        await update.message.reply_text("Could not fetch mandates.")
        return

    if not mandates:
        await update.message.reply_text("No active mandates. Create one in the dashboard.")
        return

    lines = []
    for m in mandates[:5]:
        purpose = m.get("purpose_scope", "No purpose")
        per_tx = m.get("amount_per_tx", "∞")
        spent = m.get("spent_total", "0")
        total = m.get("amount_total", "∞")
        lines.append(
            f"🛡️ {m.get('id', '?')}\n"
            f"   Purpose: {purpose}\n"
            f"   Per-tx: ${per_tx} | Spent: ${spent} / ${total}"
        )

    await update.message.reply_text("Active Mandates:\n\n" + "\n\n".join(lines))


async def cmd_revoke(update, context):
    """Emergency revoke mandate: /revoke <mandate_id> [reason]"""
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /revoke <mandate_id> [reason]")
        return

    mandate_id = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "Revoked via Telegram"

    result = await api_post(f"/api/v2/spending-mandates/{mandate_id}/revoke", {"reason": reason})
    if result:
        await update.message.reply_text(f"🚫 Mandate {mandate_id} permanently revoked.\nReason: {reason}")
    else:
        await update.message.reply_text(f"Failed to revoke mandate {mandate_id}. Check the ID and try again.")


async def cmd_status(update, context):
    """Check API health."""
    data = await api_get("/health")
    if not data:
        await update.message.reply_text("❌ API unreachable")
        return

    status = data.get("status", "unknown")
    emoji = "✅" if status in ("healthy", "ok") else "⚠️" if status == "partial" else "❌"
    uptime = data.get("uptime", "?")

    await update.message.reply_text(f"{emoji} API Status: {status}\nUptime: {uptime}")


# ── Main ──────────────────────────────────────────────────────────────

def main():
    """Start the Telegram bot."""
    if not BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN not set")
        print("Create a bot via @BotFather on Telegram and set the token.")
        return

    try:
        from telegram.ext import ApplicationBuilder, CommandHandler
    except ImportError:
        print("Error: python-telegram-bot not installed")
        print("Install it: pip install python-telegram-bot")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("pay", cmd_pay))
    app.add_handler(CommandHandler("confirm", cmd_confirm))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(CommandHandler("mandate", cmd_mandate))
    app.add_handler(CommandHandler("revoke", cmd_revoke))
    app.add_handler(CommandHandler("status", cmd_status))

    logger.info("Sardis Telegram Bot starting...")
    logger.info("API: %s", API_URL)
    logger.info("API Key: %s", "configured" if API_KEY else "NOT SET")

    app.run_polling()


if __name__ == "__main__":
    main()
