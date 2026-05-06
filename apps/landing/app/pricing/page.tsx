"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Plus_Jakarta_Sans } from "next/font/google"
import Link from "next/link"

const jakarta = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta" })

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
  navBg: "rgba(26,22,20,0.04)",
  navBorder: "rgba(26,22,20,0.06)",
  btnBg: "#1A1614",
  btnText: "#FDFBF7",
  btnIconBg: "rgba(253,251,247,0.12)",
  sectionAlt: "rgba(26,22,20,0.02)",
}

const dark: typeof light = {
  bg: "#0A0A0F",
  text: "#FDFBF7",
  textMuted: "rgba(253,251,247,0.4)",
  textFaint: "rgba(253,251,247,0.3)",
  textGhost: "rgba(253,251,247,0.2)",
  textLabel: "rgba(253,251,247,0.25)",
  border: "rgba(253,251,247,0.04)",
  borderStrong: "rgba(253,251,247,0.08)",
  cardBg: "#0A0A0F",
  navBg: "rgba(255,255,255,0.03)",
  navBorder: "rgba(255,255,255,0.06)",
  btnBg: "#FDFBF7",
  btnText: "#0A0A0F",
  btnIconBg: "rgba(10,10,15,0.08)",
  sectionAlt: "rgba(253,251,247,0.02)",
}

type Tier = {
  name: string
  price: string
  priceSuffix?: string
  tagline: string
  features: string[]
  cta: { label: string; href: string }
  highlight?: boolean
}

const TIERS: Tier[] = [
  {
    name: "Free",
    price: "$0",
    tagline: "Sandbox, 2 agents, testnet only.",
    features: [
      "Sandbox environment",
      "SDK + MCP access",
      "Basic policy engine",
      "Community support",
    ],
    cta: { label: "Get started", href: "https://app.sardis.sh" },
  },
  {
    name: "Starter",
    price: "$199",
    priceSuffix: "/ mo",
    tagline: "Production, mainnet, 25 agents.",
    features: [
      "Everything in Free",
      "Mainnet settlement",
      "Unlimited transactions",
      "Multi-chain (Tempo + Base)",
      "Audit events + webhooks",
      "Priority support",
    ],
    cta: { label: "Start building", href: "https://app.sardis.sh/billing" },
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    tagline: "Unlimited agents, white-glove.",
    features: [
      "Everything in Starter",
      "KYB + PEP screening",
      "Advanced audit trail",
      "FX support",
      "Custom SLAs",
      "Dedicated support",
    ],
    cta: { label: "Talk to sales", href: "https://cal.com/sardis/15min" },
  },
]

function SardisLogo({ color, size = 20 }: { color: string; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <path d="M20 5H10a7 7 0 000 14h2" stroke={color} strokeWidth="3" strokeLinecap="round" fill="none" />
      <path d="M8 23h10a7 7 0 000-14h-2" stroke={color} strokeWidth="3" strokeLinecap="round" fill="none" />
    </svg>
  )
}

