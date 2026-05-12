import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Agent Payments Are Necessary. Fragmented Trust Is Not.",
  description:
    "A research note on x402, MPP, ACP, AP2, TAP, early volume signals, and why agentic commerce needs shared trust semantics underneath payment protocols.",
  alternates: { canonical: "/blog/agent-payments-fragmented-trust" },
  openGraph: {
    title: "Agent Payments Are Necessary. Fragmented Trust Is Not.",
    description:
      "Agent payment protocols are emerging for the right reasons. The risk is fragmented trust semantics hardening before the market matures.",
    url: "https://sardis.sh/blog/agent-payments-fragmented-trust",
    type: "article",
    publishedTime: "2026-05-12T00:00:00Z",
    authors: ["Sardis"],
  },
}

const sections = [
  ["What is fragmenting", [
    "x402 is trying to make HTTP-native, per-request stablecoin payments work. MPP is trying to make machine payments method-agnostic. ACP is trying to make checkout programmatic. AP2 is trying to make mandates and delegated authorization verifiable. TAP is trying to let merchants recognize trusted agents and distinguish them from malicious bots.",
    "Each direction is defensible. Together, they reveal the real gap: payment movement, checkout, agent recognition, mandate signing, and credential relay are being standardized faster than the shared trust semantics underneath them.",
  ]],
  ["The data is already hard to read", [
    "Public activity numbers show how early and uneven this market still is.",
    "x402's official site reports large ecosystem numbers: tens of millions of transactions, tens of millions of dollars of 30-day volume, and tens of thousands of buyers and sellers. DeFiLlama, using a narrower DEX-volume methodology, shows much smaller 30-day and 7-day dollar flow. MPPscan shows thousands of agents and hundreds of servers, but only a few thousand dollars of recent volume on its public explorer.",
    "Those numbers are not interchangeable. They measure different scopes, chains, transaction types, and filtering assumptions.",
    "If the same ecosystem can produce very different answers to how much real agent commerce is happening, that is itself a trust-layer symptom. We do not yet have a mature shared vocabulary for what counts as an agent transaction, commercial demand, settlement, delegated authorization, or independently verifiable evidence.",
    "Low early volume does not mean the protocols are wrong. That would be the lazy critique. The stronger critique is different: if the market is still early, then this is exactly the time to avoid hardening the wrong abstractions.",
  ]],
  ["Micropayments are not the whole economy", [
    "The first wave of agent payment infrastructure naturally concentrates around micropayments and paid APIs. A model call, web scrape, search query, market-data lookup, browser session, image generation, or small compute job is a clean use case.",
    "That is real. It is also narrow.",
    "The harder version is an agent buying inventory, provisioning cloud infrastructure, signing a supplier agreement, ordering regulated services, paying a contractor, renewing insurance, booking logistics, or making a financial decision under constraints.",
    "In those cases, the payment succeeding is not enough. The system has to prove the action was legitimate before the money moved.",
  ]],
  ["The counterargument", [
    "The counterargument is strong: fragmentation is normal in early markets.",
    "Different protocols are exploring different layers. It would be wrong to force all of that into one protocol too early.",
    "The answer is not one giant standard that owns every layer. The answer is a shared trust substrate that lets specialized protocols compose without each redefining what trust means.",
    "x402 can be a payment movement primitive. MPP can be a payment negotiation primitive. ACP can be a checkout primitive. AP2 can be a mandate primitive. TAP can be an agent-recognition primitive.",
    "But unless the trust model across them is inspectable and portable, the agent economy becomes adapter glue with money attached.",
  ]],
  ["Private trust dialects do not become infrastructure", [
    "Product companies should compete on UX, distribution, compliance, liquidity, wallets, rails, integrations, risk models, and developer experience. That is where competition belongs.",
    "But the trust primitive underneath consequential agent action should not become a private dialect owned by one company.",
    "Private trust semantics can work for demos. They can work inside a closed ecosystem. They can work when one company controls the agent, the wallet, the checkout surface, the merchant network, the policy engine, and the audit log. They will not work for an economy.",
    "An economy needs independent verification. It needs another party to look at an action and understand the same thing: this agent acted for this principal, under this mandate, within these constraints, with this approval state, against this policy, producing this evidence, leaving this accountability trail.",
    "The first wave of protocols is necessary. The next layer has to be trust.",
  ]],
] as const

