import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "AI Agent Economy Glossary — 34 Key Terms Defined",
  description:
    "Comprehensive glossary of AI agent economy terms: MPC wallets, spending policies, financial hallucinations, AP2 protocol, KYA, mandate chains, stablecoins, and more. Definitions for builders and researchers.",
  keywords: [
    "AI agent glossary",
    "agent economy terms",
    "AI payments glossary",
    "MPC wallet definition",
    "spending policy definition",
    "financial hallucination definition",
    "AP2 protocol",
    "agent economy",
  ],
  authors: [{ name: "Sardis Labs" }],
  openGraph: {
    title: "AI Agent Economy Glossary — 34 Key Terms",
    description:
      "Comprehensive glossary of AI agent economy terms. Definitions for MPC wallets, spending policies, mandate chains, compliance gates, and more.",
    url: "https://sardis.sh/glossary",
    type: "website",
  },
  alternates: { canonical: "/glossary" },
}

interface GlossaryTerm {
  term: string
  definition: string
  link?: string
}

const terms: GlossaryTerm[] = [
  {
    term: "AI Agent",
    definition:
      "An autonomous software program that uses artificial intelligence to perceive its environment, make decisions, and take actions to achieve goals — including financial transactions — without continuous human oversight.",
    link: "/blog/what-is-ai-agent-payments",
  },
  {
    term: "Agent Economy",
    definition:
      "The emerging ecosystem where AI agents are first-class economic participants: earning revenue, paying for services, managing budgets, and transacting with humans, businesses, and other agents.",
    link: "/blog/what-is-ai-agent-payments#future",
  },
  {
    term: "AP2 Protocol",
    definition:
      "Agent Payment Protocol — an open standard developed by a consortium including Google, PayPal, Mastercard, and Visa that defines how AI agents express payment intent, verify identity, and construct mandate chains for financial transactions.",
    link: "/blog/what-is-ai-agent-payments#key-concepts",
  },
  {
    term: "Audit Trail",
    definition:
      "An append-only, Merkle-tree-anchored record of every transaction, policy evaluation, compliance check, and signing event. Provides cryptographic proof that no record has been altered after the fact.",
  },
  {
    term: "CCTP",
    definition:
      "Cross-Chain Transfer Protocol — Circle's protocol for trustless USDC transfers between blockchains. CCTP v2 uses unified addresses across all chains, eliminating the need for chain-specific bridging.",
  },
  {
    term: "Chain Routing",
    definition:
      "The automatic selection of the optimal blockchain for a transaction based on cost, speed, and recipient preference. Agent payment infrastructure routes payments across Base, Polygon, Ethereum, Arbitrum, and Optimism without requiring the agent to specify a chain.",
  },
  {
    term: "Compliance Gate",
    definition:
      "An automated checkpoint that every agent transaction must pass before execution. Includes sanctions screening, KYC verification, AML monitoring, and velocity checks. Follows fail-closed design: if any check cannot complete, the transaction is rejected.",
  },
  {
    term: "Context Drift",
    definition:
      "The gradual degradation of an AI agent's understanding of its original instructions as conversation history grows. A leading cause of financial hallucinations in long-running agent sessions.",
    link: "/blog/what-is-financial-hallucination#why-it-happens",
  },
  {
    term: "Credential",
    definition:
      "A cryptographic attestation that links an AI agent to its owning organization, spending policies, and behavioral constraints. Used for agent identity verification in protocols like TAP.",
  },
  {
    term: "EURC",
    definition:
      "Euro Coin — a euro-backed stablecoin issued by Circle, available on Base, Polygon, and Ethereum. Used for agent payments denominated in euros.",
  },
  {
    term: "Fail-Closed",
    definition:
      "A security design principle where every component defaults to deny. If any check cannot complete (timeout, error, ambiguous result), the transaction is rejected. The opposite of fail-open, where ambiguity defaults to approval.",
    link: "/blog/what-is-ai-agent-payments#security-model",
  },
  {
    term: "Financial Hallucination",
    definition:
      "When an AI agent makes an incorrect, unauthorized, or unintended financial transaction. The financial equivalent of an LLM confidently stating a false fact — except the output is wrong money movement, not wrong text.",
    link: "/blog/what-is-financial-hallucination",
  },
  {
    term: "Gas Optimization",
    definition:
      "Techniques to minimize blockchain transaction fees (gas costs) for agent payments. Includes batching transactions, selecting low-cost chains, and using paymasters like Circle Paymaster that sponsor gas in USDC.",
  },
  {
    term: "Identity Attestation",
    definition:
      "A cryptographic proof that verifies an AI agent's identity, capabilities, and authorization level. Part of the TAP (Trust Anchor Protocol) framework using Ed25519 and ECDSA-P256 key pairs.",
  },
  {
    term: "KYA (Know Your Agent)",
    definition:
      "The agent equivalent of KYC (Know Your Customer). Establishes who created the agent, what organization it belongs to, what it is authorized to do, what LLM it runs, and its behavioral history.",
    link: "/blog/what-is-ai-agent-payments#key-concepts",
  },
  {
    term: "KYC (Know Your Customer)",
    definition:
      "Identity verification for humans and organizations. Required by financial regulations before processing transactions. In agent payment systems, KYC applies to the agent's owner, not the agent itself.",
  },
  {
    term: "Mandate",
    definition:
      "A formal authorization that defines what an AI agent is permitted to do financially. Part of the AP2 protocol's mandate chain: Intent (what to buy), Cart (specific items and prices), Payment (actual transfer).",
    link: "/blog/what-is-ai-agent-payments#key-concepts",
  },
  {
    term: "MPC Wallet",
    definition:
      "Multi-Party Computation wallet — splits signing authority across multiple parties so no single entity ever holds the complete private key. Critical for agent payments because even a compromised agent cannot extract the key.",
    link: "/blog/what-is-ai-agent-payments#key-concepts",
  },
  {
    term: "Non-Custodial",
    definition:
      "An architecture where the platform never holds, stores, or has access to private keys. All signing is performed through distributed MPC nodes. If the platform is compromised, funds remain safe.",
    link: "/blog/what-is-ai-agent-payments#security-model",
  },
  {
    term: "Payment Channel",
    definition:
      "A mechanism for processing multiple transactions between parties without recording each one individually on the blockchain. Reduces costs for high-frequency agent-to-agent micropayments.",
  },
  {
    term: "Policy Engine",
    definition:
      "The component that compiles natural language spending policies into evaluable constraint sets and verifies every transaction before the MPC signing ceremony. Runs in a deterministic sandbox with no network access during evaluation.",
    link: "/blog/what-is-ai-agent-payments#how-sardis-solves-it",
  },
  {
    term: "Prompt Injection",
    definition:
      "An adversarial attack where malicious content in an agent's input contains hidden instructions that override the agent's original behavior. A key cause of financial hallucinations when agents process untrusted input.",
    link: "/blog/what-is-financial-hallucination#why-it-happens",
  },
  {
    term: "PYUSD",
    definition:
      "PayPal USD — a dollar-backed stablecoin issued by PayPal, available on Ethereum. Supported as a payment token in multi-stablecoin agent payment systems.",
  },
  {
    term: "Rollback Protection",
    definition:
      "Mechanisms that prevent transaction reversals or state manipulation after a payment has been confirmed. In agent payments, this includes idempotency keys, nonce management, and finality verification.",
  },
  {
    term: "Safe Smart Account",
    definition:
      "A battle-tested, audited smart contract wallet (v1.4.1) used by over $100B in assets. Sardis deploys each agent wallet as a Safe with pre-configured spending policy modules.",
  },
  {
    term: "Sardis",
    definition:
      "The Payment OS for the Agent Economy. Open-core infrastructure providing non-custodial MPC wallets with natural language spending policies for AI agents. Supports USDC, USDT, EURC, and PYUSD across Base, Polygon, Ethereum, Arbitrum, and Optimism.",
    link: "/",
  },
  {
    term: "Spending Limit",
    definition:
      "A numerical constraint on agent spending — per transaction, per day, per week, or per month. Enforced at the MPC signing layer, not the application layer, so the agent cannot exceed it regardless of reasoning.",
  },
  {
    term: "Spending Policy",
    definition:
      "Natural language rules that define what an AI agent is allowed to spend. Compiled to on-chain constraints and cryptographically enforced before every transaction. Not suggestions — immutable guardrails.",
    link: "/blog/what-is-ai-agent-payments#key-concepts",
  },
  {
    term: "Stablecoin",
    definition:
      "A blockchain-native token pegged to a fiat currency like the US dollar or euro. Provides the speed and programmability of cryptocurrency without price volatility. USDC, USDT, EURC, and PYUSD are common examples used in agent payments.",
  },
  {
    term: "TAP Protocol",
    definition:
      "Trust Anchor Protocol — an identity verification framework for AI agents using Ed25519 and ECDSA-P256 cryptographic key pairs. Creates verifiable agent identity certificates linking agents to organizations and policies.",
    link: "/blog/what-is-ai-agent-payments#key-concepts",
  },
  {
    term: "Transaction Receipt",
    definition:
      "A cryptographic proof that a payment was executed, including the on-chain transaction hash, policy evaluation result, compliance check status, and timestamp. Part of the audit trail.",
  },
  {
    term: "USDC",
    definition:
      "USD Coin — a dollar-backed stablecoin issued by Circle. The dominant choice for agent payments due to regulatory compliance, multi-chain availability (Base, Polygon, Ethereum, Arbitrum, Optimism), and transparent reserves.",
  },
  {
    term: "USDT",
    definition:
      "Tether — the largest stablecoin by market cap, pegged to the US dollar. Available on Polygon, Ethereum, Arbitrum, and Optimism. Supported alongside USDC in multi-stablecoin agent payment systems.",
  },
  {
    term: "Wallet Factory",
    definition:
      "A smart contract that creates new agent wallets on demand with pre-configured spending policies and compliance modules. Enables programmatic wallet creation through SDK calls without manual contract deployment.",
  },
  {
    term: "WebAuthn",
    definition:
      "A W3C standard for passwordless authentication using cryptographic key pairs. Used in passkey-based authentication for agent payment dashboards and management interfaces.",
  },
  {
    term: "Zero-Knowledge Proof",
    definition:
      "A cryptographic method that allows one party to prove a statement is true without revealing the underlying data. Used in advanced agent payment systems for privacy-preserving compliance checks and policy verification.",
  },
]

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "DefinedTermSet",
  name: "AI Agent Economy Glossary",
  description:
    "Comprehensive glossary of AI agent economy and agent payment terms. 34 definitions covering MPC wallets, spending policies, mandate chains, compliance gates, and more.",
  url: "https://sardis.sh/glossary",
  inLanguage: "en",
  publisher: {
    "@type": "Organization",
    name: "Sardis Labs, Inc.",
    url: "https://sardis.sh",
  },
  hasDefinedTerm: terms.map((t) => ({
    "@type": "DefinedTerm",
    name: t.term,
    description: t.definition,
    url: `https://sardis.sh/glossary#${t.term.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`,
    inDefinedTermSet: "https://sardis.sh/glossary",
  })),
}

