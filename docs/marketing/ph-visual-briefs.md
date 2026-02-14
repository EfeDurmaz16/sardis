# Product Hunt Visual Asset Briefs

> Design system: Dark background (#0a0a0a), Sardis orange (#ff4f00), white text, JetBrains Mono for code/tags, Inter for headings.
> Existing OG image reference: `landing/public/og-image.html`

---

## 1. Logo / Thumbnail

**File:** `ph-logo.png`
**Size:** 240 x 240 px (square, transparent background)
**Purpose:** PH listing thumbnail, shown in search results and feed

**Design:**
- Sardis logo mark (the bracket + square icon from og-image.html)
- Dark background (#0a0a0a) or transparent
- Logo in Sardis orange (#ff4f00)
- Clean, recognizable at small sizes
- No text — just the icon mark

**SVG reference:**
```svg
<path d="M35 25 H25 V75 H35" stroke="#ff4f00" stroke-width="10" fill="none" stroke-linecap="square"/>
<path d="M65 25 H75 V75 H65" stroke="#ff4f00" stroke-width="10" fill="none" stroke-linecap="square"/>
<rect x="40" y="40" width="20" height="20" fill="#ff4f00"/>
```

---

## 2. Gallery Image 1 — Hero Shot

**File:** `ph-gallery-1-hero.png`
**Size:** 1270 x 760 px
**Purpose:** First image people see in the PH gallery. Must hook attention.

**Content:**
- Top left: Sardis logo + "Sardis" wordmark
- Center (large): "The Payment OS for the Agent Economy" — "Agent Economy" in orange
- Below headline: "Non-custodial MPC wallets with natural language spending policies for AI agents"
- Bottom left tags: `DEVELOPER PREVIEW` `TESTNET LIVE` `OPEN-CORE`
- Bottom right: `sardis.sh`
- Corner accents (thin orange L-shaped borders in top-left and bottom-right corners)
- Subtle grid background pattern
- Decorative orange radial glow in top-right

**Essentially:** A polished version of the existing OG image (`landing/public/og-image.html`) scaled to 1270x760.

---

## 3. Gallery Image 2 — Architecture Diagram

**File:** `ph-gallery-2-architecture.png`
**Size:** 1270 x 760 px
**Purpose:** Show the technical flow — how Sardis works end-to-end

**Content — left to right flow:**

```
AI Agent  -->  SDK / MCP Server  -->  Policy Engine  -->  MPC Wallet (Turnkey)  -->  Chain Settlement
   |                                      |                                            |
Claude         "Max $100/day,         [APPROVE]                                   Base Sepolia
Cursor          SaaS only"            [DENY]                                      Polygon
OpenAI                                                                            Ethereum
LangChain                                                                         Arbitrum
                                                                                  Optimism
```

**Design details:**
- Dark background
- Each step is a card/box with an icon
- Arrows connecting the steps (orange)
- The Policy Engine box should be highlighted (orange border, glow) — this is the differentiator
- At the Policy Engine step, show a fork: green checkmark = APPROVE, red X = DENY
- Title at top: "How Sardis Works"
- Subtitle: "Every transaction passes through the policy firewall before execution"
- Bottom tag: `DEVELOPER PREVIEW — TESTNET`

---

## 4. Gallery Image 3 — Policy Firewall in Action

**File:** `ph-gallery-3-policy.png`
**Size:** 1270 x 760 px
**Purpose:** Show the NL policy engine — the core differentiator

**Content — split layout:**

**Left half — "Write policies in plain English":**
```
Policy Rules:
- "Maximum $100 per transaction"
- "Daily limit: $500"
- "Only approved SaaS vendors"
- "Block weekends"
- "Require approval over $50"
```

**Right half — "Enforced before every payment":**
Show 3 example transactions:
```
[APPROVED] $45 to OpenAI for API credits
  - Under $100 limit
  - SaaS vendor: approved
  - Weekday: yes

[DENIED] $250 to unknown-vendor.com
  - Over $100 limit
  - Vendor not in approved list

[DENIED] $30 to Anthropic (Saturday)
  - Weekend: blocked
```

**Design details:**
- Dark background
- Left side: terminal/code style (JetBrains Mono), policies in orange
- Right side: cards with green APPROVED / red DENIED badges
- Title at top: "Natural Language Spending Policies"
- Subtitle: "No code. Just say what the rules are."

---

## 5. Gallery Image 4 — MCP Server Setup

**File:** `ph-gallery-4-mcp.png`
**Size:** 1270 x 760 px
**Purpose:** Show how easy it is to get started — one command

**Content — terminal screenshot style:**

```
$ npx @sardis/mcp-server start

  Sardis MCP Server v0.2.7 running on stdio
  Mode: simulated
  Tools available: 52

  Ready. Your AI agent can now:
  - Create wallets with spending policies
  - Send payments with policy enforcement
  - Manage multi-agent group budgets
  - Check compliance and audit logs
```

**Below the terminal, show the Claude Desktop config:**
```json
{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}
```

**Design details:**
- Dark background with terminal window chrome (title bar with red/yellow/green dots)
- Terminal text in JetBrains Mono, green/white on dark
- The JSON config in a separate card below
- Title at top: "One Command. 52 Tools."
- Subtitle: "Zero-config for Claude Desktop and Cursor"
- Bottom tags: `npm` `MCP NATIVE` `SIMULATED MODE`

---

## 6. Gallery Image 5 — Group Governance

**File:** `ph-gallery-5-governance.png`
**Size:** 1270 x 760 px
**Purpose:** Show the multi-agent group budget feature — unique differentiator

**Content — diagram:**

```
                    GROUP: "Finance Team"
                    Budget: $1,000/day
                 ┌──────────┴──────────┐
                 |                      |                    |
          RESEARCHER              PURCHASER              AUDITOR
          $50/tx limit           $200/tx limit          Read-only
          SaaS only              Approved vendors        Full audit log

          Spent: $120            Spent: $450             Transactions: 23
          Remaining: $430        Remaining: $0           Alerts: 2
```

**Design details:**
- Dark background
- Group at top as a large card with orange border
- Three agent cards below, connected by lines
- Each agent card shows: role name, policy rules, spending stats
- Progress bars showing budget consumption (orange fill)
- Title at top: "Group Governance for Multi-Agent Teams"
- Subtitle: "Shared budgets. Individual limits. No agent overspends the team."
- Bottom tag: `UNIQUE TO SARDIS`

---

## 7. Demo GIF

**File:** `ph-demo.gif`
**Size:** 1270 x 760 px (or 16:9 ratio)
**Duration:** 15-30 seconds
**Purpose:** Show a real payment flow in terminal

**Sequence:**
1. Terminal shows: `python examples/simple_payment.py`
2. Output appears line by line:
   - Creating wallet... (wallet ID appears)
   - Setting policy: "Max $100 per transaction, SaaS only"
   - Sending $45 to OpenAI for "API credits"...
   - Policy check: APPROVED
   - Transaction: SUCCESS (tx hash appears)
   - Balance: $955.00 remaining
3. Second payment attempt:
   - Sending $250 to unknown-vendor...
   - Policy check: DENIED (exceeds $100 limit)
   - "No money moved."
4. Final frame holds for 3 seconds showing the summary

**Note:** This can be a screen recording of the actual `simple_payment.py` example running, or a styled animation that simulates it.

---

## 8. OG Image (Social Sharing)

**File:** `ph-og-image.png`
**Size:** 1200 x 630 px
**Purpose:** Preview image when sardis.sh link is shared on X, LinkedIn, etc.

**Design:** Use the existing `landing/public/og-image.html` as base. Update:
- Add "Developer Preview" tag (replace one of the existing bottom tags)
- Keep everything else the same — it already looks good

**Current bottom tags:** `NON-CUSTODIAL` `MULTI-CHAIN` `AP2 + TAP + x402`
**Updated bottom tags:** `DEVELOPER PREVIEW` `NON-CUSTODIAL` `MCP NATIVE`

---

## Brand Reference

| Element | Value |
|---------|-------|
| Primary color | `#ff4f00` (Sardis orange) |
| Background | `#0a0a0a` (near-black) |
| Text (primary) | `#ffffff` |
| Text (secondary) | `#a0a0a0` |
| Approved/success | `#22c55e` (green) |
| Denied/error | `#ef4444` (red) |
| Heading font | Inter (700, 800 weight) |
| Code/mono font | JetBrains Mono (400, 500) |
| Border accent | `rgba(255, 79, 0, 0.3)` |
| Corner accents | 3px solid orange L-shapes |
| Grid pattern | 40px grid, `rgba(255,79,0,0.03)` lines |

## File Delivery

All files should be exported as:
- PNG for static images (gallery, logo, OG)
- GIF or MP4 for the demo animation
- 2x resolution optional for retina (2540x1520 for gallery)
