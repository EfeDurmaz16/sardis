import { Shield, FileText, Layers, ScrollText, UserCheck, Terminal, Gauge, Activity, GitBranch } from 'lucide-react';

const cards = [
  {
    Icon: FileText,
    title: 'Natural Language Policies',
    desc: 'Define complex spending rules in plain English. "Max $200/day, only SaaS vendors, no weekend transactions." 7 built-in templates.',
    unique: true,
  },
  {
    Icon: Shield,
    title: 'Non-Custodial Security',
    desc: 'Your keys, your funds. Secured by distributed key management so no single entity — not even Sardis — can move money.',
  },
  {
    Icon: Terminal,
    title: 'Zero-Config MCP',
    desc: 'One command to add 52 payment and treasury tools to Claude or Cursor. No setup required.',
  },
  {
    Icon: Gauge,
    title: 'Confidence Routing',
    desc: 'Tiered approval workflows based on transaction confidence scores. 4-eyes quorum with distinct reviewers for high-risk mutations.',
    unique: true,
  },
  {
    Icon: Activity,
    title: 'Goal Drift Guard',
    desc: 'Chi-squared behavioral analysis detects when agents deviate from expected spending patterns. Automatic velocity governors.',
    unique: true,
  },
  {
    Icon: GitBranch,
    title: 'Merkle Audit Trail',
    desc: 'Tamper-proof audit logs anchored to Base blockchain via Merkle trees. Cryptographic proof for every transaction.',
    unique: true,
  },
  {
    Icon: Layers,
    title: 'Multi-Chain Funding',
    desc: 'Execute on Base. Fund from any chain via CCTP v2 cross-chain transfers. USDC arrives automatically.',
  },
  {
    Icon: UserCheck,
    title: 'Compliance Built In',
    desc: 'KYC verification and real-time AML screening. Every counterparty checked before funds move.',
  },
  {
    Icon: ScrollText,
    title: 'Cards + Crypto + Bank',
    desc: 'One API for every payment rail. Virtual Visa cards, stablecoin for on-chain, and fiat for traditional vendors.',
  },
];

export default function FeaturesGrid() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        {/* Header */}
        <div className="flex flex-col gap-4 mb-10">
          <span
            className="tracking-widest uppercase"
            style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: '12px', color: 'var(--landing-blue)' }}
          >
            Why Sardis
          </span>
          <h2
            className="max-w-[560px]"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 600,
              fontSize: 'clamp(30px, 4.2vw, 40px)',
              lineHeight: 'clamp(36px, 5vw, 46px)',
              color: 'var(--landing-text-primary)',
            }}
          >
            Trust without giving up control.
          </h2>
          <p
            className="max-w-[560px] font-light"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: '15px',
              lineHeight: '24px',
              color: 'var(--landing-text-tertiary)',
            }}
          >
            The only platform combining natural language policies, per-transaction risk scoring,
            drift detection, and cryptographic audit — all without holding your private keys.
          </p>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {cards.map(({ Icon, title, desc, unique }) => (
            <div
              key={title}
              className="flex flex-col gap-3.5 rounded-[14px] p-8 relative"
              style={{
                backgroundColor: 'var(--landing-surface)',
                border: unique
                  ? '1px solid rgba(59,130,246,0.2)'
                  : '1px solid var(--landing-border)',
              }}
            >
              {unique && (
                <span
                  className="absolute top-4 right-4 text-[9px] px-2 py-0.5 rounded-full font-medium tracking-wider"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    background: 'rgba(59,130,246,0.1)',
                    color: '#3B82F6',
                    border: '1px solid rgba(59,130,246,0.15)',
                  }}
                >
                  UNIQUE
                </span>
              )}
              <Icon size={24} strokeWidth={1.2} style={{ color: unique ? '#3B82F6' : 'var(--landing-text-tertiary)' }} />
              <h3
                style={{
                  fontFamily: "'Space Grotesk', sans-serif",
                  fontWeight: 600,
                  fontSize: '16px',
                  lineHeight: '22px',
                  color: 'var(--landing-text-primary)',
                }}
              >
                {title}
              </h3>
              <p
                className="font-light"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  fontSize: '14px',
                  lineHeight: '22px',
                  color: 'var(--landing-text-tertiary)',
                }}
              >
                {desc}
              </p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
