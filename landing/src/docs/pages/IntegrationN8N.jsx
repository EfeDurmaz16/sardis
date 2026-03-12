export default function DocsIntegrationN8N() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">n8n Integration</h1>
        <p className="text-xl text-muted-foreground">
          Use the Sardis node in n8n workflows to execute policy-controlled payments from visual automation pipelines.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`npm install n8n-nodes-sardis`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          After installing, restart n8n and the Sardis node will appear in the node palette under
          the "Transform" category. The node uses the Sardis API credential type for authentication.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Self-hosted n8n</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Install into your n8n custom nodes directory
cd ~/.n8n/custom
npm install n8n-nodes-sardis

# Or set the N8N_CUSTOM_EXTENSIONS env var to your custom nodes path
N8N_CUSTOM_EXTENSIONS="/path/to/custom-nodes" n8n start`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Credentials Setup
        </h2>

        <p className="text-muted-foreground mb-4">
          The node uses a Sardis API credential with two fields:
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`API Key:  sk_live_...                   # Your Sardis API key
Base URL: https://api.sardis.sh         # Default, change for self-hosted deployments`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          In the n8n UI: go to Credentials, click "Add credential", search for "Sardis API",
          and enter your API key. The credential is shared across all Sardis nodes in your workflows.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Operations
        </h2>

        <p className="text-muted-foreground mb-4">
          The Sardis node supports three operations, selectable from the Operation dropdown.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Send Payment</h3>
        <p className="text-muted-foreground mb-4">
          Execute a policy-controlled payment. Maps to POST /api/v2/wallets/{'{walletId}'}/transfer.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Node parameters
Wallet ID:  wallet_abc123             # Required
Amount:     50                        # Required — USD amount
Merchant:   api.openai.com            # Required — recipient identifier
Purpose:    GPT-4 API credits         # Optional — memo/reason
Token:      USDC | USDT | PYUSD | EURC  # Default: USDC
Chain:      base | ethereum | polygon | arbitrum | optimism  # Default: base

# Output data (passed to next node)
{
  "success": true,
  "tx_id": "pay_xyz789",
  "status": "completed",
  "amount": "50",
  "destination": "api.openai.com"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Check Balance</h3>
        <p className="text-muted-foreground mb-4">
          Retrieve wallet balance and limits. Maps to GET /api/v2/wallets/{'{walletId}'}/balance.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Node parameters
Wallet ID:  wallet_abc123
Token:      USDC (default)
Chain:      base (default)

# Output data
{
  "success": true,
  "balance": "500.00",
  "token": "USDC",
  "chain": "base"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Check Policy</h3>
        <p className="text-muted-foreground mb-4">
          Pre-check whether a payment would pass spending policy before executing it.
          Reads limit_per_tx from the wallet and compares against the requested amount.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Node parameters
Wallet ID:  wallet_abc123
Amount:     50
Merchant:   api.openai.com

# Output data (allowed)
{
  "allowed": true,
  "amount": 50,
  "merchant": "api.openai.com",
  "limitPerTx": 100,
  "message": "$50 to api.openai.com would be allowed"
}

# Output data (blocked)
{
  "allowed": false,
  "amount": 200,
  "merchant": "api.openai.com",
  "limitPerTx": 100,
  "message": "$200 exceeds per-tx limit of $100"
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Conditional Payment Workflow
        </h2>

        <p className="text-muted-foreground mb-4">
          A workflow that checks policy first and only executes payment if allowed.
          Use n8n's IF node to branch on the allowed field.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`Workflow: Conditional Payment

[Trigger]
  └── [Sardis: Check Policy]
         Wallet ID: {{ $env.SARDIS_WALLET_ID }}
         Amount:    {{ $json.amount }}
         Merchant:  {{ $json.merchant }}
  └── [IF: allowed == true]
         True  → [Sardis: Send Payment]
                   Wallet ID: {{ $env.SARDIS_WALLET_ID }}
                   Amount:    {{ $json.amount }}
                   Merchant:  {{ $json.merchant }}
                   Purpose:   {{ $json.purpose }}
                   Token:     USDC
                   Chain:     base
                 → [Slack: Notify "Payment approved: tx_id"]
         False → [Slack: Notify "Payment blocked: message"]`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Scheduled Balance Report
        </h2>

        <p className="text-muted-foreground mb-4">
          Use n8n's Schedule Trigger to send a daily balance report to Slack.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`Workflow: Daily Balance Report

[Schedule Trigger: every day at 9am]
  └── [Sardis: Check Balance]
         Wallet ID: wallet_abc123
         Token:     USDC
         Chain:     base
  └── [Slack: Send Message]
         Channel: #finance
         Message: |
           Daily Sardis Balance Report
           Balance: {{ $json.balance }} {{ $json.token }}
           Chain: {{ $json.chain }}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Supported Tokens and Chains
        </h2>

        <div className="not-prose mb-6 overflow-x-auto">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-muted/50">
                <th className="text-left p-3 border-b border-border font-mono">Token</th>
                <th className="text-left p-3 border-b border-border font-mono">Supported Chains</th>
              </tr>
            </thead>
            <tbody className="font-mono text-xs">
              <tr><td className="p-3 border-b border-border">USDC</td><td className="p-3 border-b border-border">base, ethereum, polygon, arbitrum, optimism</td></tr>
              <tr><td className="p-3 border-b border-border">USDT</td><td className="p-3 border-b border-border">ethereum, polygon, arbitrum, optimism</td></tr>
              <tr><td className="p-3 border-b border-border">PYUSD</td><td className="p-3 border-b border-border">ethereum</td></tr>
              <tr><td className="p-3 border-b border-border">EURC</td><td className="p-3 border-b border-border">base, ethereum, polygon</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Store the Sardis API key in n8n Credentials, never in node parameters directly</li>
          <li>Use the IF node to branch on the allowed field from Check Policy before Send Payment</li>
          <li>Use n8n expressions like {'{{ $json.amount }}'} to pass dynamic values between nodes</li>
          <li>Enable workflow error handling to catch payment failures and send alerts</li>
          <li>The node outputs are passed as JSON to subsequent nodes — use Set node to reshape if needed</li>
        </ul>
      </section>
    </article>
  );
}
