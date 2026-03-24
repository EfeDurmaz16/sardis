import type { Metadata } from "next";
import Link from "next/link";
import Script from "next/script";
import { createBreadcrumbSchema } from "@/lib/metadata";

export const metadata: Metadata = {
  title: "Enterprise AI Agent Payments",
  description:
    "Enterprise-grade AI agent payments with deterministic policy enforcement, approval controls, and auditable transaction trails.",
  alternates: { canonical: "https://www.sardis.sh/enterprise" },
};

const capabilities = [
  {
    title: "Policy-Controlled Wallets",
    desc: "Every agent gets its own non-custodial MPC wallet with natural language spending policies. 12-check enforcement pipeline on every transaction.",
  },
  {
    title: "Kill Switch",
    desc: "5 scopes: global, organization, agent, rail, chain. Instant freeze with sub-second propagation. No transactions slip through during investigation.",
  },
  {
    title: "Approval Workflows",
    desc: "Confidence-based routing with configurable thresholds. 4-eyes quorum for high-value transactions. Auto-approve below threshold.",
  },
  {
    title: "Cryptographic Audit Trail",
    desc: "Append-only ledger with signed attestation envelopes, HMAC receipts, Merkle proofs. Every decision recorded with tamper-proof evidence.",
  },
  {
    title: "Compliance Ready",
    desc: "SOC2 Type II, PCI DSS, GDPR, and ISO 27001 compliance pathway. Sanctions screening, KYC/KYB, and ongoing transaction monitoring.",
  },
  {
    title: "Multi-Chain Treasury",
    desc: "Execute on Base, fund from Ethereum, Polygon, Arbitrum, Optimism via CCTP v2. Unified balance across all chains.",
  },
];

export default function EnterprisePage() {
  const breadcrumbSchema = createBreadcrumbSchema([
    { name: "Home", href: "/" },
    { name: "Enterprise" },
  ]);

  return (
    <div
      className="min-h-screen"
      style={{ backgroundColor: "var(--landing-bg)" }}
    >
      <Script
        id="enterprise-breadcrumb"
        type="application/ld+json"
        strategy="beforeInteractive"
      >
        {JSON.stringify(breadcrumbSchema)}
      </Script>

      {/* Hero */}
      <section className="pt-20 pb-16 md:pt-28 md:pb-24">
        <div className="max-w-4xl mx-auto px-5 text-center">
          <p
            className="text-xs font-semibold uppercase tracking-widest mb-4"
            style={{
              fontFamily: "'JetBrains Mono', monospace",
              color: "var(--landing-accent)",
            }}
          >
            ENTERPRISE
          </p>
          <h1
            className="text-4xl md:text-5xl lg:text-6xl font-bold tracking-[-0.04em] mb-6"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              color: "var(--landing-text-primary)",
            }}
          >
            Give Your AI Agents a Corporate Wallet
            <br />
            <span style={{ color: "var(--landing-accent)" }}>
              With CFO-Grade Controls
            </span>
          </h1>

          <p
            className="text-lg max-w-3xl mx-auto mb-10"
            style={{
              fontFamily: "'Inter', sans-serif",
              color: "var(--landing-text-tertiary)",
            }}
          >
            83% of enterprises deploy AI agents. Zero have policy-controlled
            payment infrastructure. Until now.
          </p>

          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <a
              href="mailto:contact@sardis.sh"
              className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] inline-block hover:opacity-90"
              style={{
                fontFamily: "'Inter', sans-serif",
                backgroundColor: "var(--landing-accent)",
              }}
            >
              Book a Demo
            </a>
            <Link
              href="/docs"
              className="rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] inline-block hover:border-[var(--landing-text-muted)]"
              style={{
                fontFamily: "'Inter', sans-serif",
                border: "1px solid var(--landing-border)",
                color: "var(--landing-text-secondary)",
              }}
            >
              View Documentation
            </Link>
          </div>
        </div>
      </section>

      {/* Capabilities */}
      <section className="pb-20 md:pb-32">
        <div className="max-w-6xl mx-auto px-5">
          <div className="text-center mb-16">
            <h2
              className="text-3xl md:text-4xl font-bold tracking-[-0.03em] mb-4"
              style={{
                fontFamily: "'Space Grotesk', sans-serif",
                color: "var(--landing-text-primary)",
              }}
            >
              Enterprise Capabilities
            </h2>
            <p
              className="text-base max-w-2xl mx-auto"
              style={{
                fontFamily: "'Inter', sans-serif",
                color: "var(--landing-text-tertiary)",
              }}
            >
              Everything your finance and security teams need to trust
              autonomous agent spending.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {capabilities.map((cap) => (
              <div
                key={cap.title}
                className="rounded-[14px] p-8"
                style={{
                  backgroundColor: "var(--landing-surface)",
                  border: "1px solid var(--landing-border)",
                }}
              >
                <h3
                  className="font-semibold mb-3"
                  style={{
                    fontFamily: "'Space Grotesk', sans-serif",
                    fontSize: "18px",
                    color: "var(--landing-text-primary)",
                  }}
                >
                  {cap.title}
                </h3>
                <p
                  className="text-[14px] font-light leading-[22px]"
                  style={{
                    fontFamily: "'Inter', sans-serif",
                    color: "var(--landing-text-tertiary)",
                  }}
                >
                  {cap.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-20 md:pb-32">
        <div className="max-w-3xl mx-auto px-5 text-center">
          <h2
            className="text-3xl md:text-4xl font-bold tracking-[-0.03em] mb-4"
            style={{
              fontFamily: "'Space Grotesk', sans-serif",
              color: "var(--landing-text-primary)",
            }}
          >
            Ready to deploy?
          </h2>
          <p
            className="text-base mb-8"
            style={{
              fontFamily: "'Inter', sans-serif",
              color: "var(--landing-text-tertiary)",
            }}
          >
            Get a custom deployment plan with dedicated support, custom SLAs,
            and compliance assistance.
          </p>
          <a
            href="mailto:contact@sardis.sh"
            className="text-white rounded-lg py-3.5 px-9 transition-colors font-medium text-[15px] inline-block hover:opacity-90"
            style={{
              fontFamily: "'Inter', sans-serif",
              backgroundColor: "var(--landing-accent)",
            }}
          >
            Contact Sales
          </a>
        </div>
      </section>
    </div>
  );
}