export default function PricingPage() {
  const { resolvedTheme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)
  useEffect(() => {
    const frame = requestAnimationFrame(() => setMounted(true))
    return () => cancelAnimationFrame(frame)
  }, [])
  const isDark = mounted && resolvedTheme === "dark"
  const t = isDark ? dark : light

  return (
    <div style={{ background: t.bg, color: t.text, minHeight: "100vh" }} className={jakarta.variable}>
      <nav className="flex justify-center px-4 md:px-14 pt-6">
        <div
          className="flex items-center justify-between w-full max-w-[1100px] px-4 md:px-6 py-3"
          style={{ background: t.navBg, border: `1px solid ${t.navBorder}`, borderRadius: 100 }}
        >
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
            <SardisLogo color={t.text} />
            <span className={jakarta.className} style={{ fontSize: 15, fontWeight: 700, color: t.text, letterSpacing: "-0.02em" }}>
              Sardis
            </span>
          </Link>
          <div className="hidden md:flex gap-8">
            {[
              { label: "Product", href: "/#product" },
              { label: "Docs", href: "https://docs.sardis.sh" },
              { label: "Security", href: "https://docs.sardis.sh/security" },
              { label: "Pricing", href: "/pricing" },
            ].map((l) => (
              <a
                key={l.label}
                href={l.href}
                style={{ fontSize: 13, color: t.textMuted, textDecoration: "none" }}
                {...(l.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
              >
                {l.label}
              </a>
            ))}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {mounted && (
              <button
                onClick={() => setTheme(isDark ? "light" : "dark")}
                style={{ fontSize: 13, color: t.textMuted, background: "none", border: "none", cursor: "pointer", padding: "4px 8px" }}
                aria-label="Toggle theme"
              >
                {isDark ? "☀" : "☾"}
              </button>
            )}
            <a
              href="https://app.sardis.sh"
              style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 6px 8px 18px", background: t.btnBg, borderRadius: 100, textDecoration: "none" }}
            >
              <span style={{ fontSize: 13, fontWeight: 500, color: t.btnText }}>Get started</span>
              <div
                style={{ display: "flex", alignItems: "center", justifyContent: "center", width: 24, height: 24, borderRadius: "50%", background: t.btnIconBg }}
              >
                <span style={{ fontSize: 12, color: t.btnText }}>→</span>
              </div>
            </a>
          </div>
        </div>
      </nav>

      <section className="px-4 md:px-14 py-16 md:py-[120px] flex flex-col gap-8 md:gap-12">
        <div className="flex flex-col gap-4 max-w-[1100px] mx-auto w-full">
          <span style={{ fontSize: 12, fontWeight: 600, color: t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            Pricing
          </span>
          <h1
            className={`${jakarta.className} text-[32px] md:text-[44px] lg:text-[52px] leading-[1.05] tracking-[-0.035em]`}
            style={{ fontWeight: 800, maxWidth: 720 }}
          >
            Start free. Add control as spending gets real.
          </h1>
          <p style={{ fontSize: 15, color: t.textMuted, maxWidth: 560, lineHeight: "24px" }}>
            Simple, transparent pricing. Stablecoin checkout has 0% merchant fees across all tiers.
          </p>
        </div>

        <div className="flex flex-col lg:flex-row gap-5 max-w-[1100px] mx-auto w-full">
          {TIERS.map((tier) => {
            const card = (
              <div
                className="flex flex-col flex-1 p-6 md:p-9 gap-6 md:gap-7 h-full"
                style={{
                  background: t.cardBg,
                  border: `1px solid ${tier.highlight ? t.borderStrong : t.border}`,
                  borderRadius: 20,
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: tier.highlight ? t.text : t.textLabel, letterSpacing: "0.1em", textTransform: "uppercase" }}>
                    {tier.name}
                  </span>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
                    <span className={`${jakarta.className} text-[36px] md:text-[48px] tracking-[-0.03em]`} style={{ fontWeight: 800 }}>
                      {tier.price}
                    </span>
                    {tier.priceSuffix && (
                      <span style={{ fontSize: 14, color: t.textFaint }}>{tier.priceSuffix}</span>
                    )}
                  </div>
                  <span style={{ fontSize: 14, color: t.textFaint, marginTop: 4 }}>{tier.tagline}</span>
                </div>
                <div style={{ height: 1, background: t.border }} />
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {tier.features.map((f) => (
                    <span key={f} style={{ fontSize: 13, color: t.textMuted }}>
                      {f}
                    </span>
                  ))}
                </div>
                <div style={{ marginTop: "auto", paddingTop: 8 }}>
                  <a
                    href={tier.cta.href}
                    {...(tier.cta.href.startsWith("http") ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: 8,
                      padding: "10px 18px",
                      background: tier.highlight ? t.btnBg : "transparent",
                      color: tier.highlight ? t.btnText : t.text,
                      border: `1px solid ${tier.highlight ? t.btnBg : t.borderStrong}`,
                      borderRadius: 100,
                      fontSize: 13,
                      fontWeight: 500,
                      textDecoration: "none",
                    }}
                  >
                    {tier.cta.label}
                    <span style={{ fontSize: 12 }}>→</span>
                  </a>
                </div>
              </div>
            )

            if (tier.highlight) {
              return (
                <div
                  key={tier.name}
                  className="flex flex-col flex-1 lg:flex-[1.15] relative mt-4 lg:mt-0"
                  style={{ padding: 3, background: `${t.text}0F`, border: `1px solid ${t.text}1A`, borderRadius: 24 }}
                >
                  <div
                    style={{
                      position: "absolute",
                      top: -14,
                      left: "50%",
                      transform: "translateX(-50%)",
                      padding: "5px 16px",
                      background: t.btnBg,
                      borderRadius: 100,
                      zIndex: 1,
                    }}
                  >
                    <span style={{ fontSize: 10, fontWeight: 700, color: t.btnText, letterSpacing: "0.08em", textTransform: "uppercase" }}>
                      Most popular
                    </span>
                  </div>
                  {card}
                </div>
              )
            }
            return <div key={tier.name} className="flex flex-col flex-1">{card}</div>
          })}
        </div>
      </section>
    </div>
  )
}
