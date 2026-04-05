import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "FAQ — Sardis",
  description:
    "Frequently asked questions about Sardis, the Payment OS for the Agent Economy. Learn about AI agent payments, MPC wallets, spending policies, supported chains, pricing, and compliance.",
  alternates: { canonical: "/faq" },
  openGraph: {
    title: "FAQ — Sardis",
    description:
      "Frequently asked questions about Sardis, the Payment OS for the Agent Economy.",
    url: "https://sardis.sh/faq",
    siteName: "Sardis",
    type: "website",
  },
}

const faqs: { question: string; answer: string }[] = [
  {
    question: "What is Sardis?",
    answer:
      "Sardis is the Payment OS for the Agent Economy. It provides non-custodial MPC wallets and a natural language policy engine so AI agents can make real financial transactions safely. Every payment is verified against spending rules before it reaches the blockchain.",
  },
  {
    question: "How do AI agents make payments with Sardis?",
    answer:
      "An AI agent calls the Sardis SDK or API with a payment intent. Sardis evaluates the request against the agent's spending policy, checks compliance rules, and if everything passes, signs and broadcasts the transaction using an MPC wallet. The agent never holds private keys directly.",
  },
  {
    question: "What are spending policies?",
    answer:
      "Spending policies are human-readable rules that control what an AI agent can and cannot spend money on. You write them in plain English — for example, \"maximum $100 per transaction, only for SaaS subscriptions, no weekend purchases.\" Sardis enforces these rules at the infrastructure level before any transaction is signed.",
  },
  {
    question: "How does Sardis prevent unauthorized transactions?",
    answer:
      "Sardis uses a fail-closed architecture. Every transaction must pass through the policy engine, compliance checks (KYC/AML), and rate limiting before an MPC signature is generated. If any check fails, the transaction is rejected. The agent never has direct access to signing keys.",
  },
  {
    question: "What chains and tokens does Sardis support?",
    answer:
      "Sardis supports Base, Polygon, Ethereum, Arbitrum, and Optimism. Supported tokens include USDC, USDT, EURC, and PYUSD. Base with USDC is the recommended default for the lowest fees and fastest settlement.",
  },
  {
    question: "What is an MPC wallet?",
    answer:
      "MPC (Multi-Party Computation) wallets split a private key into multiple shares held by different parties. No single party — including Sardis — ever holds the complete key. This means your agent's funds are non-custodial: Sardis can enforce policies and co-sign transactions without being able to unilaterally move funds.",
  },
  {
    question: "How much does Sardis cost?",
    answer:
      "Sardis offers a free tier with simulation mode that requires no API key. Production usage is priced on a usage-based model with 0% merchant fees on USDC stablecoin checkout. Enterprise plans with dedicated support and custom SLAs are available on request.",
  },
  {
    question: "Is Sardis compliant with regulations?",
    answer:
      "Yes. Sardis integrates KYC verification (via Didit), AML and sanctions screening (via Elliptic), and maintains an append-only audit trail with cryptographic Merkle anchoring. All compliance checks run automatically before transactions are signed.",
  },
  {
    question: "What is the AP2 protocol?",
    answer:
      "AP2 (Agent Payment Protocol) is a consortium standard developed by Google, PayPal, Mastercard, and Visa for AI agent commerce. It defines a mandate chain — Intent, Cart, Payment — that Sardis verifies end-to-end before executing any transaction. This ensures agents follow proper purchasing workflows.",
  },
  {
    question: "How do I integrate Sardis into my AI agent?",
    answer:
      "Install the Python SDK with pip install sardis or the TypeScript SDK with npm install @sardis/sdk. Create an API key, define a spending policy, and call client.pay() from your agent's code. The full setup takes under 10 minutes. Sardis also offers a 52-tool MCP server for Claude Desktop and Cursor.",
  },
  {
    question: "What is a financial hallucination?",
    answer:
      "A financial hallucination occurs when an AI agent generates a plausible but incorrect financial action — like paying the wrong vendor, sending the wrong amount, or executing a duplicate transaction. Sardis prevents financial hallucinations by validating every payment against deterministic spending policies before signing.",
  },
  {
    question: "Does Sardis support fiat payments?",
    answer:
      "Yes. Sardis supports fiat on-ramp through Coinbase Onramp and virtual Visa/Mastercard card issuance through Stripe Issuing. This lets agents pay traditional merchants that don't accept crypto, while the underlying settlement still uses stablecoins for speed and cost efficiency.",
  },
  {
    question: "What makes Sardis different from regular payment processors?",
    answer:
      "Regular payment processors like Stripe are designed for human-initiated transactions with manual approval flows. Sardis is purpose-built for autonomous AI agents that transact without human oversight. It replaces manual approval with programmable spending policies, MPC co-signing, and real-time compliance checks.",
  },
  {
    question: "Can I set spending limits for my AI agents?",
    answer:
      "Yes. Spending policies support per-transaction limits, daily/weekly/monthly budgets, merchant category restrictions, time-of-day rules, and chain/token constraints. You can also set different policies for different agents, allowing fine-grained control over each agent's financial authority.",
  },
  {
    question: "What happens if an agent tries to exceed its spending policy?",
    answer:
      "The transaction is rejected immediately. Sardis uses a fail-closed model — if the policy check fails for any reason, no signature is produced and no funds move. The rejection is logged in the append-only audit trail with the specific policy violation, so you can review why the transaction was blocked.",
  },
  {
    question: "What AI frameworks does Sardis integrate with?",
    answer:
      "Sardis has native integrations with Browser Use, CrewAI, OpenAI Agents SDK, Vercel AI SDK, LangChain, Activepieces, and n8n. Each integration is available as a separate package — for example, pip install sardis-crewai or npm install @sardis/ai-sdk.",
  },
  {
    question: "Is Sardis open source?",
    answer:
      "Sardis follows an open-core model. The Python and TypeScript SDKs, MCP server, and framework integrations are open source on GitHub. The core infrastructure — policy engine, MPC signing, compliance pipeline — is proprietary to ensure security and auditability.",
  },
  {
    question: "How does the audit trail work?",
    answer:
      "Every transaction, policy evaluation, and compliance check is recorded in an append-only ledger. Entries are cryptographically anchored using Merkle trees, making the log tamper-evident. You can query the audit trail via API or the Sardis dashboard to trace any agent's complete financial history.",
  },
]

