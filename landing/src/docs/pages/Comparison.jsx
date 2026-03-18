import { Link } from 'react-router-dom';
import SEO, { createBreadcrumbSchema } from '@/components/SEO';

/* ── Feature matrix: Sardis vs named competitors ── */
const competitors = [
  { key: 'sardis', name: 'Sardis', accent: true },
  { key: 'stripe', name: 'Stripe' },
  { key: 'circle', name: 'Circle' },
  { key: 'fireblocks', name: 'Fireblocks' },
  { key: 'skyfire', name: 'Skyfire' },
  { key: 'paymanai', name: 'Payman AI' },
  { key: 'coinbase', name: 'Coinbase' },
];

const featureMatrix = [
  {
    category: 'Agent-Specific Infrastructure',
    features: [
      {
        name: 'Built for AI agents',
        sardis: 'Core mission',
        stripe: 'No — human-first',
        circle: 'No — infra layer',
        fireblocks: 'No — institutional',
        skyfire: 'Yes',
        paymanai: 'Yes',
        coinbase: 'No — consumer/dev',
      },
      {
        name: 'Natural language spending policies',
        sardis: 'Yes — 12-check pipeline',
        stripe: 'No',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'Limited',
        paymanai: 'Limited',
        coinbase: 'No',
      },
      {
        name: 'Agent identity (KYA)',
        sardis: 'Yes — Know Your Agent',
        stripe: 'No',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'No',
      },
      {
        name: 'Kill switch (5 scopes)',
        sardis: 'Yes — agent/wallet/rail/chain/global',
        stripe: 'Card-level only',
        circle: 'No',
        fireblocks: 'Vault-level',
        skyfire: 'Basic',
        paymanai: 'Basic',
        coinbase: 'Account-level',
      },
      {
        name: 'Anomaly detection',
        sardis: '6-signal risk scoring',
        stripe: 'Radar (card fraud)',
        circle: 'No',
        fireblocks: 'Transaction screening',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'Account-level',
      },
    ],
  },
  {
    category: 'Payment Rails',
    features: [
      {
        name: 'Stablecoin payments (USDC)',
        sardis: 'Yes — 0% merchant fee',
        stripe: 'No native support',
        circle: 'Yes — core product',
        fireblocks: 'Yes — OTC/institutional',
        skyfire: 'Yes',
        paymanai: 'Limited',
        coinbase: 'Yes — Coinbase Commerce',
      },
      {
        name: 'Virtual card issuance',
        sardis: 'Yes — Stripe Issuing',
        stripe: 'Yes — Stripe Issuing',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'Coinbase Card (consumer)',
      },
      {
        name: 'Fiat on/off-ramp',
        sardis: 'Coinbase Onramp + Bridge',
        stripe: 'Full fiat stack',
        circle: 'Circle Mint (institutional)',
        fireblocks: 'Partner integrations',
        skyfire: 'Limited',
        paymanai: 'No',
        coinbase: 'Yes — full consumer',
      },
      {
        name: 'Multi-chain support',
        sardis: '6 chains + CCTP v2',
        stripe: 'N/A — fiat only',
        circle: 'Yes — many chains',
        fireblocks: '50+ chains',
        skyfire: 'Limited',
        paymanai: 'Limited',
        coinbase: 'Base + Ethereum',
      },
      {
        name: 'Agent-to-agent payments',
        sardis: 'Yes — A2A protocol',
        stripe: 'No',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'Yes',
        paymanai: 'Partial',
        coinbase: 'No',
      },
    ],
  },
  {
    category: 'Wallet Infrastructure',
    features: [
      {
        name: 'Non-custodial wallets',
        sardis: 'Yes — MPC via Turnkey',
        stripe: 'N/A — not a wallet',
        circle: 'Programmable Wallets',
        fireblocks: 'Yes — MPC (TSS)',
        skyfire: 'Custodial',
        paymanai: 'Custodial',
        coinbase: 'Both (custodial + MPC)',
      },
      {
        name: 'Smart accounts (ERC-4337)',
        sardis: 'Yes — Safe v1.4.1',
        stripe: 'No',
        circle: 'Yes',
        fireblocks: 'Yes',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'Yes — Smart Wallet',
      },
      {
        name: 'Gasless transactions',
        sardis: 'Yes — Circle Paymaster',
        stripe: 'N/A',
        circle: 'Yes — Paymaster',
        fireblocks: 'Yes — Gas Station',
        skyfire: 'Unknown',
        paymanai: 'No',
        coinbase: 'Yes — Paymaster',
      },
    ],
  },
  {
    category: 'Policy & Governance',
    features: [
      {
        name: 'Spending limits (per-tx/day/week/month)',
        sardis: 'Yes — all time windows',
        stripe: 'Card-level limits',
        circle: 'No built-in',
        fireblocks: 'Transaction policies',
        skyfire: 'Basic limits',
        paymanai: 'Basic limits',
        coinbase: 'Account limits',
      },
      {
        name: 'Merchant category restrictions',
        sardis: 'Yes — MCC-based',
        stripe: 'Issuing only',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'No',
      },
      {
        name: 'Time-based spending controls',
        sardis: 'Yes — business hours, blackout dates',
        stripe: 'No',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'No',
      },
      {
        name: 'Approval workflows (4-eyes)',
        sardis: 'Yes — quorum + Slack',
        stripe: 'No',
        circle: 'No',
        fireblocks: 'Yes — governance policies',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'No',
      },
      {
        name: 'Policy Firewall (fail-closed)',
        sardis: 'Yes — deterministic',
        stripe: 'No',
        circle: 'No',
        fireblocks: 'Partial — policy engine',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'No',
      },
    ],
  },
  {
    category: 'Compliance & Audit',
    features: [
      {
        name: 'Cryptographic audit trail',
        sardis: 'Yes — signed attestations + Merkle',
        stripe: 'Payment logs',
        circle: 'Transaction logs',
        fireblocks: 'Audit logs',
        skyfire: 'Basic logs',
        paymanai: 'Basic logs',
        coinbase: 'Transaction history',
      },
      {
        name: 'KYC / KYB',
        sardis: 'iDenfy integration',
        stripe: 'Stripe Identity',
        circle: 'Enterprise KYC',
        fireblocks: 'Enterprise KYC',
        skyfire: 'Unknown',
        paymanai: 'Unknown',
        coinbase: 'Full KYC stack',
      },
      {
        name: 'Sanctions screening',
        sardis: 'OFAC + OpenSanctions + Chainalysis',
        stripe: 'Built-in',
        circle: 'Built-in',
        fireblocks: 'Chainalysis + Elliptic',
        skyfire: 'Unknown',
        paymanai: 'Unknown',
        coinbase: 'Built-in',
      },
      {
        name: 'Travel Rule compliance',
        sardis: 'Yes — Notabene',
        stripe: 'N/A — fiat',
        circle: 'Yes',
        fireblocks: 'Yes — Notabene/CipherTrace',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'Yes',
      },
    ],
  },
  {
    category: 'Developer Experience',
    features: [
      {
        name: 'Python SDK',
        sardis: 'Yes — pip install sardis',
        stripe: 'Yes',
        circle: 'Yes',
        fireblocks: 'Yes',
        skyfire: 'Yes',
        paymanai: 'Yes',
        coinbase: 'Yes',
      },
      {
        name: 'TypeScript SDK',
        sardis: 'Yes — @sardis/sdk',
        stripe: 'Yes',
        circle: 'Yes',
        fireblocks: 'Yes',
        skyfire: 'Limited',
        paymanai: 'Limited',
        coinbase: 'Yes',
      },
      {
        name: 'MCP server for Claude',
        sardis: '52 tools',
        stripe: 'Community — limited',
        circle: 'No',
        fireblocks: 'No',
        skyfire: 'No',
        paymanai: 'No',
        coinbase: 'Community — limited',
      },
      {
        name: 'Protocol support',
        sardis: 'AP2 + TAP + UCP + A2A + x402 + ACP',
        stripe: 'Proprietary',
        circle: 'CCTP',
        fireblocks: 'Proprietary',
        skyfire: 'x402',
        paymanai: 'Proprietary',
        coinbase: 'x402 + Base',
      },
      {
        name: 'Open source',
        sardis: 'BSL — source available',
        stripe: 'SDKs only',
        circle: 'SDKs only',
        fireblocks: 'No',
        skyfire: 'Partial',
        paymanai: 'No',
        coinbase: 'Partial',
      },
    ],
  },
  {
    category: 'Business Model',
    features: [
      {
        name: 'Merchant checkout fee',
        sardis: '0% on USDC',
        stripe: '2.9% + 30¢',
        circle: 'Varies',
        fireblocks: 'Enterprise pricing',
        skyfire: 'Unknown',
        paymanai: 'Unknown',
        coinbase: '1% Commerce',
      },
      {
        name: 'Target customer',
        sardis: 'Dev teams building AI agents',
        stripe: 'Any business (human payments)',
        circle: 'Enterprises, fintechs',
        fireblocks: 'Institutions ($10M+)',
        skyfire: 'AI agent developers',
        paymanai: 'AI agent developers',
        coinbase: 'Consumer + developers',
      },
      {
        name: 'Minimum to start',
        sardis: 'Free — pip install sardis',
        stripe: 'Free tier',
        circle: 'Enterprise contact',
        fireblocks: '$100K+ ACV',
        skyfire: 'Waitlist',
        paymanai: 'Waitlist',
        coinbase: 'Free tier',
      },
    ],
  },
];

