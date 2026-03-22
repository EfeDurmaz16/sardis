import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

function AccordionItem({ title, symptom, children, isOpen, onClick }) {
  return (
    <div className="bg-card/50 rounded-lg shadow-sm hover:shadow-md transition-all">
      <button
        onClick={onClick}
        className="w-full px-5 py-5 flex items-center justify-between text-left hover:text-[var(--sardis-orange)] transition-colors"
      >
        <span className="font-medium pr-4 leading-relaxed">{title}</span>
        <ChevronDown className={cn(
          "w-5 h-5 flex-shrink-0 transition-transform text-muted-foreground",
          isOpen && "rotate-180 text-[var(--sardis-orange)]"
        )} />
      </button>
      <div className={cn(
        "overflow-hidden transition-all duration-300",
        isOpen ? "max-h-[900px] pb-5 px-5" : "max-h-0"
      )}>
        {symptom && (
          <p className="text-xs font-mono text-muted-foreground mb-4 px-3 py-2 bg-muted/30 border-l-2 border-[var(--sardis-orange)]">
            Symptom: {symptom}
          </p>
        )}
        <div className="text-sm text-muted-foreground leading-7 space-y-3">
          {children}
        </div>
      </div>
    </div>
  );
}

function CodeBlock({ children }) {
  return (
    <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-xs overflow-x-auto my-2">
      <pre className="text-[var(--sardis-canvas)]">{children}</pre>
    </div>
  );
}

function InlineCode({ children }) {
  return (
    <code className="px-1 py-0.5 bg-muted font-mono text-xs">{children}</code>
  );
}

