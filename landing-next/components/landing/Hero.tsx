"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

/* ---- Mock transaction data ---- */

const MOCK_TXS = [
  {
    desc: "SaaS subscription",
    amount: "-$45.00",
    status: "allow",
    time: "2m ago",
    icon: "S",
  },
  {
    desc: "Cloud compute",
    amount: "-$127.50",
    status: "block",
    time: "5m ago",
    icon: "C",
  },
  {
    desc: "Dev tools",
    amount: "-$19.00",
    status: "allow",
    time: "12m ago",
    icon: "D",
  },
];

function WalletScreen() {
  return (
    <>
      <div className="px-6 pt-2 pb-4">
        <div className="flex items-center justify-between mb-1">
          <span
            style={{ color: "#808080", fontSize: 12, letterSpacing: "0.05em" }}
          >
            AGENT WALLET
          </span>
          <div className="flex items-center gap-1.5">
            <div
              className="w-1.5 h-1.5 rounded-full"
              style={{ background: "#22C55E" }}
            />
            <span
              style={{
                color: "#22C55E",
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              active
            </span>
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span
            style={{
              color: "#F5F5F5",
              fontSize: 40,
              fontWeight: 600,
              fontFamily: "'Space Grotesk', sans-serif",
              letterSpacing: "-0.03em",
            }}
          >
            $2,847
          </span>
          <span style={{ color: "#505460", fontSize: 16, fontWeight: 500 }}>
            .50
          </span>
        </div>
        <span
          style={{
            color: "#505460",
            fontSize: 12,
            fontFamily: "'JetBrains Mono', monospace",
          }}
        >
          2,847.50 USDC on Base
        </span>
      </div>

      <div className="px-5 pb-2">
        <div className="flex items-center justify-between mb-2">
          <span
            style={{ color: "#808080", fontSize: 11, letterSpacing: "0.05em" }}
          >
            RECENT
          </span>
        </div>
        {MOCK_TXS.map((tx, i) => (
          <div
            key={i}
            className="flex items-center gap-3 py-2.5"
            style={{
              borderTop:
                i > 0 ? "1px solid rgba(255,255,255,0.04)" : "none",
            }}
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-medium"
              style={{
                background:
                  tx.status === "allow"
                    ? "rgba(59,130,246,0.1)"
                    : "rgba(239,68,68,0.1)",
                color: tx.status === "allow" ? "#3B82F6" : "#EF4444",
              }}
            >
              {tx.icon}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span
                  style={{ color: "#E0E0E0", fontSize: 13, fontWeight: 500 }}
                >
                  {tx.desc}
                </span>
                <span
                  className="text-[9px] px-1.5 py-0.5 rounded font-medium"
                  style={{
                    fontFamily: "'JetBrains Mono', monospace",
                    background:
                      tx.status === "allow"
                        ? "rgba(34,197,94,0.1)"
                        : "rgba(239,68,68,0.1)",
                    color: tx.status === "allow" ? "#22C55E" : "#EF4444",
                  }}
                >
                  {tx.status === "allow" ? "ALLOW" : "BLOCK"}
                </span>
              </div>
              <span style={{ color: "#505460", fontSize: 11 }}>{tx.time}</span>
            </div>
            <span
              style={{
                color: tx.status === "allow" ? "#A0A0AA" : "#EF4444",
                fontSize: 13,
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: 500,
                textDecoration:
                  tx.status === "block" ? "line-through" : "none",
                opacity: tx.status === "block" ? 0.5 : 1,
              }}
            >
              {tx.amount}
            </span>
          </div>
        ))}
      </div>
    </>
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
        <span
          style={{ color: "#808080", fontSize: 11, letterSpacing: "0.05em" }}
        >
          ACTIVE POLICY
        </span>
        <span
          className="text-[9px] px-2 py-0.5 rounded-full font-medium"
          style={{
            fontFamily: "'JetBrains Mono', monospace",
            background: "rgba(34,197,94,0.1)",
            color: "#22C55E",
            border: "1px solid rgba(34,197,94,0.15)",
          }}
        >
          ENFORCED
        </span>
      </div>
      {rules.map((r, i) => (
        <div
          key={i}
          className="flex items-center gap-3 py-2.5"
          style={{
            borderTop:
              i > 0 ? "1px solid rgba(255,255,255,0.04)" : "none",
          }}
        >
          <div
            className="w-5 h-5 rounded flex items-center justify-center"
            style={{
              background: r.active
                ? "rgba(34,197,94,0.1)"
                : "rgba(255,255,255,0.04)",
            }}
          >
            {r.active ? (
              <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M2 5l2.5 2.5L8 3"
                  stroke="#22C55E"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            ) : (
              <svg
                width="10"
                height="10"
                viewBox="0 0 10 10"
                fill="none"
                aria-hidden="true"
              >
                <path
                  d="M3 5h4"
                  stroke="#505460"
                  strokeWidth="1.2"
                  strokeLinecap="round"
                />
              </svg>
            )}
          </div>
          <span
            style={{
              color: r.active ? "#E0E0E0" : "#505460",
              fontSize: 13,
              fontFamily: "'Inter', sans-serif",
            }}
          >
            {r.rule}
          </span>
        </div>
      ))}
    </div>
  );
}

const NAV_ITEMS = [
  {
    label: "Wallet",
    path: "M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
  },
  {
    label: "Policy",
    path: "M12 2L3 7v5c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z",
  },
];

const SCREENS: Record<string, () => React.JSX.Element> = {
  Wallet: WalletScreen,
  Policy: PolicyScreen,
};

function WalletMockup() {
  const [activeTab, setActiveTab] = useState("Wallet");
  const ActiveScreen = SCREENS[activeTab];

  return (
    <div
      className="relative w-[370px] select-none"
      style={{ fontFamily: "'Inter', sans-serif" }}
    >
      <div
        className="rounded-[28px] overflow-hidden"
        style={{
          background: "#0A0B0D",
          border: "1px solid rgba(255,255,255,0.08)",
          boxShadow:
            "0 25px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.03) inset",
        }}
      >
        {/* Status bar */}
        <div className="flex items-center justify-between px-6 pt-4 pb-2">
          <span
            style={{
              color: "#808080",
              fontFamily: "'JetBrains Mono', monospace",
              fontSize: 11,
            }}
          >
            9:41
          </span>
          <div className="flex items-center gap-1.5">
            <div
              className="w-4 h-2 rounded-sm"
              style={{ border: "1px solid #505460" }}
            >
              <div
                className="w-2.5 h-full rounded-sm"
                style={{ background: "#22C55E" }}
              />
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

        {/* Policy badge */}
        <div className="px-5 pb-3">
          <div
            className="flex items-center gap-2 rounded-lg px-3 py-2"
            style={{
              background: "rgba(34,197,94,0.06)",
              border: "1px solid rgba(34,197,94,0.12)",
            }}
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 14 14"
              fill="none"
              aria-hidden="true"
            >
              <path
                d="M7 1L12 3.5V6.5C12 9.5 9.5 12 7 13C4.5 12 2 9.5 2 6.5V3.5L7 1Z"
                stroke="#22C55E"
                strokeWidth="1.2"
                fill="none"
              />
              <path
                d="M5 7L6.5 8.5L9 5.5"
                stroke="#22C55E"
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span
              style={{
                color: "#22C55E",
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
            >
              Policy: Max $500/tx, SaaS only, weekdays
            </span>
          </div>
        </div>

        {/* Bottom nav */}
        <div
          className="flex items-center justify-around px-6 py-3 mt-1"
          style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}
        >
          {NAV_ITEMS.map((item) => (
            <button
              key={item.label}
              onClick={() => setActiveTab(item.label)}
              className="flex flex-col items-center gap-1 transition-colors min-w-[44px] min-h-[44px] justify-center"
              style={{
                background: "none",
                border: "none",
                cursor: "pointer",
                padding: 0,
              }}
              aria-label={`View ${item.label} tab`}
              aria-selected={activeTab === item.label}
            >
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke={
                  activeTab === item.label ? "#3B82F6" : "#505460"
                }
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d={item.path} />
              </svg>
              <span
                style={{
                  fontSize: 9,
                  color:
                    activeTab === item.label ? "#3B82F6" : "#505460",
                }}
              >
                {item.label}
              </span>
            </button>
          ))}
        </div>

        {/* Home indicator */}
        <div className="flex justify-center pb-2 pt-1">
          <div
            className="w-28 h-1 rounded-full"
            style={{ background: "rgba(255,255,255,0.15)" }}
          />
        </div>
      </div>
    </div>
  );
}

/* ---- Hero Component ---- */

export default function Hero() {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText("pip install sardis");
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section className="w-full" style={{ backgroundColor: "var(--landing-bg)" }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-16 pb-12 lg:pt-[100px] lg:pb-16 flex flex-col lg:flex-row lg:items-center lg:gap-[60px]">
        {/* Left Column */}
        <div className="flex-shrink-0 lg:max-w-[540px] w-full">
          <p
            className="uppercase tracking-[0.15em] mb-4 font-medium"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "12px",
              color: "var(--landing-accent)",
            }}
          >
            AI Agent Payment Infrastructure
          </p>
          <h1
            className="font-bold tracking-[-0.04em] mb-6"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: "clamp(36px, 5vw, 64px)",
              lineHeight: "clamp(40px, 5.5vw, 70px)",
              color: "var(--landing-text-primary)",
            }}
          >
            AI agents can reason. They cannot be trusted with money.
          </h1>

          <p
            className="font-light mb-10"
            style={{
              fontFamily: "'Inter', sans-serif",
              fontSize: "clamp(15px, 1.8vw, 17px)",
              lineHeight: "clamp(24px, 2.8vw, 28px)",
              color: "var(--landing-text-secondary)",
            }}
          >
            Sardis is the control plane for autonomous financial execution.
            Natural language policies, kill switches, approval workflows, and
            cryptographic evidence -- so your agents can make real transactions
            safely.
          </p>

          {/* CTA Row */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4 mb-6">
            <a
              href="https://dashboard.sardis.sh/signup"
              className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] whitespace-nowrap text-center inline-block hover:opacity-90"
              style={{
                fontFamily: "'Inter', sans-serif",
                backgroundColor: "var(--landing-accent)",
              }}
            >
              Get Started Free
            </a>
            <a
              href="mailto:contact@sardis.sh"
              className="rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] whitespace-nowrap text-center inline-block hover:border-[var(--landing-text-muted)] hover:text-[var(--landing-text-primary)]"
              style={{
                fontFamily: "'Inter', sans-serif",
                border: "1px solid var(--landing-border)",
                color: "var(--landing-text-secondary)",
              }}
            >
              Book a Demo &rarr;
            </a>
          </div>

          {/* Install command */}
          <div
            className="flex items-center gap-3 rounded-lg px-4 py-3 w-fit"
            style={{
              backgroundColor: "var(--landing-code-bg)",
              border: "1px solid var(--landing-border)",
            }}
          >
            <span
              className="text-[13px]"
              style={{
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                color: "var(--landing-text-secondary)",
              }}
            >
              pip install sardis
            </span>
            <button
              onClick={handleCopy}
              className="transition-colors ml-2 flex items-center"
              style={{ color: "var(--landing-text-muted)" }}
              aria-label="Copy install command"
            >
              {copied ? (
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 15 15"
                  fill="none"
                >
                  <path
                    d="M2 8L6 12L13 4"
                    stroke="#22C55E"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                <svg
                  width="15"
                  height="15"
                  viewBox="0 0 15 15"
                  fill="none"
                >
                  <rect
                    x="5"
                    y="5"
                    width="8"
                    height="8"
                    rx="1.5"
                    stroke="currentColor"
                    strokeWidth="1.2"
                  />
                  <path
                    d="M3 9.5H2.5C1.94772 9.5 1.5 9.05228 1.5 8.5V2.5C1.5 1.94772 1.94772 1.5 2.5 1.5H8.5C9.05228 1.5 9.5 1.94772 9.5 2.5V3"
                    stroke="currentColor"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
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
