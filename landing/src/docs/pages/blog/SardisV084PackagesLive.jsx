import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';

export default function SardisV084PackagesLive() {
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
          Sardis v0.8.4: Packages Live on npm & PyPI + Security Audit
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 8, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />5 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        Today we published all 18 Sardis packages to public registries. Every SDK, protocol implementation,
        and tool is now installable with a single command. This release also includes the results of a
        comprehensive security audit: 54 fixes across 8 batches covering every layer of the stack.
      </p>

      <h2>Packages Are Live</h2>

      <p>
        All Sardis packages are now publicly available. Developers can start exploring the SDK,
        protocol implementations, and tooling today.
      </p>

      <h3>npm (4 packages)</h3>
      <ul>
        <li><code>@sardis/sdk</code> - TypeScript SDK for wallets, payments, policies, and holds</li>
        <li><code>@sardis/mcp-server</code> - MCP server with 40+ payment tools for Claude and Cursor</li>
        <li><code>@sardis/ai-sdk</code> - Vercel AI SDK integration for agent payment flows</li>
        <li><code>@sardis/ramp</code> - Fiat on/off ramp integration (Onramper, Bridge)</li>
      </ul>

      <h3>PyPI (14 packages)</h3>
      <ul>
        <li><code>sardis-sdk</code> - Full Python SDK</li>
        <li><code>sardis-core</code> - Domain models, config, database layer</li>
        <li><code>sardis-protocol</code> - AP2/TAP mandate verification pipeline</li>
        <li><code>sardis-chain</code> - Multi-chain execution (Base, Polygon, Ethereum, Arbitrum, Optimism)</li>
        <li><code>sardis-api</code> - FastAPI REST endpoints</li>
        <li><code>sardis-wallet</code> - MPC wallet management (Turnkey, Fireblocks)</li>
        <li><code>sardis-ledger</code> - Append-only audit trail with Merkle anchoring</li>
        <li><code>sardis-compliance</code> - KYC (Persona) + AML (Elliptic) integrations</li>
        <li><code>sardis-cards</code> - Virtual card issuance (Lithic)</li>
        <li><code>sardis-cli</code> - Command-line tool</li>
        <li><code>sardis-checkout</code> - Merchant checkout flows</li>
        <li><code>sardis-ramp</code> - Fiat rails (Bridge, Onramper)</li>
        <li><code>sardis-ucp</code> - Universal Commerce Protocol</li>
        <li><code>sardis-a2a</code> - Agent-to-Agent Protocol</li>
      </ul>

      <h2>Security Audit: 54 Fixes</h2>

      <p>
        Before publishing, we completed a comprehensive security audit covering 8 batches
        of fixes across every layer of the stack:
      </p>

      <div className="not-prose grid md:grid-cols-2 gap-4 my-6">
        {[
          { batch: 'Batch 1-2', desc: 'Authentication & authorization hardening, API key hashing, CORS configuration' },
          { batch: 'Batch 3-4', desc: 'Input validation, SQL injection prevention, rate limiting, replay protection' },
          { batch: 'Batch 5-6', desc: 'Cryptographic improvements, smart contract security, dependency audits' },
          { batch: 'Batch 7-8', desc: 'AI prompt injection defenses, webhook signatures, JWT migration to PyJWT' },
        ].map((item) => (
          <div key={item.batch} className="p-4 border border-border">
            <h4 className="font-bold font-display mb-1 text-sm">{item.batch}</h4>
            <p className="text-sm text-muted-foreground">{item.desc}</p>
          </div>
        ))}
      </div>

      <p>
        All 649 Python tests and 91 Solidity tests (including 10K fuzz runs) pass after the audit.
        The identity registry now fail-closes in production and staging environments, and anonymous
        access is restricted to loopback addresses only.
      </p>

      <h2>What's Next: Public API & Dashboard</h2>

      <p>
        The SDKs are published, but they need a hosted API backend to connect to. Here's what's coming next week:
      </p>

      <ul>
        <li><strong>Public Staging API</strong> - Deployed on Cloud Run, accessible for testnet/Base Sepolia</li>
        <li><strong>Dashboard UI</strong> - Web dashboard for wallet management, transaction history, and policy configuration</li>
        <li><strong>API Key Self-Service</strong> - Sign up and get an API key without manual onboarding</li>
        <li><strong>OpenAPI Documentation</strong> - Interactive Swagger docs for all v2 endpoints</li>
      </ul>

      <div className="not-prose p-4 border border-yellow-500/30 bg-yellow-500/10 my-6">
        <p className="text-sm text-muted-foreground">
          <span className="font-bold text-yellow-500">Early Access:</span> The SDKs are installable now but require
          an API key to connect to the hosted backend. Join the waitlist at{' '}
          <a href="https://sardis.sh" className="text-[var(--sardis-orange)] hover:underline">sardis.sh</a>{' '}
          to get early access when the public API launches.
        </p>
      </div>

      <h2>Try It Now</h2>

      <div className="not-prose">
        <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`# Python
pip install sardis-sdk

# TypeScript
npm install @sardis/sdk

# MCP Server (for Claude Desktop / Cursor)
npx @sardis/mcp-server init --mode simulated
npx @sardis/mcp-server start`}</pre>
        </div>
      </div>

      <div className="not-prose mt-8 p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Links</h3>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li>
            → <a href="https://pypi.org/user/sardis/" target="_blank" rel="noopener noreferrer" className="text-[var(--sardis-orange)] hover:underline">PyPI Packages</a>
          </li>
          <li>
            → <a href="https://www.npmjs.com/org/sardis" target="_blank" rel="noopener noreferrer" className="text-[var(--sardis-orange)] hover:underline">npm Packages</a>
          </li>
          <li>
            → <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noopener noreferrer" className="text-[var(--sardis-orange)] hover:underline">GitHub Repository</a>
          </li>
          <li>
            → <Link to="/docs/changelog" className="text-[var(--sardis-orange)] hover:underline">Full Changelog</Link>
          </li>
        </ul>
      </div>
    </article>
  );
}
