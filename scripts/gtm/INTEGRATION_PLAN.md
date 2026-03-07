# Agent Framework Integration Plan

## Current State

We already have:
- `sardis` simple SDK with simulation mode (no API key needed to prototype)
- `sardis-sdk-python` full SDK with LangChain, OpenAI, LlamaIndex integrations
- `sardis-mcp-server` with 50+ MCP tools
- Natural language policy parser
- Group budget management

## Priority Integrations

### P0: Browser Use (78k stars, agents clicking "buy")

**Mechanism:** Browser Use uses LangChain tools under the hood. Custom tools extend `BaseTool`.

**What to build:**
```python
# sardis_browser_use/tool.py
from browser_use import Controller
from sardis import SardisClient

@controller.action("Pay for a product or service")
async def sardis_pay(amount: float, merchant: str, purpose: str = "Purchase"):
    """Execute a policy-controlled payment via Sardis wallet."""
    client = SardisClient(api_key=os.getenv("SARDIS_API_KEY"))
    wallet = client.wallets.get(os.getenv("SARDIS_WALLET_ID"))
    result = wallet.pay(to=merchant, amount=amount, purpose=purpose)
    return f"Payment {'approved' if result.success else 'blocked'}: ${amount} to {merchant}"

@controller.action("Check spending policy before purchase")
async def sardis_check_policy(amount: float, merchant: str):
    """Check if a payment would be allowed by spending policy."""
    ...
```

**Deliverable:** `sardis-browser-use` PyPI package + README example
**LOE:** 1-2 days

---

### P0: CrewAI (20k stars, multi-agent framework)

**Mechanism:** CrewAI tools extend `BaseTool` from `crewai_tools` or use `@tool` decorator.

**What to build:**
```python
# sardis_crewai/tools.py
from crewai_tools import BaseTool
from sardis import SardisClient

class SardisPaymentTool(BaseTool):
    name: str = "sardis_pay"
    description: str = "Execute a policy-controlled payment from the agent's Sardis wallet."

    def _run(self, amount: float, merchant: str, purpose: str = "Payment") -> str:
        client = SardisClient(api_key=os.getenv("SARDIS_API_KEY"))
        wallet_id = os.getenv("SARDIS_WALLET_ID")
        result = client.payments.send(wallet_id, to=merchant, amount=amount, purpose=purpose)
        return f"{'APPROVED' if result.success else 'BLOCKED'}: ${amount} to {merchant}"
```

**Deliverable:** `sardis-crewai` PyPI package
**LOE:** 1-2 days

---

### P0: Composio (250+ tool connectors)

**Mechanism:** Composio has a tool builder API. Custom tools are defined as actions with schemas.

**What to build:** Submit Sardis as a Composio integration (they have an open-source tool registry).
Three actions: `sardis_pay`, `sardis_check_balance`, `sardis_check_policy`.

**Deliverable:** PR to Composio's integrations repo
**LOE:** 1 day

---

### P1: AutoGPT (warm lead, re-engage)

**Mechanism:** AutoGPT uses a plugin system. Plugins define commands.

**What to build:**
```python
# sardis_autogpt_plugin/
class SardisPlugin:
    def can_handle_on_response(self): return True

    @command("sardis_pay", "Pay from agent wallet with policy controls")
    def pay(self, amount: float, merchant: str) -> str:
        ...
```

**Deliverable:** AutoGPT plugin + send to Nicholas (warm contact)
**LOE:** 1-2 days

---

### P1: Browserbase / Stagehand

**Mechanism:** Stagehand is TypeScript. Would need `sardis-stagehand` npm package using our JS SDK.

**What to build:**
```typescript
// sardis-stagehand/src/index.ts
import { Stagehand } from "@browserbasehq/stagehand";
import { SardisClient } from "@sardis/sdk";

export function withSardisPayment(stagehand: Stagehand, sardisConfig: SardisConfig) {
  // Wrap stagehand.act() to intercept purchase actions
  // Check policy before executing financial actions
}
```

**Deliverable:** `@sardis/stagehand` npm package
**LOE:** 2-3 days (TypeScript)

---

### P1: E2B (agent sandbox runtime)

**Mechanism:** E2B sandboxes run code. Sardis SDK would be pre-installed in sandbox.

**What to build:** E2B template with Sardis pre-configured.
```python
from e2b_code_interpreter import Sandbox

sandbox = Sandbox(template="sardis-agent")
# Sardis SDK pre-installed, env vars forwarded
sandbox.run_code("from sardis import SardisClient; client = SardisClient()")
```

**Deliverable:** E2B template + docs
**LOE:** 1 day

---

### P2: n8n / Activepieces (workflow automation)

**Mechanism:** n8n has community nodes. Activepieces has a pieces system.

**What to build:** n8n community node for Sardis (wallet, pay, check policy actions).

**Deliverable:** `n8n-nodes-sardis` npm package
**LOE:** 2-3 days

---

### P2: Vercel AI SDK

**Mechanism:** Vercel AI SDK uses `tool()` definitions.

**What to build:**
```typescript
import { tool } from 'ai';
import { SardisClient } from '@sardis/sdk';

export const sardisPay = tool({
  description: 'Execute a policy-controlled payment',
  parameters: z.object({
    amount: z.number(),
    merchant: z.string(),
    purpose: z.string().optional(),
  }),
  execute: async ({ amount, merchant, purpose }) => {
    const client = new SardisClient({ apiKey: process.env.SARDIS_API_KEY });
    return client.wallets.transfer(...);
  },
});
```

**Deliverable:** Example in sardis-sdk-js
**LOE:** 0.5 days

---

## Existing Integrations (Already Built)

| Framework | Package | Status |
|-----------|---------|--------|
| LangChain | `sardis-langchain` | Built, has `SardisToolkit` |
| OpenAI Function Calling | `sardis_sdk.integrations.openai` | Built |
| LlamaIndex | `sardis_sdk.integrations.llamaindex` | Built |
| MCP (Claude/Cursor) | `@sardis/mcp-server` | Built, 50+ tools |

## Execution Order

1. **Week 1:** Browser Use + CrewAI (Python, highest star count, clearest pain)
2. **Week 1:** Send integration partnership emails to all targets
3. **Week 2:** Composio PR + AutoGPT plugin (leverage warm lead)
4. **Week 2:** Stagehand/Browserbase (TypeScript)
5. **Week 3:** E2B template + n8n node
6. **Ongoing:** Vercel AI SDK example, more frameworks as requested

## Key Insight

The simple `sardis` package with simulation mode is the secret weapon for integrations:
- `pip install sardis` — no API key needed
- Developers can prototype agent payment flows immediately
- When ready for production, swap `SardisClient()` for `SardisClient(api_key="sk_...")`
- Same code, same API, real money flows

This is the Stripe playbook: make integration so easy that developers choose us by default.

## Outreach Strategy

For each framework:
1. Build the integration (working code)
2. Create a 2-minute demo video / GIF
3. Email the founders with: "We built this for you. Here's the code. Here's the demo."
4. Open a PR if they have an open-source integrations repo
5. Post on their Discord/community with the integration

"Show, don't tell" — code speaks louder than cold emails.
