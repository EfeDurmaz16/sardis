import { Link } from 'react-router-dom';
// eslint-disable-next-line no-unused-vars -- motion is used as JSX namespace (motion.div)
import { motion } from 'framer-motion';
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/inter/300.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/jetbrains-mono/400.css';
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
    tag: 'Spending Mandates',
    title: 'Delegated financial authority',
    body: 'Issue time-bound, amount-capped mandates to your agents. Every transaction requires a valid mandate chain before money moves.',
    stat: '0 unauthorized transactions',
  },
  {
    tag: 'Policy Engine',
    title: '12-check enforcement pipeline',
    body: 'Every payment passes through 12 independent checks: amount limits, merchant whitelist, time windows, velocity controls, sanctions screening, and more.',
    stat: '12 checks per transaction',
  },
  {
    tag: 'Kill Switch',
    title: 'Instant freeze across all agents',
    body: 'One API call freezes every agent wallet in your organization. Sub-second propagation. No transactions slip through during investigation.',
    stat: '<100ms propagation',
  },
  {
    tag: 'Audit Trail',
    title: 'Cryptographic evidence for every dollar',
    body: 'Append-only ledger with Merkle-anchored proofs. Every transaction, policy check, and approval is recorded with signed attestation envelopes.',
    stat: 'Immutable proof',
  },
];

const pipelineSteps = [
  { num: '01', label: 'Intent received', detail: 'Agent submits payment request' },
  { num: '02', label: 'Mandate verified', detail: 'Spending authority chain validated' },
  { num: '03', label: 'Policy evaluated', detail: '12 independent checks executed' },
  { num: '04', label: 'Sanctions screened', detail: 'OFAC + Elliptic real-time check' },
  { num: '05', label: 'Route selected', detail: 'Optimal chain + token chosen' },
  { num: '06', label: 'MPC signed', detail: 'Non-custodial multi-party signature' },
  { num: '07', label: 'On-chain executed', detail: 'Transaction broadcast + confirmed' },
  { num: '08', label: 'Audit anchored', detail: 'Merkle proof + attestation envelope' },
];

