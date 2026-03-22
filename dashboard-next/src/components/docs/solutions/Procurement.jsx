import { useState } from 'react';
import Link from 'next/link';
// eslint-disable-next-line no-unused-vars -- motion is used as JSX namespace (motion.div)
import { motion } from 'framer-motion';
import WaitlistModal from '@/components/WaitlistModal';

const fadeUp = {
  initial: { opacity: 0, y: 24 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.55, ease: [0.25, 0.46, 0.45, 0.94] },
};

const stagger = { animate: { transition: { staggerChildren: 0.1 } } };

function SardisWordmark() {
  return (
    <Link href="/" className="flex items-center gap-2.5" style={{ textDecoration: 'none' }}>
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
    tag: 'Approval Workflows',
    title: 'Confidence-based routing & 4-eyes quorum',
    body: 'High-confidence purchases flow automatically within policy. Edge cases route to a human reviewer. Quorum rules ensure no single agent can authorize a large transaction solo.',
  },
  {
    tag: 'Evidence Trail',
    title: 'HMAC receipts and Merkle proofs for auditors',
    body: 'Every purchase generates a tamper-proof HMAC receipt anchored to Base via Merkle tree. Hand your auditors a cryptographic proof — no spreadsheet reconciliation.',
  },
  {
    tag: 'Merchant Protection',
    title: 'First-seen scrutiny and trust scoring',
    body: 'New merchants are held to a higher standard. Sardis tracks vendor history, applies trust scores, and flags first-seen counterparties for human review before funds move.',
  },
  {
    tag: 'Policy Management',
    title: 'Department-level spending policies',
    body: 'Engineering, marketing, and finance can each operate under distinct policy sets. Changes propagate instantly across all wallets — no re-deployment, no config drift.',
  },
];

const approvalFlow = [
  { step: '01', label: 'Agent submits payment intent', status: 'auto', detail: 'amount, vendor, memo, mandate chain' },
  { step: '02', label: 'Policy engine scores the request', status: 'auto', detail: 'confidence 0–100 across 6 signals' },
  { step: '03', label: 'Routing decision', status: 'branch', detail: 'score ≥ 80 → auto-approve / score < 80 → human queue' },
  { step: '04', label: 'Transaction signed & settled', status: 'auto', detail: 'HMAC receipt + Merkle anchor issued' },
  { step: '05', label: 'Ledger entry appended', status: 'auto', detail: 'immutable, queryable, exportable' },
];

