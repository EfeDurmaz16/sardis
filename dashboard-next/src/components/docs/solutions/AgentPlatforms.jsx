import { useState } from 'react';
import { Link } from 'next/navigation';
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
    tag: 'Natural Language Policies',
    title: 'Define rules in plain English',
    body: 'Write spending policies the same way you brief your team. Sardis compiles them into deterministic guardrails — no DSL, no YAML, no regex.',
    example: '"max $500/day, block gambling, SaaS vendors only"',
  },
  {
    tag: 'Simulation & Dry-Run',
    title: 'Test before your agents spend a cent',
    body: 'Run any transaction against your full policy suite in simulation mode. Ship payment integrations with the same confidence as unit tests.',
    example: 'sardis.simulate(tx) → { verdict: "APPROVED", signals: [...] }',
  },
  {
    tag: 'Kill Switch',
    title: 'Instant freeze across every agent',
    body: 'One API call halts all outbound transactions for a wallet, a group, or your entire fleet. No waiting for webhooks. No race conditions.',
    example: 'sardis.wallets.freeze("wlt_abc") → { frozen: true, latency_ms: 12 }',
  },
  {
    tag: 'Evidence Trail',
    title: 'Every decision cryptographically proved',
    body: 'HMAC-signed receipts and Merkle proofs anchor every approval and rejection to your immutable ledger. Pass any audit without calling a human.',
    example: 'receipt.merkle_root → "0x3fa9...e1c2" (anchored to Base)',
  },
];

const sdkSnippet = `from sardis import SardisClient

client = SardisClient(api_key="sk_live_...")

# Create a wallet for your agent
wallet = client.wallets.create(name="research-agent-01")

# Define spending policy in plain English
policy = client.policies.create_from_nl(
    wallet_id=wallet.id,
    policy="max $500/day, block gambling, approved SaaS vendors only"
)

# Payments are gated automatically — no extra code
tx = client.payments.send(
    from_wallet=wallet.id,
    href="vendor.eth",
    amount_usd=49.00,
    memo="OpenAI API subscription"
)
# → { status: "APPROVED", policy_signals: [...], receipt_id: "rcpt_..." }`;