function CellValue({ value, isAccent }) {
  if (!value) return <span className="text-muted-foreground/40">—</span>;
  const isPositive = value.startsWith('Yes') || value === 'Core mission' || value === '52 tools' || value === '0% on USDC' || value === 'Free — pip install sardis';
  const isNegative = value.startsWith('No');
  const isPartial = value.startsWith('Limited') || value.startsWith('Partial') || value.startsWith('Basic') || value === 'Unknown' || value.startsWith('Card-level') || value.startsWith('Account');

  if (isAccent && isPositive) return <span className="text-emerald-500 text-xs font-medium">{value}</span>;
  if (isNegative) return <span className="text-red-400/70 text-xs">{value}</span>;
  if (isPartial) return <span className="text-yellow-500/80 text-xs">{value}</span>;
  if (isAccent) return <span className="text-emerald-400 text-xs font-medium">{value}</span>;
  return <span className="text-muted-foreground text-xs">{value}</span>;
}

/* ── Individual competitor deep-dives ── */
const deepDives = [
  {
    name: 'Stripe',
    tagline: 'The incumbent payment processor',
    color: 'purple',
    whyNot: [
      'Stripe is designed for human-initiated payments. Their entire API assumes a user is clicking "Pay" in a browser. AI agents don\'t have browsers.',
      'Stripe Issuing can issue virtual cards, but the policy controls are basic — card-level limits only. No merchant category restrictions, no time-based controls, no natural language policies.',
      'No protocol support for agent-to-agent payments (AP2, A2A, x402). No MPC wallets. No agent identity.',
      'Stripe\'s fraud detection (Radar) is trained on human spending patterns. Agent spending looks completely different — high-frequency, programmatic, narrow merchant set.',
    ],
    whenToUse: 'Use Stripe when your business needs traditional human payment processing (subscriptions, invoices, POS). Use Sardis when your AI agent needs to make payments autonomously with policy guardrails.',
    sardisAdvantage: 'Sardis actually uses Stripe Issuing under the hood for virtual cards — but wraps it with agent-specific policy enforcement, spending mandates, and cryptographic audit trails that Stripe alone cannot provide.',
  },
  {
    name: 'Circle',
    tagline: 'USDC infrastructure provider',
    color: 'blue',
    whyNot: [
      'Circle is an infrastructure layer — they issue USDC and provide Programmable Wallets. But they don\'t provide agent-specific spending controls, policy engines, or approval workflows.',
      'Circle Programmable Wallets are powerful but general-purpose. No natural language policies, no kill switch with multiple scopes, no anomaly detection tuned for agent behavior.',
      'No agent identity (KYA), no A2A protocol support, no MCP server integration.',
      'Circle is enterprise-first with enterprise pricing. There\'s no "pip install" developer experience.',
    ],
    whenToUse: 'Use Circle when you need raw USDC infrastructure (minting, CCTP bridging, programmable wallets) for your own application. Use Sardis when you need agent-specific payment controls on top of USDC.',
    sardisAdvantage: 'Sardis uses Circle\'s CCTP v2 for cross-chain bridging and Circle Paymaster for gasless transactions. We build the agent governance layer on top of Circle\'s infrastructure.',
  },
  {
    name: 'Fireblocks',
    tagline: 'Enterprise-grade MPC wallet infrastructure',
    color: 'orange',
    whyNot: [
      'Fireblocks is built for institutional custody — hedge funds, exchanges, and enterprises with $10M+ in assets. Their minimum contract is typically $100K+ ACV.',
      'They have excellent MPC technology and transaction policies, but nothing agent-specific. No natural language policies, no agent identity, no AP2/A2A protocol support.',
      'The governance engine is powerful but designed for human approval workflows in traditional finance, not for autonomous agent decision-making.',
      'Massive overkill for a startup deploying AI agents. You don\'t need 50+ chain support and OTC desk access to let your agent pay for SaaS subscriptions.',
    ],
    whenToUse: 'Use Fireblocks when you\'re a large institution managing billions in digital assets with complex custody requirements. Use Sardis when you\'re building AI agents that need to make payments with policy guardrails.',
    sardisAdvantage: 'Sardis provides MPC wallets (via Turnkey) with agent-specific policy enforcement at a fraction of Fireblocks\' cost. We\'re purpose-built for agent payments, not institutional custody.',
  },
  {
    name: 'Skyfire',
    tagline: 'AI agent payment network',
    color: 'cyan',
    whyNot: [
      'Skyfire is a direct competitor building AI agent payments. They support x402 micropayments and agent-to-agent transactions.',
      'Key differences: Skyfire uses custodial wallets (they hold your funds). Sardis uses non-custodial MPC wallets (you hold your keys).',
      'Skyfire lacks the deep policy engine — no 12-check enforcement pipeline, no natural language policies with merchant category restrictions and time-based controls.',
      'No cryptographic audit trail with signed attestation envelopes and Merkle proofs. No approval workflows with quorum-based governance.',
      'Limited multi-chain support compared to Sardis\' 6 chains + CCTP v2 bridging.',
    ],
    whenToUse: 'Skyfire may work for simple agent micropayments. Use Sardis when you need non-custodial wallets, comprehensive policy enforcement, approval workflows, and enterprise-grade audit trails.',
    sardisAdvantage: 'Non-custodial architecture (your keys, your funds), deeper policy engine (12 checks vs basic limits), cryptographic audit trail, and broader protocol support (AP2 + TAP + UCP + A2A + x402 + ACP vs x402 only).',
  },
  {
    name: 'Payman AI',
    tagline: 'AI agent payment platform',
    color: 'pink',
    whyNot: [
      'Payman AI is another direct competitor focused on letting AI agents make payments. Similar positioning to Sardis.',
      'Key differences: Payman AI uses custodial wallet architecture. Sardis uses non-custodial MPC wallets — you never trust a third party with your funds.',
      'Payman lacks the comprehensive policy engine. No merchant category restrictions, no time-based controls, no anomaly detection with 6-signal scoring.',
      'No AP2 protocol support (the Google/PayPal/Mastercard/Visa standard). No MCP server with 52 tools for Claude.',
      'No cryptographic audit trail with Merkle tree anchoring. Basic logging only.',
    ],
    whenToUse: 'Payman AI may be simpler to get started with for basic agent payments. Use Sardis when you need non-custodial security, enterprise compliance, deep policy controls, and protocol-standard payments.',
    sardisAdvantage: 'Non-custodial MPC wallets, 12-check policy firewall, AP2 consortium protocol compliance, 52-tool MCP server, and cryptographic audit trail with Merkle proofs.',
  },
  {
    name: 'Coinbase',
    tagline: 'Consumer crypto platform with developer tools',
    color: 'blue',
    whyNot: [
      'Coinbase offers Commerce (merchant checkout), Smart Wallets, Base chain, and Onramp. Excellent infrastructure, but not designed for autonomous agent payments.',
      'No agent-specific spending policies. No natural language policy engine. No kill switch with 5 scopes.',
      'Coinbase Commerce charges 1% vs Sardis Pay\'s 0% on USDC.',
      'No AP2/TAP/UCP/A2A protocol support. No agent identity (KYA). No approval workflows.',
      'Consumer-focused UX doesn\'t translate to programmatic agent usage.',
    ],
    whenToUse: 'Use Coinbase for consumer crypto products, Base chain development, and fiat onramp. Use Sardis when your AI agents need autonomous payments with policy controls.',
    sardisAdvantage: 'Sardis uses Coinbase Onramp for fiat-to-crypto and builds on Base for execution — but adds the entire agent governance layer: policies, mandates, approvals, audit trail, and multi-framework integration.',
  },
];

