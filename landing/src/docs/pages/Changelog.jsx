import { cn } from '@/lib/utils';

const releases = [
  {
    version: '0.8.6',
    date: '2026-02-13',
    tag: 'latest',
    changes: [
      {
        type: 'improved',
        items: [
          'SardisClient convenience wrapper added to reduce SDK onboarding friction',
          'Landing/docs claims synchronized around package count (19), chain count (5), and MCP tool count (46)',
          'README and launch materials updated with validated link/badge checks',
          'Landing production deployment completed and aliased to www.sardis.sh',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Python SDK version constant aligned with package metadata (0.3.3 parity)',
          'Release-readiness script now degrades gracefully when optional design-partner checklist file is absent',
          'Launch documentation now records URL/badge validation outcomes and npm curl 403 caveat',
        ]
      },
    ]
  },
  {
    version: '0.8.5',
    date: '2026-02-11',
    tag: '',
    changes: [
      {
        type: 'security',
        items: [
          'Travel Rule (FATF R.16) compliance module for cross-border transfers exceeding $3,000',
          'Lithic ASA real-time authorization handler with MCC blocking and velocity checks',
          'Expanded high-risk MCC blocklist: gambling (7800-7802), cash advances (6010-6011), stored value (6540), wire transfers (4829), escorts (7273)',
          'Replaced placeholder country list with 16 real OFAC/FATF high-risk country codes (KP, IR, SY, CU, etc.)',
          'Expanded disposable email domain detection from 6 to 40 providers',
          'Co-sign threshold limits added to SardisAgentWallet.sol smart contract',
          'Factory owner secured with OpenZeppelin TimelockController (48-hour delay)',
          'Gas fee now included in policy evaluation (total cost = amount + estimated gas)',
          'Velocity checks at policy layer: per-transaction, daily, weekly, and monthly limits',
        ]
      },
      {
        type: 'added',
        items: [
          'PostgreSQL persistence for spending policy state (replaces in-memory)',
          'PostgreSQL persistence for SAR storage, identity registry, and ledger engine',
          'Redis-backed velocity monitoring with atomic increment/check operations',
          'KYB (Know Your Business) verification via Persona for organizational onboarding',
          'Centralized price oracle for gas cost estimation across all supported chains',
          'Per-organization rate limiting with configurable tier overrides',
          'Async PostgreSQL support for ledger receipts and reconciliation',
        ]
      },
      {
        type: 'improved',
        items: [
          'Refactored API main.py into focused modules (1392 to 683 lines: lifespan, health, OpenAPI, card adapter)',
          'Consolidated duplicate Turnkey MPC clients into single canonical client with correct P-256 stamp format',
          'Resolved dual-SDK confusion with unified sardis package as single entry point',
        ]
      },
    ]
  },
  {
    version: '0.8.4',
    date: '2026-02-08',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Published all 15 Python packages to PyPI (sardis meta-package + sardis-sdk, sardis-core, sardis-protocol, sardis-chain, sardis-ledger, sardis-compliance, sardis-api, sardis-wallet, sardis-cards, sardis-cli, sardis-checkout, sardis-ramp, sardis-ucp, sardis-a2a)',
          'Published all 4 npm packages (@sardis/sdk, @sardis/mcp-server, @sardis/ai-sdk, @sardis/ramp)',
          'SDK installation section on landing page with early access messaging and package links',
          'Vercel SPA routing fix for /docs and all sub-routes',
          'Human-in-the-Loop approval queue — payments above policy threshold pause for human sign-off before execution',
          'Goal drift detection — intent scope vs. payment destination mismatch blocking with configurable drift score threshold',
          'Public staging API deployed to GCP Cloud Run with Neon Postgres + Upstash Redis',
          'Admin dashboard deployed to Vercel at app.sardis.sh with live API integration',
          'API key bootstrap script for staging environments',
        ]
      },
      {
        type: 'security',
        items: [
          'Comprehensive security audit: 54 fixes across 8 batches covering auth, crypto, input validation, SQL injection, rate limiting, CORS, webhook signatures, AI prompt injection, and JWT',
          'JWT authentication migrated from custom HMAC to PyJWT with proper claim validation',
          'Identity registry now fail-closed in production and staging environments',
          'Anonymous access restricted to loopback addresses only',
        ]
      },
      {
        type: 'improved',
        items: [
          'TypeScript strict mode fixes for MCP server rate limiter and onramper quote sorting',
          '.gitignore updated to exclude Foundry build artifacts (contracts/out/, contracts/cache/)',
          'All 649 Python tests and 91 Solidity tests passing after security hardening',
        ]
      },
    ]
  },
  {
    version: '0.8.3',
    date: '2026-02-08',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Cloud Run staging deployment automation script with health checks and post-deploy bootstrap instructions',
          'AWS App Runner staging deployment automation script (ECR build/push + service create/update)',
          'Unified deployment env templates for GCP and AWS staging',
          'Cloud deployment + frontend integration runbook for /demo live mode',
        ]
      },
      {
        type: 'improved',
        items: [
          'Demo live-mode auth UX now shows explicit server-side password setup guidance',
          'Demo transaction history now persists across browser refreshes (local storage)',
          'Deployment docs now map directly to repo scripts and required env vars',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Landing-local Vercel config simplified to avoid route/header config conflicts in local `vercel dev` sessions',
          'Roadmap/docs alignment updated with current staging hardening milestones',
        ]
      },
    ]
  },
  {
    version: '0.8.2',
    date: '2026-02-06',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'JS bootstrap preflight script (`bootstrap:js`) with DNS/registry checks before install',
          'Optional live-chain conformance gate (`check:live-chain`) for Turnkey + testnet verification',
          'Release scripts for strict/degraded readiness flows in constrained local environments',
        ]
      },
      {
        type: 'improved',
        items: [
          'Protocol conformance lane now isolates root and UCP package scopes to avoid pytest import collisions',
          'Conformance report generator now supports fallback parsing when pytest JSON plugin is unavailable',
          'Start-to-end release runbook updated for reproducible MCP + SDK validation workflow',
        ]
      },
      {
        type: 'fixed',
        items: [
          'False skip/noise in protocol conformance by excluding integration/e2e test trees from the conformance marker lane',
          'Fragile pass/fail parsing in Python readiness script replaced with summary-based extraction',
        ]
      },
    ]
  },
  {
    version: '0.8.1',
    date: '2026-02-06',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Protocol source map with canonical AP2/TAP/UCP/x402 references and test mappings',
          'AP2 PaymentMandate visibility signals: ai_agent_presence and transaction_modality',
          'TAP linked-object signature-base helper for agenticConsumer and agenticPaymentContainer',
          'New negative tests for TAP algorithm validation and linked-object signature checks',
        ]
      },
      {
        type: 'improved',
        items: [
          'AP2 verifier now enforces explicit agent-presence and modality semantics',
          'TAP header validation now enforces message signature algorithm allowlist',
          'Start-to-end engineering flow documentation now includes protocol source governance',
        ]
      },
      {
        type: 'security',
        items: [
          'Fail-closed behavior for invalid TAP algorithms in headers and signed objects',
          'Stronger protocol-level guardrails before payment execution',
        ]
      },
    ]
  },
  {
    version: '0.8.0',
    date: '2026-02-03',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Human Approval Workflows - Full create/approve/deny/expire/cancel lifecycle',
          'ApprovalRepository with PostgreSQL persistence',
          'ApprovalService with business logic and webhook notifications',
          'Approvals API router with REST endpoints (/api/v2/approvals)',
          'Background Job Scheduler - APScheduler integration with FastAPI lifespan',
          'Scheduled jobs: approval expiration, hold cleanup, spending limit reset',
          'Alembic database migration framework with 6 versioned migrations',
          'Wallet freeze/unfreeze capability with transaction blocking',
          'Velocity limit checks for off-ramp (daily/weekly/monthly)',
          'MCC (Merchant Category Code) lookup service',
          'EIP-2771 meta-transaction support for gasless transactions',
          'Batch transfer API endpoint',
          'SAR (Suspicious Activity Report) generation',
        ]
      },
      {
        type: 'improved',
        items: [
          'Prometheus metrics endpoint for monitoring',
          'Sentry integration for error tracking',
          'Structured logging with correlation IDs',
          'CI/CD deployment workflow with staging/production gates',
          'GitHub Actions: mypy type checking, 70% coverage enforcement',
          'Dependabot configuration for automated security updates',
        ]
      },
      {
        type: 'fixed',
        items: [
          'npm audit vulnerabilities across all packages',
          'Updated hono to latest secure version',
          'Updated esbuild to fix CVE vulnerabilities',
          'SDK tests updated for new RetryConfig API',
          'Deprecated regex parameter replaced with pattern in routers',
        ]
      },
      {
        type: 'security',
        items: [
          'HMAC webhook verification for card routes',
          'Feature flags for card API routes',
          'Health monitoring workflow for E2E card lifecycle',
        ]
      },
    ]
  },
  {
    version: '0.7.0',
    date: '2026-02-02',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Invoices API - Full CRUD endpoints for merchant invoice management',
          'Fireblocks MPC signer - Institutional-grade vault account creation and transaction signing',
          'PostgreSQL-backed mandate store - Mandates now persist across restarts',
          'PostgreSQL-backed checkout sessions - Checkout state no longer in-memory',
          'PostgreSQL-backed KYC verification storage with DB lookup fallback',
          'ABI revert reason decoding - Human-readable Solidity error messages',
          'Dashboard invoices page wired to real API (replaces mock data)',
        ]
      },
      {
        type: 'improved',
        items: [
          'Auth context wired into all API routes (agents, webhooks, marketplace)',
          'Webhook secret rotation now persisted to database',
          'sardis-ai-sdk resolved as pnpm workspace dependency',
          'ChainId, TokenConfig, GasConfig exports fixed in sardis-chain',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Critical NameError: turnkey_client referenced before assignment in main.py',
          'Database schema idempotency: consolidated ALTER TABLE into CREATE TABLE',
          'Hardcoded secret removed from .env.example',
          'Solidity contract file permissions (600 → 644)',
          'Python 3.13 compatibility: pinned asyncpg>=0.30 and fastapi>=0.115',
        ]
      },
      {
        type: 'security',
        items: [
          'API routes now enforce authentication via require_api_key dependency',
          'Marketplace endpoints require X-Agent-Id header instead of hardcoded demo values',
        ]
      },
    ]
  },
  {
    version: '0.6.0',
    date: '2026-01-27',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Fiat Rails - Bank on-ramp and off-ramp support via Bridge and Onramper',
          'Virtual Cards - Lithic integration for instant card issuance',
          'Unified Balance - USDC/USD treated as 1:1 equivalent',
          'KYC/AML Integration - Persona verification and Elliptic sanctions screening',
          'sardis-ramp-js package for JavaScript/TypeScript fiat operations',
          'sardis-cards package for virtual card management',
          '8 new MCP fiat tools (sardis_fund_wallet, sardis_withdraw_to_bank, etc.)',
          'Bank account linking and verification',
        ]
      },
      {
        type: 'improved',
        items: [
          'MCP Server expanded to 40+ tools with fiat and card support',
          'TypeScript SDK v0.2.0 with fiat.fund(), fiat.withdraw(), cards.create()',
          'Python SDK with full fiat rails and unified balance support',
          'Policy Engine now validates across crypto, fiat, and card transactions',
          'Documentation updated with fiat rails guides',
        ]
      },
      {
        type: 'fixed',
        items: [
          'Wallet balance now shows unified USDC + USD total',
          'Rate limiter now tracks spend across all payment rails',
          'KYC status properly cached to reduce API calls',
        ]
      },
    ]
  },
  {
    version: '0.5.0',
    date: '2026-01-24',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'UCP (Universal Commerce Protocol) - Standardized checkout flows for AI agents',
          'A2A (Agent-to-Agent) protocol - Multi-agent communication and discovery',
          'sardis-ucp package with checkout, order, and fulfillment capabilities',
          'sardis-a2a package with agent cards and message handling',
          'MCP Server expanded from 4 to 36+ tools',
          'AP2 mandate adapter for UCP-AP2 interoperability',
          'Agent discovery service with TTL caching',
          'TAP (Trust Anchor Protocol) identity verification',
        ]
      },
      {
        type: 'improved',
        items: [
          'TypeScript SDK now includes UCP, A2A, and Agents resources',
          'Python SDK with full UCP and A2A support',
          'MCP Server modularized into tool categories',
          'Policy engine with natural language support',
          'Documentation updated with protocol guides',
        ]
      },
      {
        type: 'fixed',
        items: [
          'SDK method naming standardized (get() instead of getById())',
          'MCP policy configuration now uses environment variables',
          'Rate limiter persistence with Redis support',
        ]
      },
    ]
  },
  {
    version: '0.4.0',
    date: '2026-01-23',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Demo agent showcasing policy-enforced autonomous payments',
          'Real on-chain ERC20 balance queries in wallet API',
          'pnpm workspace configuration for monorepo',
          'Database health check in API server',
        ]
      },
      {
        type: 'fixed',
        items: [
          'TypeScript SDK build error from duplicate exports in openai.ts',
          'MCP Server wallet endpoints now use correct /api/v2 prefix',
          'Python SDK Wallet model alias mismatch with API',
          'Demo agent now uses correct wallet creation API',
        ]
      },
      {
        type: 'improved',
        items: [
          'Wallet balance endpoint now queries real chain via ChainExecutor',
          'MCP Server no longer requires unused SDK dependency',
          'API health endpoint returns proper component status',
        ]
      },
    ]
  },
  {
    version: '0.3.0',
    date: '2026-01-20',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Real API integration in MCP server (no more mock data)',
          'LangChain.js integration for TypeScript SDK',
          'OpenAI function calling integration for both SDKs',
          'Environment variable configuration for MCP server',
          'Comprehensive FAQ, Blog, and Changelog documentation pages',
        ]
      },
      {
        type: 'improved',
        items: [
          'Vercel AI SDK integration with proper mandate signing',
          'Python SDK LangChain tool with async execution',
          'LlamaIndex integration with full payment flow',
          'Error handling with policy violation detection',
        ]
      },
      {
        type: 'fixed',
        items: [
          'MCP server now connects to real Sardis API',
          'Python SDK properly handles async event loops',
          'TypeScript SDK exports all integration modules',
        ]
      },
    ]
  },
  {
    version: '0.2.0',
    date: '2026-01-02',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Python SDK with LangChain and LlamaIndex integrations',
          'TypeScript SDK with Vercel AI integration',
          'MCP server for Claude Desktop integration',
          'Policy engine with vendor allowlists',
          'Spending limits (per-transaction and daily)',
        ]
      },
      {
        type: 'improved',
        items: [
          'Documentation with Lydian Protocol design system',
          'API response types for better TypeScript support',
        ]
      },
    ]
  },
  {
    version: '0.1.0',
    date: '2025-12-15',
    tag: '',
    changes: [
      {
        type: 'added',
        items: [
          'Initial release of Sardis SDK',
          'MPC wallet integration via Turnkey',
          'Basic mandate execution pipeline',
          'USDC support on Base Sepolia testnet',
          'Ledger with Merkle tree audit anchoring',
          'Health and status endpoints',
        ]
      },
    ]
  },
];

