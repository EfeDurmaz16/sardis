"use client"

import { useState, useEffect, useRef } from "react"
import { useTheme } from "next-themes"
import { Plus_Jakarta_Sans } from "next/font/google"
import { motion } from "framer-motion"
import Link from "next/link"

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta" })

/* ── Scroll-triggered fade-up ── */
function useInView() {
  const ref = useRef<HTMLElement>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setInView(true); obs.disconnect() } },
      { threshold: 0.1 }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])
  return { ref, inView }
}

function Section({ children, className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return (
    <section className={className || ""} {...props}>
      {children}
    </section>
  )
}

/* ── Theme colors ── */
const light = {
  bg: "#FDFBF7",
  text: "#1A1614",
  textMuted: "rgba(26,22,20,0.45)",
  textFaint: "rgba(26,22,20,0.35)",
  textGhost: "rgba(26,22,20,0.2)",
  textLabel: "rgba(26,22,20,0.3)",
  border: "rgba(26,22,20,0.06)",
  borderStrong: "rgba(26,22,20,0.1)",
  cardBg: "#FDFBF7",
  shellBg: "rgba(26,22,20,0.03)",
  shellBorder: "rgba(26,22,20,0.06)",
  navBg: "rgba(26,22,20,0.04)",
  navBorder: "rgba(26,22,20,0.06)",
  btnBg: "#1A1614",
  btnText: "#FDFBF7",
  btnIconBg: "rgba(253,251,247,0.12)",
  sectionAlt: "rgba(26,22,20,0.02)",
  success: "#22C55E",
  terminalBg: "#1A1614",
  terminalBorder: "rgba(255,255,255,0.06)",
  terminalCode: "rgba(255,255,255,0.4)",
  terminalMuted: "rgba(255,255,255,0.3)",
  terminalDim: "rgba(255,255,255,0.2)",
  terminalInnerText: "#FDFBF7",
}

const dark = {
  bg: "#0A0A0F",
  text: "#FDFBF7",
  textMuted: "rgba(253,251,247,0.4)",
  textFaint: "rgba(253,251,247,0.3)",
  textGhost: "rgba(253,251,247,0.2)",
  textLabel: "rgba(253,251,247,0.25)",
  border: "rgba(253,251,247,0.04)",
  borderStrong: "rgba(253,251,247,0.08)",
  cardBg: "#0A0A0F",
  shellBg: "rgba(253,251,247,0.03)",
  shellBorder: "rgba(253,251,247,0.05)",
  navBg: "rgba(255,255,255,0.03)",
  navBorder: "rgba(255,255,255,0.06)",
  btnBg: "#FDFBF7",
  btnText: "#0A0A0F",
  btnIconBg: "rgba(10,10,15,0.08)",
  sectionAlt: "rgba(253,251,247,0.02)",
  success: "#22C55E",
  terminalBg: "#12121A",
  terminalBorder: "rgba(253,251,247,0.04)",
  terminalCode: "rgba(253,251,247,0.35)",
  terminalMuted: "rgba(253,251,247,0.25)",
  terminalDim: "rgba(253,251,247,0.2)",
  terminalInnerText: "#0A0A0F",
}

/* ── Sardis Logo SVG ── */
function SardisLogo({ color, size = 20 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <path d="M20 5H10a7 7 0 000 14h2" stroke={color} strokeWidth="3" strokeLinecap="round" fill="none" />
      <path d="M8 23h10a7 7 0 000-14h-2" stroke={color} strokeWidth="3" strokeLinecap="round" fill="none" />
    </svg>
  )
}

/* ── Button-in-Button CTA ── */
function PrimaryCTA({ label, t, slide }: { label: string; t: typeof light; slide?: boolean }) {
  const [slid, setSlid] = useState(false)

  if (slide) {
    return (
      <>
        <style>{`
          .sardis-slide-track { position: relative; border-radius: 100px; cursor: pointer; overflow: hidden; }
          .sardis-slide-pill { transition: transform 500ms cubic-bezier(0.32,0.72,0,1); }
          .sardis-slide-pill.slid { transform: translateX(calc(150%)); }
          .sardis-slide-pill .sardis-arrow { transition: transform 300ms cubic-bezier(0.32,0.72,0,1); }
          .sardis-slide-track:hover .sardis-arrow { transform: translateX(3px); }
          .sardis-slide-track:hover .sardis-slide-pill:not(.slid) { transform: translateX(4px); }
          .sardis-btn { transition: transform 250ms cubic-bezier(0.32,0.72,0,1); cursor: pointer; }
          .sardis-btn:hover { transform: scale(1.04); }
          .sardis-btn:active { transform: scale(0.96); }
          .sardis-btn:hover .sardis-btn-icon { transform: translateX(2px) scale(1.08); }
          .sardis-btn-icon { transition: transform 250ms cubic-bezier(0.32,0.72,0,1); }
        `}</style>
        <div
          className="sardis-slide-track"
          style={{ display: "inline-flex", padding: 4, background: `${t.text}06`, border: `1px solid ${t.text}0A`, borderRadius: 100, width: "100%" }}
          onClick={() => { setSlid(true); setTimeout(() => setSlid(false), 1200) }}
        >
          <div
            className={`sardis-slide-pill ${slid ? "slid" : ""}`}
            style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 8px 12px 24px", background: t.btnBg, borderRadius: 100 }}
          >
            <span className={jakarta.className} style={{ fontSize: 14, fontWeight: 500, color: t.btnText }}>{label}</span>
            <div className="sardis-arrow" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 26, height: 26, borderRadius: "50%", background: t.btnIconBg }}>
              <span style={{ fontSize: 13, color: t.btnText }}>→</span>
            </div>
          </div>
        </div>
      </>
    )
  }

  return (
    <div
      className="sardis-btn"
      style={{ display: "inline-flex", padding: "2px", background: `${t.text}08`, border: `1px solid ${t.text}14`, borderRadius: 100 }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "14px 8px 14px 28px", background: t.btnBg, borderRadius: 100 }}>
        <span className={jakarta.className} style={{ fontSize: 15, fontWeight: 500, color: t.btnText }}>{label}</span>
        <div className="sardis-btn-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 28, height: 28, borderRadius: "50%", background: t.btnIconBg }}>
          <span style={{ fontSize: 14, color: t.btnText }}>→</span>
        </div>
      </div>
    </div>
  )
}

