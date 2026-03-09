import { Shield, FileText, UserCheck, Power, Gauge, Activity } from 'lucide-react';

const cards = [
  {
    Icon: FileText,
    title: 'Natural Language Policies',
    desc: '12-check enforcement pipeline. "Max $500/day, block gambling, require approval above $200." Parsed, validated, and enforced on every transaction.',
    unique: true,
  },
  {
    Icon: Power,
    title: 'Kill Switch',
    desc: '5 scopes: global, organization, agent, rail, chain. Instant freeze with optional auto-reactivation. Every activation logged with evidence.',
    unique: true,
  },
  {
    Icon: UserCheck,
    title: 'Approval Workflows',
    desc: 'Confidence-based routing. Transactions above configurable thresholds route to human approval with 4-eyes quorum. Auto-approve below threshold.',
    unique: true,
  },
  {
    Icon: Shield,
    title: 'Cryptographic Evidence',
    desc: 'Signed attestation envelopes, HMAC receipts, Merkle proofs, and policy snapshots for every decision. Tamper-proof audit trail anchored to Base.',
    unique: true,
  },
  {
    Icon: Activity,
    title: 'Simulation & Replay',
    desc: 'Dry-run any payment against current policies. Replay blocked transactions with modified parameters. Batch simulate policy changes.',
    unique: true,
  },
  {
    Icon: Gauge,
    title: 'Anomaly Detection',
    desc: '6-signal risk scoring: amount anomaly, velocity, new merchant, time, category, behavioral alerts. Auto-freeze at configurable thresholds.',
    unique: true,
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
            THE CONTROL PLANE
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
            Every check. Every decision. Every proof.
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
            Natural language policies, kill switches, approval workflows,
            signed attestation envelopes, simulation, and anomaly detection — routed through a single execution gateway, without holding your private keys.
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
