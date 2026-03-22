export default function GetAPIKey() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            30 SECONDS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Get Your API Key</h1>
        <p className="text-xl text-muted-foreground">
          Three ways to start using Sardis. Pick the one that fits your workflow.
        </p>
      </div>

      {/* Option 1: Quickest — SDK */}
      <div className="not-prose mb-8 p-6 border border-emerald-500/30 bg-emerald-500/5 rounded-xl">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl font-bold text-emerald-500">1</span>
          <h3 className="text-lg font-semibold text-foreground">Quickest: No API key needed</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Start in simulation mode immediately. No signup, no API key, no credit card.
          Everything runs locally.
        </p>
        <pre className="bg-[#0a0b0d] border border-border p-4 rounded-lg font-mono text-sm overflow-x-auto">
          <code>{`pip install sardis

python -c "
from sardis import SardisClient
client = SardisClient()       # Simulation mode — no API key needed
result = client.quickstart()  # Guided first payment in 30 seconds
"`}</code>
        </pre>
        <p className="text-xs text-muted-foreground mt-3">
          When you're ready for real payments, continue to option 2 or 3.
        </p>
      </div>

      {/* Option 2: Dashboard */}
      <div className="not-prose mb-8 p-6 border border-blue-500/30 bg-blue-500/5 rounded-xl">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl font-bold text-blue-500">2</span>
          <h3 className="text-lg font-semibold text-foreground">Dashboard: Full control</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Sign up to get a sandbox API key. Create wallets, set policies, and manage
          spending mandates from the dashboard.
        </p>
        <ol className="text-sm text-muted-foreground space-y-2 mb-4">
          <li>1. Go to <a href="https://dashboard.sardis.sh/signup" className="text-blue-400 hover:underline">dashboard.sardis.sh/signup</a></li>
          <li>2. Register with email + password</li>
          <li>3. <strong className="text-foreground">Your API key is shown immediately</strong> (copy it — shown only once)</li>
          <li>4. You're redirected to the onboarding wizard with quickstart code</li>
        </ol>
        <pre className="bg-[#0a0b0d] border border-border p-4 rounded-lg font-mono text-sm overflow-x-auto">
          <code>{`import os
from sardis import SardisClient

client = SardisClient(api_key=os.environ["SARDIS_API_KEY"])
wallet = client.wallets.create(name="my-agent", policy="Max $100/day")
tx = wallet.pay(to="openai.com", amount=25)
print(tx.success)  # True`}</code>
        </pre>
      </div>

      {/* Option 3: CLI */}
      <div className="not-prose mb-8 p-6 border border-purple-500/30 bg-purple-500/5 rounded-xl">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl font-bold text-purple-500">3</span>
          <h3 className="text-lg font-semibold text-foreground">CLI: Terminal-first</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Use the interactive setup wizard. It guides you through account creation,
          API key configuration, and your first payment.
        </p>
        <pre className="bg-[#0a0b0d] border border-border p-4 rounded-lg font-mono text-sm overflow-x-auto">
          <code>{`pip install sardis-cli

# Interactive setup wizard
sardis init

# Check your connection
sardis status

# Make your first payment
sardis payments execute --to openai.com --amount 25 --purpose "API credits"`}</code>
        </pre>
      </div>

      {/* Option 4: MCP */}
      <div className="not-prose mb-8 p-6 border border-amber-500/30 bg-amber-500/5 rounded-xl">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-2xl font-bold text-amber-500">4</span>
          <h3 className="text-lg font-semibold text-foreground">MCP: For Claude & Cursor</h3>
        </div>
        <p className="text-sm text-muted-foreground mb-4">
          Use Sardis directly from Claude Desktop, Cursor, or any MCP-compatible client.
          No code needed — just natural language.
        </p>
        <pre className="bg-[#0a0b0d] border border-border p-4 rounded-lg font-mono text-sm overflow-x-auto">
          <code>{`# Install and start (simulated mode — no API key)
npx @sardis/mcp-server init --mode simulated
npx @sardis/mcp-server start

# Then ask Claude: "Create a wallet and make a $25 payment to OpenAI"`}</code>
        </pre>
      </div>

      {/* API Key Types */}
      <h2>API Key Types</h2>
      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Prefix</th>
              <th className="text-left p-3 border-b border-border">Mode</th>
              <th className="text-left p-3 border-b border-border">Real Money?</th>
              <th className="text-left p-3 border-b border-border">Use Case</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['(none)', 'Simulation', 'No', 'Local development, prototyping, learning'],
              ['sk_test_', 'Sandbox', 'No', 'Testing with real API, testnet chains'],
              ['sk_live_', 'Production', 'Yes', 'Real payments on mainnet'],
            ].map(([prefix, mode, money, use]) => (
              <tr key={prefix} className="border-b border-border">
                <td className="p-3 font-mono">{prefix}</td>
                <td className="p-3">{mode}</td>
                <td className="p-3">{money}</td>
                <td className="p-3 text-muted-foreground">{use}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Managing API Keys</h2>
      <p>
        From the <a href="https://dashboard.sardis.sh/api-keys">dashboard API Keys page</a>, you can:
      </p>
      <ul>
        <li><strong>Create</strong> new keys with specific scopes (read, write, admin)</li>
        <li><strong>Set expiration</strong> (30, 90, 365 days, or never)</li>
        <li><strong>Revoke</strong> keys instantly (takes effect immediately)</li>
        <li><strong>View</strong> key prefix and last usage timestamp</li>
      </ul>
      <p>
        Keys are SHA-256 hashed before storage — we never store or display the full key after creation.
      </p>

      <h2>Next Steps</h2>
      <p>Once you have your API key:</p>
      <ul>
        <li><a href="/docs/spending-mandates">Set up a spending mandate</a> — define what your agent can spend</li>
        <li><a href="/docs/policies">Configure spending policies</a> — fine-grained rules</li>
        <li><a href="/docs/production-guide">Go to production</a> — simulation → testnet → mainnet</li>
      </ul>
    </article>
  );
}