function GhostCTA({ label, t }: { label: string; t: typeof light }) {
  return (
    <div className="sardis-btn" style={{ display: "flex", alignItems: "center", padding: "16px 24px", border: `1px solid ${t.borderStrong}`, borderRadius: 100, cursor: "pointer" }}>
      <span style={{ fontSize: 15, color: t.textMuted }}>{label}</span>
    </div>
  )
}

/* ── Eyebrow Label ── */
function Eyebrow({ text, t }: { text: string; t: typeof light }) {
  return (
    <span style={{ fontFamily: "var(--font-geist-sans)", fontSize: 11, fontWeight: 500, color: t.textFaint, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>{text}</span>
  )
}

/* ── Double-Bezel Card ── */
function BezelCard({ children, t }: { children: React.ReactNode; t: typeof light }) {
  return (
    <div style={{ display: "flex", flex: 1, padding: 2, background: t.shellBg, border: `1px solid ${t.shellBorder}`, borderRadius: 20 }}>
      <div style={{ display: "flex", flexDirection: "column" as const, gap: 14, padding: 28, background: t.cardBg, borderRadius: 18, flex: 1 }}>
        {children}
      </div>
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════════
   MAIN PAGE
   ════════════════════════════════════════════════════════════════════ */

export default function LandingPage() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => setMounted(true), [])

  const isDark = mounted && resolvedTheme === "dark"
  const t = isDark ? dark : light

  const codeLines = `from sardis import Sardis

client = Sardis(api_key="sk_demo_live_redacted")

agent = client.agents.create(
    name="Procurement Bot",
    chain="base",
    limit_per_tx="100.00",
)

payment = client.pay(
    agent_id=agent.id,
    amount="49.99",
    merchant="openai",
    purpose="inference credits",
)`

  return (
    <div className={jakarta.variable} style={{ background: t.bg, color: t.text, minHeight: "100vh" }}>

      {/* ═══ NAVBAR ═══ */}
      <nav style={{ display: "flex", justifyContent: "center", padding: "24px 56px 0" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", maxWidth: 1100, padding: "12px 8px 12px 24px", background: t.navBg, border: `1px solid ${t.navBorder}`, borderRadius: 100 }}>
          <Link href="/landing" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <SardisLogo color={t.text} />
            <span className={jakarta.className} style={{ fontSize: 15, fontWeight: 700, color: t.text, letterSpacing: "-0.02em" }}>Sardis</span>
          </Link>
          <div style={{ display: "flex", gap: 32 }}>
            {["Product", "Developers", "Security", "Pricing", "Docs"].map((l) => (
              <span key={l} style={{ fontSize: 13, color: t.textMuted, cursor: "pointer" }}>{l}</span>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <span style={{ fontSize: 13, color: t.textMuted, cursor: "pointer" }}>Sign in</span>
            {mounted && (
              <button
                onClick={() => setTheme(isDark ? "light" : "dark")}
                style={{ fontSize: 13, color: t.textMuted, background: "none", border: "none", cursor: "pointer", padding: "4px 8px" }}
              >
                {isDark ? "☀" : "☾"}
              </button>
            )}
            <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 6px 8px 18px", background: t.btnBg, borderRadius: 100, cursor: "pointer" }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: t.btnText }}>Get started</span>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, borderRadius: "50%", background: t.btnIconBg }}>
                <span style={{ fontSize: 12, color: t.btnText }}>→</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      {/* ═══ HERO ═══ */}
      <Section style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "120px 56px 80px", gap: 40 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 16px 6px 10px", background: `${t.text}06`, border: `1px solid ${t.text}14`, borderRadius: 100 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: t.success }} />
          <span style={{ fontSize: 12, fontWeight: 500, color: t.textMuted, letterSpacing: "0.04em" }}>Now in Public Beta</span>
        </div>
        <h1 className={jakarta.className} style={{ fontSize: 80, fontWeight: 800, color: t.text, lineHeight: "82px", letterSpacing: "-0.05em", textAlign: "center", maxWidth: 900 }}>
          Safe payments<br />for AI agents.
        </h1>
        <p style={{ fontSize: 18, color: t.textMuted, lineHeight: "28px", textAlign: "center", maxWidth: 520 }}>
          Set spending rules, enforce compliance guardrails, and let your agents transact autonomously. Every payment verified.
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 14, paddingTop: 8 }}>
          <PrimaryCTA label="Get started free" t={t} />
          <GhostCTA label="Read the docs" t={t} />
        </div>
      </Section>

      {/* ═══ CODE TERMINAL (Z-Axis Cascade) ═══ */}
      <Section style={{ display: "flex", justifyContent: "center", padding: "0 56px 60px", position: "relative", height: 480, overflow: "hidden" }}>
        {/* Shadow card */}
        <div style={{ position: "absolute", left: "50%", top: 20, transform: "translateX(-48%) rotate(-2deg)", width: 560, padding: 2, background: t.shellBg, border: `1px solid ${t.shellBorder}`, borderRadius: 24 }}>
          <div style={{ background: isDark ? "#12121A" : "#F5F2ED", borderRadius: 22, height: 440 }} />
        </div>
        {/* Main terminal */}
        <div style={{ position: "absolute", left: "50%", top: 0, transform: "translateX(-52%) rotate(1deg)", width: 560, display: "flex", flexDirection: "column", padding: 2, background: isDark ? "rgba(253,251,247,0.05)" : "rgba(26,22,20,0.06)", border: `1px solid ${isDark ? "rgba(253,251,247,0.08)" : "rgba(26,22,20,0.1)"}`, borderRadius: 24, boxShadow: "0 24px 64px rgba(0,0,0,0.08)" }}>
          <div style={{ display: "flex", flexDirection: "column", background: t.terminalBg, borderRadius: 22, overflow: "hidden" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", borderBottom: `1px solid ${t.terminalBorder}` }}>
              <div style={{ display: "flex", gap: 7 }}>
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#FF5F57" }} />
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#FEBC2E" }} />
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#28C840" }} />
              </div>
              <span style={{ fontFamily: "var(--font-geist-mono)", fontSize: 11, color: t.terminalMuted }}>quickstart.py</span>
              <div style={{ padding: "3px 10px", border: `1px solid ${t.terminalBorder}`, borderRadius: 6 }}>
                <span style={{ fontSize: 10, fontWeight: 500, color: t.terminalMuted }}>Python</span>
              </div>
            </div>
            <pre style={{ fontFamily: "var(--font-geist-mono)", fontSize: 13, lineHeight: "24px", color: t.terminalCode, whiteSpace: "pre", padding: 24, margin: 0 }}>
              {codeLines}
            </pre>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "12px 20px", borderTop: `1px solid ${t.terminalBorder}` }}>
              <span style={{ fontFamily: "var(--font-geist-mono)", fontSize: 10, color: t.terminalDim }}>✓ policy verified · compliance passed</span>
              <span style={{ fontFamily: "var(--font-geist-mono)", fontSize: 12, fontWeight: 600, color: t.success }}>12ms</span>
            </div>
          </div>
        </div>
      </Section>

      {/* ═══ LOGO STRIP ═══ */}
      <Section style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "48px 56px", gap: 28, borderTop: `1px solid ${t.border}`, borderBottom: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 48 }}>
          <Eyebrow text="Early partners" t={t} />
          <span className={jakarta.className} style={{ fontSize: 16, fontWeight: 700, color: t.textGhost }}>Stripe</span>
          <span className={jakarta.className} style={{ fontSize: 16, fontWeight: 700, color: t.textGhost }}>Bridge</span>
          <span className={jakarta.className} style={{ fontSize: 16, fontWeight: 700, color: t.textGhost }}>Base</span>
          <span className={jakarta.className} style={{ fontSize: 16, fontWeight: 700, color: t.textGhost }}>Tempo</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 48 }}>
          <Eyebrow text="Live integrations" t={t} />
          <span className={jakarta.className} style={{ fontSize: 16, fontWeight: 700, color: t.textGhost }}>AutoGPT</span>
          <span className={jakarta.className} style={{ fontSize: 16, fontWeight: 700, color: t.textGhost }}>Activepieces</span>
        </div>
      </Section>

      {/* ═══ PROBLEM ═══ */}
      <Section style={{ padding: "120px 56px", display: "flex", flexDirection: "column", gap: 56 }}>
        <div style={{ display: "flex", gap: 80 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 20, flex: 1 }}>
            <Eyebrow text="The problem" t={t} />
            <h2 className={jakarta.className} style={{ fontSize: 44, fontWeight: 800, lineHeight: "48px", letterSpacing: "-0.04em" }}>
              AI agents are getting smarter. They still can&apos;t spend safely.
            </h2>
            <p style={{ fontSize: 15, color: t.textMuted, lineHeight: "24px", maxWidth: 400 }}>
              Autonomy removes the human checkpoint. Without a payment layer that enforces rules, one bad prompt can move real money.
            </p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
            {[
              { num: "01", label: "Autonomy gap", desc: "Agents can decide before your stack can object." },
              { num: "02", label: "Control problem", desc: "Finance needs limits and approvals agents can follow." },
              { num: "03", label: "Security gap", desc: "Without verification, one bad prompt can move real money." },
            ].map((item, i) => (
              <div key={i} style={{ display: "flex", flexDirection: "column", gap: 8, padding: "28px 0", borderBottom: i < 2 ? `1px solid ${t.border}` : "none" }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>{item.num}. {item.label}</span>
                <span className={jakarta.className} style={{ fontSize: 19, fontWeight: 600, lineHeight: "27px", letterSpacing: "-0.02em" }}>{item.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══ HOW IT WORKS ═══ */}
      <Section style={{ padding: "120px 56px", display: "flex", flexDirection: "column", gap: 48, background: t.sectionAlt }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Eyebrow text="How it works" t={t} />
            <h2 className={jakarta.className} style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: "42px" }}>
              Three layers between intent<br />and money movement.
            </h2>
          </div>
          <span style={{ fontSize: 13, color: t.textLabel }}>Define. Send. Verify.</span>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          {[
            { num: "01", label: "Set rules", title: "Budgets, merchants, and fallback logic in one policy layer.", desc: "Per-tx limits, daily caps, approved merchants, approval thresholds." },
            { num: "02", label: "Agents transact", title: "Requests carry purpose, counterparty, and policy context.", desc: "Structured intent — who, what, why — evaluated before execution." },
            { num: "03", label: "Everything verified", title: "Sardis signs execution and emits an audit-grade event.", desc: "Cryptographic receipts, on-chain settlement, replay-safe webhooks." },
          ].map((step) => (
            <BezelCard key={step.num} t={t}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 36, height: 36, borderRadius: 10, background: `${t.text}08`, border: `1px solid ${t.text}0F` }}>
                <span className={jakarta.className} style={{ fontSize: 14, fontWeight: 800, color: t.text }}>{step.num}</span>
              </div>
              <span style={{ fontSize: 12, fontWeight: 600, color: t.textLabel, letterSpacing: "0.06em", textTransform: "uppercase" as const }}>{step.label}</span>
              <span className={jakarta.className} style={{ fontSize: 17, fontWeight: 600, lineHeight: "24px" }}>{step.title}</span>
              <span style={{ fontSize: 13, color: t.textFaint, lineHeight: "20px" }}>{step.desc}</span>
            </BezelCard>
          ))}
        </div>
      </Section>

      {/* ═══ FEATURES BENTO ═══ */}
      <Section style={{ padding: "120px 56px", display: "flex", flexDirection: "column", gap: 40 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Eyebrow text="Features" t={t} />
          <h2 className={jakarta.className} style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: "42px" }}>
            The control plane for money<br />inside agent systems.
          </h2>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div style={{ display: "flex", gap: 12 }}>
            <BezelCard t={t}>
              <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>SDKs</span>
              <span className={jakarta.className} style={{ fontSize: 19, fontWeight: 600 }}>Python and TypeScript clients for policy and authorizations.</span>
              <div style={{ display: "flex", gap: 8, paddingTop: 12 }}>
                <code style={{ padding: "4px 10px", background: `${t.text}06`, border: `1px solid ${t.text}0F`, borderRadius: 6, fontFamily: "var(--font-geist-mono)", fontSize: 11, color: t.textFaint }}>pip install sardis</code>
                <code style={{ padding: "4px 10px", background: `${t.text}06`, border: `1px solid ${t.text}0F`, borderRadius: 6, fontFamily: "var(--font-geist-mono)", fontSize: 11, color: t.textFaint }}>npm i @sardis/sdk</code>
              </div>
            </BezelCard>
            <BezelCard t={t}>
              <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>MCP tools</span>
              <span className={jakarta.className} style={{ fontSize: 19, fontWeight: 600 }}>Native MCP server for Claude, Cursor, and Windsurf.</span>
              <span style={{ fontSize: 13, color: t.textFaint, lineHeight: "20px" }}>Agents call Sardis tools natively.</span>
            </BezelCard>
          </div>
          <div style={{ display: "flex", gap: 12 }}>
            {[
              { label: "Frameworks", title: "CrewAI, LangChain, Vercel AI, custom runtimes." },
              { label: "Multi-chain", title: "Stablecoin settlement on Base, Polygon, Arbitrum." },
              { label: "Sandbox", title: "Test prompts and policies before funds move." },
            ].map((f) => (
              <BezelCard key={f.label} t={t}>
                <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>{f.label}</span>
                <span className={jakarta.className} style={{ fontSize: 17, fontWeight: 600 }}>{f.title}</span>
              </BezelCard>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══ ENTERPRISE ═══ */}
      <Section style={{ display: "flex", padding: "120px 56px", gap: 80, borderTop: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
          <Eyebrow text="Enterprise" t={t} />
          <h2 className={jakarta.className} style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: "42px" }}>
            Compliance your finance team can trust.
          </h2>
          <p style={{ fontSize: 15, color: t.textMuted, lineHeight: "24px", maxWidth: 380 }}>
            KYC, sanctions, audit trails, and kill switches.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
          {[
            { label: "KYC-linked identity", status: "active" },
            { label: "Sanctions screening", status: "clear" },
            { label: "Audit trail", status: "recorded" },
            { label: "Agent kill switch", status: "armed" },
          ].map((item, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "20px 0", borderBottom: i < 3 ? `1px solid ${t.border}` : "none" }}>
              <span style={{ fontSize: 15, color: t.textMuted }}>{item.label}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: t.success }}>{item.status}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══ PRICING ═══ */}
      <Section style={{ padding: "120px 56px", display: "flex", flexDirection: "column", gap: 48, background: t.sectionAlt }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Eyebrow text="Pricing" t={t} />
            <h2 className={jakarta.className} style={{ fontSize: 38, fontWeight: 800, letterSpacing: "-0.035em", lineHeight: "42px" }}>
              Start free. Add control<br />as spending gets real.
            </h2>
          </div>
          <span style={{ fontSize: 13, color: t.textLabel }}>Three tiers, less complexity.</span>
        </div>
        <div style={{ display: "flex", gap: 16 }}>
          {/* Free */}
          <div style={{ display: "flex", flexDirection: "column", flex: 1, padding: 32, gap: 24, border: `1px solid ${t.border}`, borderRadius: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>Free</span>
              <span className={jakarta.className} style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.03em" }}>$0</span>
              <span style={{ fontSize: 13, color: t.textFaint }}>Internal testing.</span>
            </div>
            <div style={{ height: 1, background: t.border }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {["Sandbox", "SDK access", "Basic policy"].map((f) => (
                <span key={f} style={{ fontSize: 13, color: t.textMuted }}>{f}</span>
              ))}
            </div>
            <GhostCTA label="Get started" t={t} />
          </div>
          {/* Pro — Double Bezel */}
          <div style={{ display: "flex", flexDirection: "column", flex: 1, padding: 2, background: `${t.text}0F`, border: `1px solid ${t.text}1A`, borderRadius: 22 }}>
            <div style={{ display: "flex", flexDirection: "column", flex: 1, padding: 32, gap: 24, background: t.cardBg, borderRadius: 20, boxShadow: isDark ? "inset 0 1px 0 rgba(253,251,247,0.04)" : "0 8px 32px rgba(26,22,20,0.06)" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: t.text, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>Pro</span>
                <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <span className={jakarta.className} style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.03em" }}>$49</span>
                  <span style={{ fontSize: 13, color: t.textFaint }}>/ month</span>
                </div>
                <span style={{ fontSize: 13, color: t.textFaint }}>Production teams.</span>
              </div>
              <div style={{ height: 1, background: t.border }} />
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {["Production API", "MCP + frameworks", "Audit events + webhooks", "Multi-chain settlement"].map((f) => (
                  <span key={f} style={{ fontSize: 13, color: t.textMuted }}>{f}</span>
                ))}
              </div>
              <PrimaryCTA label="Start Pro" t={t} slide />
            </div>
          </div>
          {/* Enterprise */}
          <div style={{ display: "flex", flexDirection: "column", flex: 1, padding: 32, gap: 24, border: `1px solid ${t.border}`, borderRadius: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>Enterprise</span>
              <span className={jakarta.className} style={{ fontSize: 44, fontWeight: 800, letterSpacing: "-0.03em" }}>Custom</span>
              <span style={{ fontSize: 13, color: t.textFaint }}>Regulated workflows.</span>
            </div>
            <div style={{ height: 1, background: t.border }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {["KYC + sanctions", "Policy review", "SLAs + support"].map((f) => (
                <span key={f} style={{ fontSize: 13, color: t.textMuted }}>{f}</span>
              ))}
            </div>
            <GhostCTA label="Talk to sales" t={t} />
          </div>
        </div>
      </Section>

      {/* ═══ FINAL CTA ═══ */}
      <Section style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "120px 56px", borderTop: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 600 }}>
          <Eyebrow text="Safe by design" t={t} />
          <h2 className={jakarta.className} style={{ fontSize: 48, fontWeight: 800, letterSpacing: "-0.04em", lineHeight: "52px" }}>
            Sardis is how they earn your trust.
          </h2>
          <p style={{ fontSize: 15, color: t.textMuted, lineHeight: "24px" }}>
            Build agent payments with infrastructure-grade discipline.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 14 }}>
          <PrimaryCTA label="Get started" t={t} />
          <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "12px 22px", border: `1px solid ${t.borderStrong}`, borderRadius: 100, cursor: "pointer" }}>
            <span style={{ fontSize: 14, color: t.textMuted }}>Talk to sales</span>
            <span style={{ fontSize: 14, color: t.textGhost }}>↗</span>
          </div>
        </div>
      </Section>

      {/* ═══ FOOTER ═══ */}
      <footer style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "24px 56px", borderTop: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <SardisLogo color={t.textGhost} size={16} />
          <span style={{ fontSize: 12, color: t.textGhost }}>© 2026 Sardis. Payment OS for AI agents.</span>
        </div>
        <div style={{ display: "flex", gap: 24 }}>
          {["Product", "Docs", "Security", "Pricing", "Privacy", "Terms"].map((l) => (
            <span key={l} style={{ fontSize: 12, color: t.textLabel, cursor: "pointer" }}>{l}</span>
          ))}
        </div>
      </footer>

    </div>
  )
}
