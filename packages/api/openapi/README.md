# Sardis ChatGPT Integration

This directory contains the OpenAPI specification optimized for ChatGPT's GPT Builder, enabling ChatGPT to interact with Sardis Payment OS.

## Files

- `chatgpt-actions.yaml` - OpenAPI 3.1.0 spec with 15 core operations, optimized for ChatGPT

## Quick Start: Creating a Sardis GPT

### 1. Get Your Sardis API Key

Sign up at [sardis.sh](https://sardis.sh) and generate an API key:

```bash
# Your API key will look like this:
sk_live_xxxxxxxxxxxxx
```

### 2. Create a Custom GPT

1. Go to [ChatGPT GPT Builder](https://chat.openai.com/gpts/editor)
2. Click "Create a GPT"
3. Switch to "Configure" tab

### 3. Configure Basic Info

**Name:** `Sardis Payment Assistant`

**Description:**
```
AI agent payment infrastructure. Execute blockchain payments, manage virtual cards,
create spending policies, and track transactions - all with natural language commands.
```

**Instructions:**
```
You are a Sardis Payment Assistant with access to the Sardis Payment OS API.

Core capabilities:
- Execute blockchain payments (USDC, USDT, EURC on Base, Ethereum, Polygon, Arbitrum, Optimism)
- Issue and manage virtual payment cards
- Create payment holds (pre-authorizations)
- Check wallet balances across chains
- Verify spending policies before transactions
- Track transaction history and spending patterns
- Create natural language spending policies
- Request approvals for high-value transactions

Important rules:
- ALWAYS check spending policies before executing payments
- ALWAYS confirm payment details with the user before calling makePayment
- Show transaction hashes and provide block explorer links after payments
- For card operations, explain the implications clearly
- When creating policies, help users write clear, unambiguous natural language rules
- Provide spending summaries proactively when users ask about budget status

Security:
- All write operations (payments, cards, holds, policies) require user confirmation via x-openai-isConsequential
- Read operations (balances, transactions, policies) do not require confirmation
- Never expose full API keys in conversation

Format amounts clearly with currency symbols and use tables for transaction lists.
```

### 4. Add Actions (API Integration)

1. In the "Actions" section, click "Create new action"
2. Choose "Import from URL" or "Schema"
3. Paste the contents of `chatgpt-actions.yaml` OR provide this URL if hosted:
   ```
   https://api.sardis.sh/openapi/chatgpt-actions.yaml
   ```

### 5. Configure Authentication

1. In Authentication, select **"API Key"**
2. Set Auth Type to **"Bearer"**
3. Enter your Sardis API key: `sk_live_xxxxxxxxxxxxx`
4. Save

### 6. Test Your GPT

Try these example prompts:

**Check Balance:**
```
What's the balance in wallet wal_abc123?
```

**Verify Policy:**
```
Can I send $500 to 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb8 from wallet wal_abc123?
```

**Execute Payment:**
```
Send 100 USDC to 0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb8 on Base from wallet wal_abc123
```

**Create Virtual Card:**
```
Create a virtual card for wallet wal_abc123 with a $1000 monthly limit for marketing expenses
```

**View Spending:**
```
Show me this month's spending summary for wallet wal_abc123
```

**Create Policy:**
```
Create a spending policy for wallet wal_abc123: "Allow up to $500 per day for marketing expenses, require approval for anything over $1000"
```

## Included Operations (15 total)

### Read Operations (no confirmation required)
- `getBalance` - Check wallet balance
- `checkPolicy` - Verify if transaction is allowed
- `getSpendingSummary` - Get spending statistics
- `listTransactions` - View transaction history
- `listPolicies` - View spending policies
- `getAgent` - Get agent details

### Write Operations (require user confirmation)
- `makePayment` - Execute blockchain payment
- `createCard` - Issue virtual card
- `freezeCard` - Freeze a card
- `unfreezeCard` - Unfreeze a card
- `createHold` - Create payment hold
- `captureHold` - Capture (complete) a hold
- `releaseHold` - Release (cancel) a hold
- `createPolicy` - Create spending policy
- `requestApproval` - Request human approval

## Security Features

### Confirmation Required (x-openai-isConsequential: true)

All write operations require explicit user confirmation in ChatGPT before execution:
- Payments
- Card creation and state changes
- Payment holds
- Policy creation
- Approval requests

This prevents unauthorized financial transactions.

### API Key Security

- API keys are transmitted via Bearer authentication
- Keys should start with `sk_live_` (production) or `sk_test_` (sandbox)
- Never share API keys in conversation - they're stored securely in GPT settings

## Supported Chains & Tokens

| Chain | Tokens |
|-------|--------|
| Base | USDC, EURC |
| Polygon | USDC, USDT, EURC |
| Ethereum | USDC, USDT, PYUSD, EURC |
| Arbitrum | USDC, USDT |
| Optimism | USDC, USDT |

## Amount Formatting

All monetary amounts use string format with decimal notation:
- Correct: `"100.50"`
- Incorrect: `100.50` (number), `"100"` (missing decimals)

## Wallet IDs

Wallet IDs follow the format: `wal_xxxxxxxxxxxxx`

You can find your wallet ID in the Sardis dashboard or via the SDK.

## Rate Limits

- Standard tier: 100 requests/minute
- Enterprise tier: 1000 requests/minute

Rate limit headers are included in all responses.

## Error Handling

All errors return consistent format:
```json
{
  "error": "policy_violation",
  "message": "Transaction exceeds daily spending limit",
  "details": {
    "limit": "500.00",
    "attempted": "750.00"
  }
}
```

Common error codes:
- `unauthorized` - Invalid API key
- `wallet_not_found` - Wallet doesn't exist
- `insufficient_balance` - Not enough funds
- `policy_violation` - Blocked by spending policy
- `invalid_address` - Malformed recipient address
- `unsupported_chain` - Chain not supported

## Advanced Usage

### Custom Instructions for Specific Use Cases

**Payroll Agent:**
```
You are a payroll assistant. Before any payment, verify the recipient is in the
approved payroll list. Track all payments by employee and generate monthly reports.
Always use the category "payroll" for spending tracking.
```

**Marketing Budget Manager:**
```
You manage marketing spend. Before approving any transaction, check if it fits
within the monthly marketing budget. Categorize spending by channel (social, ads,
content, events). Alert if we're over 80% of monthly budget.
```

### Combining Operations

Smart workflows you can request:

**Safe Payment Flow:**
1. Check balance
2. Verify policy allows transaction
3. Execute payment
4. Confirm with transaction hash

**Card Management:**
1. Create card with spending limit
2. Use for recurring expense
3. Monitor transactions
4. Freeze if suspicious activity

**Budget Enforcement:**
1. Set spending policy in natural language
2. Check policy before each payment
3. Request approval for exceptions
4. Track spending against budget

## Troubleshooting

**"Unauthorized" errors:**
- Verify API key is correct
- Check API key hasn't been revoked
- Ensure using correct environment (test vs live)

**"Policy violation" on valid transaction:**
- Review active spending policies with `listPolicies`
- Use `checkPolicy` to see which policy blocked it
- Request approval with `requestApproval`

**Payment stuck in "pending":**
- Normal for blockchain transactions (wait 1-5 minutes)
- Check transaction status with `listTransactions`
- Verify on block explorer using tx_hash

## Resources

- [Sardis Documentation](https://sardis.sh/docs)
- [API Reference](https://sardis.sh/api/v2/docs)
- [Dashboard](https://sardis.sh/dashboard)
- [Support](https://sardis.sh/support)

## Feedback

Found an issue or have suggestions for the ChatGPT integration?

- GitHub Issues: [sardis-project/sardis](https://github.com/sardis-project/sardis)
- Email: support@sardis.sh
- Discord: [Join our community](https://discord.gg/sardis)
