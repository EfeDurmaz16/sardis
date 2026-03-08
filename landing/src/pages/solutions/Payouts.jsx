import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/jetbrains-mono/400.css';
import WaitlistModal from '../../components/WaitlistModal';
import SEO from '@/components/SEO';

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] },
};

const stagger = { animate: { transition: { staggerChildren: 0.1 } } };

function SardisWordmark() {
  return (
    <Link to="/" className="flex items-center gap-2.5" style={{ textDecoration: 'none' }}>
      <svg width="30" height="30" viewBox="0 0 28 28" fill="none">
        <path d="M20 5H10a7 7 0 000 14h2" stroke="var(--landing-text-primary)" strokeWidth="3" strokeLinecap="round" fill="none" />
        <path d="M8 23h10a7 7 0 000-14h-2" stroke="var(--landing-text-primary)" strokeWidth="3" strokeLinecap="round" fill="none" />
      </svg>
      <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.25rem', color: 'var(--landing-text-primary)' }}>
        Sardis
      </span>
    </Link>
  );
}

const features = [
  {
    tag: 'Anomaly Detection',
    title: '6-signal scoring, auto-freeze on breach',
    body: 'Every payout is scored against velocity, time-of-day, counterparty history, amount deviation, behavioral baseline, and policy compliance. A suspicious combination triggers an automatic freeze before funds leave.',
  },
  {
    tag: 'Evidence Trail',
    title: 'Prove every payout decision',
    body: 'Each approved or blocked payout generates an HMAC-signed receipt anchored to an immutable Merkle ledger. Dispute a chargeback with cryptographic proof in seconds.',
  },
  {
    tag: 'Exception Handling',
    title: 'Automatic retry and human escalation',
    body: 'Transient failures retry with exponential backoff. Persistent anomalies escalate to your ops team with full context — signal scores, transaction history, and suggested resolution.',
  },
  {
    tag: 'Kill Switch',
    title: 'Instant halt on suspicious activity',
    body: 'One API call freezes a wallet, a recipient, or your entire payout fleet. Sub-20ms propagation. No race conditions. Roll back pending batches with a single command.',
  },
];

const riskResponseFlow = [
  {
    trigger: 'Payout batch submitted',
    signals: [],
    action: 'Scoring engine evaluates all 6 signals',
    outcome: null,
    type: 'neutral',
  },
  {
    trigger: 'Score ≥ 80 — low risk',
    signals: ['normal velocity', 'known recipient', 'within policy'],
    action: 'Auto-approve, sign, settle',
    outcome: 'APPROVED',
    type: 'approved',
  },
  {
    trigger: 'Score 50–79 — medium risk',
    signals: ['first-time recipient', 'amount +3σ above baseline'],
    action: 'Queue for ops review (SLA: 4h)',
    outcome: 'PENDING',
    type: 'pending',
  },
  {
    trigger: 'Score < 50 — high risk',
    signals: ['velocity spike 4×', 'sanctioned jurisdiction match'],
    action: 'Auto-freeze + alert ops + block batch',
    outcome: 'FROZEN',
    type: 'frozen',
  },
];

const outcomeColor = {
  approved: 'var(--landing-green)',
  pending: 'var(--landing-amber)',
  frozen: 'var(--landing-red)',
  neutral: 'var(--landing-blue)',
};

const outcomeBackground = {
  approved: 'color-mix(in srgb, var(--landing-green) 10%, transparent)',
  pending: 'color-mix(in srgb, var(--landing-amber) 10%, transparent)',
  frozen: 'color-mix(in srgb, var(--landing-red) 10%, transparent)',
  neutral: 'color-mix(in srgb, var(--landing-blue) 10%, transparent)',
};

