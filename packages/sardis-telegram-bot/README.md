# Sardis Telegram Bot

Manage AI agent payments directly from Telegram.

## Setup

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram
2. Set environment variables:
   ```bash
   export TELEGRAM_BOT_TOKEN="your-bot-token"
   export SARDIS_API_KEY=<your-api-key>
   export SARDIS_API_URL="https://api.sardis.sh"
   ```
3. Install dependencies:
   ```bash
   pip install python-telegram-bot httpx
   ```
4. Run:
   ```bash
   python -m packages.sardis-telegram-bot.bot
   ```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Connect and show available commands |
| `/balance` | Check wallet balances |
| `/pay <to> <amount> [purpose]` | Execute a payment (with confirmation) |
| `/confirm` | Confirm pending payment |
| `/cancel` | Cancel pending payment |
| `/history` | Show recent transactions |
| `/mandate` | Show active spending mandates |
| `/revoke <id> [reason]` | Emergency revoke a mandate |
| `/status` | Check API health |
| `/help` | Show commands |

## Architecture

The bot is a thin client over the Sardis REST API. All financial
operations go through the same policy enforcement pipeline as the
dashboard, CLI, and SDK. No payment logic lives in the bot itself.
