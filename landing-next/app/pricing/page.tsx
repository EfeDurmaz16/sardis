import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import { createBreadcrumbSchema, createFAQSchema } from "@/lib/metadata";
import PricingContent from "./PricingContent";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Simple, transparent pricing for AI agent payments. Start free, scale as you grow. No credit card required.",
  alternates: { canonical: "https://www.sardis.sh/pricing" },
};

const PLANS = [
  {
    name: "Free",
    priceLabel: "$0",
    period: "/mo",
    tagline: "Get started with no credit card.",
    highlighted: false,
    badge: null as string | null,
    cta: "Get Started Free",
    ctaHref: "https://dashboard.sardis.sh/signup",
    features: [
      { label: "1,000 API calls / mo", included: true },
      { label: "2 agents", included: true },
      { label: "1.5% transaction fee", included: true },
      { label: "$1K / mo transaction volume", included: true },
      { label: "Shared MPC wallets", included: true },
      { label: "Community support", included: true },
      { label: "Basic policy engine", included: true },
      { label: "Compliance", included: false },
    ],
  },
  {
    name: "Dev",
    priceLabel: "$49",
    period: "/mo",
    tagline: "Testnet only. Build and iterate.",
    highlighted: false,
    badge: null as string | null,
    cta: "Start Free Trial",
    ctaHref: "https://dashboard.sardis.sh/signup?plan=dev",
    features: [
      { label: "10,000 API calls / mo", included: true },
      { label: "5 agents", included: true },
      { label: "100 tx / mo (testnet)", included: true },
      { label: "Testnet wallets only", included: true },
      { label: "Shared MPC wallets", included: true },
      { label: "Email support", included: true },
      { label: "Full policy engine", included: true },
      { label: "No SLA", included: false },
    ],
  },
  {
    name: "Starter",
    priceLabel: "$199",
    period: "/mo",
    tagline: "For teams shipping to production.",
    highlighted: true,
    badge: "Most Popular",
    cta: "Start Free Trial",
    ctaHref: "https://dashboard.sardis.sh/signup?plan=starter",
    features: [
      { label: "50,000 API calls / mo", included: true },
      { label: "10 agents", included: true },
      { label: "1.0% transaction fee", included: true },
      { label: "$25K / mo transaction volume", included: true },
      { label: "Dedicated MPC wallets", included: true },
      { label: "Email support + SLA", included: true },
      { label: "Full policy engine", included: true },
      { label: "Standard compliance", included: true },
    ],
  },
  {
    name: "Enterprise",
    priceLabel: "Custom",
    period: null as string | null,
    tagline: "Built around your requirements.",
    highlighted: false,
    badge: null as string | null,
    cta: "Contact Sales",
    ctaHref: "/enterprise",
    features: [
      { label: "Unlimited API calls", included: true },
      { label: "Unlimited agents", included: true },
      { label: "0.5% transaction fee", included: true },
      { label: "Custom transaction volume", included: true },
      { label: "Custom MPC wallets", included: true },
      { label: "Dedicated support", included: true },
      { label: "Full policy engine + custom", included: true },
      { label: "Full compliance + audit", included: true },
    ],
  },
];

const FAQS = [
  {
    q: "What happens when I exceed my limits?",
    a: "We send you a warning at 80% of your monthly limit. At 100% we soft-block further calls until the next billing cycle (or until you upgrade).",
  },
  {
    q: "Can I change plans anytime?",
    a: "Yes. Upgrades take effect immediately and are prorated. Downgrades take effect at the start of the next billing cycle.",
  },
  {
    q: "What payment methods do you accept?",
    a: "We accept all major credit and debit cards via Stripe. Enterprise customers can pay via bank transfer on annual contracts.",
  },
  {
    q: "Is there a free trial?",
    a: "The Free tier is permanent -- no credit card, no expiry. Paid tiers come with a 14-day free trial.",
  },
  {
    q: "Do you offer annual pricing?",
    a: "Yes. Annual plans come with a meaningful discount compared to month-to-month. Contact us through the Enterprise page.",
  },
];

