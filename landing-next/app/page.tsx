import type { Metadata } from "next";
import Link from "next/link";
import Hero from "@/components/landing/Hero";
import SocialProof from "@/components/landing/SocialProof";
import HeroTrace from "@/components/landing/HeroTrace";
import PressStrip from "@/components/landing/PressStrip";
import HowItWorks from "@/components/landing/HowItWorks";
import FeaturesGrid from "@/components/landing/FeaturesGrid";
import StatsSection from "@/components/landing/StatsSection";
import DevExperience from "@/components/landing/DevExperience";
import BuiltFor from "@/components/landing/BuiltFor";
import Marquee from "@/components/landing/Marquee";
import Protocols from "@/components/landing/Protocols";
import Integrations from "@/components/landing/Integrations";
import CTASection from "@/components/landing/CTASection";
import AnimatedSection from "@/components/landing/AnimatedSection";

export const metadata: Metadata = {
  title: "Sardis: The Payment OS for the Agent Economy",
  description:
    "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust. Non-custodial wallets, spending policies, on-chain payments on Base with multi-chain funding.",
  alternates: {
    canonical: "https://www.sardis.sh",
  },
};

const exploreLinks = [
  {
    to: "/docs/quickstart",
    title: "Quickstart Guide",
    desc: "Set up Sardis and make your first AI agent payment in minutes.",
  },
  {
    to: "/docs/wallets",
    title: "AI Agent Wallets",
    desc: "Non-custodial MPC wallets with programmable spending limits.",
  },
  {
    to: "/docs/policies",
    title: "Spending Policies",
    desc: "Define spending rules in natural language with a 12-check enforcement pipeline.",
  },
  {
    to: "/docs/spending-mandates",
    title: "Spending Mandates",
    desc: "Delegate financial authority to agents with cryptographic controls.",
  },
  {
    to: "/docs/security",
    title: "Security & Audit Trail",
    desc: "Append-only ledger with signed attestation envelopes and Merkle proofs.",
  },
  {
    to: "/docs/integrations",
    title: "Framework Integrations",
    desc: "Works with Claude MCP, OpenAI, LangChain, CrewAI, AutoGPT, and more.",
  },
  {
    to: "/docs/ap2",
    title: "AP2 Protocol",
    desc: "Industry-standard Agent Payment Protocol by Google, PayPal, Mastercard, and Visa.",
  },
  {
    to: "/docs/mcp-server",
    title: "MCP Server",
    desc: "52 tools for Claude Desktop -- wallets, payments, treasury, and compliance.",
  },
  {
    to: "/docs/faq",
    title: "FAQ",
    desc: "Frequently asked questions about AI agent payments and Sardis.",
  },
];

export default function HomePage() {
  return (
    <div
      className="min-h-screen [font-synthesis:none]"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:left-4 focus:z-[100] focus:px-4 focus:py-2 focus:rounded-lg focus:text-white"
        style={{ backgroundColor: "var(--landing-accent)" }}
      >
        Skip to main content
      </a>

      <main id="main-content">
        <Hero />

        {/* Live payment trace animation */}
        <AnimatedSection>
          <div
            className="flex justify-center py-10 md:py-16"
            style={{ backgroundColor: "var(--landing-bg)" }}
          >
            <HeroTrace />
          </div>
        </AnimatedSection>

        <PressStrip />

        <AnimatedSection>
          <SocialProof />
        </AnimatedSection>

        <AnimatedSection>
          <HowItWorks />
        </AnimatedSection>

        <AnimatedSection>
          <FeaturesGrid />
        </AnimatedSection>

        <StatsSection />

        <AnimatedSection>
          <DevExperience />
        </AnimatedSection>

        <AnimatedSection>
          <BuiltFor />
        </AnimatedSection>

        <AnimatedSection>
          <Protocols />
        </AnimatedSection>

        <AnimatedSection>
          <Integrations />
        </AnimatedSection>

        <Marquee />

        {/* GEO: Internal links for AI crawlers + SEO */}
        <section
          className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-16"
          style={{ borderTop: "1px solid var(--landing-border)" }}
        >
          <h2
            className="text-center mb-10 font-semibold tracking-[-0.02em]"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: "clamp(22px, 3vw, 32px)",
              color: "var(--landing-text-primary)",
            }}
          >
            Explore the Platform
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {exploreLinks.map((item) => (
              <Link
                key={item.to}
                href={item.to}
                className="block rounded-lg p-5 transition-colors hover:border-[var(--landing-accent)]"
                style={{
                  border: "1px solid var(--landing-border)",
                  backgroundColor: "transparent",
                }}
              >
                <h3
                  className="font-medium mb-1.5"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "15px",
                    color: "var(--landing-text-primary)",
                  }}
                >
                  {item.title}
                </h3>
                <p
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    fontSize: "13px",
                    color: "var(--landing-text-ghost)",
                    lineHeight: "1.5",
                  }}
                >
                  {item.desc}
                </p>
              </Link>
            ))}
          </div>
        </section>

        <AnimatedSection>
          <CTASection />
        </AnimatedSection>
      </main>
    </div>
  );
}