/* Static JSON-LD — all content is hardcoded, no user input */
const faqJsonLdString = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: faqs.map((faq) => ({
    "@type": "Question",
    name: faq.question,
    acceptedAnswer: {
      "@type": "Answer",
      text: faq.answer,
    },
  })),
})

const breadcrumbJsonLdString = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    {
      "@type": "ListItem",
      position: 1,
      name: "Home",
      item: "https://sardis.sh",
    },
    {
      "@type": "ListItem",
      position: 2,
      name: "FAQ",
      item: "https://sardis.sh/faq",
    },
  ],
})

export default function FAQPage() {
  return (
    <>
      {/* eslint-disable-next-line react/no-danger -- static JSON-LD, no user input */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: faqJsonLdString }} />
      {/* eslint-disable-next-line react/no-danger -- static JSON-LD, no user input */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: breadcrumbJsonLdString }} />
      <main
        style={{
          background: "#FDFBF7",
          color: "#1A1614",
          minHeight: "100vh",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
        }}
      >
        {/* Nav */}
        <nav
          style={{
            display: "flex",
            justifyContent: "center",
            padding: "24px 16px 0",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              width: "100%",
              maxWidth: 1100,
              padding: "12px 24px",
              background: "rgba(26,22,20,0.04)",
              border: "1px solid rgba(26,22,20,0.06)",
              borderRadius: 100,
            }}
          >
            <Link
              href="/landing"
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                textDecoration: "none",
              }}
            >
              <svg width={20} height={20} viewBox="0 0 28 28" fill="none">
                <path
                  d="M20 5H10a7 7 0 000 14h2"
                  stroke="#1A1614"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M8 23h10a7 7 0 000-14h-2"
                  stroke="#1A1614"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>
              <span
                style={{
                  fontSize: 15,
                  fontWeight: 700,
                  color: "#1A1614",
                  letterSpacing: "-0.02em",
                }}
              >
                Sardis
              </span>
            </Link>
            <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
              <Link
                href="/landing"
                style={{
                  fontSize: 13,
                  color: "rgba(26,22,20,0.45)",
                  textDecoration: "none",
                }}
              >
                Home
              </Link>
              <a
                href="https://docs.sardis.sh"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  fontSize: 13,
                  color: "rgba(26,22,20,0.45)",
                  textDecoration: "none",
                }}
              >
                Docs
              </a>
            </div>
          </div>
        </nav>

        {/* Header */}
        <section
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "80px 16px 48px",
            textAlign: "center",
          }}
        >
          <span
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: "rgba(26,22,20,0.35)",
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              marginBottom: 16,
            }}
          >
            Frequently Asked Questions
          </span>
          <h1
            style={{
              fontSize: "clamp(32px, 5vw, 56px)",
              fontWeight: 800,
              letterSpacing: "-0.04em",
              lineHeight: 1.1,
              maxWidth: 700,
              margin: 0,
            }}
          >
            Everything you need to know about Sardis
          </h1>
          <p
            style={{
              fontSize: 17,
              color: "rgba(26,22,20,0.45)",
              lineHeight: "28px",
              maxWidth: 540,
              marginTop: 20,
            }}
          >
            AI agent payments, spending policies, MPC wallets, compliance, and
            integration — answered.
          </p>
        </section>

        {/* FAQ Accordion */}
        <section
          style={{
            maxWidth: 760,
            margin: "0 auto",
            padding: "0 16px 96px",
          }}
        >
          {faqs.map((faq, i) => (
            <details
              key={i}
              style={{
                borderTop:
                  i === 0 ? "1px solid rgba(26,22,20,0.08)" : undefined,
                borderBottom: "1px solid rgba(26,22,20,0.08)",
              }}
            >
              <summary
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "20px 0",
                  cursor: "pointer",
                  listStyle: "none",
                  fontSize: 16,
                  fontWeight: 600,
                  color: "#1A1614",
                  lineHeight: "24px",
                }}
              >
                {faq.question}
                <span
                  style={{
                    flexShrink: 0,
                    marginLeft: 16,
                    fontSize: 18,
                    color: "rgba(26,22,20,0.3)",
                    transition: "transform 200ms ease",
                  }}
                  aria-hidden="true"
                >
                  +
                </span>
              </summary>
              <div
                style={{
                  padding: "0 0 20px",
                  fontSize: 15,
                  color: "rgba(26,22,20,0.55)",
                  lineHeight: "26px",
                  maxWidth: 660,
                }}
              >
                {faq.answer}
              </div>
            </details>
          ))}
        </section>

        {/* CTA */}
        <section
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            padding: "64px 16px 96px",
            textAlign: "center",
            background: "rgba(26,22,20,0.02)",
            borderTop: "1px solid rgba(26,22,20,0.06)",
          }}
        >
          <h2
            style={{
              fontSize: 28,
              fontWeight: 700,
              letterSpacing: "-0.03em",
              margin: "0 0 12px",
            }}
          >
            Ready to get started?
          </h2>
          <p
            style={{
              fontSize: 15,
              color: "rgba(26,22,20,0.45)",
              lineHeight: "24px",
              maxWidth: 420,
              marginBottom: 28,
            }}
          >
            Give your AI agents safe spending power in under 10 minutes.
          </p>
          <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
            <a
              href="https://app.sardis.sh"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                padding: "14px 28px",
                background: "#1A1614",
                color: "#FDFBF7",
                borderRadius: 100,
                fontSize: 14,
                fontWeight: 500,
                textDecoration: "none",
              }}
            >
              Get started free
              <span style={{ fontSize: 13 }}>&#8594;</span>
            </a>
            <a
              href="https://docs.sardis.sh"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "14px 28px",
                border: "1px solid rgba(26,22,20,0.1)",
                borderRadius: 100,
                fontSize: 14,
                color: "rgba(26,22,20,0.45)",
                textDecoration: "none",
              }}
            >
              Read the docs
            </a>
          </div>
        </section>

        {/* Footer */}
        <footer
          style={{
            display: "flex",
            justifyContent: "center",
            padding: "24px 16px",
            borderTop: "1px solid rgba(26,22,20,0.06)",
          }}
        >
          <span
            style={{
              fontSize: 12,
              color: "rgba(26,22,20,0.3)",
            }}
          >
            &copy; {new Date().getFullYear()} Sardis Labs, Inc.
          </span>
        </footer>
      </main>
    </>
  )
}
