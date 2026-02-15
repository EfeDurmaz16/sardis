import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';

export default function SardisV087LaunchHardening() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      <header className="not-prose mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-500">
            RELEASE
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
            FEATURED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Sardis v0.8.8: ERC-4337 Base Preview + Truth Alignment
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 15, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />4 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        v0.8.8 adds a real ERC-4337 implementation lane for design partners on Base Sepolia, introduces
        account_type parity across API and SDKs, and tightens public language around non-custodial posture
        and fiat partner rails.
      </p>

      <h2>Gasless Smart Wallets (ERC-4337)</h2>

      <p>
        The headline feature is a Base Sepolia preview lane for sponsored UserOperations. This lane is
        feature-flagged and fail-closed until bundler/paymaster and signer configuration are present.
      </p>

      <ul>
        <li>New contracts: <code>SardisSmartAccount</code>, <code>SardisSmartAccountFactory</code>, <code>SardisVerifyingPaymaster</code></li>
        <li>Pimlico bundler/paymaster clients wired into execution runtime with explicit config gates</li>
        <li>Wallet API and SDKs now support <code>account_type=&quot;erc4337_v2&quot;</code></li>
        <li>Transfer responses now expose <code>execution_path</code> and <code>user_op_hash</code></li>
        <li>v1 wallets remain unchanged and fully supported</li>
        <li>Current preview scope: Base Sepolia only</li>
      </ul>

      <h2>PostgreSQL Persistence for Cards & Ledger</h2>

      <p>
        We migrated all remaining in-memory stores to PostgreSQL. Card services (conversions, wallet
        mappings, offramp transactions) and the ledger engine now persist to Neon serverless PostgreSQL
        with full ACID guarantees.
      </p>

      <ul>
        <li><code>PostgresUnifiedBalanceService</code> — replaces in-memory USD balance tracking</li>
        <li><code>PostgresAutoConversionService</code> — replaces in-memory USDC↔USD conversion records</li>
        <li><code>PostgresOfframpService</code> — replaces in-memory offramp transaction tracking</li>
        <li><code>PostgresLedgerEngine</code> — full-precision NUMERIC(38,18) entries with advisory locks</li>
        <li>Alembic migration 015: 5 new tables with proper indexes</li>
      </ul>

      <h2>Context7 Documentation Improvements</h2>

      <p>
        Three new documentation areas to improve AI agent discoverability:
      </p>

      <ul>
        <li><strong>Time-Based Policies</strong> — timezone handling, DST, overnight windows, multiple schedules</li>
        <li><strong>Merchant Categories (MCC)</strong> — 18 categories, allowlist vs blocklist modes, auto-detection</li>
        <li><strong>Combined Limit Strategy</strong> — per-merchant overrides, Conservative/Standard/Enterprise profiles</li>
      </ul>

      <h2>Security: Timestamped Webhook Verification</h2>

      <p>
        Onramper webhook validation now requires time-bounded signatures. We enforce a 5-minute replay
        tolerance window and reject old signatures to reduce replay attack risk.
      </p>

      <ul>
        <li>Supports signature format <code>t=&lt;timestamp&gt;,v1=&lt;hmac&gt;</code> using <code>timestamp.body</code> payload signing</li>
        <li>Supports legacy raw-body HMAC only when a timestamp header is present and valid</li>
        <li>Rejects missing, invalid, and stale timestamps with explicit 401 responses</li>
      </ul>

      <h2>SDK and API Parity</h2>

      <p>
        Wallet and transfer surfaces now expose the same fields across API, Python SDK, TypeScript SDK, and MCP.
      </p>

      <ul>
        <li>Create wallet now supports <code>account_type</code> (<code>mpc_v1</code> or <code>erc4337_v2</code>)</li>
        <li>Upgrade endpoint added: <code>POST /api/v2/wallets/{'{id}'}/upgrade-smart-account</code></li>
        <li>Transfer response includes <code>execution_path</code> and <code>user_op_hash</code> when applicable</li>
      </ul>

      <h2>Truth Alignment</h2>

      <p>
        We normalized docs and landing claims to match what is actually running:
      </p>

      <ul>
        <li>Non-custodial wording now explicitly scoped to stablecoin live-MPC mode</li>
        <li>Fiat rails wording now reflects regulated partner settlement/custody boundaries</li>
        <li>Gasless wording now explicitly states Base Sepolia preview scope</li>
      </ul>

      <div className="not-prose mt-8 p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Read Next</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            → <Link to="/docs/changelog" className="text-[var(--sardis-orange)] hover:underline">Full Changelog</Link>
          </li>
          <li>
            → <Link to="/docs/roadmap" className="text-[var(--sardis-orange)] hover:underline">Roadmap</Link>
          </li>
          <li>
            → <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noopener noreferrer" className="text-[var(--sardis-orange)] hover:underline">GitHub Repository</a>
          </li>
        </ul>
      </div>
    </article>
  );
}