export default function AgentPlatforms() {
  const [waitlistOpen, setWaitlistOpen] = useState(false);

  return (
    <div style={{ backgroundColor: 'var(--landing-bg)', minHeight: '100vh' }}>
      <SEO
        title="Sardis for Agent Platforms — Real Wallets, Real Guardrails"
        description="Give your AI agents non-custodial wallets with natural language spending policies, simulation, and cryptographic evidence trails. Python and TypeScript SDKs."
        path="/solutions/agent-platforms"
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
              Start Building Free
            </button>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 pt-20 pb-16">
        <motion.div initial="initial" animate="animate" variants={stagger} className="max-w-3xl">
          <motion.div variants={fadeUp}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-accent)' }}>
              For Agent Platforms
            </span>
          </motion.div>

          <motion.h1 variants={fadeUp} style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(2.4rem, 5vw, 3.75rem)', lineHeight: 1.08, color: 'var(--landing-text-primary)', marginTop: '1rem', marginBottom: '1.5rem' }}>
            Give your agents real wallets<br />with real guardrails
          </motion.h1>

          <motion.p variants={fadeUp} style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.125rem', color: 'var(--landing-text-secondary)', lineHeight: 1.7, maxWidth: '560px', marginBottom: '2rem' }}>
            LangChain, CrewAI, AutoGPT — every major framework can connect to Sardis in three lines. Your agents get non-custodial wallets, natural language spending policies, and a kill switch you can trigger at any time.
          </motion.p>

          <motion.div variants={fadeUp} className="flex flex-wrap gap-3">
            <button
              onClick={() => setWaitlistOpen(true)}
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '0.95rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '12px 24px', cursor: 'pointer' }}
            >
              Start Building Free
            </button>
            <Link href="/demo"
              style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: '0.95rem', color: 'var(--landing-text-primary)', border: '1px solid var(--landing-border)', borderRadius: '8px', padding: '12px 24px', textDecoration: 'none', display: 'inline-block' }}>
              See the Demo
            </Link>
          </motion.div>
        </motion.div>

        {/* Hero code snippet */}
        <motion.div
          initial={{ opacity: 0, y: 32 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.6, ease: [0.25, 0.46, 0.45, 0.94] }}
          style={{ marginTop: '3rem', borderRadius: '12px', border: '1px solid var(--landing-border)', backgroundColor: 'var(--landing-surface)', overflow: 'hidden' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '12px 16px', borderBottom: '1px solid var(--landing-border)', backgroundColor: 'var(--landing-surface-elevated)' }}>
            <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#FF5F57', display: 'inline-block' }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#FFBD2E', display: 'inline-block' }} />
            <span style={{ width: 10, height: 10, borderRadius: '50%', backgroundColor: '#28C840', display: 'inline-block' }} />
            <span style={{ marginLeft: 8, fontFamily: "'Geist Mono', 'JetBrains Mono', monospace", fontSize: '0.78rem', color: 'var(--landing-text-muted)' }}>sardis_quickstart.py</span>
          </div>
          <pre style={{ margin: 0, padding: '20px 24px', overflowX: 'auto', fontFamily: "'Geist Mono', 'JetBrains Mono', monospace", fontSize: '0.82rem', lineHeight: 1.7, color: 'var(--landing-text-primary)', backgroundColor: 'var(--landing-code-bg)' }}>
            <code>{sdkSnippet}</code>
          </pre>
        </motion.div>
      </section>

      {/* Feature cards */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0' }}>
        <div className="max-w-6xl mx-auto px-6">
          <div style={{ marginBottom: '3rem' }}>
            <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-text-muted)' }}>
              Why Agent Platforms Choose Sardis
            </span>
            <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.75rem, 3vw, 2.5rem)', color: 'var(--landing-text-primary)', marginTop: '0.75rem', marginBottom: 0 }}>
              Everything you need. Nothing you don't.
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
                <h3 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 600, fontSize: '1.15rem', color: 'var(--landing-text-primary)', margin: '10px 0 8px' }}>
                  {f.title}
                </h3>
                <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.9rem', color: 'var(--landing-text-secondary)', lineHeight: 1.65, marginBottom: '16px' }}>
                  {f.body}
                </p>
                <code style={{ fontFamily: "'Geist Mono', 'JetBrains Mono', monospace", fontSize: '0.78rem', color: 'var(--landing-text-tertiary)', backgroundColor: 'var(--landing-code-bg)', border: '1px solid var(--landing-border)', borderRadius: '6px', padding: '8px 12px', display: 'block', lineHeight: 1.5 }}>
                  {f.example}
                </code>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Policy creation spotlight */}
      <section style={{ borderTop: '1px solid var(--landing-border)', padding: '80px 0', backgroundColor: 'var(--landing-surface)' }}>
        <div className="max-w-6xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-16 items-center">
            <div>
              <span style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.8rem', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--landing-blue)' }}>
                3 Lines to First Policy
              </span>
              <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 'clamp(1.6rem, 2.8vw, 2.25rem)', color: 'var(--landing-text-primary)', margin: '0.75rem 0 1rem' }}>
                Policies that read like your Confluence page
              </h2>
              <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.95rem', color: 'var(--landing-text-secondary)', lineHeight: 1.7, marginBottom: '1.5rem' }}>
                No proprietary DSL to learn. No regex to maintain. Write your spending rules in English — Sardis compiles them into a deterministic policy engine that fires before every transaction clears.
              </p>
              <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 2rem', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {['Python SDK (pip install sardis)', 'TypeScript SDK (npm install @sardis/sdk)', 'MCP server for Claude / Cursor'].map(item => (
                  <li key={item} style={{ fontFamily: "'Inter', sans-serif", fontSize: '0.9rem', color: 'var(--landing-text-secondary)', display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ color: 'var(--landing-accent)', fontWeight: 700 }}>+</span> {item}
                  </li>
                ))}
              </ul>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => setWaitlistOpen(true)}
                  style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '0.9rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '11px 22px', cursor: 'pointer' }}
                >
                  Start Building Free
                </button>
                <Link href="/docs/sdk-python"
                  style={{ fontFamily: "'Inter', sans-serif", fontWeight: 500, fontSize: '0.9rem', color: 'var(--landing-text-primary)', border: '1px solid var(--landing-border)', borderRadius: '8px', padding: '11px 22px', textDecoration: 'none', display: 'inline-block' }}>
                  Python SDK docs
                </Link>
              </div>
            </div>

            <div style={{ borderRadius: '10px', border: '1px solid var(--landing-border)', overflow: 'hidden' }}>
              <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--landing-border)', backgroundColor: 'var(--landing-surface-elevated)', fontFamily: "'Geist Mono', monospace", fontSize: '0.78rem', color: 'var(--landing-text-muted)' }}>
                Natural language → policy engine
              </div>
              <pre style={{ margin: 0, padding: '20px 24px', fontFamily: "'Geist Mono', 'JetBrains Mono', monospace", fontSize: '0.8rem', lineHeight: 1.75, color: 'var(--landing-text-primary)', backgroundColor: 'var(--landing-code-bg)', overflowX: 'auto' }}>
                <code>{`policy = client.policies.create_from_nl(
    wallet_id="wlt_research_01",
    policy="max $500/day, block gambling, "
           "approved SaaS vendors only"
)

# Sardis compiles this into:
# {
#   daily_limit_usd: 500,
#   blocked_categories: ["GAMBLING"],
#   vendor_allowlist: true,
#   enforce_before_sign: true
# }`}
                </code>
              </pre>
            </div>
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
              Your agents deserve better than a shared credit card
            </h2>
            <p style={{ fontFamily: "'Inter', sans-serif", fontSize: '1.05rem', color: 'var(--landing-text-secondary)', marginBottom: '2rem', maxWidth: '520px', margin: '0 auto 2rem' }}>
              Free tier includes 1,000 policy checks and 100 test transactions per month.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <button
                onClick={() => setWaitlistOpen(true)}
                style={{ fontFamily: "'Inter', sans-serif", fontWeight: 600, fontSize: '1rem', backgroundColor: 'var(--landing-accent)', color: '#fff', border: 'none', borderRadius: '8px', padding: '14px 28px', cursor: 'pointer' }}
              >
                Start Building Free
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
            <Link href="/solutions/procurement" style={{ color: 'var(--landing-text-muted)', textDecoration: 'none' }}>Procurement</Link>
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
