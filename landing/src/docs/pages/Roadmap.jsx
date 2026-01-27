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
    <div className="relative pl-8 pb-12 last:pb-0">
      {/* Timeline line */}
      <div className="absolute left-[11px] top-3 bottom-0 w-0.5 bg-border last:hidden" />

      {/* Timeline dot */}
      <div className={`absolute left-0 top-1.5 w-6 h-6 rounded-full ${statusColors[status]} flex items-center justify-center`}>
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
      <div className="bg-card border border-border p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <span className="text-xs font-mono text-muted-foreground">{version}</span>
            <h3 className="text-xl font-semibold" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
              {title}
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 text-xs font-medium text-white ${statusColors[status]}`}>
              {statusLabels[status]}
            </span>
            <span className="text-xs text-muted-foreground">{date}</span>
          </div>
        </div>

        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
              <span className={`mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0 ${
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

const Roadmap = () => {
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
      status: 'current',
      date: 'Jan 2026',
      items: [
        { text: 'Fiat on-ramp via Onramper', done: true },
        { text: 'Fiat off-ramp via Bridge', done: true },
        { text: 'Virtual card issuance (Lithic)', done: true },
        { text: 'Unified USDC/USD balance (1:1)', done: true },
        { text: 'KYC integration (Persona)', done: true },
        { text: 'AML screening (Elliptic)', done: true },
        { text: 'Smart contract audit', done: false },
        { text: 'Base mainnet deployment', done: false },
      ],
    },
    {
      version: 'v0.7.0',
      title: 'Production Hardening',
      status: 'upcoming',
      date: 'Q1 2026',
      items: [
        { text: 'SOC 2 Type II certification', done: false },
        { text: 'Multi-chain mainnet deployment', done: false },
        { text: 'Enhanced rate limiting', done: false },
        { text: 'Webhook reliability improvements', done: false },
        { text: 'Dashboard analytics', done: false },
      ],
    },
    {
      version: 'v0.8.0',
      title: 'Enterprise Features',
      status: 'planned',
      date: 'Q2 2026',
      items: [
        { text: 'Multi-tenant organization support', done: false },
        { text: 'Custom policy templates', done: false },
        { text: 'Advanced analytics dashboard', done: false },
        { text: 'Webhook management UI', done: false },
        { text: 'Enterprise SLA & support', done: false },
        { text: 'Recurring payments', done: false },
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
      <h1 className="text-3xl font-bold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
        Roadmap
      </h1>
      <p className="text-muted-foreground mb-8">
        Our development journey and planned features. This roadmap is subject to change based on
        community feedback and market conditions.
      </p>

      {/* Progress Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-12">
        {[
          { label: 'Completed', count: 2, color: 'bg-emerald-500' },
          { label: 'In Progress', count: 1, color: 'bg-[var(--sardis-orange)]' },
          { label: 'Upcoming', count: 1, color: 'bg-blue-500' },
          { label: 'Planned', count: 2, color: 'bg-slate-400' },
        ].map((stat, i) => (
          <div key={i} className="bg-card border border-border p-4 text-center">
            <div className={`w-3 h-3 ${stat.color} mx-auto mb-2`} />
            <div className="text-2xl font-bold">{stat.count}</div>
            <div className="text-xs text-muted-foreground">{stat.label}</div>
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
      <div className="mt-12 bg-card border border-border p-6">
        <h2 className="text-xl font-semibold mb-4" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
          Request a Feature
        </h2>
        <p className="text-muted-foreground mb-4">
          Have a feature in mind? We'd love to hear from you. Submit feature requests on GitHub
          or reach out directly.
        </p>
        <div className="flex flex-wrap gap-3">
          <a
            href="https://github.com/EfeDurmaz16/sardis/issues/new?template=feature_request.md"
            target="_blank"
            rel="noopener noreferrer"
            className="px-4 py-2 bg-[var(--sardis-orange)] text-white text-sm font-medium hover:bg-[var(--sardis-orange)]/90 transition-colors"
          >
            Submit on GitHub
          </a>
          <a
            href="mailto:dev@sardis.sh"
            className="px-4 py-2 border border-border text-foreground text-sm font-medium hover:border-[var(--sardis-orange)] transition-colors"
          >
            Email Us
          </a>
        </div>
      </div>
    </div>
  );
};

export default Roadmap;