const changeTypeConfig = {
  added: {
    label: 'Added',
    color: 'bg-emerald-500/10 border-emerald-500/30 text-emerald-500',
    icon: '+',
  },
  improved: {
    label: 'Improved',
    color: 'bg-blue-500/10 border-blue-500/30 text-blue-500',
    icon: '^',
  },
  fixed: {
    label: 'Fixed',
    color: 'bg-amber-500/10 border-amber-500/30 text-amber-500',
    icon: '*',
  },
  deprecated: {
    label: 'Deprecated',
    color: 'bg-red-500/10 border-red-500/30 text-red-500',
    icon: '-',
  },
  security: {
    label: 'Security',
    color: 'bg-purple-500/10 border-purple-500/30 text-purple-500',
    icon: '!',
  },
};

function ReleaseSection({ release }) {
  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'long',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <section className="relative pl-8 pb-14 border-l border-border last:pb-0">
      {/* Timeline dot */}
      <div className={cn(
        "absolute -left-2 w-4 h-4 rounded-full border-2 border-border bg-background",
        release.tag === 'latest' && "border-[var(--sardis-orange)] bg-[var(--sardis-orange)]"
      )} />

      {/* Version header */}
      <div className="mb-5">
        <div className="flex items-center gap-3 mb-2">
          <h3 className="text-xl font-bold font-display">v{release.version}</h3>
          {release.tag && (
            <span className="px-2 py-0.5 text-xs font-mono bg-[var(--sardis-orange)] text-white rounded">
              {release.tag.toUpperCase()}
            </span>
          )}
        </div>
        <p className="text-sm text-muted-foreground font-mono">
          {formatDate(release.date)}
        </p>
      </div>

      {/* Changes */}
      <div className="space-y-5">
        {release.changes.map((group, idx) => {
          const config = changeTypeConfig[group.type];
          return (
            <div key={idx}>
              <div className="flex items-center gap-2 mb-3">
                <span className={`px-2 py-0.5 text-xs font-mono border rounded ${config.color}`}>
                  {config.icon} {config.label.toUpperCase()}
                </span>
              </div>
              <ul className="space-y-2">
                {group.items.map((item, itemIdx) => (
                  <li key={itemIdx} className="text-sm text-muted-foreground flex items-start gap-2 leading-relaxed">
                    <span className="text-[var(--sardis-orange)] mt-1">-</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default function DocsChangelog() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-10">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
            CHANGELOG
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Changelog</h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Release history and version updates for Sardis SDK and API.
        </p>
      </div>

      {/* Version format guide */}
      <div className="not-prose mb-10 p-5 rounded-lg bg-card/50 shadow-sm">
        <p className="text-sm text-muted-foreground font-mono">
          Version format: <span className="text-foreground">MAJOR.MINOR.PATCH</span>
        </p>
        <p className="text-xs text-muted-foreground mt-2 leading-relaxed">
          We follow semantic versioning. Breaking changes increment MAJOR,
          new features increment MINOR, and bug fixes increment PATCH.
        </p>
      </div>

      {/* Releases timeline */}
      <div className="not-prose">
        {releases.map((release, idx) => (
          <ReleaseSection key={idx} release={release} />
        ))}
      </div>

      {/* Subscribe section */}
      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mt-12">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Stay Updated</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Follow our GitHub releases for the latest updates.
        </p>
        <a
          href="https://github.com/EfeDurmaz16/sardis/releases"
          className="inline-flex items-center gap-2 px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
        >
          View on GitHub
        </a>
      </section>
    </article>
  );
}
