# @sardis/mcp-server

[![npm](https://img.shields.io/npm/v/@sardis/mcp-server?color=CB3837&logo=npm&logoColor=white)](https://www.npmjs.com/package/@sardis/mcp-server)
[![npm downloads](https://img.shields.io/npm/dm/@sardis/mcp-server.svg)](https://www.npmjs.com/package/@sardis/mcp-server)
[![Node](https://img.shields.io/node/v/@sardis/mcp-server)](https://www.npmjs.com/package/@sardis/mcp-server)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?logo=discord&logoColor=white)](https://discord.gg/XMA9JwDJ)

**Payment tools for AI agents over the [Model Context Protocol](https://modelcontextprotocol.io).**

`@sardis/mcp-server` exposes the [Sardis](https://sardis.sh) financial authority layer as a stdio MCP server: 50+ tools for wallets, holds, cards, payments, approvals, policy checks, facility gates, and spending analytics — usable from Claude Desktop, Cursor, ChatGPT, Windsurf, VS Code, Claude Code, and any other MCP-compatible client. Non-custodial. Policy-enforced. Audit-ready.

---

## Quick start (30 seconds)

### Claude Desktop

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": { "SARDIS_API_KEY": "your_sardis_key" }
    }
  }
}
```

### Cursor — `.cursor/mcp.json`

```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": { "SARDIS_API_KEY": "your_sardis_key" }
    }
  }
}
```

### Windsurf — `.windsurf/mcp.json`

Same shape as Cursor.

### VS Code

Install the [MCP extension](https://marketplace.visualstudio.com/items?itemName=modelcontextprotocol.mcp), then:

```json
{
  "mcp.servers": {
    "sardis": {
      "command": "npx",
      "args": ["-y", "@sardis/mcp-server"],
      "env": { "SARDIS_API_KEY": "your_sardis_key" }
    }
  }
}
```

### Claude Code

```bash
claude mcp add sardis -- npx -y @sardis/mcp-server
export SARDIS_API_KEY=your_sardis_key
```

### ChatGPT

ChatGPT Settings → **MCP Servers** → **Add Custom**:
Name `sardis` · Command `npx -y @sardis/mcp-server` · Env `SARDIS_API_KEY=your_sardis_key`.

---

## Try it without an API key

```bash
npx @sardis/mcp-server --demo
```

Sandbox tools simulate payments, wallets, and policy checks end-to-end. Useful for integration testing before going live.

---

## Available tools

### Payments
| Tool | Description |
| --- | --- |
| `sardis_pay` | Execute a payment to a merchant or wallet address |
| `sardis_get_transaction` | Retrieve details of a transaction |
| `sardis_list_transactions` | List recent transactions with filters |

### Wallets
| Tool | Description |
| --- | --- |
| `sardis_create_wallet` | Create a new non-custodial MPC wallet |
| `sardis_list_wallets` | List wallets visible to the caller |
| `sardis_get_wallet` | Inspect a single wallet |
| `sardis_get_balance` | Get balances across chains and tokens |
| `sardis_fund_wallet` | Fund a wallet via on-ramp or transfer |
| `sardis_withdraw_to_bank` / `sardis_withdraw` | Off-ramp to fiat |
| `sardis_get_funding_status` / `sardis_get_withdrawal_status` / `sardis_list_funding_transactions` | Funding-flow status |

### Holds
| Tool | Description |
| --- | --- |
| `sardis_create_hold` | Authorize without capture |
| `sardis_capture_hold` | Capture a prior authorization |
| `sardis_release_hold` / `sardis_void_hold` | Release / void |
| `sardis_extend_hold` / `sardis_get_hold` / `sardis_list_holds` | Lifecycle + introspection |

### Cards
| Tool | Description |
| --- | --- |
| `sardis_issue_card` / `sardis_create_card` | Issue a virtual card for an agent |
| `sardis_get_card` / `sardis_list_cards` | Read |
| `sardis_freeze_card` / `sardis_unfreeze_card` / `sardis_cancel_card` | Lifecycle |

### Policy
| Tool | Description |
| --- | --- |
| `sardis_check_policy` | Validate a transaction against spending policies |
| `sardis_validate_limits` | Check tx against per-tx / daily / monthly limits |
| `sardis_check_compliance` | KYC / AML gate |
| `sardis_get_policies` | List active policies |

### Approvals
| Tool | Description |
| --- | --- |
| `sardis_request_approval` | Request human approval |
| `sardis_get_approval_status` / `sardis_check_approval` | Status |
| `sardis_list_pending_approvals` / `sardis_cancel_approval` | Queue management |

### Agents
| Tool | Description |
| --- | --- |
| `sardis_create_agent` / `sardis_get_agent` / `sardis_list_agents` / `sardis_update_agent` | Agent CRUD with KYA trust scoring |

### Groups
| Tool | Description |
| --- | --- |
| `sardis_create_group` / `sardis_get_group` / `sardis_list_groups` | Shared-budget groups |
| `sardis_add_agent_to_group` / `sardis_remove_agent_from_group` | Membership |
| `sardis_get_group_spending` | Group-level analytics |

### Analytics
| Tool | Description |
| --- | --- |
| `sardis_get_spending_summary` / `sardis_get_spending` | Period summary |
| `sardis_get_spending_by_vendor` / `sardis_get_spending_by_category` | Breakdowns |
| `sardis_get_spending_trends` | Trend analysis |

### Facility Gate
| Tool | Description |
| --- | --- |
| `sardis_facility_request` | Create a mandate-aware access request |
| `sardis_facility_attach_evidence` | Attach evidence references + hashes |
| `sardis_facility_authorize` | Evaluate mandate, policy, risk, evidence, revocation |
| `sardis_facility_execute` | Execute via the configured adapter |
| `sardis_facility_audit` / `sardis_facility_export_audit` | Reconstruct / export the audit packet |
| `sardis_facility_list_requests` | List visible requests |

### Sandbox
| Tool | Description |
| --- | --- |
| `sardis_sandbox_demo` | Walk-through demo with no API key |

---

## Example prompts

- "Check my procurement agent's USDC balance on Base."
- "Pay $50 USDC to merchant@example.com — only if it's within today's SaaS budget."
- "Issue a virtual card capped at $200/month for SaaS subscriptions."
- "Create a spending policy: max $500/day for API services, no gambling, no crypto exchanges."
- "Authorize a $1,200 hold on wallet `wallet_abc`, capture $980 once delivery confirms."
- "Request approval for a $2,500 payment to Stripe; show me when it's decided."
- "Summarize this month's spending by vendor and flag anything above policy."

---

## Security model

- **Non-custodial.** Keys are managed via Turnkey MPC — private keys exist only as distributed shares across secure enclaves and are never exposed to Sardis or the agent.
- **Policy firewall.** Every tool call passes through deterministic per-tx, daily, monthly, vendor, and category limits, plus KYA trust scoring and configurable blocklists. Fail-closed.
- **Approval & revocation.** High-risk actions step up to a human; the kill switch propagates within one decision cycle.
- **Append-only audit ledger.** Ed25519-signed attestation envelopes for every decision — compliance-ready, dispute-ready, forensic-ready.

Full threat model: [docs.sardis.sh/security](https://docs.sardis.sh/security).

---

## Environment variables

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `SARDIS_API_KEY` | No (required for live) | — | Your Sardis API key — [get one](https://sardis.sh) |
| `SARDIS_WALLET_ID` | No | — | Default wallet ID |
| `SARDIS_AGENT_ID` | No | — | Default agent ID for this MCP connection |
| `SARDIS_MODE` | No | `sandbox` | `live` for real transactions |
| `SARDIS_API_URL` | No | `https://api.sardis.sh` | Override for enterprise / self-hosted |

---

## Troubleshooting

**Server not starting** — `node --version` (need ≥ 18); `npx clear-npx-cache`; try `npm i -g @sardis/mcp-server`.

**Tools not appearing** — restart your MCP client; verify JSON syntax; confirm the config file path for your OS.

**API errors** — verify the key at [sardis.sh/settings/api-keys](https://sardis.sh/settings/api-keys); set `SARDIS_MODE=live` for production; confirm the wallet ID exists.

---

## Links

- Website — [sardis.sh](https://sardis.sh)
- Docs — [docs.sardis.sh](https://docs.sardis.sh) · [MCP setup](https://docs.sardis.sh/mcp)
- GitHub — [EfeDurmaz16/sardis](https://github.com/EfeDurmaz16/sardis)
- Discord — [discord.gg/XMA9JwDJ](https://discord.gg/XMA9JwDJ)
- Support — support@sardis.sh

## Requirements

Node.js 18+ · any MCP-compatible client.

## License

MIT — see [LICENSE](./LICENSE).
