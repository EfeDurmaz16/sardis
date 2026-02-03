import { cn } from '@/lib/utils';

const releases = [
  {
    version: '0.8.0',
    date: '2026-02-03',
    tag: 'latest',
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