export default function Procurement() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <div style={{ backgroundColor: 'var(--landing-bg)', minHeight: '100vh' }}>
      <SEO
        title="Sardis for Procurement — Every Purchase Approved, Verified, Auditable"
        description="Confidence-based approval routing, HMAC receipts, Merkle audit proofs, and merchant trust scoring for procurement and business spend automation."
        path="/solutions/procurement"
      />

      {/* Navbar */}
      <nav style={{ borderBottom: '1px solid var(--landing-border)', backgroundColor: 'var(--landing-bg)' }}
        className="sticky top-0 z-50 backdrop-blur-md">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <SardisWordmark />
          <div className="flex items-center gap-6">
            <Link href="/docs" style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.875rem', color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Docs</Link>
            <Link href="/enterprise" style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.875rem', color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Enterprise</Link>
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
              For Procurement Teams
            </span>
          </motion.div>

          <motion.h1 variants={fadeUp} style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(2.4rem, 5vw, 3.75rem)', lineHeight: 1.08, color: 'var(--landing-text-primary)', marginTop: '1rem', marginBottom: '1.5rem' }}>
            Every purchase approved,<br />verified, and auditable
          </motion.h1>

          <motion.p variants={fadeUp} style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.125rem', color: 'var(--landing-text-secondary)', lineHeight: 1.7, maxWidth: '580px', marginBottom: '2rem' }}>
            AI agents are handling more of your procurement pipeline. Sardis gives you confidence-based approval routing, department-level spending policies, and a cryptographic audit trail that satisfies even the most demanding auditor.
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-wrap gap-3">
            <button
              onClick={() => setWaitlistOpen(true)}
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '0.95rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '12px 24px', cursor: 'pointer' }}
            >
              Talk to Sales
            </button>
            <Link href="/demo"
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: '0.95rem', color: 'var(--landing-text-primary)', border: '1px solid var(--landing-border)', borderRadius: '8px', padding: '12px 24px', textDecoration: 'none', display: 'inline-block' }}>
              See the Demo
            </Link>
          </motion.div>
        </motion.div>

        {/* KPI strip */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.55 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-5 mt-14"
        >
          {[
            { value: '< 50ms', label: 'Policy check latency' },
            { value: '100%', label: 'Transactions auditable' },
            { value: '6-signal', label: 'Confidence scoring' },
            { value: 'Zero', label: 'Config drift risk' },
          ].map(kpi => (
            <div key={kpi.label} style={{ border: '1px solid var(--landing-border)', borderRadius: '10px', padding: '20px', backgroundColor: 'var(--landing-surface)' }}>
              <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: '1.6rem', color: 'var(--landing-accent)', marginBottom: '4px' }}>{kpi.value}</div>
              <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.82rem', color: 'var(--landing-text-muted)' }}>{kpi.label}</div>
            </div>
          ))}
        </motion.div>
      </section>

      {/* Feature cards */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0' }}>
        <div className="max-w-6xl mx-auto px-6">
          <div style={{ marginBottom: '3rem' }}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-text-muted)' }}>
              Built for Procurement Teams
            </span>
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.75rem, 3vw, 2.5rem)', color: 'var(--landing-text-primary)', marginTop: '0.75rem', marginBottom: 0 }}>
              Controls built for humans who move money
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

      {/* Approval flow diagram */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0', backgroundColor: 'var(--landing-surface)' }}>
        <div className="max-w-6xl mx-auto px-6">
          <div style={{ marginBottom: '3rem' }}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-blue)' }}>
              Approval Flow
            </span>
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.6rem, 2.8vw, 2.25rem)', color: 'var(--landing-text-primary)', marginTop: '0.75rem', marginBottom: 0 }}>
              From intent to receipt in under 200ms
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {approvalFlow.map((item, i) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, x: -16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, amount: 0.3 }}
                transition={{ duration: 0.45, delay: i * 0.07 }}
                style={{ display: 'flex', alignItems: 'center', gap: '20px', padding: '18px 24px', border: '1px solid var(--landing-border)', borderRadius: '8px', backgroundColor: 'var(--landing-bg)', marginBottom: i < approvalFlow.length - 1 ? '6px' : 0 }}
              >
                <span style={{ fontFamily: "'Geist Mono', monospace", fontSize: '0.78rem', fontWeight: 700, color: 'var(--landing-accent)', minWidth: '28px' }}>
                  {item.step}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '0.95rem', color: 'var(--landing-text-primary)', marginBottom: '2px' }}>
                    {item.label}
                  </div>
                  <div style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.82rem', color: 'var(--landing-text-muted)' }}>
                    {item.detail}
                  </div>
                </div>
                <span style={{
                  fontFamily: "'Inter', sans-serif", fontSize: '0.72rem', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.06em',
                  padding: '4px 10px', borderRadius: '20px',
                  backgroundColor: item.status === 'auto' ? 'color-mix(in srgb, var(--landing-green) 12%, transparent)' : 'color-mix(in srgb, var(--landing-blue) 12%, transparent)',
                  color: item.status === 'auto' ? 'var(--landing-green)' : 'var(--landing-blue)',
                  border: `1px solid ${item.status === 'auto' ? 'color-mix(in srgb, var(--landing-green) 30%, transparent)' : 'color-mix(in srgb, var(--landing-blue) 30%, transparent)'}`,
                  whiteSpace: 'nowrap',
                }}>
                  {item.status === 'branch' ? 'decision' : 'automated'}
                </span>
              </motion.div>
            ))}
          </div>

          <div style={{ marginTop: '2rem', padding: '16px 20px', border: '1px solid var(--landing-border)', borderRadius: '8px', backgroundColor: 'var(--landing-code-bg)', fontFamily: "'Geist Mono', monospace", fontSize: '0.82rem', color: 'var(--landing-text-secondary)', lineHeight: 1.6 }}>
            <span style={{ color: 'var(--landing-text-muted)' }}># Human review queue entry</span>{'\n'}
            {`{ "tx_id": "tx_...", "confidence": 61, "reason": "first_seen_vendor", "reviewer": null, "queued_at": "2026-03-08T14:22:01Z" }`}
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
              Your procurement team deserves infrastructure that keeps up
            </h2>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.05rem', color: 'var(--landing-text-secondary)', marginBottom: '2rem', maxWidth: '520px', margin: '0 auto 2rem' }}>
              Talk to our team and we'll walk you through an approval workflow tailored to your spend categories.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <button
                onClick={() => setWaitlistOpen(true)}
                style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '1rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '14px 28px', cursor: 'pointer' }}
              >
                Talk to Sales
              </button>
              <Link href="/demo"
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
            <Link href="/solutions/agent-platforms" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Agent Platforms</Link>
            <Link href="/solutions/payouts" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Payouts</Link>
            <Link href="/enterprise" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Enterprise</Link>
            <Link href="/docs" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Docs</Link>
          </div>
          <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', color: 'var(--landing-text-ghost)' }}>© 2026 Sardis</span>
        </div>
      </footer>

      <WaitlistModal isOpen={waitlistOpen} onClose={() => setWaitlistOpen(false)} />
    </div>
  );
}