export default function Payouts() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <div style={{ backgroundColor: 'var(--landing-bg)', minHeight: '100vh' }}>
      <SEO
        title="Sardis for Payouts — Catch the Anomaly Before It Becomes a Loss"
        description="6-signal anomaly scoring, auto-freeze, cryptographic evidence trails, and instant kill switch for payout and refund automation."
        path="/solutions/payouts"
      />

      {/* Navbar */}
      <nav style={{ borderBottom: '1px solid var(--landing-border)', backgroundColor: 'var(--landing-bg)' }}
        className="sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <SardisWordmark />
          <div className="flex items-center gap-6">
            <Link to="/docs" style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.875rem', color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Docs</Link>
            <Link to="/enterprise" style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.875rem', color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Enterprise</Link>
            <button
              onClick={() => setWaitlistOpen(true)}
              style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.875rem', fontWeight: 500, backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '8px 18px', cursor: 'pointer' }}
            >
              Talk to Sales
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16">
        <motion.div initial="initial" animate="animate" variants={stagger} className="max-w-3xl">
          <motion.div variants={fadeUp}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-accent)' }}>
              For Payout Operations
            </span>
          </motion.div>

          <motion.h1 variants={fadeUp} style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(2.4rem, 5vw, 3.75rem)', lineHeight: 1.08, color: 'var(--landing-text-primary)', marginTop: '1rem', marginBottom: '1.5rem' }}>
            Catch the anomaly<br />before it becomes a loss
          </motion.h1>

          <motion.p variants={fadeUp} style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.125rem', color: 'var(--landing-text-secondary)', lineHeight: 1.7, maxWidth: '580px', marginBottom: '2rem' }}>
            AI-driven payout pipelines move fast. One bad actor or one misfired refund can drain millions before a human spots it. Sardis scores every payout in real time, auto-freezes on breach, and gives you the evidence trail to prove every decision.
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-wrap gap-3">
            <button
              onClick={() => setWaitlistOpen(true)}
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '0.95rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '12px 24px', cursor: 'pointer' }}
            >
              Talk to Sales
            </button>
            <Link to="/demo"
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: '0.95rem', color: 'var(--landing-text-primary)', border: '1px solid var(--landing-border)', borderRadius: '8px', padding: '12px 24px', textDecoration: 'none', display: 'inline-block' }}>
              See the Demo
            </Link>
          </motion.div>
        </motion.div>

        {/* Anomaly detection visual — live-feel score ticker */}
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.38, duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
          style={{ marginTop: '3.5rem', border: '1px solid var(--landing-border)', borderRadius: '12px', backgroundColor: 'var(--landing-surface)', overflow: 'hidden' }}
        >
          <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--landing-border)', backgroundColor: 'var(--landing-surface-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: '0.78rem', color: 'var(--landing-text-muted)' }}>
              sardis anomaly engine — live scoring
            </span>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.72rem', fontWeight: 600, color: 'var(--landing-green)', backgroundColor: 'color-mix(in srgb, var(--landing-green) 10%, transparent)', border: '1px solid color-mix(in srgb, var(--landing-green) 25%, transparent)', padding: '2px 8px', borderRadius: '20px' }}>
              ACTIVE
            </span>
          </div>
          <div style={{ padding: '20px 24px', display: 'grid', gap: '10px' }}>
            {[
              { id: 'pyt_8823', recipient: 'acct_...4f2a', amount: '$142.00', score: 94, verdict: 'APPROVED' },
              { id: 'pyt_8824', recipient: 'acct_...9e11', amount: '$8,400.00', score: 47, verdict: 'FROZEN' },
              { id: 'pyt_8825', recipient: 'acct_...7c3d', amount: '$310.00', score: 82, verdict: 'APPROVED' },
              { id: 'pyt_8826', recipient: 'acct_...2b90', amount: '$975.00', score: 63, verdict: 'PENDING' },
            ].map(row => {
              const color = row.verdict === 'APPROVED' ? 'var(--landing-green)' : row.verdict === 'FROZEN' ? 'var(--landing-red)' : 'var(--landing-amber)';
              const bg = row.verdict === 'APPROVED' ? 'color-mix(in srgb, var(--landing-green) 8%, transparent)' : row.verdict === 'FROZEN' ? 'color-mix(in srgb, var(--landing-red) 8%, transparent)' : 'color-mix(in srgb, var(--landing-amber) 8%, transparent)';
              return (
                <div key={row.id} style={{ display: 'flex', alignItems: 'center', gap: '16px', padding: '10px 14px', border: '1px solid var(--landing-border)', borderRadius: '6px', backgroundColor: 'var(--landing-bg)', fontFamily: "'Geist Mono', monospace", fontSize: '0.8rem' }}>
                  <span style={{ color: 'var(--landing-text-muted)', minWidth: '80px' }}>{row.id}</span>
                  <span style={{ color: 'var(--landing-text-secondary)', flex: 1 }}>{row.recipient}</span>
                  <span style={{ color: 'var(--landing-text-primary)', minWidth: '80px', textAlign: 'right' }}>{row.amount}</span>
                  <span style={{ color: 'var(--landing-text-muted)', minWidth: '50px', textAlign: 'right' }}>
                    <span style={{ color: row.score < 50 ? 'var(--landing-red)' : row.score < 80 ? 'var(--landing-amber)' : 'var(--landing-green)' }}>{row.score}</span>/100
                  </span>
                  <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.7rem', fontWeight: 700, padding: '3px 10px', borderRadius: '20px', backgroundColor: bg, color: color, border: `1px solid ${color}`, minWidth: '80px', textAlign: 'center' }}>
                    {row.verdict}
                  </span>
                </div>
              );
            })}
          </div>
        </motion.div>
      </section>

      {/* Feature cards */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0' }}>
        <div className="max-w-6xl mx-auto px-6">
          <div style={{ marginBottom: '3rem' }}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-text-muted)' }}>
              Built for Payout Operations
            </span>
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.75rem, 3vw, 2.5rem)', color: 'var(--landing-text-primary)', marginTop: '0.75rem', marginBottom: 0 }}>
              Defense in depth, not a single check
            </h2>
          </div>

          <div className="grid md:grid-cols-2 gap-5">
            {features.map((f, i) => (
              <motion.div
                key={f.tag}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                style={{ border: '1px solid var(--landing-border)', borderRadius: '10px', padding: '28px', backgroundColor: 'var(--landing-surface)' }}
              >
                <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--landing-accent)' }}>
                  {f.tag}
                </span>
                <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1.1rem', color: 'var(--landing-text-primary)', margin: '10px 0 8px' }}>
                  {f.title}
                </h3>
                <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.9rem', color: 'var(--landing-text-secondary)', lineHeight: 1.65, margin: 0 }}>
                  {f.body}
                </p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Risk response diagram */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0', backgroundColor: 'var(--landing-surface)' }}>
        <div className="max-w-6xl mx-auto px-6">
          <div style={{ marginBottom: '3rem' }}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-blue)' }}>
              Risk Response
            </span>
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.6rem, 2.8vw, 2.25rem)', color: 'var(--landing-text-primary)', marginTop: '0.75rem', marginBottom: 0 }}>
              Three risk tiers, one unified response framework
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {riskResponseFlow.map((row, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.45, delay: i * 0.07 }}
                style={{ border: '1px solid var(--landing-border)', borderRadius: '8px', padding: '18px 22px', backgroundColor: 'var(--landing-bg)', display: 'grid', gridTemplateColumns: '1fr 1fr auto', gap: '20px', alignItems: 'start' }}
              >
                <div>
                  <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '0.9rem', color: 'var(--landing-text-primary)', marginBottom: '6px' }}>
                    {row.trigger}
                  </div>
                  {row.signals.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '5px' }}>
                      {row.signals.map(sig => (
                        <span key={sig} style={{ fontFamily: "'Geist Mono', monospace", fontSize: '0.72rem', color: 'var(--landing-text-muted)', backgroundColor: 'var(--landing-code-bg)', border: '1px solid var(--landing-border)', borderRadius: '4px', padding: '2px 7px' }}>
                          {sig}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.88rem', color: 'var(--landing-text-secondary)', paddingTop: '2px' }}>
                  {row.action}
                </div>
                {row.outcome ? (
                  <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.72rem', fontWeight: 700, padding: '4px 12px', borderRadius: '20px', backgroundColor: outcomeBackground[row.type], color: outcomeColor[row.type], border: `1px solid ${outcomeColor[row.type]}`, whiteSpace: 'nowrap', alignSelf: 'center' }}>
                    {row.outcome}
                  </span>
                ) : (
                  <span />
                )}
              </motion.div>
            ))}
          </div>

          <div style={{ marginTop: '2rem', padding: '16px 20px', border: '1px solid var(--landing-border)', borderRadius: '8px', backgroundColor: 'var(--landing-code-bg)', fontFamily: "'Geist Mono', monospace", fontSize: '0.82rem', color: 'var(--landing-text-secondary)', lineHeight: 1.6 }}>
            <span style={{ color: 'var(--landing-red)' }}># Auto-freeze triggered</span>{'\n'}
            {`sardis.wallets.freeze("wlt_payout_main")
# → { frozen: true, affected_txs: 14, latency_ms: 18, reason: "velocity_spike_4x" }`}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0' }}>
        <div className="max-w-6xl mx-auto px-6 text-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.55 }}
          >
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.8rem, 3vw, 2.75rem)', color: 'var(--landing-text-primary)', marginBottom: '1rem' }}>
              Stop letting anomalies become post-mortems
            </h2>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.05rem', color: 'var(--landing-text-secondary)', marginBottom: '2rem', maxWidth: '520px', margin: '0 auto 2rem' }}>
              We'll walk you through a payout risk scenario specific to your volume and fraud surface.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <button
                onClick={() => setWaitlistOpen(true)}
                style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '1rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '14px 28px', cursor: 'pointer' }}
              >
                Talk to Sales
              </button>
              <Link to="/demo"
                style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: '1rem', color: 'var(--landing-text-primary)', border: '1px solid var(--landing-border)', borderRadius: '8px', padding: '14px 28px', textDecoration: 'none', display: 'inline-block' }}>
                See the Demo
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid var(--landing-border)', padding: '40px 0' }}>
        <div className="max-w-6xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4">
          <SardisWordmark />
          <div className="flex gap-6" style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.85rem', color: 'var(--landing-text-muted)' }}>
            <Link to="/solutions/agent-platforms" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Agent Platforms</Link>
            <Link to="/solutions/procurement" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Procurement</Link>
            <Link to="/enterprise" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Enterprise</Link>
            <Link to="/docs" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Docs</Link>
          </div>
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', color: 'var(--landing-text-ghost)' }}>© 2026 Sardis</span>
        </div>
      </footer>

      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </div>
  );
}
