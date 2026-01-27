# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-01-27

### Added

- Initial release of the Sardis MCP Server
- 36 MCP tools for AI agent payment operations
- **Wallet Tools (5)**:
  - `sardis_get_wallet` - Get wallet details and configuration
  - `sardis_get_balance` - Get current wallet balance and spending limits
  - `sardis_create_wallet` - Create a new MPC wallet with optional spending policy
  - `sardis_update_wallet_policy` - Update the spending policy for a wallet
  - `sardis_list_wallets` - List all wallets
- **Payment Tools (3)**:
  - `sardis_pay` - Execute a secure payment with policy validation
  - `sardis_get_transaction` - Get transaction status and details
  - `sardis_list_transactions` - List recent transactions
- **Policy Tools (3)**:
  - `sardis_check_policy` - Check if a payment would be allowed
  - `sardis_validate_limits` - Validate spending against limits
  - `sardis_check_compliance` - Check vendor against compliance rules
- **Hold Tools (6)**:
  - `sardis_create_hold` - Create a pre-authorization hold
  - `sardis_capture_hold` - Capture a previously created hold
  - `sardis_void_hold` - Void/cancel a hold
  - `sardis_get_hold` - Get hold status and details
  - `sardis_list_holds` - List active holds
  - `sardis_extend_hold` - Extend the expiration of a hold
- **Agent Tools (4)**:
  - `sardis_create_agent` - Create a new AI agent
  - `sardis_get_agent` - Get agent details
  - `sardis_list_agents` - List all agents
  - `sardis_update_agent` - Update agent configuration
- **Card Tools (6)**:
  - `sardis_issue_card` - Issue a virtual card
  - `sardis_get_card` - Get virtual card details
  - `sardis_list_cards` - List all virtual cards
  - `sardis_freeze_card` - Temporarily freeze a card
  - `sardis_unfreeze_card` - Unfreeze a card
  - `sardis_cancel_card` - Permanently cancel a card
- **Fiat Tools (4)**:
  - `sardis_fund_wallet` - Fund from bank account
  - `sardis_withdraw_to_bank` - Withdraw to bank account
  - `sardis_get_funding_status` - Check funding status
  - `sardis_get_withdrawal_status` - Check withdrawal status
- **Approval Tools (2)**:
  - `sardis_request_approval` - Request human approval
  - `sardis_get_approval_status` - Check approval status
- **Spending Analytics Tools (3)**:
  - `sardis_get_spending_summary` - Get spending summary
  - `sardis_get_spending_by_vendor` - Get spending by vendor
  - `sardis_get_spending_by_category` - Get spending by category

### Features

- Financial Hallucination Prevention through policy validation
- Simulated mode for testing without API key
- Claude Desktop and Cursor integration support
- Natural language spending policies
- Risk scoring for each payment request
- Human-in-the-loop approval workflows

[0.1.0]: https://github.com/sardis-network/sardis/releases/tag/mcp-server-v0.1.0