export default function Comparison() {
  const schemas = [
    createBreadcrumbSchema([
      { name: 'Home', href: '/' },
      { name: 'Documentation', href: '/docs' },
      { name: 'Sardis vs Competitors', href: '/docs/comparison' },
    ]),
  ];

  return (
    <>
      <SEO
        title="Sardis vs Stripe vs Circle vs Fireblocks vs Skyfire vs Payman AI — AI Agent Payment Comparison"
        description="Detailed comparison of AI agent payment platforms: Sardis vs Stripe, Circle, Fireblocks, Skyfire, Payman AI, and Coinbase. Compare spending policies, MPC wallets, protocol support, pricing, and developer experience."
        path="/docs/comparison"
        schemas={schemas}
      />
      <article className="prose dark:prose-invert max-w-none">
        <div className="not-prose mb-10">
          <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
            <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
              COMPARISON
            </span>
            <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
              UPDATED MARCH 2026
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">
            Sardis vs Every Alternative
          </h1>
          <p className="text-xl text-muted-foreground leading-relaxed mb-2">
            An honest, detailed comparison of every way to give AI agents access to money — from traditional payment processors to direct competitors.
          </p>
          <p className="text-sm text-muted-foreground">
            Comparing: <strong>Sardis</strong> vs <strong>Stripe</strong> vs <strong>Circle</strong> vs <strong>Fireblocks</strong> vs <strong>Skyfire</strong> vs <strong>Payman AI</strong> vs <strong>Coinbase</strong>
          </p>
        </div>

        {/* TL;DR */}
        <section className="not-prose mb-12 p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
          <h2 className="text-lg font-bold font-display mb-3 text-[var(--sardis-orange)]">TL;DR — When to Use What</h2>
          <div className="space-y-2 text-sm text-muted-foreground">
            <p><strong className="text-foreground">Sardis</strong> — You're building AI agents that make real payments and need policy guardrails, non-custodial wallets, and audit trails.</p>
            <p><strong className="text-foreground">Stripe</strong> — You need traditional human payment processing (subscriptions, invoices, checkout).</p>
            <p><strong className="text-foreground">Circle</strong> — You need raw USDC infrastructure (minting, bridging, programmable wallets) without agent-specific controls.</p>
            <p><strong className="text-foreground">Fireblocks</strong> — You're an institution with $10M+ in digital assets needing enterprise custody.</p>
            <p><strong className="text-foreground">Skyfire</strong> — You need simple agent micropayments and are okay with custodial wallets.</p>
            <p><strong className="text-foreground">Payman AI</strong> — You want basic agent payments and don't need deep policy controls or non-custodial security.</p>
            <p><strong className="text-foreground">Coinbase</strong> — You need consumer crypto products, Base chain, or fiat onramp without agent-specific governance.</p>
          </div>
        </section>

        {/* Full Feature Matrix */}
        <section className="not-prose mb-16">
          <h2 className="text-2xl font-bold font-display mb-6">Complete Feature Matrix</h2>
          <p className="text-sm text-muted-foreground mb-6">Scroll horizontally on mobile to see all competitors.</p>

          {featureMatrix.map((section) => (
            <div key={section.category} className="mb-10">
              <h3 className="text-sm font-mono uppercase tracking-wider text-muted-foreground mb-3 px-2">{section.category}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse min-w-[900px]">
                  <thead>
                    <tr className="border-b border-border">
                      <th className="text-left py-2 px-3 font-mono text-xs uppercase tracking-wider text-muted-foreground w-[180px]">Feature</th>
                      {competitors.map((c) => (
                        <th key={c.key} className={`text-center py-2 px-2 font-mono text-xs uppercase tracking-wider ${c.accent ? 'text-[var(--sardis-orange)]' : 'text-muted-foreground'}`}>
                          {c.name}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {section.features.map((row, i) => (
                      <tr key={i} className="border-b border-border/30 hover:bg-card/50 transition-colors">
                        <td className="py-2.5 px-3 font-medium text-xs">{row.name}</td>
                        {competitors.map((c) => (
                          <td key={c.key} className="py-2.5 px-2 text-center">
                            <CellValue value={row[c.key]} isAccent={c.accent} />
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </section>

        {/* Deep Dives */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-8">Competitor Deep Dives</h2>

          {deepDives.map((comp) => (
            <div key={comp.name} className="mb-10 border border-border p-6">
              <div className="flex items-center gap-3 mb-4">
                <h3 className="text-xl font-bold font-display">Sardis vs {comp.name}</h3>
                <span className="text-xs font-mono text-muted-foreground">{comp.tagline}</span>
              </div>

              <div className="mb-4">
                <h4 className="text-sm font-bold font-mono uppercase tracking-wider text-red-400 mb-2">Why {comp.name} alone isn't enough for AI agents</h4>
                <ul className="space-y-2">
                  {comp.whyNot.map((point, i) => (
                    <li key={i} className="text-sm text-muted-foreground pl-4 border-l-2 border-border">
                      {point}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="mb-4 p-3 bg-card/50 border border-border">
                <h4 className="text-sm font-bold font-mono uppercase tracking-wider text-yellow-500 mb-1">When to use {comp.name}</h4>
                <p className="text-sm text-muted-foreground">{comp.whenToUse}</p>
              </div>

              <div className="p-3 border border-emerald-500/30 bg-emerald-500/5">
                <h4 className="text-sm font-bold font-mono uppercase tracking-wider text-emerald-500 mb-1">Sardis advantage</h4>
                <p className="text-sm text-muted-foreground">{comp.sardisAdvantage}</p>
              </div>
            </div>
          ))}
        </section>

        {/* The Core Problem */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-4">The Fundamental Problem</h2>
          <p className="text-muted-foreground leading-relaxed mb-6">
            Traditional payment infrastructure was designed for humans clicking buttons. AI agents don't have browsers, don't click buttons, and don't respond to 2FA prompts. They need infrastructure built for programmatic, policy-governed, autonomous financial execution.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-red-500/30 bg-red-500/5">
              <h3 className="font-bold text-red-400 mb-2 text-sm">Human-first platforms</h3>
              <p className="text-xs text-muted-foreground">Stripe, PayPal, Square — excellent for human payments, but their APIs assume human authorization flows. No agent identity, no policy engines, no autonomous spending controls.</p>
            </div>
            <div className="p-4 border border-yellow-500/30 bg-yellow-500/5">
              <h3 className="font-bold text-yellow-400 mb-2 text-sm">Crypto infrastructure</h3>
              <p className="text-xs text-muted-foreground">Circle, Fireblocks, Coinbase — powerful wallet and chain infrastructure, but general-purpose. You'd need to build the entire agent governance layer yourself.</p>
            </div>
            <div className="p-4 border border-emerald-500/30 bg-emerald-500/5">
              <h3 className="font-bold text-emerald-400 mb-2 text-sm">Agent-native (Sardis)</h3>
              <p className="text-xs text-muted-foreground">Purpose-built for AI agents. Non-custodial wallets + 12-check policy firewall + AP2 protocol + cryptographic audit trail. The agent proposes, the infrastructure enforces.</p>
            </div>
          </div>
        </section>

        {/* Supported Frameworks */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-6">Framework Integrations</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Framework</th>
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Integration</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Claude Desktop / Cursor', 'MCP Server — 52 tools', 'Stable'],
                  ['OpenAI Agents SDK', 'Python SDK + function calling', 'Stable'],
                  ['Google ADK', 'Python SDK + tool definitions', 'Stable'],
                  ['LangChain / LlamaIndex', 'pip install sardis', 'Stable'],
                  ['Vercel AI SDK', 'npm install @sardis/ai-sdk', 'Stable'],
                  ['CrewAI', 'pip install sardis — multi-agent', 'Beta'],
                  ['AutoGPT', 'pip install sardis — block integration', 'Beta'],
                  ['Browser Use', 'pip install sardis — browser agent', 'Beta'],
                  ['Activepieces', 'Built-in piece — workflow automation', 'Live'],
                  ['n8n', 'Custom node — workflow automation', 'Planned'],
                ].map(([name, cmd, status], i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-3 px-4 font-medium">{name}</td>
                    <td className="py-3 px-4"><code className="text-xs text-[var(--sardis-orange)]">{cmd}</code></td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 text-xs font-mono ${
                        status === 'Stable' || status === 'Live' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-500' :
                        status === 'Beta' ? 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-500' :
                        'bg-muted/50 border border-border text-muted-foreground'
                      }`}>
                        {status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Multi-Chain Support */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-6">Multi-Chain Support</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Chain</th>
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Tokens</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Role</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Gasless</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Base', 'USDC, EURC', 'Execution chain', true],
                  ['Ethereum', 'USDC, USDT, PYUSD, EURC', 'Funding via CCTP v2', true],
                  ['Polygon', 'USDC, USDT, EURC', 'Funding via CCTP v2', true],
                  ['Arbitrum', 'USDC, USDT', 'Funding via CCTP v2', true],
                  ['Optimism', 'USDC, USDT', 'Funding via CCTP v2', true],
                ].map(([chain, tokens, role, gasless], i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-3 px-4 font-medium">{chain}</td>
                    <td className="py-3 px-4 text-muted-foreground">{tokens}</td>
                    <td className="py-3 px-4 text-center text-xs text-muted-foreground">{role}</td>
                    <td className="py-3 px-4 text-center">
                      {gasless ? <span className="text-emerald-500 font-bold">Yes</span> : <span className="text-red-400">No</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* CTA */}
        <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mt-12">
          <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Ready to give your agents safe access to money?</h3>
          <p className="text-muted-foreground text-sm mb-4">
            5 minutes to your first agent payment. Non-custodial. Policy-enforced. Fully audited.
          </p>
          <div className="flex flex-wrap gap-4">
            <Link
              to="/docs/quickstart"
              className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
            >
              Quick Start Guide
            </Link>
            <Link
              to="/playground"
              className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
            >
              Try the Playground
            </Link>
            <Link
              to="/docs/blog/spending-rules-explained"
              className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
            >
              How Spending Rules Work
            </Link>
          </div>
        </section>
      </article>
    </>
  );
}
