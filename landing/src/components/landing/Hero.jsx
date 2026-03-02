import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/* ── Wallet Screens ───────────────────────────────────────────── */

const MOCK_TXS = [
  { desc: "SaaS subscription", amount: "-$45.00", status: "allow", time: "2m ago", icon: "S" },
  { desc: "Cloud compute", amount: "-$127.50", status: "block", time: "5m ago", icon: "C" },
  { desc: "Dev tools", amount: "-$19.00", status: "allow", time: "12m ago", icon: "D" },
];

function WalletScreen() {
  return (
    <>
      {/* Wallet header */}
      <div className="px-6 pt-2 pb-4">
        <div className="flex items-center justify-between mb-1">
          <span style={{ color: '#808080', fontSize: 12, letterSpacing: '0.05em' }}>AGENT WALLET</span>
          <div className="flex items-center gap-1.5">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: '#22C55E' }} />
            <span style={{ color: '#22C55E', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>active</span>
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span style={{ color: '#F5F5F5', fontSize: 40, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif", letterSpacing: '-0.03em' }}>$2,847</span>
          <span style={{ color: '#505460', fontSize: 16, fontWeight: 500 }}>.50</span>
        </div>
        <span style={{ color: '#505460', fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>2,847.50 USDC on Base</span>
      </div>

      {/* Recent transactions */}
      <div className="px-5 pb-2">
        <div className="flex items-center justify-between mb-2">
          <span style={{ color: '#808080', fontSize: 11, letterSpacing: '0.05em' }}>RECENT</span>
        </div>
        {MOCK_TXS.map((tx, i) => (
          <div key={i} className="flex items-center gap-3 py-2.5" style={{ borderTop: i > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-medium"
              style={{
                background: tx.status === 'allow' ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)',
                color: tx.status === 'allow' ? '#3B82F6' : '#EF4444',
              }}
            >
              {tx.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span style={{ color: '#E0E0E0', fontSize: 13, fontWeight: 500 }}>{tx.desc}</span>
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded font-medium"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    background: tx.status === 'allow' ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                    color: tx.status === 'allow' ? '#22C55E' : '#EF4444',
                  }}
                >
                  {tx.status === 'allow' ? 'ALLOW' : 'BLOCK'}
                </span>
              </div>
              <span style={{ color: '#505460', fontSize: 11 }}>{tx.time}</span>
            </div>
            <span style={{ color: tx.status === 'allow' ? '#A0A0AA' : '#EF4444', fontSize: 13, fontFamily: "'JetBrains Mono', monospace", fontWeight: 500, textDecoration: tx.status === 'block' ? 'line-through' : 'none', opacity: tx.status === 'block' ? 0.5 : 1 }}>{tx.amount}</span>
          </div>
        ))}
      </div>
    </>
  );
}

function CardsScreen() {
  return (
    <div className="px-5 pt-2 pb-4">
      {/* Virtual card */}
      <div
        className="rounded-2xl p-5 relative overflow-hidden mb-4"
        style={{
          background: 'linear-gradient(135deg, #1A1C24 0%, #111318 50%, #0D0F14 100%)',
          border: '1px solid rgba(59,130,246,0.15)',
        }}
      >
        <div className="absolute top-0 right-0 w-32 h-32 rounded-full" style={{ background: 'radial-gradient(circle, rgba(59,130,246,0.08) 0%, transparent 70%)' }} />
        <div className="absolute bottom-0 left-0 w-24 h-24 rounded-full" style={{ background: 'radial-gradient(circle, rgba(139,92,246,0.06) 0%, transparent 70%)' }} />

        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <rect width="24" height="24" rx="4" fill="#3B82F6" fillOpacity="0.15" />
              <path d="M6 9H18M6 15H18" stroke="#3B82F6" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
            <span style={{ color: '#A0A0AA', fontSize: 12, fontWeight: 500 }}>Sardis Virtual</span>
          </div>
          <span style={{ color: '#505460', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>VISA</span>
        </div>

        <div className="flex items-center gap-3 mb-5" style={{ fontFamily: "'JetBrains Mono', monospace", color: '#606070', fontSize: 14, letterSpacing: '0.15em' }}>
          <span>****</span><span>****</span><span>****</span>
          <span style={{ color: '#A0A0AA' }}>4242</span>
        </div>

        <div className="flex items-center justify-between">
          <div>
            <div style={{ color: '#505460', fontSize: 9, letterSpacing: '0.1em', marginBottom: 2 }}>CARDHOLDER</div>
            <div style={{ color: '#A0A0AA', fontSize: 12 }}>PROCUREMENT AGENT</div>
          </div>
          <div>
            <div style={{ color: '#505460', fontSize: 9, letterSpacing: '0.1em', marginBottom: 2 }}>EXPIRES</div>
            <div style={{ color: '#A0A0AA', fontSize: 12 }}>12/28</div>
          </div>
          <div className="w-8 h-6 rounded" style={{ background: 'linear-gradient(135deg, #C9A84C 0%, #D4B85A 50%, #B8942F 100%)', opacity: 0.7 }}>
            <div className="w-full h-full rounded" style={{ background: 'repeating-linear-gradient(90deg, transparent, transparent 2px, rgba(0,0,0,0.1) 2px, rgba(0,0,0,0.1) 4px)' }} />
          </div>
        </div>
      </div>

      {/* Card stats */}
      <div className="flex gap-3">
        <div className="flex-1 rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
          <div style={{ color: '#505460', fontSize: 9, letterSpacing: '0.05em', marginBottom: 4 }}>THIS MONTH</div>
          <div style={{ color: '#F5F5F5', fontSize: 16, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>$1,247</div>
        </div>
        <div className="flex-1 rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.04)' }}>
          <div style={{ color: '#505460', fontSize: 9, letterSpacing: '0.05em', marginBottom: 4 }}>LIMIT LEFT</div>
          <div style={{ color: '#22C55E', fontSize: 16, fontWeight: 600, fontFamily: "'Space Grotesk', sans-serif" }}>$3,753</div>
        </div>
      </div>
    </div>
  );
}

function PolicyScreen() {
  const rules = [
    { rule: "Max $500 per transaction", active: true },
    { rule: "SaaS & dev tools only", active: true },
    { rule: "Weekdays 9am-6pm", active: true },
    { rule: "No crypto exchanges", active: true },
    { rule: "Monthly cap: $5,000", active: false },
  ];
  return (
    <div className="px-5 pt-2 pb-4">
      <div className="flex items-center justify-between mb-4">
        <span style={{ color: '#808080', fontSize: 11, letterSpacing: '0.05em' }}>ACTIVE POLICY</span>
        <span
          className="text-[9px] px-2 py-0.5 rounded-full font-medium"
          style={{ fontFamily: "'JetBrains Mono', monospace", background: 'rgba(34,197,94,0.1)', color: '#22C55E', border: '1px solid rgba(34,197,94,0.15)' }}
        >
          ENFORCED
        </span>
      </div>
      {rules.map((r, i) => (
        <div key={i} className="flex items-center gap-3 py-2.5" style={{ borderTop: i > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
          <div
            className="w-5 h-5 rounded flex items-center justify-center"
            style={{ background: r.active ? 'rgba(34,197,94,0.1)' : 'rgba(255,255,255,0.04)' }}
          >
            {r.active ? (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M2 5l2.5 2.5L8 3" stroke="#22C55E" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            ) : (
              <svg width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M3 5h4" stroke="#505460" strokeWidth="1.2" strokeLinecap="round" /></svg>
            )}
          </div>
          <span style={{ color: r.active ? '#E0E0E0' : '#505460', fontSize: 13, fontFamily: "'Inter', sans-serif" }}>{r.rule}</span>
        </div>
      ))}
    </div>
  );
}

function AuditScreen() {
  const logs = [
    { action: "Payment approved", detail: "$45.00 USDC", time: "14:32", status: "ok" },
    { action: "Policy violation", detail: "$127.50 blocked", time: "14:28", status: "err" },
    { action: "Payment approved", detail: "$19.00 USDC", time: "14:15", status: "ok" },
    { action: "Wallet funded", detail: "+$500.00 USDC", time: "13:50", status: "ok" },
    { action: "Policy updated", detail: "Max $500/tx", time: "13:41", status: "ok" },
  ];
  return (
    <div className="px-5 pt-2 pb-4">
      <div className="flex items-center justify-between mb-3">
        <span style={{ color: '#808080', fontSize: 11, letterSpacing: '0.05em' }}>AUDIT LOG</span>
        <span style={{ color: '#505460', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>Merkle-anchored</span>
      </div>
      {logs.map((log, i) => (
        <div key={i} className="flex items-center gap-3 py-2" style={{ borderTop: i > 0 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}>
          <div
            className="w-1.5 h-1.5 rounded-full shrink-0"
            style={{ background: log.status === 'ok' ? '#22C55E' : '#EF4444' }}
          />
          <div className="flex-1 min-w-0">
            <span style={{ color: '#E0E0E0', fontSize: 12 }}>{log.action}</span>
            <span style={{ color: '#505460', fontSize: 11, marginLeft: 6 }}>{log.detail}</span>
          </div>
          <span style={{ color: '#505460', fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>{log.time}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Wallet Mockup ──────────────────────────────────────────────── */

const NAV_ITEMS = [
  { label: 'Wallet', path: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z' },
  { label: 'Cards', path: 'M2 5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5zM2 10h20' },
  { label: 'Policy', path: 'M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z' },
  { label: 'Audit', path: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M14 2v6h6 M16 13H8 M16 17H8 M10 9H8' },
];

const SCREENS = { Wallet: WalletScreen, Cards: CardsScreen, Policy: PolicyScreen, Audit: AuditScreen };

function WalletMockup() {
  const [activeTab, setActiveTab] = useState('Wallet');
  const ActiveScreen = SCREENS[activeTab];

  return (
    <div
      className="relative w-[370px] select-none"
      style={{ fontFamily: "'Inter', sans-serif" }}
    >
      <div
        className="rounded-[28px] overflow-hidden"
        style={{
          background: '#0A0B0D',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.03) inset',
        }}
      >
        {/* Status bar */}
        <div className="flex items-center justify-between px-6 pt-4 pb-2">
          <span style={{ color: '#808080', fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>9:41</span>
          <div className="flex items-center gap-1.5">
            <div className="w-4 h-2 rounded-sm" style={{ border: '1px solid #505460' }}>
              <div className="w-2.5 h-full rounded-sm" style={{ background: '#22C55E' }} />
            </div>
          </div>
        </div>

        {/* Screen content */}
        <div style={{ minHeight: 280 }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              transition={{ duration: 0.15 }}
            >
              <ActiveScreen />
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Policy badge (always visible) */}
        <div className="px-5 pb-3">
          <div
            className="flex items-center gap-2 rounded-lg px-3 py-2"
            style={{
              background: 'rgba(34,197,94,0.06)',
              border: '1px solid rgba(34,197,94,0.12)',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
              <path d="M7 1L12 3.5V6.5C12 9.5 9.5 12 7 13C4.5 12 2 9.5 2 6.5V3.5L7 1Z" stroke="#22C55E" strokeWidth="1.2" fill="none" />
              <path d="M5 7L6.5 8.5L9 5.5" stroke="#22C55E" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            <span style={{ color: '#22C55E', fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>Policy: Max $500/tx, SaaS only, weekdays</span>
          </div>
        </div>

        {/* Bottom nav - interactive */}
        <div className="flex items-center justify-around px-6 py-3 mt-1" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.label}
              onClick={() => setActiveTab(item.label)}
              className="flex flex-col items-center gap-1 transition-colors"
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={activeTab === item.label ? '#3B82F6' : '#505460'} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                <path d={item.path} />
              </svg>
              <span style={{ fontSize: 9, color: activeTab === item.label ? '#3B82F6' : '#505460' }}>{item.label}</span>
            </button>
          ))}
        </div>

        {/* Home indicator */}
        <div className="flex justify-center pb-2 pt-1">
          <div className="w-28 h-1 rounded-full" style={{ background: 'rgba(255,255,255,0.15)' }} />
        </div>
      </div>
    </div>
  );
}

/* ── Hero Component ─────────────────────────────────────────────── */

export default function Hero({ onOpenWaitlist }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText("pip install sardis");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="w-full" style={{ backgroundColor: 'var(--landing-bg)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-16 pb-12 lg:pt-[100px] lg:pb-16 flex flex-col lg:flex-row lg:items-center lg:gap-[60px]">
        {/* Left Column */}
        <div className="flex-shrink-0 lg:max-w-[540px] w-full">
          <h1
            className="font-bold tracking-[-0.04em] mb-6"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: "clamp(36px, 5vw, 64px)",
              lineHeight: "clamp(40px, 5.5vw, 70px)",
              color: 'var(--landing-text-primary)',
            }}
          >
            Give your agents guardrails for every dollar.
          </h1>

          <p
            className="font-light mb-10"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "clamp(15px, 1.8vw, 17px)",
              lineHeight: "clamp(24px, 2.8vw, 28px)",
              color: 'var(--landing-text-secondary)',
            }}
          >
            The payment layer for AI agents. Define spending policies in plain
            English, connect any agent, and let them transact safely across
            chains.
          </p>

          {/* CTA Row */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
            <button
              onClick={onOpenWaitlist}
              className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] whitespace-nowrap"
              style={{
                fontFamily: "'Inter', sans-serif",
                backgroundColor: 'var(--landing-accent)',
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--landing-accent-hover)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'var(--landing-accent)'}
            >
              Start Building Free
            </button>
          </div>

          {/* Install command */}
          <div
            className="flex items-center gap-3 rounded-lg px-4 py-3 w-fit"
            style={{
              backgroundColor: 'var(--landing-code-bg)',
              border: '1px solid var(--landing-border)',
            }}
          >
            <span
              className="text-[13px]"
              style={{
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                color: 'var(--landing-text-secondary)',
              }}
            >
              pip install sardis
            </span>
            <button
              onClick={handleCopy}
              className="transition-colors ml-2 flex items-center"
              style={{ color: 'var(--landing-text-muted)' }}
              onMouseEnter={(e) => e.currentTarget.style.color = 'var(--landing-text-secondary)'}
              onMouseLeave={(e) => e.currentTarget.style.color = 'var(--landing-text-muted)'}
              aria-label="Copy install command"
            >
              {copied ? (
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M2 8L6 12L13 4" stroke="#22C55E" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                <svg width="15" height="15" viewBox="0 0 15 15" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="5" y="5" width="8" height="8" rx="1.5" stroke="currentColor" strokeWidth="1.2" />
                  <path d="M3 9.5H2.5C1.94772 9.5 1.5 9.05228 1.5 8.5V2.5C1.5 1.94772 1.94772 1.5 2.5 1.5H8.5C9.05228 1.5 9.5 1.94772 9.5 2.5V3" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Right Column: Wallet Mockup */}
        <div className="hidden lg:flex flex-1 justify-center items-center">
          <motion.div
            animate={{ y: [0, -8, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          >
            <WalletMockup />
          </motion.div>
        </div>
      </div>
    </section>
  );
}
