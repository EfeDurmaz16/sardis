import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function SardisV07ProductionHardening() {
  return (
    <article className="prose prose-invert max-w-none">
      {/* Back link */}
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      {/* Header */}
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
          Sardis v0.7: Production Hardening and Fireblocks Integration
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 2, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />6 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        Sardis v0.7 is our biggest infrastructure release yet. We eliminated 24 technical debt items across 11 files,
        moving from prototype-grade in-memory stores to production-ready PostgreSQL persistence, adding institutional
        MPC custody via Fireblocks, and hardening authentication across every API route.
      </p>

      <h2>The Problem: Technical Debt at Scale</h2>

      <p>
        As Sardis grew from a testnet prototype to a near-production system, several critical patterns
        accumulated that would prevent reliable deployment: in-memory mandate and checkout stores that
        lost state on restart, hardcoded authentication bypasses in API routes, a webhook secret rotation
        endpoint that generated secrets but never saved them, and missing database tables for invoices and KYC.
      </p>

      <p>
        v0.7 addresses all of these systematically, in 11 atomic commits that each represent a self-contained improvement.
      </p>

      <h2>PostgreSQL Everywhere</h2>

      <p>
        Three core stores have been migrated from in-memory dictionaries to PostgreSQL:
      </p>

      <ul>
        <li><strong>Mandate Store</strong> &mdash; The AP2 mandate lifecycle (create &rarr; validate &rarr; execute &rarr; cancel) now persists
          across restarts with full status tracking, attestation bundles, and execution results.</li>
        <li><strong>Checkout Sessions</strong> &mdash; PSP checkout sessions (Stripe, PayPal, etc.) now persist with proper
          timestamps, fixing the long-standing <code>created_at=""</code> TODO.</li>
        <li><strong>KYC Verifications</strong> &mdash; Persona KYC results are now stored in a dedicated <code>kyc_verifications</code> table
          with database lookup fallback when the in-memory cache misses.</li>
      </ul>

      <h2>Fireblocks MPC Signer</h2>

      <p>
        For institutional deployments that require Fireblocks instead of Turnkey, we've added a complete
        <code>FireblocksSigner</code> implementation:
      </p>

      <ul>
        <li>Vault account creation with auto-fuel</li>
        <li>Deposit address generation per asset</li>
        <li>Transaction signing via Fireblocks REST API with JWT authentication</li>
        <li>Transaction status polling</li>
      </ul>

      <p>
        The executor now automatically selects the Fireblocks signer when <code>mpc_config.name == "fireblocks"</code>,
        with environment variables <code>FIREBLOCKS_API_KEY</code> and <code>FIREBLOCKS_API_SECRET</code>.
      </p>

      <h2>Authentication Hardening</h2>

      <p>
        Every API route that previously used hardcoded <code>"default"</code> or <code>"demo_agent"</code> values
        now enforces real authentication:
      </p>

      <ul>
        <li><strong>Agent routes</strong> &mdash; <code>owner_id</code> extracted from <code>api_key.organization_id</code></li>
        <li><strong>Webhook routes</strong> &mdash; <code>organization_id</code> from the API key</li>
        <li><strong>Marketplace routes</strong> &mdash; Agent identity from <code>X-Agent-Id</code> header</li>
      </ul>

      <h2>Invoices API</h2>

      <p>
        A new <code>/api/v2/invoices</code> router provides full CRUD for merchant invoices:
        create, list (with status filtering), get by ID, and update status. The dashboard Invoices
        page has been rewired from mock data to the real API with loading states and error handling.
      </p>

      <h2>Developer Experience Improvements</h2>

      <ul>
        <li><strong>ABI Revert Decoding</strong> &mdash; Solidity <code>Error(string)</code> revert reasons are now decoded from raw hex
          into human-readable messages instead of showing <code>0x08c379a0...</code></li>
        <li><strong>sardis-chain exports</strong> &mdash; Fixed <code>ChainId</code>, <code>TokenConfig</code>, <code>GasConfig</code>, <code>RPCConfig</code>,
          and <code>TurnkeyConfig</code> exports that were missing from <code>config.py</code></li>
        <li><strong>pnpm workspace</strong> &mdash; <code>sardis-ai-sdk</code> now resolves <code>@sardis/sdk</code> via <code>workspace:*</code> instead
          of a non-existent npm package</li>
        <li><strong>Python 3.13</strong> &mdash; Pinned <code>asyncpg&gt;=0.30</code> and <code>fastapi&gt;=0.115</code> for compatibility</li>
      </ul>

      <h2>Critical Bug Fixes</h2>

      <ul>
        <li><strong>NameError in main.py</strong> &mdash; <code>app.state.turnkey_client</code> was assigned before the variable was defined,
          causing a crash on every API server startup</li>
        <li><strong>Schema idempotency</strong> &mdash; <code>ALTER TABLE</code> migrations for the mandates table consolidated into
          the <code>CREATE TABLE</code> statement for clean fresh initialization</li>
        <li><strong>Webhook secret rotation</strong> &mdash; The rotate-secret endpoint now actually persists the new secret
          to the database</li>
      </ul>

      <h2>What's Next</h2>

      <p>
        With v0.7 landing, Sardis is substantially closer to production readiness. The remaining items
        on our pre-deployment checklist are:
      </p>

      <ul>
        <li>Container/Docker configuration for deployment</li>
        <li>Coverage tracking in CI/CD (target: 70%+)</li>
        <li>Health checks for deployed smart contract addresses</li>
        <li>Cross-chain routing in the CLI</li>
      </ul>

      <p>
        If you're building AI agents that need real financial capabilities, <Link to="/docs/quickstart" className="text-[var(--sardis-orange)]">get started with Sardis</Link> or
        join our Alpha Design Partner Program.
      </p>

      {/* Footer */}
      <div className="not-prose mt-12 pt-6 border-t border-border">
        <Link
          to="/docs/changelog"
          className="inline-flex items-center gap-2 text-sm text-[var(--sardis-orange)] hover:underline"
        >
          View full changelog &rarr;
        </Link>
      </div>
    </article>
  );
}