export default function WedgeSecurePayments() {
  return (
    <div className="min-h-screen" style={{ backgroundColor: 'var(--landing-bg)', fontFamily: "'Inter', sans-serif" }}>
      <SEO
        title="Secure AI Payments | Sardis"
        description="Your AI agents spend money. Do you know how much? Sardis gives you spending mandates, policy enforcement, and cryptographic audit trails for every dollar."
      />

      {/* Nav */}
      <nav
        className="fixed top-0 left-0 right-0 z-50 backdrop-blur-md border-b"
        style={{ backgroundColor: 'color-mix(in srgb, var(--landing-bg) 80%, transparent)', borderBottomColor: 'var(--landing-border)' }}
      >
        <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
          <div className="flex items-center justify-between h-16">
            <SardisWordmark />
            <div className="hidden md:flex items-center gap-8">
              <a href="/docs" className="text-[14px] transition-colors" style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-muted)' }}>Docs</a>
              <a href="/pricing" className="text-[14px] transition-colors" style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-muted)' }}>Pricing</a>
              <a
                href="https://dashboard.sardis.sh/signup"
                className="text-[14px] font-medium text-white rounded-lg px-4 py-2"
                style={{ fontFamily: "'Inter', sans-serif", backgroundColor: 'var(--landing-accent)' }}
              >
                Get Started
              </a>
            </div>
          </div>
        </div>
      </nav>

      {/* Spacer */}
      <div className="h-16" />

      {/* Hero */}
      <motion.section
        variants={stagger}
        initial="initial"
        animate="animate"
        className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-20 md:pt-32 pb-16 md:pb-24 text-center"
      >
        <motion.div variants={fadeUp}>
          <span
            className="inline-flex items-center gap-2 rounded-full px-4 py-1.5 mb-6 text-xs font-medium"
            style={{
              background: 'rgba(34,197,94,0.08)',
              border: '1px solid rgba(34,197,94,0.2)',
              color: '#22C55E',
              fontFamily: "'Inter', sans-serif",
            }}
          >
            Wedge 1: Secure Payments
          </span>
        </motion.div>

        <motion.h1
          variants={fadeUp}
          className="text-[36px] md:text-[56px] lg:text-[64px] font-bold tracking-[-0.04em] leading-tight mb-6"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
        >
          Your AI agents spend money.
          <br />
          Do you know how much?
        </motion.h1>

        <motion.p
          variants={fadeUp}
          className="text-[16px] md:text-[18px] leading-relaxed max-w-2xl mx-auto mb-10 font-light"
          style={{ color: 'var(--landing-text-secondary)' }}
        >
          Sardis gives every agent a policy-controlled wallet with spending mandates,
          real-time enforcement, and cryptographic proof of every dollar spent.
        </motion.p>

        <motion.div variants={fadeUp} className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="https://dashboard.sardis.sh/signup?plan=starter"
            className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px]"
            style={{ backgroundColor: 'var(--landing-accent)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--landing-accent-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--landing-accent)'}
          >
            Start at $199/mo
          </a>
          <a
            href="mailto:contact@sardis.sh"
            className="rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px]"
            style={{ border: '1px solid var(--landing-border)', color: 'var(--landing-text-secondary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = 'var(--landing-text-muted)';
              e.currentTarget.style.color = 'var(--landing-text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = 'var(--landing-border)';
              e.currentTarget.style.color = 'var(--landing-text-secondary)';
            }}
          >
            Book a Demo →
          </a>
        </motion.div>
      </motion.section>

      {/* Features */}
      <section className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pb-20">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {features.map((f, i) => (
            <motion.div
              key={f.tag}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ delay: i * 0.1, duration: 0.5 }}
              className="rounded-2xl p-6 md:p-8"
              style={{ background: 'var(--landing-surface, rgba(255,255,255,0.02))', border: '1px solid var(--landing-border)' }}
            >
              <span
                className="inline-block text-[11px] font-medium uppercase tracking-widest mb-4 px-2.5 py-1 rounded"
                style={{
                  fontFamily: "'JetBrains Mono', monospace",
                  background: 'rgba(34,197,94,0.08)',
                  color: '#22C55E',
                  border: '1px solid rgba(34,197,94,0.15)',
                }}
              >
                {f.tag}
              </span>
              <h3
                className="text-[20px] md:text-[24px] font-bold mb-3 tracking-tight"
                style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
              >
                {f.title}
              </h3>
              <p
                className="text-[14px] leading-relaxed mb-4 font-light"
                style={{ color: 'var(--landing-text-secondary)' }}
              >
                {f.body}
              </p>
              <div
                className="text-[13px] font-medium"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
              >
                {f.stat}
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Pipeline visualization */}
      <section
        className="py-20"
        style={{ borderTop: '1px solid var(--landing-border)', borderBottom: '1px solid var(--landing-border)' }}
      >
        <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20">
          <h2
            className="text-center text-[28px] md:text-[36px] font-bold tracking-tight mb-4"
            style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
          >
            Every payment, 8 gates
          </h2>
          <p
            className="text-center text-[15px] font-light mb-12 max-w-xl mx-auto"
            style={{ color: 'var(--landing-text-secondary)' }}
          >
            From intent to settlement, every transaction passes through Sardis's enforcement pipeline.
          </p>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {pipelineSteps.map((step, i) => (
              <motion.div
                key={step.num}
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06, duration: 0.4 }}
                className="rounded-xl p-5"
                style={{ background: 'var(--landing-surface, rgba(255,255,255,0.02))', border: '1px solid var(--landing-border)' }}
              >
                <span
                  className="text-[24px] font-bold block mb-2"
                  style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-ghost)' }}
                >
                  {step.num}
                </span>
                <span
                  className="text-[14px] font-medium block mb-1"
                  style={{ color: 'var(--landing-text-primary)' }}
                >
                  {step.label}
                </span>
                <span
                  className="text-[12px]"
                  style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
                >
                  {step.detail}
                </span>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-20 md:py-28 text-center">
        <h2
          className="text-[32px] md:text-[44px] font-bold tracking-tight mb-4"
          style={{ fontFamily: "'Space Grotesk', sans-serif", color: 'var(--landing-text-primary)' }}
        >
          Stop hoping your agents behave.
        </h2>
        <p
          className="text-[16px] font-light mb-8 max-w-lg mx-auto"
          style={{ color: 'var(--landing-text-secondary)' }}
        >
          Start with the Starter plan. No credit card for the free tier.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="https://dashboard.sardis.sh/signup?plan=starter"
            className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px]"
            style={{ backgroundColor: 'var(--landing-accent)' }}
            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--landing-accent-hover)'}
            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--landing-accent)'}
          >
            Start at $199/mo
          </a>
          <Link
            to="/pricing"
            className="rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] text-center"
            style={{ border: '1px solid var(--landing-border)', color: 'var(--landing-text-secondary)' }}
          >
            Compare plans
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer
        className="border-t py-8 text-center"
        style={{ borderColor: 'var(--landing-border)' }}
      >
        <p
          className="text-xs"
          style={{ color: 'var(--landing-text-ghost)' }}
        >
          &copy; {new Date().getFullYear()} Sardis Labs, Inc. All rights reserved.{' '}
          <Link to="/docs/terms" className="underline" style={{ color: 'var(--landing-text-muted)' }}>Terms</Link>{' '}
          &middot;{' '}
          <Link to="/docs/privacy" className="underline" style={{ color: 'var(--landing-text-muted)' }}>Privacy</Link>
        </p>
      </footer>
    </div>
  );
}
