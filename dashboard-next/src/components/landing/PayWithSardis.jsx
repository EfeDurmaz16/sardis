import { useState } from 'react';
// eslint-disable-next-line no-unused-vars -- motion is used as JSX namespace (motion.div)
import { motion, AnimatePresence } from 'framer-motion';

/* ── Checkout Mockup ──────────────────────────────────────────── */

function CheckoutMockup() {
  const [step, setStep] = useState('pay'); // pay | processing | success

  return (
    <div className="relative w-[370px] select-none" style={{ fontFamily: "'Inter', sans-serif" }}>
      <div
        className="rounded-[28px] overflow-hidden"
        style={{
          background: '#FFFFFF',
          border: '1px solid rgba(0,0,0,0.08)',
          boxShadow: '0 25px 60px rgba(0,0,0,0.08), 0 0 0 1px rgba(0,0,0,0.03)',
        }}
      >
        {/* Merchant header */}
        <div className="flex flex-col items-center pt-8 pb-4 px-6">
          <div
            className="w-10 h-10 rounded-full flex items-center justify-center mb-2"
            style={{ background: '#F0F0F0' }}
          >
            <span style={{ fontSize: 16, fontWeight: 600, color: '#4A4A4A' }}>A</span>
          </div>
          <span style={{ color: '#71717A', fontSize: 13 }}>Acme Corp</span>
          <div className="flex items-baseline gap-1.5 mt-2">
            <span style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 36, fontWeight: 600, color: '#18181B', letterSpacing: '-0.03em' }}>
              49.99
            </span>
            <span style={{ color: '#A1A1AA', fontSize: 14 }}>USDC</span>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {step === 'pay' && (
            <motion.div
              key="pay"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-6 pb-4"
            >
              {/* Tab switcher */}
              <div className="flex rounded-lg p-1 mb-4" style={{ background: '#F4F4F5' }}>
                <div className="flex-1 py-1.5 text-center text-[12px] font-medium rounded-md shadow-sm" style={{ background: '#FFFFFF', color: '#18181B' }}>
                  Pay from Wallet
                </div>
                <div className="flex-1 py-1.5 text-center text-[12px] font-medium rounded-md" style={{ color: '#A1A1AA' }}>
                  Fund &amp; Pay
                </div>
              </div>

              {/* Wallet input */}
              <div className="mb-3">
                <div style={{ fontSize: 10, color: '#71717A', letterSpacing: '0.05em', marginBottom: 4 }}>WALLET ID</div>
                <div className="rounded-lg px-3 py-2" style={{ border: '1px solid #E4E4E7', background: '#FAFAFA' }}>
                  <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: '#18181B' }}>wal_8f3k...x9m2</span>
                </div>
              </div>

              {/* Balance */}
              <div className="flex items-center justify-between rounded-lg px-3 py-2 mb-4" style={{ background: '#F8F8F6' }}>
                <span style={{ fontSize: 10, color: '#71717A', letterSpacing: '0.05em' }}>BALANCE</span>
                <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 13, color: '#2775CA', fontWeight: 500 }}>
                  2,847.50 <span style={{ color: '#A1A1AA' }}>USDC</span>
                </span>
              </div>

              {/* Pay button */}
              <button
                onClick={() => {
                  setStep('processing');
                  setTimeout(() => setStep('success'), 1800);
                }}
                className="w-full py-2.5 rounded-lg text-white text-[13px] font-medium transition-colors"
                style={{ background: '#2563EB' }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#1D4ED8'}
                onMouseLeave={(e) => e.currentTarget.style.background = '#2563EB'}
              >
                Pay 49.99 USDC
              </button>
            </motion.div>
          )}

          {step === 'processing' && (
            <motion.div
              key="processing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="px-6 pb-6 flex flex-col items-center"
            >
              <div className="w-8 h-8 border-2 rounded-full mb-4 animate-spin" style={{ borderColor: '#E4E4E7', borderTopColor: '#2563EB' }} />
              <span style={{ fontSize: 14, fontWeight: 500, color: '#18181B', marginBottom: 12 }}>Processing Payment</span>
              <div className="w-full space-y-2">
                {[
                  { label: 'Policy verified', done: true },
                  { label: 'Submitting transaction', done: false, active: true },
                  { label: 'Awaiting confirmation', done: false },
                ].map((s) => (
                  <div key={s.label} className="flex items-center gap-2 rounded-lg px-3 py-2" style={{ background: '#F8F8F6' }}>
                    {s.done ? (
                      <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M3 6l2 2 4-4" stroke="#16A34A" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    ) : s.active ? (
                      <div className="w-3 h-3 border-[1.5px] rounded-full animate-spin" style={{ borderColor: '#E4E4E7', borderTopColor: '#2563EB' }} />
                    ) : (
                      <div className="w-3 h-3 rounded-full" style={{ border: '1.5px solid #E4E4E7' }} />
                    )}
                    <span style={{ fontSize: 12, color: s.done ? '#16A34A' : s.active ? '#18181B' : '#A1A1AA', fontWeight: s.active ? 500 : 400 }}>{s.label}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}

          {step === 'success' && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="px-6 pb-6 flex flex-col items-center"
            >
              <div className="w-10 h-10 rounded-full flex items-center justify-center mb-3" style={{ background: '#DCFCE7' }}>
                <svg width="24" height="24" viewBox="0 0 20 20" fill="none"><path d="M5 10.5l3.5 3.5L15 7" stroke="#16A34A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
              </div>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#18181B', marginBottom: 2 }}>Payment Successful</span>
              <span style={{ fontSize: 12, color: '#A1A1AA', marginBottom: 10 }}>49.99 USDC sent</span>
              <div className="w-full rounded-lg overflow-hidden" style={{ background: '#F8F8F6' }}>
                {[
                  { label: 'STATUS', value: 'Confirmed', color: '#16A34A' },
                  { label: 'TX HASH', value: '0x8f3k...x9m2', mono: true },
                  { label: 'CHAIN', value: 'Base', color: '#2563EB' },
                ].map((row, i) => (
                  <div key={row.label} className="flex items-center justify-between px-3 py-2.5" style={{ borderTop: i > 0 ? '1px solid #E4E4E7' : 'none' }}>
                    <span style={{ fontSize: 9, color: '#A1A1AA', letterSpacing: '0.05em' }}>{row.label}</span>
                    <span style={{ fontSize: 12, color: row.color || '#18181B', fontFamily: row.mono ? "'JetBrains Mono', monospace" : 'inherit', fontWeight: 500 }}>{row.value}</span>
                  </div>
                ))}
              </div>
              <button
                onClick={() => setStep('pay')}
                className="mt-3 text-[11px] font-medium"
                style={{ color: '#2563EB', background: 'none', border: 'none', cursor: 'pointer' }}
              >
                Replay demo
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3" style={{ borderTop: '1px solid rgba(0,0,0,0.06)' }}>
          <div className="flex items-center gap-1.5">
            <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M6 8v1M4 5h4a2 2 0 012 2v2a1 1 0 01-1 1H3a1 1 0 01-1-1V7a2 2 0 012-2zM4 5V3a2 2 0 014 0v2" stroke="#A1A1AA" strokeWidth="0.9" strokeLinecap="round" />
            </svg>
            <span style={{ color: '#A1A1AA', fontSize: 10 }}>Secured by Sardis</span>
          </div>
          <span style={{ color: '#A1A1AA', fontSize: 10 }}>Base Network</span>
        </div>
      </div>
    </div>
  );
}

/* ── Section ──────────────────────────────────────────────────── */

const benefits = [
  {
    title: '0% merchant fee',
    desc: 'USDC settlement is free. Fiat offramp via Bridge at ~1%. No card network fees.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
        <circle cx="10" cy="10" r="8" stroke="currentColor" strokeWidth="1.2" />
        <path d="M10 6v8M7 10h6" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
      </svg>
    ),
  },
  {
    title: 'Fiat-to-USDC onramp',
    desc: 'Customers buy USDC with card or bank via Coinbase Onramp. Zero conversion fee.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
        <rect x="2" y="4" width="16" height="12" rx="2" stroke="currentColor" strokeWidth="1.2" />
        <path d="M2 8h16" stroke="currentColor" strokeWidth="1.2" />
      </svg>
    ),
  },
  {
    title: '3 lines to integrate',
    desc: 'Drop in a script tag and a web component. Or use the JS SDK for full control.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
        <path d="M7 7l-4 3 4 3M13 7l4 3-4 3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    title: 'Instant settlement',
    desc: 'USDC arrives in your wallet on-chain. No 2-day hold. No chargebacks.',
    icon: (
      <svg width="24" height="24" viewBox="0 0 20 20" fill="none">
        <path d="M10 2v16M14 6l-4-4-4 4M6 14l4 4 4-4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export default function PayWithSardis() {
  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-[100px] md:pt-[140px]">
        <div className="flex flex-col lg:flex-row lg:items-center lg:gap-[80px]">
          {/* Left: content */}
          <div className="flex-1 mb-12 lg:mb-0">
            <span
              className="inline-block tracking-widest uppercase px-2.5 py-1 rounded-full"
              style={{
                fontFamily: "'JetBrains Mono', monospace",
                fontSize: '10px',
                color: 'var(--landing-accent)',
                background: 'rgba(255,79,0,0.08)',
                border: '1px solid rgba(255,79,0,0.15)',
                fontWeight: 500,
              }}
            >
              NEW FEATURE
            </span>
            <h2
              className="mt-4 mb-4 max-w-[480px]"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 600,
                fontSize: 'clamp(34px, 4.8vw, 48px)',
                lineHeight: 'clamp(40px, 5.4vw, 54px)',
                color: 'var(--landing-text-primary)',
              }}
            >
              Pay with Sardis.
            </h2>
            <p
              className="max-w-[440px] font-light mb-10"
              style={{
                fontFamily: "'Inter', sans-serif",
                fontSize: '15px',
                lineHeight: '24px',
                color: 'var(--landing-text-tertiary)',
              }}
            >
              A stablecoin-native checkout that costs merchants 0%. Embed a button,
              accept USDC on Base, settle instantly. Customers pay from wallet or buy
              USDC with card — zero fee via Coinbase Onramp.
            </p>

            {/* Benefits grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {benefits.map((b) => (
                <div
                  key={b.title}
                  className="flex flex-col gap-2.5 rounded-[14px] p-5"
                  style={{
                    backgroundColor: 'var(--landing-surface)',
                    border: '1px solid var(--landing-border)',
                  }}
                >
                  <div style={{ color: 'var(--landing-accent)' }}>{b.icon}</div>
                  <h3
                    style={{
                      fontFamily: "'Space Grotesk', sans-serif",
                      fontWeight: 600,
                      fontSize: '15px',
                      color: 'var(--landing-text-primary)',
                    }}
                  >
                    {b.title}
                  </h3>
                  <p
                    className="font-light"
                    style={{
                      fontFamily: "'Inter', sans-serif",
                      fontSize: '13px',
                      lineHeight: '20px',
                      color: 'var(--landing-text-tertiary)',
                    }}
                  >
                    {b.desc}
                  </p>
                </div>
              ))}
            </div>

            {/* Embed code snippet */}
            <div className="mt-6">
              <span
                className="text-[10px] uppercase tracking-wider mb-2 block"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
              >
                Embed in one line
              </span>
              <div
                className="rounded-lg px-4 py-3 w-fit flex items-center gap-3"
                style={{
                  backgroundColor: 'var(--landing-code-bg)',
                  border: '1px solid var(--landing-border)',
                }}
              >
                <span
                  className="text-[12px]"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    color: 'var(--landing-text-secondary)',
                  }}
                >
                  {'<sardis-pay client-secret="cs_..." />'}
                </span>
                <button
                  onClick={() => navigator.clipboard.writeText('<sardis-pay client-secret="cs_..." />')}
                  className="flex-shrink-0 opacity-40 hover:opacity-80 transition-opacity"
                  style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
                  aria-label="Copy to clipboard"
                >
                  <svg width="14" height="14" viewBox="0 0 16 16" fill="none">
                    <rect x="5" y="5" width="9" height="9" rx="1.5" stroke="var(--landing-text-secondary)" strokeWidth="1.2" />
                    <path d="M11 5V3.5A1.5 1.5 0 009.5 2h-6A1.5 1.5 0 002 3.5v6A1.5 1.5 0 003.5 11H5" stroke="var(--landing-text-secondary)" strokeWidth="1.2" />
                  </svg>
                </button>
              </div>
            </div>
          </div>

          {/* Right: checkout mockup */}
          <div className="hidden lg:flex flex-shrink-0 justify-center items-start lg:pt-8">
            <motion.div
              animate={{ y: [0, -8, 0] }}
              transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
            >
              <CheckoutMockup />
            </motion.div>
          </div>
        </div>
      </div>
    </section>
  );
}