function JsonLd({ data }: { data: Record<string, unknown> }) {
  // Static JSON-LD structured data — hardcoded term definitions, not user input
  const html = JSON.stringify(data)
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: html }}
    />
  )
}

export default function Glossary() {
  return (
    <>
      <JsonLd data={jsonLd} />

      <div
        style={{
          minHeight: "100vh",
          background: "#FDFBF7",
          color: "#1A1614",
        }}
      >
        {/* Nav */}
        <nav
          style={{
            position: "sticky",
            top: 0,
            zIndex: 50,
            background: "rgba(253,251,247,0.92)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid rgba(26,22,20,0.06)",
            padding: "14px 0",
          }}
        >
          <div
            style={{
              maxWidth: 720,
              margin: "0 auto",
              padding: "0 24px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Link
              href="/"
              style={{
                fontSize: 15,
                fontWeight: 600,
                color: "#1A1614",
                textDecoration: "none",
                letterSpacing: "-0.02em",
              }}
            >
              Sardis
            </Link>
            <div style={{ display: "flex", gap: 20, fontSize: 13, color: "rgba(26,22,20,0.45)" }}>
              <Link href="/blog/what-is-ai-agent-payments" style={{ color: "inherit", textDecoration: "none" }}>
                AI Agent Payments
              </Link>
              <Link href="/blog/what-is-financial-hallucination" style={{ color: "inherit", textDecoration: "none" }}>
                Financial Hallucinations
              </Link>
            </div>
          </div>
        </nav>

        {/* Content */}
        <main
          style={{
            maxWidth: 720,
            margin: "0 auto",
            padding: "64px 24px 96px",
          }}
        >
          {/* Header */}
          <header style={{ marginBottom: 48 }}>
            <div
              style={{
                fontSize: 12,
                fontWeight: 500,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "rgba(26,22,20,0.35)",
                marginBottom: 16,
              }}
            >
              Reference
            </div>
            <h1
              style={{
                fontSize: "clamp(32px, 5vw, 44px)",
                fontWeight: 700,
                lineHeight: 1.12,
                letterSpacing: "-0.035em",
                color: "#1A1614",
                marginBottom: 20,
              }}
            >
              AI Agent Economy Glossary
            </h1>
            <p
              style={{
                fontSize: 18,
                lineHeight: 1.6,
                color: "rgba(26,22,20,0.55)",
                maxWidth: 560,
              }}
            >
              {terms.length} essential terms for understanding how AI agents make
              payments, manage wallets, and participate in the agent economy.
            </p>
            <div
              style={{
                marginTop: 20,
                fontSize: 13,
                color: "rgba(26,22,20,0.35)",
              }}
            >
              Last updated: April 4, 2026
            </div>
          </header>

          {/* Alphabet Jump Links */}
          <nav
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 6,
              marginBottom: 40,
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            {Array.from(new Set(terms.map((t) => t.term[0].toUpperCase()))).sort().map((letter) => (
              <a
                key={letter}
                href={`#letter-${letter}`}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 32,
                  height: 32,
                  borderRadius: 6,
                  background: "rgba(26,22,20,0.03)",
                  color: "#1A1614",
                  textDecoration: "none",
                  border: "1px solid rgba(26,22,20,0.06)",
                }}
              >
                {letter}
              </a>
            ))}
          </nav>

          {/* Terms */}
          <dl>
            {Array.from(new Set(terms.map((t) => t.term[0].toUpperCase())))
              .sort()
              .map((letter) => (
                <section key={letter} id={`letter-${letter}`} style={{ marginBottom: 40 }}>
                  <div
                    style={{
                      fontSize: 14,
                      fontWeight: 700,
                      color: "rgba(26,22,20,0.25)",
                      letterSpacing: "0.04em",
                      marginBottom: 16,
                      paddingBottom: 8,
                      borderBottom: "1px solid rgba(26,22,20,0.06)",
                    }}
                  >
                    {letter}
                  </div>
                  {terms
                    .filter((t) => t.term[0].toUpperCase() === letter)
                    .map((t) => {
                      const anchor = t.term.toLowerCase().replace(/[^a-z0-9]+/g, "-")
                      return (
                        <div
                          key={t.term}
                          id={anchor}
                          style={{
                            marginBottom: 24,
                          }}
                        >
                          <dt
                            style={{
                              fontSize: 17,
                              fontWeight: 600,
                              color: "#1A1614",
                              letterSpacing: "-0.01em",
                              marginBottom: 4,
                            }}
                          >
                            {t.link ? (
                              <Link href={t.link} style={{ color: "inherit", textDecoration: "none" }}>
                                {t.term}
                              </Link>
                            ) : (
                              t.term
                            )}
                          </dt>
                          <dd
                            style={{
                              fontSize: 15,
                              lineHeight: 1.7,
                              color: "rgba(26,22,20,0.6)",
                              margin: 0,
                            }}
                          >
                            {t.definition}
                            {t.link && (
                              <>
                                {" "}
                                <Link
                                  href={t.link}
                                  style={{
                                    color: "rgba(26,22,20,0.4)",
                                    fontSize: 13,
                                    textDecoration: "none",
                                  }}
                                >
                                  Learn more
                                </Link>
                              </>
                            )}
                          </dd>
                        </div>
                      )
                    })}
                </section>
              ))}
          </dl>

          {/* CTA */}
          <section
            style={{
              background: "#1A1614",
              color: "#FDFBF7",
              borderRadius: 12,
              padding: "40px 36px",
              textAlign: "center",
              marginTop: 32,
            }}
          >
            <h2
              style={{
                fontSize: 22,
                fontWeight: 700,
                letterSpacing: "-0.02em",
                marginBottom: 12,
              }}
            >
              Build with Sardis
            </h2>
            <p
              style={{
                fontSize: 15,
                color: "rgba(253,251,247,0.5)",
                marginBottom: 24,
                maxWidth: 400,
                marginLeft: "auto",
                marginRight: "auto",
              }}
            >
              Non-custodial MPC wallets with natural language spending policies
              for AI agents.
            </p>
            <div style={{ display: "flex", gap: 12, justifyContent: "center", flexWrap: "wrap" }}>
              <a
                href="https://sardis.sh/docs"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "10px 20px",
                  background: "#FDFBF7",
                  color: "#1A1614",
                  borderRadius: 100,
                  fontSize: 14,
                  fontWeight: 500,
                  textDecoration: "none",
                }}
              >
                Read the docs
              </a>
              <Link
                href="/blog/what-is-ai-agent-payments"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "10px 20px",
                  background: "rgba(253,251,247,0.08)",
                  color: "#FDFBF7",
                  borderRadius: 100,
                  fontSize: 14,
                  fontWeight: 500,
                  textDecoration: "none",
                  border: "1px solid rgba(253,251,247,0.1)",
                }}
              >
                AI Agent Payments Guide
              </Link>
            </div>
          </section>

          {/* Footer */}
          <footer
            style={{
              marginTop: 64,
              paddingTop: 32,
              borderTop: "1px solid rgba(26,22,20,0.06)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: 16,
              fontSize: 13,
              color: "rgba(26,22,20,0.35)",
            }}
          >
            <span>Sardis Labs, Inc.</span>
            <div style={{ display: "flex", gap: 20 }}>
              <Link
                href="/blog/what-is-ai-agent-payments"
                style={{ color: "inherit", textDecoration: "none" }}
              >
                AI Agent Payments
              </Link>
              <Link
                href="/blog/what-is-financial-hallucination"
                style={{ color: "inherit", textDecoration: "none" }}
              >
                Financial Hallucinations
              </Link>
              <Link href="/" style={{ color: "inherit", textDecoration: "none" }}>
                Home
              </Link>
            </div>
          </footer>
        </main>
      </div>
    </>
  )
}