function CheckIcon({ color = "#22C55E" }: { color?: string }) {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 mt-0.5">
      <path d="M3 8l3.5 3.5L13 4" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function DashIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" className="shrink-0 mt-0.5">
      <path d="M4 8h8" stroke="#3F3F4A" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export default function PricingPage() {
  const breadcrumbSchema = createBreadcrumbSchema([
    { name: "Home", href: "/" },
    { name: "Pricing" },
  ]);
  const faqSchema = createFAQSchema(FAQS);

  return (
    <div className="min-h-screen" style={{ backgroundColor: "#08090A", color: "#F5F5F5" }}>
      <Script id="pricing-breadcrumb" type="application/ld+json" strategy="beforeInteractive">
        {JSON.stringify(breadcrumbSchema)}
      </Script>
      <Script id="pricing-faq" type="application/ld+json" strategy="beforeInteractive">
        {JSON.stringify(faqSchema)}
      </Script>

      {/* Hero */}
      <section className="pt-20 pb-16 text-center">
        <div className="max-w-4xl mx-auto px-5">
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-4"
            style={{ fontFamily: "'JetBrains Mono', monospace", color: "#818CF8" }}
          >
            PRICING
          </p>
          <h1
            className="text-4xl md:text-5xl font-bold tracking-[-0.04em] mb-4"
            style={{ fontFamily: "'Space Grotesk', sans-serif" }}
          >
            Simple, transparent pricing
          </h1>
          <p
            className="text-base max-w-2xl mx-auto"
            style={{ fontFamily: "'Inter', sans-serif", color: "#808080" }}
          >
            Start free. Scale as your agents grow. No hidden fees, no surprise invoices.
          </p>
        </div>
      </section>

      {/* Plans */}
      <section className="pb-20">
        <div className="max-w-6xl mx-auto px-5 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-5">
          {PLANS.map((plan) => (
            <div
              key={plan.name}
              className="relative flex flex-col rounded-2xl p-6"
              style={{
                background: plan.highlighted ? "#0D0E16" : "#0A0B0D",
                border: plan.highlighted
                  ? "1px solid rgba(99,102,241,0.6)"
                  : "1px solid rgba(255,255,255,0.08)",
              }}
            >
              {plan.badge && (
                <div
                  className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-semibold"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)",
                    color: "#fff",
                  }}
                >
                  {plan.badge}
                </div>
              )}

              <p
                className="text-xs font-semibold uppercase tracking-widest mb-4"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  color: plan.highlighted ? "#818CF8" : "#505460",
                }}
              >
                {plan.name}
              </p>

              <div className="flex items-end gap-1 mb-2">
                <span
                  className="text-4xl font-bold"
                  style={{ fontFamily: "'Space Grotesk', sans-serif", color: "#F5F5F5" }}
                >
                  {plan.priceLabel}
                </span>
                {plan.period && (
                  <span className="text-sm mb-1" style={{ fontFamily: "'Inter', sans-serif", color: "#505460" }}>
                    {plan.period}
                  </span>
                )}
              </div>

              <p className="text-sm mb-6" style={{ fontFamily: "'Inter', sans-serif", color: "#606070" }}>
                {plan.tagline}
              </p>

              <Link
                href={plan.ctaHref}
                className="block w-full text-center rounded-lg py-2.5 text-sm font-medium mb-6 transition-colors"
                style={{
                  fontFamily: "'Inter', sans-serif",
                  ...(plan.highlighted
                    ? { background: "linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%)", color: "#fff" }
                    : { background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)", color: "#E0E0E0" }),
                }}
              >
                {plan.cta}
              </Link>

              <div className="w-full h-px mb-6" style={{ background: "rgba(255,255,255,0.06)" }} />

              <ul className="flex flex-col gap-3">
                {plan.features.map((f) => (
                  <li key={f.label} className="flex items-start gap-3">
                    {f.included ? <CheckIcon color={plan.highlighted ? "#818CF8" : "#22C55E"} /> : <DashIcon />}
                    <span
                      className="text-sm"
                      style={{ fontFamily: "'Inter', sans-serif", color: f.included ? "#A0A0AA" : "#3F3F4A" }}
                    >
                      {f.label}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="pb-20">
        <div className="max-w-3xl mx-auto px-5">
          <h2 className="text-2xl font-bold text-center mb-10" style={{ fontFamily: "'Space Grotesk', sans-serif" }}>
            Frequently Asked Questions
          </h2>
          <PricingContent faqs={FAQS} />
        </div>
      </section>
    </div>
  );
}
