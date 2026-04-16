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
function PrimaryCTA({ label, t, slide, href }: { label: string; t: typeof light; slide?: boolean; href?: string }) {
  const [slid, setSlid] = useState(false)
  const Tag = href ? "a" : "div"
  const linkProps = href ? { href, ...(href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {}) } : {}

  if (slide) {
    return (
      <>
        <style>{`
          .sardis-slide-track { position: relative; border-radius: 100px; cursor: pointer; overflow: hidden; }
          .sardis-slide-pill { transition: transform 500ms cubic-bezier(0.32,0.72,0,1); }
          .sardis-slide-pill.slid { transform: translateX(calc(100% - 4px)); }
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
          style={{ display: "inline-flex", padding: 4, background: `${t.text}06`, border: `1px solid ${t.text}0A`, borderRadius: 100, width: "100%", textDecoration: "none", cursor: "pointer" }}
          onClick={() => {
            if (slid) return
            setSlid(true)
            if (href) {
              setTimeout(() => { window.location.href = href }, 650)
              setTimeout(() => setSlid(false), 700)
            } else {
              setTimeout(() => setSlid(false), 1200)
            }
          }}
        >
          <div
            className={`sardis-slide-pill ${slid ? "slid" : ""}`}
            style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 8px 12px 24px", background: t.btnBg, borderRadius: 100 }}
          >
            <span className={jakarta.className} style={{ fontSize: 14, fontWeight: 500, color: t.btnText }}>{label}</span>
            <div className="sardis-arrow" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 26, height: 28, borderRadius: "50%", background: t.btnIconBg }}>
              <span style={{ fontSize: 13, color: t.btnText }}>→</span>
            </div>
          </div>
        </div>
      </>
    )
  }

  return (
    <Tag
      className="sardis-btn"
      style={{ display: "inline-flex", padding: "2px", background: `${t.text}08`, border: `1px solid ${t.text}14`, borderRadius: 100, textDecoration: "none" }}
      {...linkProps}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "14px 8px 14px 28px", background: t.btnBg, borderRadius: 100 }}>
        <span className={jakarta.className} style={{ fontSize: 15, fontWeight: 500, color: t.btnText }}>{label}</span>
        <div className="sardis-btn-icon" style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 28, height: 28, borderRadius: "50%", background: t.btnIconBg }}>
          <span style={{ fontSize: 14, color: t.btnText }}>→</span>
        </div>
      </div>
    </Tag>
  )
}

function GhostCTA({ label, t, href }: { label: string; t: typeof light; href?: string }) {
  const Tag = href ? "a" : "div"
  const linkProps = href ? { href, ...(href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {}) } : {}
  return (
    <Tag className="sardis-btn" style={{ display: "flex", alignItems: "center", padding: "16px 24px", border: `1px solid ${t.borderStrong}`, borderRadius: 100, cursor: "pointer", textDecoration: "none" }} {...linkProps}>
      <span style={{ fontSize: 15, color: t.textMuted }}>{label}</span>
    </Tag>
  )
}

/* ── Eyebrow Label ── */
function Eyebrow({ text, t }: { text: string; t: typeof light }) {
  return (
    <span style={{ fontFamily: "var(--font-geist-sans)", fontSize: 12, fontWeight: 500, color: t.textFaint, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>{text}</span>
  )
}

/* ── Double-Bezel Card ── */
function BezelCard({ children, t }: { children: React.ReactNode; t: typeof light }) {
  return (
    <div style={{ display: "flex", flex: 1, padding: 2, background: t.shellBg, border: `1px solid ${t.shellBorder}`, borderRadius: 20 }}>
      <div className="p-5 md:p-7" style={{ display: "flex", flexDirection: "column" as const, gap: 14, background: t.cardBg, borderRadius: 18, flex: 1 }}>
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
    <div className={`${jakarta.variable} overflow-x-hidden`} style={{ background: t.bg, color: t.text, minHeight: "100vh" }}>

      {/* ═══ NAVBAR ═══ */}
      <nav className="flex justify-center px-4 md:px-14 pt-6">
        <div className="flex items-center justify-between w-full max-w-[1100px] px-4 md:px-6 py-3" style={{ background: t.navBg, border: `1px solid ${t.navBorder}`, borderRadius: 100 }}>
          <Link href="/landing" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <SardisLogo color={t.text} />
            <span className={jakarta.className} style={{ fontSize: 15, fontWeight: 700, color: t.text, letterSpacing: "-0.02em" }}>Sardis</span>
          </Link>
          <div className="hidden md:flex gap-8">
            {[
              { label: "Product", href: "#product" },
              { label: "Docs", href: "https://docs.sardis.sh" },
              { label: "Security", href: "https://docs.sardis.sh/security" },
              { label: "Pricing", href: "/pricing" },
            ].map((l) => (
              <a key={l.label} href={l.href} style={{ fontSize: 13, color: t.textMuted, cursor: "pointer", textDecoration: "none" }} {...(l.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}>{l.label}</a>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {mounted && (
              <button
                onClick={() => setTheme(isDark ? "light" : "dark")}
                style={{ fontSize: 13, color: t.textMuted, background: "none", border: "none", cursor: "pointer", padding: "4px 8px" }}
              >
                {isDark ? "☀" : "☾"}
              </button>
            )}
            <a href="https://app.sardis.sh" style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 6px 8px 18px", background: t.btnBg, borderRadius: 100, cursor: "pointer", textDecoration: "none" }}>
              <span style={{ fontSize: 13, fontWeight: 500, color: t.btnText }}>Get started</span>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, borderRadius: "50%", background: t.btnIconBg }}>
                <span style={{ fontSize: 12, color: t.btnText }}>→</span>
              </div>
            </a>
          </div>
        </div>
      </nav>

      {/* ═══ HERO ═══ */}
      <Section className="flex flex-col items-center px-4 md:px-14 pt-16 md:pt-[120px] pb-12 md:pb-20 gap-8 md:gap-10">
        <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 16px 6px 10px", background: `${t.text}06`, border: `1px solid ${t.text}14`, borderRadius: 100 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: t.success }} />
          <span style={{ fontSize: 12, fontWeight: 500, color: t.textMuted, letterSpacing: "0.04em" }}>Now in Public Beta</span>
        </div>
        <h1 className={`${jakarta.className} text-[40px] md:text-[64px] lg:text-[80px] leading-[1.05] tracking-[-0.05em] text-center max-w-[900px]`} style={{ fontWeight: 800, color: t.text }}>
          Safe payments<br />for AI agents.
        </h1>
        <p className="text-base md:text-lg text-center max-w-[520px]" style={{ color: t.textMuted, lineHeight: "28px" }}>
          Set spending rules, enforce compliance guardrails, and let your agents transact autonomously. Every payment verified.
        </p>
        <div className="flex flex-col sm:flex-row items-center gap-3 sm:gap-3.5 pt-2 w-full sm:w-auto">
          <PrimaryCTA label="Get started free" t={t} href="https://app.sardis.sh/signup" />
          <GhostCTA label="Read the docs" t={t} href="https://docs.sardis.sh" />
        </div>
      </Section>

      {/* ═══ CODE TERMINAL (Z-Axis Cascade) ═══ */}
      <Section className="flex justify-center px-4 md:px-14 pb-10 md:pb-[60px] relative h-[340px] md:h-[480px] overflow-hidden">
        {/* Shadow card */}
        <div className="absolute left-1/2 top-5 w-[calc(100%-2rem)] max-w-[560px] -translate-x-[48%] -rotate-2" style={{ padding: 2, background: t.shellBg, border: `1px solid ${t.shellBorder}`, borderRadius: 24 }}>
          <div className="h-[300px] md:h-[440px]" style={{ background: isDark ? "#12121A" : "#F5F2ED", borderRadius: 22 }} />
        </div>
        {/* Main terminal */}
        <div className="absolute left-1/2 top-0 w-[calc(100%-2rem)] max-w-[560px] -translate-x-[52%] rotate-1 flex flex-col" style={{ padding: 2, background: isDark ? "rgba(253,251,247,0.05)" : "rgba(26,22,20,0.06)", border: `1px solid ${isDark ? "rgba(253,251,247,0.08)" : "rgba(26,22,20,0.1)"}`, borderRadius: 24, boxShadow: "0 24px 64px rgba(0,0,0,0.08)" }}>
          <div style={{ display: "flex", flexDirection: "column", background: t.terminalBg, borderRadius: 22, overflow: "hidden" }}>
            <div className="flex items-center justify-between px-4 md:px-5 py-3" style={{ borderBottom: `1px solid ${t.terminalBorder}` }}>
              <div style={{ display: "flex", gap: 7 }}>
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#FF5F57" }} />
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#FEBC2E" }} />
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#28C840" }} />
              </div>
              <span style={{ fontFamily: "var(--font-geist-mono)", fontSize: 12, color: t.terminalMuted }}>quickstart.py</span>
              <div style={{ padding: "3px 10px", border: `1px solid ${t.terminalBorder}`, borderRadius: 6 }}>
                <span style={{ fontSize: 10, fontWeight: 500, color: t.terminalMuted }}>Python</span>
              </div>
            </div>
            <pre className="p-4 md:p-6 text-xs md:text-[13px] overflow-x-auto" style={{ fontFamily: "var(--font-geist-mono)", lineHeight: "24px", color: t.terminalCode, whiteSpace: "pre", margin: 0 }}>
              {codeLines}
            </pre>
            <div className="flex items-center justify-between px-4 md:px-5 py-3" style={{ borderTop: `1px solid ${t.terminalBorder}` }}>
              <span style={{ fontFamily: "var(--font-geist-mono)", fontSize: 10, color: t.terminalDim }}>✓ policy verified · compliance passed</span>
              <span style={{ fontFamily: "var(--font-geist-mono)", fontSize: 12, fontWeight: 600, color: t.success }}>12ms</span>
            </div>
          </div>
        </div>
      </Section>

      {/* ═══ LOGO STRIP ═══ */}
      <Section className="flex flex-col items-center px-4 md:px-14 py-10 md:py-14 gap-6 md:gap-8 mt-6" style={{ borderTop: `1px solid ${t.border}`, borderBottom: `1px solid ${t.border}` }}>
        <div className="flex flex-col md:flex-row items-center gap-4 md:gap-5 flex-wrap justify-center">
          <Eyebrow text="Early partners" t={t} />
          <div className="flex items-center gap-6 md:gap-9 flex-wrap justify-center">
            {[
              { name: "Stripe", domain: "stripe.com" },
              { name: "Bridge", domain: "bridge.xyz" },
              { name: "Base", domain: "base.org" },
              { name: "Tempo", domain: "tempo.xyz" },
              { name: "Arc", domain: "arc.network" },
            ].map((p) => (
              <img key={p.name} src={`https://cdn.brandfetch.io/${p.domain}/w/200/h/40`} alt={p.name} className="h-5 md:h-7" style={{ opacity: 0.85, objectFit: "contain" }} />
            ))}
          </div>
        </div>
        <div className="flex flex-col md:flex-row items-center gap-4 md:gap-5 flex-wrap justify-center">
          <Eyebrow text="Powered by" t={t} />
          <div className="flex items-center gap-6 md:gap-9 flex-wrap justify-center">
            {[
              { name: "Turnkey", domain: "turnkey.com" },
              { name: "Coinbase", domain: "coinbase.com" },
              { name: "Circle", domain: "circle.com" },
            ].map((p) => (
              <img key={p.name} src={`https://cdn.brandfetch.io/${p.domain}/w/200/h/40`} alt={p.name} className="h-5 md:h-7" style={{ opacity: 0.85, objectFit: "contain" }} />
            ))}
          </div>
        </div>
        <div className="flex flex-col md:flex-row items-center gap-4 md:gap-5 flex-wrap justify-center">
          <Eyebrow text="Live integrations" t={t} />
          <div className="flex items-center gap-6 md:gap-9 flex-wrap justify-center">
            {[
              { name: "AutoGPT", domain: "agpt.co" },
              { name: "Activepieces", domain: "activepieces.com" },
            ].map((p) => (
              <img key={p.name} src={`https://cdn.brandfetch.io/${p.domain}/w/200/h/40`} alt={p.name} className="h-5 md:h-7" style={{ opacity: 0.85, objectFit: "contain" }} />
            ))}
          </div>
        </div>
      </Section>

      {/* ═══ PROBLEM ═══ */}
      <Section className="px-4 md:px-14 py-16 md:py-[120px] flex flex-col gap-10 md:gap-14">
        <div className="flex flex-col md:flex-row gap-10 md:gap-20">
          <div style={{ display: "flex", flexDirection: "column", gap: 20, flex: 1 }}>
            <Eyebrow text="The problem" t={t} />
            <h2 className={`${jakarta.className} text-[28px] md:text-[36px] lg:text-[44px] leading-[1.1] tracking-[-0.04em]`} style={{ fontWeight: 800 }}>
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
              <div key={i} className="py-5 md:py-7" style={{ display: "flex", flexDirection: "column", gap: 8, borderBottom: i < 2 ? `1px solid ${t.border}` : "none" }}>
                <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>{item.num}. {item.label}</span>
                <span className={`${jakarta.className} text-base md:text-[19px]`} style={{ fontWeight: 600, lineHeight: "27px", letterSpacing: "-0.02em" }}>{item.desc}</span>
              </div>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══ HOW IT WORKS ═══ */}
      <Section className="px-4 md:px-14 py-16 md:py-[120px] flex flex-col gap-8 md:gap-12" style={{ background: t.sectionAlt }}>
        <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Eyebrow text="How it works" t={t} />
            <h2 className={`${jakarta.className} text-[26px] md:text-[32px] lg:text-[38px] leading-[1.1] tracking-[-0.035em]`} style={{ fontWeight: 800 }}>
              Three layers between intent<br />and money movement.
            </h2>
          </div>
          <span className="hidden md:block" style={{ fontSize: 13, color: t.textLabel }}>Define. Send. Verify.</span>
        </div>
        <div className="flex flex-col md:flex-row gap-4">
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
              <span className={`${jakarta.className} text-[15px] md:text-[17px]`} style={{ fontWeight: 600, lineHeight: "24px" }}>{step.title}</span>
              <span style={{ fontSize: 13, color: t.textFaint, lineHeight: "20px" }}>{step.desc}</span>
            </BezelCard>
          ))}
        </div>
      </Section>

      {/* ═══ FEATURES BENTO ═══ */}
      <Section id="product" className="px-4 md:px-14 py-16 md:py-[120px] flex flex-col gap-8 md:gap-10">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <Eyebrow text="Features" t={t} />
          <h2 className={`${jakarta.className} text-[26px] md:text-[32px] lg:text-[38px] leading-[1.1] tracking-[-0.035em]`} style={{ fontWeight: 800 }}>
            The control plane for money<br className="hidden md:block" /> inside agent systems.
          </h2>
        </div>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col md:flex-row gap-3">
            <BezelCard t={t}>
              <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>SDKs</span>
              <span className={`${jakarta.className} text-base md:text-[19px]`} style={{ fontWeight: 600 }}>Python and TypeScript clients for policy and authorizations.</span>
              <div className="flex flex-wrap gap-2 pt-3">
                <code style={{ padding: "4px 10px", background: `${t.text}06`, border: `1px solid ${t.text}0F`, borderRadius: 6, fontFamily: "var(--font-geist-mono)", fontSize: 12, color: t.textFaint }}>pip install sardis</code>
                <code style={{ padding: "4px 10px", background: `${t.text}06`, border: `1px solid ${t.text}0F`, borderRadius: 6, fontFamily: "var(--font-geist-mono)", fontSize: 12, color: t.textFaint }}>npm i @sardis/sdk</code>
              </div>
            </BezelCard>
            <BezelCard t={t}>
              <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>MCP tools</span>
              <span className={`${jakarta.className} text-base md:text-[19px]`} style={{ fontWeight: 600 }}>Native MCP server for Claude, Cursor, and Windsurf.</span>
              <span style={{ fontSize: 13, color: t.textFaint, lineHeight: "20px" }}>Agents call Sardis tools natively.</span>
            </BezelCard>
          </div>
          <div className="flex flex-col md:flex-row gap-3">
            {[
              { label: "Frameworks", title: "CrewAI, LangChain, Vercel AI, custom runtimes." },
              { label: "Multi-chain", title: "Live on Tempo and Base. Arc testnet next. Polygon, Arbitrum, Optimism on deck." },
              { label: "Sandbox", title: "Test prompts and policies before funds move." },
            ].map((f) => (
              <BezelCard key={f.label} t={t}>
                <span style={{ fontSize: 10, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>{f.label}</span>
                <span className={`${jakarta.className} text-[15px] md:text-[17px]`} style={{ fontWeight: 600 }}>{f.title}</span>
              </BezelCard>
            ))}
          </div>
        </div>
      </Section>

      {/* ═══ ENTERPRISE ═══ */}
      <Section className="flex flex-col md:flex-row px-4 md:px-14 py-16 md:py-[120px] gap-10 md:gap-20" style={{ borderTop: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, flex: 1 }}>
          <Eyebrow text="Enterprise" t={t} />
          <h2 className={`${jakarta.className} text-[26px] md:text-[32px] lg:text-[38px] leading-[1.1] tracking-[-0.035em]`} style={{ fontWeight: 800 }}>
            Compliance your finance team can trust.
          </h2>
          <p style={{ fontSize: 15, color: t.textMuted, lineHeight: "24px", maxWidth: 380 }}>
            KYC, sanctions, audit trails, and kill switches. Non-custodial MPC custody powered by Turnkey — Sardis never holds your keys.
          </p>
        </div>
        <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
          {[
            { label: "Non-custodial MPC (Turnkey)", status: "live" },
            { label: "KYC-linked identity", status: "active" },
            { label: "Sanctions screening", status: "clear" },
            { label: "Audit trail", status: "recorded" },
            { label: "Agent kill switch", status: "armed" },
          ].map((item, i) => (
            <div key={i} className="py-4 md:py-5" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: i < 4 ? `1px solid ${t.border}` : "none" }}>
              <span style={{ fontSize: 15, color: t.textMuted }}>{item.label}</span>
              <span style={{ fontSize: 13, fontWeight: 600, color: t.success }}>{item.status}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* ═══ PRICING ═══ */}
      <Section id="pricing" className="px-4 md:px-14 py-16 md:py-[120px] flex flex-col gap-8 md:gap-12" style={{ background: t.sectionAlt }}>
        <div className="flex flex-col md:flex-row md:justify-between md:items-end gap-4">
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <Eyebrow text="Pricing" t={t} />
            <h2 className={`${jakarta.className} text-[26px] md:text-[32px] lg:text-[38px] leading-[1.1] tracking-[-0.035em]`} style={{ fontWeight: 800 }}>
              Start free. Add control<br />as spending gets real.
            </h2>
          </div>
          <span className="hidden md:block" style={{ fontSize: 13, color: t.textLabel }}>Simple pricing, real control.</span>
        </div>
        <div className="flex flex-col lg:flex-row gap-5 max-w-[1100px] mx-auto w-full">
          {/* Free */}
          <div className="flex flex-col flex-1 p-6 md:p-9 gap-6 md:gap-7" style={{ border: `1px solid ${t.border}`, borderRadius: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>Free</span>
              <span className={`${jakarta.className} text-[36px] md:text-[48px] tracking-[-0.03em]`} style={{ fontWeight: 800 }}>$0</span>
              <span style={{ fontSize: 14, color: t.textFaint, marginTop: 4 }}>Sandbox, 2 agents, testnet only.</span>
            </div>
            <div style={{ height: 1, background: t.border }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {["Sandbox environment", "SDK + MCP access", "Basic policy engine", "Community support"].map((f) => (
                <span key={f} style={{ fontSize: 13, color: t.textMuted }}>{f}</span>
              ))}
            </div>
            <div style={{ marginTop: "auto", paddingTop: 8 }}>
              <PrimaryCTA label="Get started" t={t} slide href="https://app.sardis.sh" />
            </div>
          </div>
          {/* Starter — MOST POPULAR — Double Bezel */}
          <div className="flex flex-col flex-1 lg:flex-[1.25] relative mt-4 lg:mt-0" style={{ padding: 3, background: `${t.text}0F`, border: `1px solid ${t.text}1A`, borderRadius: 24 }}>
            <div style={{ position: "absolute", top: -14, left: "50%", transform: "translateX(-50%)", padding: "5px 16px", background: t.btnBg, borderRadius: 100, zIndex: 1 }}>
              <span style={{ fontSize: 10, fontWeight: 700, color: t.btnText, letterSpacing: "0.08em", textTransform: "uppercase" as const }}>Most popular</span>
            </div>
            <div className="flex flex-col flex-1 p-7 md:p-10 pt-10 md:pt-11 gap-6 md:gap-8" style={{ background: t.cardBg, borderRadius: 21, boxShadow: isDark ? "inset 0 1px 0 rgba(253,251,247,0.04)" : "0 12px 40px rgba(26,22,20,0.08)" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600, color: t.text, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>Starter</span>
                <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                  <span className={`${jakarta.className} text-[36px] md:text-[48px] tracking-[-0.03em]`} style={{ fontWeight: 800 }}>$199</span>
                  <span style={{ fontSize: 14, color: t.textFaint }}>/ mo</span>
                </div>
                <span style={{ fontSize: 14, color: t.textFaint, marginTop: 4 }}>Production, mainnet, 25 agents.</span>
              </div>
              <div style={{ height: 1, background: t.border }} />
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                {["Everything in Free", "Mainnet settlement", "Unlimited transactions", "Multi-chain (Tempo + Base)", "Audit events + webhooks", "Priority support"].map((f) => (
                  <span key={f} style={{ fontSize: 13, color: t.textMuted }}>{f}</span>
                ))}
              </div>
              <div style={{ marginTop: "auto", paddingTop: 8 }}>
                <PrimaryCTA label="Start building" t={t} slide href="https://app.sardis.sh/billing" />
              </div>
            </div>
          </div>
          {/* Enterprise */}
          <div className="flex flex-col flex-1 p-6 md:p-9 gap-6 md:gap-7" style={{ border: `1px solid ${t.border}`, borderRadius: 20 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" as const }}>Enterprise</span>
              <span className={`${jakarta.className} text-[36px] md:text-[48px] tracking-[-0.03em]`} style={{ fontWeight: 800 }}>Custom</span>
              <span style={{ fontSize: 14, color: t.textFaint, marginTop: 4 }}>Unlimited agents, white-glove.</span>
            </div>
            <div style={{ height: 1, background: t.border }} />
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {["Everything in Starter", "KYB + PEP screening", "Advanced audit trail", "FX support", "Custom SLAs", "Dedicated support"].map((f) => (
                <span key={f} style={{ fontSize: 13, color: t.textMuted }}>{f}</span>
              ))}
            </div>
            <div style={{ marginTop: "auto", paddingTop: 8 }}>
              <PrimaryCTA label="Talk to sales" t={t} slide href="https://cal.com/sardis/15min" />
            </div>
          </div>
        </div>
      </Section>

      {/* ═══ FINAL CTA ═══ */}
      <Section className="flex flex-col md:flex-row items-start md:items-center justify-between px-4 md:px-14 py-16 md:py-[120px] gap-10 md:gap-20" style={{ borderTop: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 600 }}>
          <Eyebrow text="Safe by design" t={t} />
          <h2 className={`${jakarta.className} text-[32px] md:text-[40px] lg:text-[48px] leading-[1.1] tracking-[-0.04em]`} style={{ fontWeight: 800 }}>
            Sardis is how they earn your trust.
          </h2>
          <p style={{ fontSize: 15, color: t.textMuted, lineHeight: "24px" }}>
            Build agent payments with infrastructure-grade discipline.
          </p>
        </div>
        <div className="flex flex-col items-start md:items-end gap-3.5">
          <PrimaryCTA label="Get started" t={t} href="https://app.sardis.sh" />
          <a href="https://cal.com/sardis/15min" target="_blank" rel="noopener noreferrer" style={{ display: "flex", alignItems: "center", gap: 6, padding: "12px 22px", border: `1px solid ${t.borderStrong}`, borderRadius: 100, cursor: "pointer", textDecoration: "none" }}>
            <span style={{ fontSize: 14, color: t.textMuted }}>Talk to sales</span>
            <span style={{ fontSize: 14, color: t.textGhost }}>↗</span>
          </a>
        </div>
      </Section>

      {/* ═══ FOOTER ═══ */}
      <footer className="flex flex-col md:flex-row items-center justify-between px-4 md:px-14 py-6 gap-4" style={{ borderTop: `1px solid ${t.border}` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <SardisLogo color={t.textGhost} size={16} />
          <span style={{ fontSize: 12, color: t.textGhost }}>© 2026 Sardis. Payment OS for AI agents.</span>
        </div>
        <div className="flex flex-wrap justify-center gap-4 md:gap-6">
          {[
            { label: "Product", href: "#product" },
            { label: "Docs", href: "https://docs.sardis.sh" },
            { label: "Security", href: "https://docs.sardis.sh/security" },
            { label: "Pricing", href: "#pricing" },
            { label: "Privacy", href: "https://docs.sardis.sh/privacy" },
            { label: "Terms", href: "https://docs.sardis.sh/terms" },
          ].map((l) => (
            <a key={l.label} href={l.href} style={{ fontSize: 12, color: t.textLabel, cursor: "pointer", textDecoration: "none" }} {...(l.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}>{l.label}</a>
          ))}
        </div>
      </footer>

    </div>
  )
}