export default function DocsTroubleshooting() {
  const [openItems, setOpenItems] = useState({});

  const toggle = (key) => {
    setOpenItems(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <>
      <SEO
        title="Troubleshooting Guide - Common Sardis Issues and Fixes"
        description="Diagnose and fix common Sardis integration issues: wallet configuration errors, policy blocks, authentication failures, chain timeouts, rate limits, KYC requirements, and debug logging."
        path="/docs/troubleshooting"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Troubleshooting', href: '/docs/troubleshooting' },
          ]),
        ]}
      />
      <article className="prose dark:prose-invert max-w-none">
        <div className="not-prose mb-10">
          <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
            <span className="px-2 py-1 bg-yellow-500/10 border border-yellow-500/30 text-yellow-500">
              SUPPORT
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">Troubleshooting Guide</h1>
          <p className="text-xl text-muted-foreground leading-relaxed">
            Diagnose and fix common issues when integrating Sardis into your AI agent stack.
          </p>
        </div>

        {/* Quick Nav */}
        <div className="not-prose mb-10 p-5 border border-border bg-card/50">
          <h2 className="font-bold font-display mb-3 text-sm text-muted-foreground uppercase tracking-widest">Jump to issue</h2>
          <ul className="space-y-1.5 text-sm">
            {[
              ['no-wallet', '"No wallet ID configured"'],
              ['policy-blocked', '"Policy blocked" / Payment denied'],
              ['auth-failed', '"Authentication failed" / 401 errors'],
              ['chain-timeout', '"Chain execution timeout"'],
              ['sim-vs-prod', 'Simulation vs Production confusion'],
              ['rate-limit', '"Rate limit exceeded" / 429'],
              ['kyc-required', '"KYC required" errors'],
              ['env-checklist', 'Environment variable checklist'],
              ['debug-logging', 'Enable debug logging'],
            ].map(([id, label]) => (
              <li key={id}>
                <a
                  href={`#${id}`}
                  className="text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors font-mono"
                >
                  → {label}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Section 1 */}
        <section id="no-wallet" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 1. "No wallet ID configured"
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title='Error: "No wallet ID configured" or wallet_id is None'
              symptom='SDK raises ValueError or returns a 400 response with message "wallet_id required"'
              isOpen={openItems['no-wallet-1']}
              onClick={() => toggle('no-wallet-1')}
            >
              <p><strong>Cause:</strong> The SDK could not resolve a wallet ID. It checks (in order): the argument passed to the call, the client-level default, and the <InlineCode>SARDIS_WALLET_ID</InlineCode> environment variable. All three are unset.</p>
              <p><strong>Fix — option A:</strong> Set the environment variable before running your agent:</p>
              <CodeBlock>{`export SARDIS_WALLET_ID=wal_your_wallet_id_here`}</CodeBlock>
              <p><strong>Fix — option B:</strong> Pass <InlineCode>wallet_id</InlineCode> when initialising the SDK client:</p>
              <CodeBlock>{`from sardis import SardisClient

client = SardisClient(
    api_key="sk_test_...",
    wallet_id="wal_your_wallet_id_here",
)`}</CodeBlock>
              <p><strong>Fix — option C:</strong> Pass it per call when you need multiple wallets in one process:</p>
              <CodeBlock>{`await client.payments.create(
    amount=10.00,
    currency="USDC",
    merchant="aws.amazon.com",
    wallet_id="wal_your_wallet_id_here",
)`}</CodeBlock>
              <p>You can look up wallet IDs in the <a href="https://app.sardis.sh" className="text-[var(--sardis-orange)] hover:underline">Sardis dashboard</a> under Wallets, or via the API:</p>
              <CodeBlock>{`curl https://api.sardis.sh/api/v2/wallets \\
  -H "Authorization: Bearer sk_test_..."`}</CodeBlock>
            </AccordionItem>
          </div>
        </section>

        {/* Section 2 */}
        <section id="policy-blocked" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 2. "Policy blocked" / Payment denied
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title="Payment returns status 'blocked' with policy_violation reason"
              symptom='API returns 403 with {"error": "policy_violation", "reason": "daily_limit_exceeded"} or similar'
              isOpen={openItems['policy-1']}
              onClick={() => toggle('policy-1')}
            >
              <p><strong>Cause:</strong> One or more policy rules rejected the transaction before it reached the chain. Common triggers:</p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Daily or monthly spending limit reached</li>
                <li>Merchant not on the allowlist (or explicitly blocklisted)</li>
                <li>Merchant category (MCC) restricted for this wallet</li>
                <li>Time-window restriction (e.g. business hours only)</li>
                <li>Per-transaction amount over the configured cap</li>
              </ul>
              <p><strong>Fix — inspect the active policy:</strong></p>
              <CodeBlock>{`from sardis import SardisClient

client = SardisClient(api_key="sk_test_...")
policy = await client.policies.get(wallet_id="wal_...")
print(policy)`}</CodeBlock>
              <p><strong>Fix — pre-flight check before attempting a payment:</strong></p>
              <CodeBlock>{`result = await client.policies.check(
    wallet_id="wal_...",
    amount=25.00,
    merchant="vercel.com",
)
if result.allowed:
    await client.payments.create(...)
else:
    print("Blocked because:", result.reason)`}</CodeBlock>
              <p><strong>Fix — update the policy</strong> via the dashboard at <a href="https://app.sardis.sh" className="text-[var(--sardis-orange)] hover:underline">app.sardis.sh</a> → Wallet → Policy, or via the API:</p>
              <CodeBlock>{`curl -X PATCH https://api.sardis.sh/api/v2/wallets/wal_.../policy \\
  -H "Authorization: Bearer sk_test_..." \\
  -H "Content-Type: application/json" \\
  -d '{"daily_limit": 500, "merchant_allowlist": ["vercel.com", "aws.amazon.com"]}'`}</CodeBlock>
            </AccordionItem>
          </div>
        </section>

        {/* Section 3 */}
        <section id="auth-failed" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 3. "Authentication failed" / 401 errors
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title='HTTP 401 Unauthorized or "Invalid API key"'
              symptom='Every request returns 401 with {"error": "authentication_failed"}'
              isOpen={openItems['auth-1']}
              onClick={() => toggle('auth-1')}
            >
              <p><strong>Cause:</strong> The API key is missing, malformed, expired, or the wrong type for the environment you are targeting.</p>
              <p><strong>Check key prefix:</strong></p>
              <ul className="list-disc pl-5 space-y-1">
                <li><InlineCode>sk_test_...</InlineCode> — test mode (in-memory simulation, safe for development)</li>
                <li><InlineCode>sk_live_...</InlineCode> — live mode (real funds, requires full infra)</li>
              </ul>
              <p>Mixing a <InlineCode>sk_test_</InlineCode> key against the live API endpoint (or vice versa) returns 401.</p>
              <p><strong>Fix — verify the Authorization header format:</strong></p>
              <CodeBlock>{`# Correct
curl https://api.sardis.sh/api/v2/wallets \\
  -H "Authorization: Bearer YOUR_API_KEY_HERE"

# Wrong — missing "Bearer"
# Authorization: YOUR_API_KEY_HERE  ← this will fail`}</CodeBlock>
              <p><strong>Fix — Python SDK:</strong></p>
              <CodeBlock>{`import os
from sardis import SardisClient

# Key comes from environment variable — never hardcode
client = SardisClient(api_key=os.environ["SARDIS_API_KEY"])`}</CodeBlock>
              <p>If the key was recently rotated or revoked, generate a new one in the dashboard under Settings → API Keys.</p>
            </AccordionItem>
          </div>
        </section>

        {/* Section 4 */}
        <section id="chain-timeout" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 4. "Chain execution timeout"
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title='Payment stuck in "pending" or raises ChainExecutionTimeout'
              symptom='SDK raises ChainExecutionTimeout after 30 s, or payment stays in pending state indefinitely'
              isOpen={openItems['chain-1']}
              onClick={() => toggle('chain-1')}
            >
              <p><strong>Cause:</strong> The RPC endpoint used to broadcast or poll the transaction is rate-limited, degraded, or unavailable. By default Sardis falls back to public RPCs which are shared and heavily rate-limited.</p>
              <p><strong>Fix — set a dedicated RPC URL (strongly recommended for production):</strong></p>
              <CodeBlock>{`# .env or shell
export SARDIS_BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_ALCHEMY_KEY

# Or for testnet
export SARDIS_BASE_RPC_URL=https://base-sepolia.g.alchemy.com/v2/YOUR_ALCHEMY_KEY`}</CodeBlock>
              <p>Alchemy, Infura, and QuickNode all offer free tiers with generous rate limits. Alchemy is the recommended provider for Base.</p>
              <p><strong>Fix — check chain status:</strong></p>
              <ul className="list-disc pl-5 space-y-1">
                <li>Base mainnet status: <a href="https://status.base.org" className="text-[var(--sardis-orange)] hover:underline" target="_blank" rel="noopener noreferrer">status.base.org</a></li>
                <li>Alchemy status: <a href="https://alchemyapi.statuspage.io" className="text-[var(--sardis-orange)] hover:underline" target="_blank" rel="noopener noreferrer">alchemyapi.statuspage.io</a></li>
              </ul>
              <p><strong>Fix — increase the SDK timeout (not a cure, but buys time during congestion):</strong></p>
              <CodeBlock>{`client = SardisClient(
    api_key="sk_test_...",
    chain_timeout_seconds=60,  # default is 30
)`}</CodeBlock>
            </AccordionItem>
          </div>
        </section>

        {/* Section 5 */}
        <section id="sim-vs-prod" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 5. Simulation vs Production confusion
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title="Payments succeed in test but nothing happens on-chain in production"
              symptom='Payments return success locally but no on-chain activity is visible, or live users report nothing happened'
              isOpen={openItems['sim-1']}
              onClick={() => toggle('sim-1')}
            >
              <p><strong>Cause:</strong> <InlineCode>sk_test_</InlineCode> keys run entirely in-memory simulation mode. No chain transactions are submitted, no real funds move. This is intentional and ideal for development, but behaviour differs from live mode.</p>

              <div className="not-prose overflow-x-auto my-3">
                <table className="w-full text-xs font-mono border-collapse">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left px-3 py-2 text-muted-foreground">Feature</th>
                      <th className="text-left px-3 py-2 text-yellow-500">sk_test_ (simulation)</th>
                      <th className="text-left px-3 py-2 text-emerald-500">sk_live_ (production)</th>
                    </tr>
                  </thead>
                  <tbody className="text-muted-foreground">
                    <tr className="border-b border-border/50">
                      <td className="px-3 py-2">On-chain txn</td>
                      <td className="px-3 py-2">No</td>
                      <td className="px-3 py-2">Yes</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="px-3 py-2">Real funds</td>
                      <td className="px-3 py-2">No</td>
                      <td className="px-3 py-2">Yes</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="px-3 py-2">MPC signing</td>
                      <td className="px-3 py-2">No (simulated)</td>
                      <td className="px-3 py-2">Yes (Turnkey)</td>
                    </tr>
                    <tr className="border-b border-border/50">
                      <td className="px-3 py-2">Policy engine</td>
                      <td className="px-3 py-2">Yes (same rules)</td>
                      <td className="px-3 py-2">Yes</td>
                    </tr>
                    <tr>
                      <td className="px-3 py-2">KYC required</td>
                      <td className="px-3 py-2">No</td>
                      <td className="px-3 py-2">Yes (for fiat)</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <p><strong>Fix — use test keys during development, switch to live keys for production:</strong></p>
              <CodeBlock>{`# Development (.env.development)
SARDIS_API_KEY=sk_test_...

# Production (.env.production)
SARDIS_API_KEY=sk_live_...`}</CodeBlock>
              <p>Never commit live keys. Use your CI/CD secrets manager or a tool like <InlineCode>doppler</InlineCode> / <InlineCode>infisical</InlineCode> for production key injection.</p>
            </AccordionItem>
          </div>
        </section>

        {/* Section 6 */}
        <section id="rate-limit" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 6. "Rate limit exceeded" / 429
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title='HTTP 429 Too Many Requests from the Sardis API'
              symptom='Burst of requests causes 429 responses; agent retries loop and exhaust quota faster'
              isOpen={openItems['rate-1']}
              onClick={() => toggle('rate-1')}
            >
              <p><strong>Cause:</strong> Your account has reached the API call limit for its plan. Free tier: 1,000 calls/month. Calls reset on the first of each month (UTC).</p>
              <p><strong>Fix — check current usage:</strong></p>
              <CodeBlock>{`curl https://api.sardis.sh/api/v2/account/usage \\
  -H "Authorization: Bearer sk_test_..."`}</CodeBlock>
              <p>You can also view real-time usage and remaining quota in the <a href="https://app.sardis.sh" className="text-[var(--sardis-orange)] hover:underline">dashboard</a> under Settings → Usage.</p>
              <p><strong>Fix — add exponential backoff in your agent loop:</strong></p>
              <CodeBlock>{`import asyncio

async def pay_with_retry(client, **kwargs):
    for attempt in range(5):
        try:
            return await client.payments.create(**kwargs)
        except sardis.RateLimitError as e:
            wait = 2 ** attempt  # 1, 2, 4, 8, 16 s
            print(f"Rate limited, retrying in {wait}s...")
            await asyncio.sleep(wait)
    raise RuntimeError("Exhausted retries")`}</CodeBlock>
              <p><strong>Fix — upgrade your plan</strong> at <a href="/pricing" className="text-[var(--sardis-orange)] hover:underline">/pricing</a> for higher limits or unlimited API calls on the Pro and Enterprise tiers.</p>
            </AccordionItem>
          </div>
        </section>

        {/* Section 7 */}
        <section id="kyc-required" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 7. "KYC required" errors
          </h2>
          <div className="not-prose space-y-3">
            <AccordionItem
              title='"KYC verification required" when attempting live transactions or fiat off-ramp'
              symptom='API returns 403 with {"error": "kyc_required"} on live payment or withdrawal request'
              isOpen={openItems['kyc-1']}
              onClick={() => toggle('kyc-1')}
            >
              <p><strong>Cause:</strong> Identity verification (KYC) is required for live fiat transactions and off-ramp operations. This applies to <InlineCode>sk_live_</InlineCode> keys only — test keys bypass KYC.</p>
              <p><strong>Fix — complete KYC via the dashboard:</strong></p>
              <ol className="list-decimal pl-5 space-y-1">
                <li>Go to <a href="https://app.sardis.sh" className="text-[var(--sardis-orange)] hover:underline">app.sardis.sh</a></li>
                <li>Navigate to Settings → Identity Verification</li>
                <li>Complete the iDenfy identity flow (government ID + liveness check)</li>
                <li>Verification typically completes within 5 minutes</li>
              </ol>
              <p><strong>Fix — check KYC status programmatically via MCP tools:</strong></p>
              <CodeBlock>{`# In Claude Desktop or Cursor with Sardis MCP configured
# Ask Claude: "Check my KYC status"
# Claude will call sardis_get_kyc_status automatically`}</CodeBlock>
              <p><strong>Fix — check status via API:</strong></p>
              <CodeBlock>{`curl https://api.sardis.sh/api/v2/account/kyc \\
  -H "Authorization: Bearer sk_live_..."`}</CodeBlock>
              <p>Stablecoin-only wallets (no fiat off-ramp) do not require KYC. If you only need on-chain USDC payments, you can proceed without verification.</p>
            </AccordionItem>
          </div>
        </section>

        {/* Section 8 — Env Checklist */}
        <section id="env-checklist" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 8. Environment variable checklist
          </h2>
          <div className="not-prose overflow-x-auto border border-border">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/30">
                  <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground">Variable</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground">Purpose</th>
                  <th className="text-left px-4 py-3 font-mono text-xs text-muted-foreground">Required</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['SARDIS_API_KEY', 'Authenticates all SDK and API calls', 'Required'],
                  ['DATABASE_URL', 'PostgreSQL connection string (Neon recommended)', 'Required (server)'],
                  ['TURNKEY_API_KEY', 'MPC signing via Turnkey (live mode only)', 'Required (live)'],
                  ['TURNKEY_ORGANIZATION_ID', 'Turnkey organisation identifier', 'Required (live)'],
                  ['SARDIS_WALLET_ID', 'Default wallet ID used when none is passed to calls', 'Optional'],
                  ['SARDIS_BASE_RPC_URL', 'Alchemy/Infura RPC for Base chain — overrides public RPC', 'Optional (recommended)'],
                  ['SARDIS_LOG_LEVEL', 'Logging verbosity: DEBUG, INFO, WARNING, ERROR', 'Optional'],
                  ['SARDIS_IDENFY_API_KEY', 'KYC provider (iDenfy) — required for fiat off-ramp in production', 'Optional'],
                  ['SARDIS_REDIS_URL', 'Redis for rate limiting and dedup — required in non-dev environments', 'Optional'],
                  ['POSTHOG_API_KEY', 'Analytics (PostHog) — not required for SDK operation', 'Optional'],
                  ['SMTP_HOST', 'Email delivery for notifications', 'Optional'],
                ].map(([name, purpose, req]) => (
                  <tr key={name} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-foreground">{name}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{purpose}</td>
                    <td className="px-4 py-3">
                      <span className={cn(
                        "px-2 py-0.5 text-xs font-mono border",
                        req.startsWith('Required') ? 'bg-red-500/10 text-red-500 border-red-500/30' : 'bg-muted/50 text-muted-foreground border-border'
                      )}>
                        {req}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="not-prose mt-4 p-4 border border-border bg-card/50">
            <p className="text-sm text-muted-foreground">
              A minimal <InlineCode>.env</InlineCode> for local development with test keys only needs <InlineCode>SARDIS_API_KEY</InlineCode> and <InlineCode>SARDIS_WALLET_ID</InlineCode>.
              No database or Turnkey credentials are required when using <InlineCode>sk_test_</InlineCode> keys.
            </p>
          </div>
        </section>

        {/* Section 9 — Debug Logging */}
        <section id="debug-logging" className="mb-10">
          <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2 not-prose">
            <span className="text-[var(--sardis-orange)]">#</span> 9. Enable debug logging
          </h2>
          <div className="not-prose space-y-4">
            <p className="text-sm text-muted-foreground">When an error is unclear, enable verbose output to see the full request/response cycle and policy evaluation trace.</p>

            <div>
              <h3 className="font-bold font-display text-sm mb-2">Environment variable (affects all Sardis output)</h3>
              <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-xs overflow-x-auto">
                <pre className="text-[var(--sardis-canvas)]">{`export SARDIS_LOG_LEVEL=DEBUG`}</pre>
              </div>
            </div>

            <div>
              <h3 className="font-bold font-display text-sm mb-2">Python SDK — enable verbose HTTP logging</h3>
              <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-xs overflow-x-auto">
                <pre className="text-[var(--sardis-canvas)]">{`import logging

# Log all Sardis SDK activity
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("sardis").setLevel(logging.DEBUG)

# Also log the underlying HTTP requests (httpx)
logging.getLogger("httpx").setLevel(logging.DEBUG)

from sardis import SardisClient
client = SardisClient(api_key="sk_test_...")`}</pre>
              </div>
            </div>

            <div>
              <h3 className="font-bold font-display text-sm mb-2">TypeScript SDK</h3>
              <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-xs overflow-x-auto">
                <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({
  apiKey: process.env.SARDIS_API_KEY!,
  debug: true,  // logs all requests and policy decisions
});`}</pre>
              </div>
            </div>

            <div>
              <h3 className="font-bold font-display text-sm mb-2">What to look for in debug output</h3>
              <ul className="space-y-2 text-sm text-muted-foreground">
                {[
                  'Policy check result — which rule triggered (daily_limit, merchant_allowlist, category, time_window)',
                  'RPC call latency — indicates if chain timeout is an RPC issue',
                  'Request headers — confirms the Authorization header is present and correctly formatted',
                  'Response body — full error detail from the API, often more descriptive than the SDK exception',
                ].map((item) => (
                  <li key={item} className="flex items-start gap-3">
                    <span className="w-1.5 h-1.5 bg-[var(--sardis-orange)] shrink-0 mt-1.5"></span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </section>

        {/* Still stuck */}
        <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mt-4">
          <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Still stuck?</h3>
          <p className="text-muted-foreground text-sm mb-4">
            If none of the above resolves your issue, open a discussion on GitHub with your debug logs (redact your API key) or contact us directly.
          </p>
          <div className="flex gap-4">
            <a
              href="https://github.com/EfeDurmaz16/sardis/discussions"
              className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
            >
              Open GitHub Discussion
            </a>
            <a
              href="mailto:dev@sardis.sh"
              className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
            >
              Email dev@sardis.sh
            </a>
          </div>
        </section>
      </article>
    </>
  );
}
