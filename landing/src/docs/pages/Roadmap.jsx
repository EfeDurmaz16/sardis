import React from 'react';

const RoadmapItem = ({ version, title, status, date, items }) => {
  const statusColors = {
    completed: 'bg-emerald-500',
    current: 'bg-[var(--sardis-orange)]',
    upcoming: 'bg-blue-500',
    planned: 'bg-slate-400',
  };

  const statusLabels = {
    completed: 'Completed',
    current: 'In Progress',
    upcoming: 'Next Up',
    planned: 'Planned',
  };

  return (
    <div className="relative pl-10 pb-14 last:pb-0">
      {/* Timeline line */}
      <div className="absolute left-[11px] top-3 bottom-0 w-0.5 bg-border last:hidden" />

      {/* Timeline dot */}
      <div className={`absolute left-0 top-1.5 w-6 h-6 rounded-full ${statusColors[status]} flex items-center justify-center shadow-sm`}>
        {status === 'completed' && (
          <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
          </svg>
        )}
        {status === 'current' && (
          <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
        )}
      </div>

      {/* Content */}
      <div className="bg-card/50 rounded-lg shadow-sm p-7">
        <div className="flex items-center justify-between mb-5">
          <div>
            <span className="text-xs font-mono text-muted-foreground">{version}</span>
            <h3 className="text-xl font-semibold" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
              {title}
            </h3>
          </div>
          <div className="flex items-center gap-3">
            <span className={`px-2.5 py-1 text-xs font-medium text-white rounded ${statusColors[status]}`}>
              {statusLabels[status]}
            </span>
            <span className="text-xs text-muted-foreground">{date}</span>
          </div>
        </div>

        <ul className="space-y-2.5">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-muted-foreground leading-relaxed">
              <span className={`mt-2 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                item.done ? 'bg-emerald-500' : 'bg-border'
              }`} />
              <span className={item.done ? 'line-through opacity-60' : ''}>{item.text}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default function Roadmap() {
  const roadmapData = [
    {
      version: 'v0.1.0 - v0.3.0',
      title: 'Foundation',
      status: 'completed',
      date: 'Dec 2025',
      items: [
        { text: 'Core payment infrastructure', done: true },
        { text: 'MPC wallet integration (Turnkey)', done: true },
        { text: 'Base chain support', done: true },
        { text: 'Basic spending policies', done: true },
        { text: 'REST API v2', done: true },
        { text: 'MCP Server (4 tools)', done: true },
      ],
    },
    {
      version: 'v0.4.0 - v0.5.0',
      title: 'Protocols & Multi-Chain',
      status: 'completed',
      date: 'Jan 2026',
      items: [
        { text: 'Polygon, Ethereum, Arbitrum, Optimism support', done: true },
        { text: 'AP2 (Agent Payment Protocol) implementation', done: true },
        { text: 'UCP (Universal Commerce Protocol)', done: true },
        { text: 'A2A (Agent-to-Agent) protocol', done: true },
        { text: 'TAP identity verification', done: true },
        { text: 'MCP Server expanded to 36+ tools', done: true },
      ],
    },
    {
      version: 'v0.6.0',
      title: 'Fiat Rails & Virtual Cards',
      status: 'completed',
      date: 'Jan 2026',
      items: [
        { text: 'Fiat on-ramp via Onramper', done: true },
        { text: 'Fiat off-ramp via Bridge (sandbox/design-partner lane)', done: true },
        { text: 'Virtual card issuance (Lithic sandbox lane)', done: true },
        { text: 'Unified balance policy model with quote-based conversion (no fixed 1:1 claim)', done: true },
        { text: 'KYC integration (Persona production onboarding)', done: false },
        { text: 'AML screening (Elliptic production onboarding)', done: false },
      ],
    },
    {
      version: 'v0.7.0',
      title: 'Database & Persistence',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'PostgreSQL-backed mandate store', done: true },
        { text: 'PostgreSQL-backed checkout sessions', done: true },
        { text: 'Fireblocks MPC signer integration', done: true },
        { text: 'Invoices API', done: true },
        { text: 'ABI revert reason decoding', done: true },
      ],
    },
    {
      version: 'v0.8.4',
      title: 'Public API & Dashboard Launch',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'All 15 Python packages published to PyPI (19 total across npm + PyPI)', done: true },
        { text: 'All 4 npm packages published (@sardis/sdk, @sardis/mcp-server, @sardis/ai-sdk, @sardis/ramp)', done: true },
        { text: 'Comprehensive security audit (54 fixes across 8 batches)', done: true },
        { text: 'JWT authentication migrated to PyJWT', done: true },
        { text: 'SDK install section added to landing page with early access messaging', done: true },
        { text: 'Human-in-the-Loop approval queue for payments above policy threshold', done: true },
        { text: 'Goal drift detection — intent vs. payment scope mismatch blocking', done: true },
        { text: 'Public staging API deployment (Cloud Run / Vercel)', done: true },
        { text: 'Dashboard UI deployment for testnet', done: true },
        { text: 'API key self-service provisioning', done: true },
        { text: 'Public API documentation (Swagger/OpenAPI)', done: true },
      ],
    },
    {
      version: 'v0.8.3',
      title: 'Demo + Deployment Readiness',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'Cloud Run staging deployment script and env templates', done: true },
        { text: 'AWS App Runner staging deployment script and env templates', done: true },
        { text: 'Demo live/private mode auth hardening', done: true },
        { text: 'Demo transaction history persistence and telemetry hooks', done: true },
        { text: 'Frontend ↔ API integration runbook for staging', done: true },
        { text: 'One-command staging bring-up for partner demos', done: true },
      ],
    },
    {
      version: 'v0.8.2',
      title: 'Release Readiness Hardening',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'Deterministic JS bootstrap preflight (`bootstrap:js`)', done: true },
        { text: 'Live-chain conformance gate (`check:live-chain`)', done: true },
        { text: 'Protocol conformance lane isolation (root + package suites)', done: true },
        { text: 'Conformance report fallback when pytest JSON plugin is unavailable', done: true },
        { text: 'Design-partner release runbook updated with strict/degraded paths', done: true },
        { text: 'MCP + TS SDK verification scripts hardened', done: true },
      ],
    },
    {
      version: 'v0.8.1',
      title: 'Protocol Conformance Hardening',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'AP2 payment modality and agent-presence signals enforced', done: true },
        { text: 'TAP algorithm allowlist for message signatures', done: true },
        { text: 'TAP linked object signature validation hooks', done: true },
        { text: 'Protocol source map for AP2/TAP/UCP/x402 added', done: true },
        { text: 'Negative protocol test coverage expanded', done: true },
        { text: 'CI conformance gate wiring for protocol suites', done: true },
      ],
    },
    {
      version: 'v0.8.0',
      title: 'Production Hardening',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'Human approval workflows (create/approve/deny/expire)', done: true },
        { text: 'Background job scheduler (APScheduler)', done: true },
        { text: 'Alembic database migrations', done: true },
        { text: 'Wallet freeze capability', done: true },
        { text: 'Velocity limit checks for off-ramp', done: true },
        { text: 'E2E tests for critical flows', done: true },
        { text: 'Prometheus metrics endpoint', done: true },
        { text: 'Sentry error tracking', done: true },
        { text: 'CI/CD deployment workflows', done: true },
        { text: 'Security audit fixes (npm/pip)', done: true },
      ],
    },
    {
      version: 'v0.8.5',
      title: 'Security & Architecture Hardening',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'Travel Rule (FATF R.16) compliance for cross-border transfers', done: true },
        { text: 'Lithic ASA real-time card authorization handler', done: true },
        { text: 'PostgreSQL persistence for spending policy, SAR, identity, and ledger', done: true },
        { text: 'Redis-backed velocity monitoring with atomic operations', done: true },
        { text: 'KYB verification via Persona for org onboarding', done: true },
        { text: 'Centralized price oracle for gas cost estimation', done: true },
        { text: 'Per-org rate limiting with tier overrides', done: true },
        { text: 'Expanded OFAC/FATF country lists, MCC blocklists, disposable email detection', done: true },
        { text: 'Smart contract hardening: co-sign limits + TimelockController', done: true },
        { text: 'API refactoring: main.py split + Turnkey client consolidation', done: true },
      ],
    },
    {
      version: 'v0.8.7',
      title: 'Smart Wallets, DB Persistence & Launch Hardening',
      status: 'completed',
      date: 'Feb 2026',
      items: [
        { text: 'ERC-4337 smart account contracts + factory + verifying paymaster (Base-first)', done: true },
        { text: 'Fail-closed UserOperation runtime path with Pimlico bundler/paymaster config gates', done: true },
        { text: 'Wallet API/SDK/MCP parity for account_type=erc4337_v2 and execution_path metadata', done: true },
        { text: 'PostgreSQL persistence for card services (conversions, mappings, offramp)', done: true },
        { text: 'PostgreSQL persistence for ledger engine (NUMERIC(38,18) precision)', done: true },
        { text: 'Alembic migration 015: card_conversions, card_wallet_mappings, offramp_transactions, ledger_entries_v2', done: true },
        { text: 'Context7 documentation: time-based policies, MCC categories, combined limits', done: true },
        { text: 'SardisClient convenience wrapper shipped for simpler SDK onboarding', done: true },
        { text: 'Onramper webhook signatures hardened with timestamp replay-window validation', done: true },
        { text: 'Landing page: gasless smart wallets section, updated competitive positioning', done: true },
        { text: 'Awesome-list submission target activity verification pass', done: false },
      ],
    },
    {
      version: 'v0.8.9',
      title: 'Fiat-First Treasury Execution',
      status: 'current',
      date: 'Feb 2026 (Now)',
      items: [
        { text: 'Treasury API endpoints added: sync accounts, link bank, verify micro-deposits, fund, withdraw, balances', done: true },
        { text: 'USD-first card funding route with stablecoin fallback feature flag', done: true },
        { text: 'Lithic ACH webhook ingestion + replay protection + return code handling state machine', done: true },
        { text: 'Treasury reconciliation + retry orchestration jobs with limits and velocity caps', done: true },
        { text: 'Python SDK and TypeScript SDK treasury resources shipped', done: true },
        { text: 'MCP treasury tools aligned to /api/v2/treasury endpoints', done: true },
        { text: 'Design partner ACH support playbook and runbook coverage', done: true },
      ],
    },
    {
      version: 'v0.9.0',
      title: 'ERC-4337 Implementation & Enterprise Features',
      status: 'upcoming',
      date: 'Q1-Q2 2026',
      items: [
        { text: 'Turnkey/Fireblocks UserOperation signing path (production signer support)', done: false },
        { text: 'Base Sepolia full E2E proof artifact with userOp hash and on-chain receipt', done: false },
        { text: 'Base mainnet ERC-4337 rollout with staged sponsor caps', done: false },
        { text: 'Stablecoin-only token allowlist smart contract', done: false },
        { text: 'Recurring payments engine (subscription registry + scheduled billing + auto-fund)', done: false },
        { text: 'Multi-tenant organization support', done: false },
        { text: 'Custom policy templates', done: false },
        { text: 'Advanced analytics dashboard', done: false },
        { text: 'Enterprise SLA & support', done: false },
      ],
    },
    {
      version: 'v1.0.0',
      title: 'General Availability',
      status: 'planned',
      date: 'Q3 2026',
      items: [
        { text: 'Full production readiness', done: false },
        { text: 'Public API stability guarantee', done: false },
        { text: 'Mobile SDK (iOS/Android)', done: false },
        { text: 'Self-service onboarding', done: false },
        { text: 'Developer portal launch', done: false },
      ],
    },
  ];

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-3" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
        Roadmap
      </h1>
      <p className="text-muted-foreground mb-10 leading-relaxed">
        Our development journey and planned features. This roadmap is subject to change based on
        community feedback and market conditions.
      </p>

      {/* Progress Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-5 mb-14">
        {[
          { label: 'Completed', count: 11, color: 'bg-emerald-500' },
          { label: 'In Progress', count: 1, color: 'bg-[var(--sardis-orange)]' },
          { label: 'Upcoming', count: 1, color: 'bg-blue-500' },
          { label: 'Planned', count: 1, color: 'bg-slate-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-card/50 rounded-lg shadow-sm p-5 text-center">
            <div className={`w-3 h-3 rounded-full ${stat.color} mx-auto mb-3`} />
            <div className="text-2xl font-bold">{stat.count}</div>
            <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Timeline */}
      <div className="relative">
        {roadmapData.map((item, i) => (
          <RoadmapItem key={i} {...item} />
        ))}
      </div>

      {/* Feature Requests */}
      <div className="mt-14 bg-card/50 rounded-lg shadow-sm p-7">
        <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
          Request a Feature
        </h2>
        <p className="text-muted-foreground mb-5 leading-relaxed">
          Have a feature in mind? We'd love to hear from you. Submit feature requests on GitHub
          or reach out directly.
        </p>
        <div className="flex flex-wrap gap-4">
          <a
            href="https://github.com/EfeDurmaz16/sardis/issues/new?template=feature_request.md"
            target="_blank"
            rel="noopener noreferrer"
            className="px-5 py-2.5 bg-[var(--sardis-orange)] text-white text-sm font-medium rounded-md hover:bg-[var(--sardis-orange)]/90 transition-colors"
          >
            Submit on GitHub
          </a>
          <a
            href="mailto:dev@sardis.sh"
            className="px-5 py-2.5 border border-border text-foreground text-sm font-medium rounded-md hover:border-[var(--sardis-orange)] transition-colors"
          >
            Email Us
          </a>
        </div>
      </div>
    </div>
  );
}