const sources = [
  ["x402 official site", "https://www.x402.org/"],
  ["Coinbase x402 docs", "https://docs.cdp.coinbase.com/x402/welcome"],
  ["DeFiLlama x402 volume", "https://defillama.com/protocol/x402"],
  ["MPP official site", "https://mpp.dev/"],
  ["MPPscan", "https://mppscan.org/"],
  ["Cloudflare MPP docs", "https://developers.cloudflare.com/agents/agentic-payments/mpp/"],
  ["MPP specifications", "https://paymentauth.org/"],
  ["OpenAI ACP announcement", "https://openai.com/index/buy-it-in-chatgpt/"],
  ["ACP docs", "https://www.agenticcommerce.dev/docs"],
  ["AP2 agent authorization docs", "https://ap2-protocol.org/ap2/agent_authorization/"],
  ["Visa TAP docs", "https://developer.visa.com/capabilities/trusted-agent-protocol/docs"],
  ["RFC 9421, HTTP Message Signatures", "https://www.rfc-editor.org/rfc/rfc9421.html"],
  ["Hardening x402 paper", "https://arxiv.org/abs/2604.11430"],
  ["A402 paper", "https://arxiv.org/abs/2603.01179"],
  ["AP2 red-team paper", "https://arxiv.org/abs/2601.22569"],
] as const

export default function FragmentedTrustArticle() {
  return (
    <main style={page}>
      <Nav />
      <article style={article}>
        <p style={eyebrow}>Research note · May 2026</p>
        <h1 style={title}>Agent payments are necessary. Fragmented trust is not.</h1>
        {[
          "The first wave of agent payment protocols is directionally correct.",
          "The web was not designed for software actors that can discover a resource, decide it is worth paying for, execute the payment, prove authorization, and continue the workflow without a human opening a checkout page. HTTP had a placeholder for payment, but not a living payment layer.",
          "Agents do not fit that shape.",
          "That is why protocols like x402, MPP, ACP, AP2, TAP, and similar efforts matter. They are not noise. They are early attempts to give non-human actors a way to pay, check out, prove intent, present authorization, and be recognized as legitimate traffic instead of malicious automation.",
          "The problem is not that these protocols exist. The problem is that agentic commerce is fragmenting before it has matured.",
        ].map((text) => <p key={text} style={paragraph}>{text}</p>)}
        {sections.map(([sectionTitle, body]) => (
          <section key={sectionTitle} style={{ marginTop: 44 }}>
            <h2 style={heading}>{sectionTitle}</h2>
            {body.map((text) => <p key={text} style={paragraph}>{text}</p>)}
          </section>
        ))}
        <section style={{ marginTop: 54, borderTop: "1px solid rgba(26,22,20,0.12)", paddingTop: 28 }}>
          <h2 style={heading}>Sources</h2>
          <ul style={{ paddingLeft: 20, margin: 0 }}>
            {sources.map(([label, href]) => (
              <li key={href} style={{ marginBottom: 8, lineHeight: 1.6 }}>
                <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: "#1A1614" }}>{label}</a>
              </li>
            ))}
          </ul>
        </section>
      </article>
    </main>
  )
}

function Nav() {
  return (
    <nav style={{ borderBottom: "1px solid rgba(26,22,20,0.08)", padding: "18px 24px" }}>
      <div style={{ maxWidth: 760, margin: "0 auto", display: "flex", justifyContent: "space-between" }}>
        <Link href="/" style={{ color: "inherit", textDecoration: "none", fontWeight: 700 }}>Sardis</Link>
        <Link href="/manifesto" style={{ color: "rgba(26,22,20,0.56)", textDecoration: "none", fontSize: 13 }}>Manifesto</Link>
      </div>
    </nav>
  )
}

const page = { background: "#FDFBF7", color: "#1A1614", minHeight: "100vh" }
const article = { maxWidth: 760, margin: "0 auto", padding: "64px 24px 96px" }
const eyebrow = { fontSize: 12, letterSpacing: "0.1em", textTransform: "uppercase" as const, color: "rgba(26,22,20,0.42)", marginBottom: 14 }
const title = { fontSize: "clamp(34px, 6vw, 54px)", lineHeight: 1.04, letterSpacing: "-0.05em", margin: "0 0 34px" }
const paragraph = { fontSize: 17, lineHeight: 1.78, color: "rgba(26,22,20,0.84)", margin: "0 0 20px" }
const heading = { fontSize: 24, lineHeight: 1.2, letterSpacing: "-0.03em", margin: "0 0 18px" }
