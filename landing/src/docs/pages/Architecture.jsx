export default function DocsArchitecture() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            CORE CONCEPTS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Architecture</h1>
        <p className="text-xl text-muted-foreground">
          Understanding the Sardis system architecture and data flow.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> System Overview
        </h2>
        <p className="text-muted-foreground mb-6">
          Sardis acts as a financial middleware layer between AI agents and payment rails.
          Every transaction passes through the Policy Engine before reaching the settlement layer.
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-xs overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`┌─────────────────────────────────────────────────────────────────┐
│                        AI AGENT LAYER                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐               │
│  │   Claude    │ │   Cursor    │ │  LangChain  │  ...          │
│  └──────┬──────┘ └──────┬──────┘ └──────┬──────┘               │
└─────────┼───────────────┼───────────────┼───────────────────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                    ┌─────▼─────┐
                    │  MCP/SDK  │
                    └─────┬─────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│                   SARDIS POLICY ENGINE                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Natural Language Rules    Merchant Allowlist           │   │
│  │  Amount Limits             Category Restrictions        │   │
│  │  Risk Scoring              Compliance Checks            │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                    ┌─────▼─────┐
                    │    MPC    │
                    │ (Turnkey) │
                    └─────┬─────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
┌─────────▼───────┐ ┌─────▼─────┐ ┌───────▼───────┐
│   ON-CHAIN      │ │   FIAT    │ │   VIRTUAL     │
│   RAILS         │ │   RAILS   │ │   CARDS       │
│ (Base,Polygon)  │ │  (Banks)  │ │  (Lithic)     │
└─────────────────┘ └───────────┘ └───────────────┘`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Core Components
        </h2>

        <div className="not-prose grid gap-4">
          {[
            {
              name: 'Policy Engine',
              desc: 'Real-time transaction validation against defined rules. Supports natural language policy definitions, merchant allowlists, amount limits, and category restrictions.',
              color: 'orange'
            },
            {
              name: 'MPC Wallets (Turnkey)',
              desc: 'Non-custodial Multi-Party Computation wallets. Keys are split across multiple parties, ensuring no single entity can access funds.',
              color: 'emerald'
            },
            {
              name: 'MCP Server',
              desc: 'Model Context Protocol server for zero-integration setup with Claude Desktop and Cursor. Exposes sardis_pay, sardis_check_policy, and sardis_get_balance tools.',
              color: 'blue'
            },
            {
              name: 'Virtual Card Service',
              desc: 'On-demand virtual card issuance via Lithic. Cards are single-use or limited-use, locked to specific merchants and amounts.',
              color: 'purple'
            },
          ].map((comp) => (
            <div key={comp.name} className={`p-4 border border-${comp.color}-500/30 bg-${comp.color}-500/5`}>
              <h3 className={`font-bold font-display mb-2 text-${comp.color}-500`}>{comp.name}</h3>
              <p className="text-sm text-muted-foreground">{comp.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Transaction Flow
        </h2>

        <div className="not-prose space-y-4">
          {[
            { step: '1', title: 'Agent Request', desc: 'Agent calls sardis.pay() with vendor, amount, and purpose' },
            { step: '2', title: 'Policy Check', desc: 'Engine validates against rules, merchant allowlist, and limits' },
            { step: '3', title: 'Risk Scoring', desc: 'Transaction receives a risk score (0-1) based on patterns' },
            { step: '4', title: 'MPC Signing', desc: 'Approved transactions are signed via Turnkey MPC' },
            { step: '5', title: 'Settlement', desc: 'Funds settle via on-chain rails or virtual card issuance' },
            { step: '6', title: 'Response', desc: 'Agent receives confirmation with transaction ID and card details' },
          ].map((item) => (
            <div key={item.step} className="flex gap-4 items-start">
              <div className="w-8 h-8 border border-[var(--sardis-orange)] flex items-center justify-center font-mono font-bold text-[var(--sardis-orange)] shrink-0">
                {item.step}
              </div>
              <div>
                <h4 className="font-bold font-display">{item.title}</h4>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Policy Engine Rules
        </h2>
        <p className="text-muted-foreground mb-4">
          The Policy Engine supports natural language rule definitions that are compiled into executable policies.
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Example Policy Configuration
{
  "rules": [
    "Allow SaaS vendors up to $100 per transaction",
    "Allow DevTools vendors up to $50 per transaction",
    "Block all retail and gift card purchases",
    "Maximum $500 daily spend across all categories"
  ],
  "allowlist": [
    "openai.com",
    "github.com",
    "vercel.com",
    "aws.amazon.com"
  ],
  "blocklist": [
    "amazon.com",
    "ebay.com",
    "coinbase.com"
  ]
}`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Security Model</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Sardis follows a defense-in-depth security approach:
        </p>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--sardis-orange)]"></span>
            Non-custodial: Users maintain control of their keys via MPC
          </li>
          <li className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--sardis-orange)]"></span>
            Policy-first: Every transaction validated before execution
          </li>
          <li className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--sardis-orange)]"></span>
            Audit trail: Complete transaction history with cryptographic proofs
          </li>
          <li className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-[var(--sardis-orange)]"></span>
            Compliance: KYC/AML integration via Persona and Elliptic
          </li>
        </ul>
      </section>
    </article>
  );
}
