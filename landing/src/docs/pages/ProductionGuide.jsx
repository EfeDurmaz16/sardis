export default function ProductionGuide() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            GOING TO PRODUCTION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Production Migration Guide</h1>
        <p className="text-xl text-muted-foreground">
          Take your agent payments from simulation to mainnet in 3 phases.
        </p>
      </div>

      <section className="not-prose mb-8 p-4 border border-amber-500/30 bg-amber-500/10">
        <div className="flex items-center gap-2 mb-2">
          <span className="font-bold text-amber-500">BEFORE YOU START</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Sardis supports three deployment modes. Start with simulation, move to testnet, then go mainnet.
          Each phase builds on the previous one — you don't need to rewrite any code.
        </p>
      </section>

      {/* Phase 1 */}
      <h2>Phase 1: Simulation (Local)</h2>
      <p>
        This is the default mode. No API key, no blockchain, no real money.
        All operations run in-memory on your machine.
      </p>

      <pre className="not-prose"><code className="language-python">{`from sardis import SardisClient

# No API key = simulation mode (automatic)
client = SardisClient()

# Everything works locally
wallet = client.wallets.create(name="my-agent", initial_balance=1000)
wallet.pay(to="openai.com", amount=25, purpose="API credits")
print(wallet.balance)  # 975
`}</code></pre>

      <p><strong>What to test in simulation:</strong></p>
      <ul>
        <li>Wallet creation and balance management</li>
        <li>Policy enforcement (limits, allowlists, blocklists)</li>
        <li>Multi-agent group budgets</li>
        <li>Approval thresholds</li>
        <li>Transaction logging</li>
      </ul>

      <div className="not-prose mb-6 p-4 border border-emerald-500/30 bg-emerald-500/10">
        <p className="text-sm text-muted-foreground">
          <strong className="text-emerald-500">Tip:</strong> Use <code>client.quickstart()</code> for a guided walkthrough of all simulation features.
        </p>
      </div>

      {/* Phase 2 */}
      <h2>Phase 2: Testnet (Base Sepolia)</h2>
      <p>
        Real blockchain transactions with test tokens. No real money at risk.
      </p>

      <h3>Step 1: Get your API key</h3>
      <ol>
        <li>Sign up at <a href="https://dashboard.sardis.sh/signup" target="_blank" rel="noopener noreferrer">dashboard.sardis.sh/signup</a></li>
        <li>Go to <strong>API Keys</strong> in the dashboard</li>
        <li>Create a new key with <code>write</code> scope</li>
        <li>Copy the key (starts with <code>sk_test_</code>)</li>
      </ol>

      <h3>Step 2: Install the production SDK</h3>
      <pre className="not-prose"><code className="language-bash">{`pip install sardis sardis-sdk`}</code></pre>

      <h3>Step 3: Set environment variables</h3>
      <pre className="not-prose"><code className="language-bash">{`# Set your API key (from dashboard.sardis.sh/api-keys)
export SARDIS_API_KEY=<your-sk_test-key>
export SARDIS_API_URL=https://api.sardis.sh
`}</code></pre>

      <h3>Step 4: Run your first testnet payment</h3>
      <pre className="not-prose"><code className="language-python">{`from sardis import SardisClient

# API key triggers production mode automatically
client = SardisClient(api_key=os.environ["SARDIS_API_KEY"])

# Create a wallet on Base Sepolia
wallet = client.wallets.create(
    name="test-agent",
    chain="base_sepolia",
    token="USDC",
    policy="Max $100 per transaction"
)

# Fund the wallet (use dashboard or faucet)
# Then execute a real testnet payment
tx = wallet.pay(to="0xRecipient...", amount=5.00, purpose="Test payment")
print(tx.success)   # True
print(tx.tx_hash)   # Real blockchain tx hash
`}</code></pre>

      <h3>Step 5: Fund your testnet wallet</h3>
      <p>Options for getting testnet USDC:</p>
      <ul>
        <li><strong>Dashboard faucet:</strong> Go to the dashboard and click "Fund Wallet" on your wallet</li>
        <li><strong>Circle faucet:</strong> Get testnet USDC from <a href="https://faucet.circle.com/" target="_blank" rel="noopener noreferrer">faucet.circle.com</a></li>
        <li><strong>Direct transfer:</strong> Send Base Sepolia USDC to your wallet address</li>
      </ul>

      {/* Phase 3 */}
      <h2>Phase 3: Mainnet (Production)</h2>
      <p>
        Real money, real transactions. Only change is the chain configuration.
      </p>

      <h3>Step 1: Get a production API key</h3>
      <ol>
        <li>In the dashboard, create a new API key with <code>sk_live_</code> prefix</li>
        <li>Store it securely (environment variable, secrets manager — never hardcode)</li>
      </ol>

      <h3>Step 2: Update environment</h3>
      <pre className="not-prose"><code className="language-bash">{`# Set your production API key (from dashboard.sardis.sh/api-keys)
export SARDIS_API_KEY=<your-sk_live-key>
export SARDIS_API_URL=https://api.sardis.sh
`}</code></pre>

      <h3>Step 3: Switch to mainnet chain</h3>
      <pre className="not-prose"><code className="language-python">{`from sardis import SardisClient

client = SardisClient(api_key=os.environ["SARDIS_API_KEY"])

# Create wallet on Base mainnet
wallet = client.wallets.create(
    name="production-agent",
    chain="base",       # mainnet!
    token="USDC",
    policy="Max $500 per day. Only allow approved vendors. Require approval above $200."
)
`}</code></pre>

      <h3>Step 4: Fund with real USDC</h3>
      <ul>
        <li><strong>Coinbase Onramp (recommended):</strong> Free, instant USDC purchase directly to your wallet</li>
        <li><strong>Direct transfer:</strong> Send USDC on Base to your wallet address</li>
        <li><strong>Bridge from other chains:</strong> Use Circle CCTP to bridge USDC from Ethereum, Polygon, etc.</li>
      </ul>

      <h3>Step 5: Production checklist</h3>
      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Check</th>
              <th className="text-left p-3 border-b border-border">Status</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Production API key (sk_live_) configured', 'Required'],
              ['sardis-sdk package installed', 'Required'],
              ['Spending policy set for production limits', 'Required'],
              ['Wallet funded with real USDC', 'Required'],
              ['Webhook endpoint registered for notifications', 'Recommended'],
              ['Approval workflow configured for large payments', 'Recommended'],
              ['Kill switch tested in staging', 'Recommended'],
              ['Dashboard access verified for all team members', 'Optional'],
            ].map(([check, status]) => (
              <tr key={check} className="border-b border-border">
                <td className="p-3">{check}</td>
                <td className="p-3">
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    status === 'Required' ? 'bg-red-500/10 text-red-500' :
                    status === 'Recommended' ? 'bg-amber-500/10 text-amber-500' :
                    'bg-muted text-muted-foreground'
                  }`}>{status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Environment Variables */}
      <h2>Environment Variable Reference</h2>
      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">Variable</th>
              <th className="text-left p-3 border-b border-border">Required</th>
              <th className="text-left p-3 border-b border-border">Description</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['SARDIS_API_KEY', 'Yes', 'Your API key (sk_test_ for testnet, sk_live_ for mainnet)'],
              ['SARDIS_API_URL', 'No', 'API base URL (default: https://api.sardis.sh)'],
              ['TURNKEY_API_KEY', 'Production', 'Turnkey MPC signing key (auto-configured with Sardis keys)'],
              ['TURNKEY_ORGANIZATION_ID', 'Production', 'Turnkey org ID (auto-configured with Sardis keys)'],
            ].map(([name, required, desc]) => (
              <tr key={name} className="border-b border-border">
                <td className="p-3 font-mono text-xs">{name}</td>
                <td className="p-3">{required}</td>
                <td className="p-3">{desc}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Troubleshooting */}
      <h2>Troubleshooting</h2>

      <h3>"SardisClient is running in simulation mode"</h3>
      <p>
        This warning means no real payments will execute. Fix: provide an API key
        and install <code>sardis-sdk</code>:
      </p>
      <pre className="not-prose"><code className="language-bash">{`pip install sardis-sdk
export SARDIS_API_KEY="sk_test_..."
`}</code></pre>

      <h3>"Insufficient funds or limit exceeded"</h3>
      <p>
        Your wallet doesn't have enough USDC. Check your balance in the dashboard
        or fund it using one of the methods above.
      </p>

      <h3>"Policy check failed"</h3>
      <p>
        The payment was rejected by your spending policy. Check:
      </p>
      <ul>
        <li>Is the amount within your per-transaction limit?</li>
        <li>Is the destination in your allowed list?</li>
        <li>Have you exceeded your daily/monthly budget?</li>
      </ul>
      <p>
        Use the <a href="/policy-management">Policy Playground</a> to test your policy against different scenarios.
      </p>

      <h3>"Transaction failed" with no details</h3>
      <p>
        Check the transaction in the <a href="/transactions">Transaction Explorer</a> for the full lifecycle
        and error details. Common causes: RPC timeout (retry), gas estimation failure, or nonce conflict.
      </p>

      <h3>Need help?</h3>
      <p>
        Join our <a href="https://discord.gg/sardis" target="_blank" rel="noopener noreferrer">Discord</a> or
        email <a href="mailto:support@sardis.sh">support@sardis.sh</a>.
      </p>
    </article>
  );
}
