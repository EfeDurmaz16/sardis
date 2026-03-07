export default function DocsIntegrations() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATIONS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Framework Integrations</h1>
        <p className="text-xl text-muted-foreground">
          Sardis works with every major AI agent framework. One payment layer, every platform.
        </p>
      </div>

      {/* Overview table */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> All Integrations
        </h2>

        <div className="not-prose mb-6 overflow-x-auto">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3 border-b border-border font-mono">Package</th>
                <th className="text-left p-3 border-b border-border font-mono">Framework</th>
                <th className="text-left p-3 border-b border-border font-mono">Install</th>
                <th className="text-left p-3 border-b border-border font-mono">Pattern</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              <tr><td className="p-3 border-b border-border">sardis-browser-use</td><td className="p-3 border-b border-border">Browser Use</td><td className="p-3 border-b border-border">pip install sardis-browser-use</td><td className="p-3 border-b border-border">register_sardis_actions(controller)</td></tr>
              <tr><td className="p-3 border-b border-border">sardis-crewai</td><td className="p-3 border-b border-border">CrewAI</td><td className="p-3 border-b border-border">pip install sardis-crewai</td><td className="p-3 border-b border-border">create_sardis_toolkit()</td></tr>
              <tr><td className="p-3 border-b border-border">sardis-autogpt</td><td className="p-3 border-b border-border">AutoGPT</td><td className="p-3 border-b border-border">pip install sardis-autogpt</td><td className="p-3 border-b border-border">SardisPayBlock.run(input)</td></tr>
              <tr><td className="p-3 border-b border-border">sardis-openai-agents</td><td className="p-3 border-b border-border">OpenAI Agents SDK</td><td className="p-3 border-b border-border">pip install sardis-openai-agents</td><td className="p-3 border-b border-border">get_sardis_tools()</td></tr>
              <tr><td className="p-3 border-b border-border">sardis-composio</td><td className="p-3 border-b border-border">Composio</td><td className="p-3 border-b border-border">pip install sardis-composio</td><td className="p-3 border-b border-border">SARDIS_TOOLS dict</td></tr>
              <tr><td className="p-3 border-b border-border">@sardis/ai-sdk</td><td className="p-3 border-b border-border">Vercel AI SDK</td><td className="p-3 border-b border-border">npm install @sardis/ai-sdk</td><td className="p-3 border-b border-border">createSardisTools()</td></tr>
              <tr><td className="p-3 border-b border-border">@sardis/stagehand</td><td className="p-3 border-b border-border">Stagehand</td><td className="p-3 border-b border-border">npm install @sardis/stagehand</td><td className="p-3 border-b border-border">createSardisTools()</td></tr>
              <tr><td className="p-3 border-b border-border">n8n-nodes-sardis</td><td className="p-3 border-b border-border">n8n</td><td className="p-3 border-b border-border">npm install n8n-nodes-sardis</td><td className="p-3 border-b border-border">Visual workflow node</td></tr>
              <tr><td className="p-3 border-b border-border">@activepieces/piece-sardis</td><td className="p-3 border-b border-border">Activepieces</td><td className="p-3 border-b border-border">npm install @activepieces/piece-sardis</td><td className="p-3 border-b border-border">Workflow piece</td></tr>
              <tr><td className="p-3 border-b border-border">@sardis/mcp-server</td><td className="p-3 border-b border-border">Claude / MCP</td><td className="p-3 border-b border-border">npx @sardis/mcp-server start</td><td className="p-3 border-b border-border">52 MCP tools</td></tr>
              <tr><td className="p-3 border-b border-border">sardis-gpt</td><td className="p-3 border-b border-border">ChatGPT</td><td className="p-3 border-b border-border">Custom GPT Actions</td><td className="p-3 border-b border-border">OpenAPI 3.1 spec</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Universal pattern */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Universal Pattern
        </h2>
        <p className="text-muted-foreground mb-4">
          Every integration follows the same core pattern. The Sardis SDK works in simulation mode
          by default — no API key needed for development and testing.
        </p>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

client = SardisClient()  # simulation mode
wallet = client.wallets.create(name="my-agent", policy="Max $100/day")

# Every framework wraps these three operations:
tx = wallet.pay(to="vendor.com", amount=25.00)     # 1. Pay
bal = client.wallets.get_balance(wallet.id)          # 2. Check balance
# Policy enforcement happens automatically            # 3. Policy check`}</pre>
          </div>
        </div>
      </section>

      {/* Quick starts for each framework */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Starts
        </h2>

        <h3 className="text-xl font-bold mb-3">Browser Use</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from browser_use import Controller
from sardis_browser_use import register_sardis_actions

controller = Controller()
register_sardis_actions(controller, wallet_id="wallet_...")
# Agent can now pay, check balance, and verify policies`}</pre>
          </div>
        </div>

        <h3 className="text-xl font-bold mb-3">CrewAI</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from crewai import Agent
from sardis_crewai import create_sardis_toolkit

tools = create_sardis_toolkit(wallet_id="wallet_...")
agent = Agent(role="Buyer", tools=tools)`}</pre>
          </div>
        </div>

        <h3 className="text-xl font-bold mb-3">OpenAI Agents SDK</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from agents import Agent
from sardis_openai_agents import get_sardis_tools, configure

configure(wallet_id="wallet_...")
agent = Agent(name="buyer", tools=get_sardis_tools())`}</pre>
          </div>
        </div>

        <h3 className="text-xl font-bold mb-3">Vercel AI SDK</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { generateText } from 'ai';
import { createSardisTools } from '@sardis/ai-sdk';

const tools = createSardisTools({ walletId: 'wallet_...' });
const result = await generateText({ model, tools, prompt: 'Pay $50 to OpenAI' });`}</pre>
          </div>
        </div>
      </section>

      {/* Links to individual docs */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Detailed Guides
        </h2>
        <ul>
          <li><a href="/docs/integration-langchain">LangChain Integration Guide</a></li>
          <li><a href="/docs/integration-crewai">CrewAI Integration Guide</a></li>
          <li><a href="/docs/integration-adk">Google ADK Integration Guide</a></li>
          <li><a href="/docs/integration-agent-sdk">Agent SDK Integration Guide</a></li>
          <li><a href="/docs/mcp-server">MCP Server Reference</a></li>
        </ul>
      </section>
    </article>
  );
}
