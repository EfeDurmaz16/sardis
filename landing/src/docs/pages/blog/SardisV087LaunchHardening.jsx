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
          Sardis v0.8.7: Smart Wallets, DB Persistence & Launch Hardening
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
        v0.8.7 is our biggest pre-launch release. It introduces ERC-4337 gasless smart wallet architecture,
        migrates card and ledger services to PostgreSQL persistence, adds comprehensive spending policy
        documentation, and hardens webhook security for production.
      </p>

      <h2>Gasless Smart Wallets (ERC-4337)</h2>

      <p>
        The headline feature: agents can now transact without holding ETH. We designed an ERC-4337 account
        abstraction architecture where Sardis sponsors gas fees via a paymaster contract. Agents only deal
        in stablecoins (USDC, USDT, EURC).
      </p>

      <ul>
        <li>Smart accounts implementing <code>IAccount</code> with Turnkey MPC signing</li>
        <li>Paymaster integration (Pimlico) sponsors gas — agents pay $0.00 in gas</li>
        <li>Bundler submits UserOperations to ERC-4337 EntryPoint v0.7</li>
        <li>Supported on all 5 L2s: Base, Polygon, Arbitrum, Optimism, Ethereum</li>
        <li>Backward compatible — v1 MPC wallets continue working unchanged</li>
        <li>Stablecoin-only token allowlist: on-chain smart contract prevents non-stablecoin transfers</li>
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

      <h2>SDK and Package Metadata Parity</h2>

      <p>
        We fixed runtime version constants so SDK clients report the same versions that are published in
        npm and PyPI metadata. This prevents confusion during support and release validation.
      </p>

      <ul>
        <li><code>@sardis/sdk</code> runtime version aligned to <code>0.3.4</code></li>
        <li><code>sardis-sdk</code> runtime version aligned to <code>0.3.3</code></li>
        <li><code>@sardis/ai-sdk</code> workspace dependency aligned to current SDK range</li>
      </ul>

      <h2>Launch Docs Cleanup</h2>

      <p>
        We normalized public claims and quickstarts so they map cleanly to code:
      </p>

      <ul>
        <li>MCP tools: <strong>52</strong></li>
        <li>Total packages: <strong>19</strong> (npm + PyPI)</li>
        <li>Supported chains: <strong>5</strong></li>
        <li>README TypeScript quickstart now uses current SDK methods</li>
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
