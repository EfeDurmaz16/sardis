import type { Metadata } from "next"
import Link from "next/link"
import type { ReactNode } from "react"

export const metadata: Metadata = {
  title: "RFC: Shared Trust Semantics for Agentic Commerce",
  description:
    "A draft RFC for the portable trust vocabulary underneath agentic commerce, payment protocols, checkout protocols, wallet abstractions, and agent identity systems.",
  alternates: { canonical: "/rfc/shared-trust-semantics" },
  openGraph: {
    title: "RFC: Shared Trust Semantics for Agentic Commerce",
    description:
      "Identity, authority, delegation, constraints, mandates, approvals, policy, evidence, receipts, and verification for consequential agent action.",
    url: "https://sardis.sh/rfc/shared-trust-semantics",
    type: "article",
  },
}

const coreObjects = [
  {
    title: "Principal",
    body: "The human, organization, or system that owns the authority being delegated.",
    items: ["stable identifier", "issuer or namespace", "accountability boundary", "optional organization or team context"],
  },
  {
    title: "Agent",
    body: "The non-human actor requesting or executing a consequential action.",
    items: ["stable identifier", "key material or verification method", "runtime or provider metadata when available", "relationship to principal", "revocation status"],
  },
  {
    title: "Mandate",
    body: "A signed statement delegating bounded authority from a principal to an agent.",
    items: ["issuer", "subject agent", "principal", "allowed action class", "constraints", "validity window", "revocation reference", "signature or proof binding"],
  },
  {
    title: "Constraint",
    body: "A machine-verifiable limit on what an agent may do. Unknown constraints must fail closed unless an enclosing protocol explicitly defines a safe downgrade rule.",
    items: ["merchant allowlist", "category restriction", "amount limits", "currency or rail restriction", "time window", "approval threshold", "purpose requirement"],
  },
  {
    title: "Policy",
    body: "An enforcement program that evaluates a proposed action against mandates, constraints, account state, risk state, and local rules before execution.",
    items: ["policy identifier", "policy version", "input action hash", "decision", "reason codes", "evaluated constraints", "evaluator identity", "evaluation time"],
  },
  {
    title: "Approval",
    body: "A first-class transition that changes the authorization state of a proposed action. Approvals are state transitions that other systems can verify.",
    items: ["approver identity", "approval scope", "approval time", "action or action class covered", "expiry", "evidence of consent", "revocation or rejection state"],
  },
  {
    title: "Evidence",
    body: "The durable material used to justify, audit, or verify an action.",
    items: ["user instruction", "mandate hash", "merchant quote", "invoice or cart snapshot", "policy decision record", "approval record", "payment object", "settlement receipt"],
  },
  {
    title: "Receipt",
    body: "A signed or otherwise verifiable statement that a verifier accepted, rejected, settled, or observed an action.",
    items: ["issuer", "referenced action", "result", "timestamp", "verifier signature or proof", "error information when rejected"],
  },
  {
    title: "Action",
    body: "A proposed or completed consequential operation by an agent.",
    items: ["action identifier", "action type", "principal", "agent", "mandate reference", "policy decision reference", "approval reference when required", "evidence references", "receipt references", "status"],
  },
]

const lifecycle = [
  "Propose action.",
  "Bind action to mandate.",
  "Evaluate policy before execution.",
  "Request approval when required.",
  "Execute only after policy and approval state allow it.",
  "Emit evidence.",
  "Emit receipt.",
  "Make the final state independently verifiable.",
]

const verification = [
  "the agent identity was valid at the time of action",
  "the mandate was valid at the time of action",
  "the action was inside mandate constraints",
  "the policy decision was produced before execution",
  "required approvals existed before execution",
  "evidence references match the action being verified",
  "receipts refer to the same action hash",
  "no known revocation invalidated the authority",
]

const security = [
  "fail closed on unknown constraints",
  "evaluate policy before signing or executing payment instructions",
  "bind mandates to specific agents or proof-of-possession keys",
  "prevent replay through nonces, expiry, and action hashes",
  "preserve enough evidence for third-party verification",
  "avoid logging secrets, private keys, raw credentials, and sensitive payment data",
  "distinguish authorization proof from settlement proof",
  "make revocation checkable",
  "make bypass paths visible in audit output",
]

const related = ["x402", "MPP", "ACP", "AP2", "TAP", "MCP", "A2A", "OSP", "OAPS"]

export default function SharedTrustSemanticsRFC() {
  return (
    <main style={{ background: "#FDFBF7", color: "#1A1614", minHeight: "100vh" }}>
      <nav style={{ borderBottom: "1px solid rgba(26,22,20,0.08)", padding: "18px 24px" }}>
        <div style={{ maxWidth: 820, margin: "0 auto", display: "flex", justifyContent: "space-between" }}>
          <Link href="/" style={{ color: "inherit", textDecoration: "none", fontWeight: 700 }}>Sardis</Link>
          <Link href="/manifesto" style={{ color: "rgba(26,22,20,0.56)", textDecoration: "none", fontSize: 13 }}>Manifesto</Link>
        </div>
      </nav>
      <article style={{ maxWidth: 820, margin: "0 auto", padding: "64px 24px 96px" }}>
        <p style={eyebrow}>Draft RFC · May 2026</p>
        <h1 style={title}>Shared trust semantics for agentic commerce</h1>
        <p style={lede}>
          Agentic commerce needs shared trust semantics underneath payment protocols, checkout protocols, wallet abstractions, agent identity systems, and service-discovery layers.
        </p>

        <Section title="Summary">
          <p style={paragraph}>
            The goal is not to replace specialized protocols. x402, MPP, ACP, AP2, TAP, MCP, A2A, OSP, and other protocols can each own useful slices of the stack. The goal is to define the minimum common trust vocabulary that allows independent systems to verify the same consequential agent action.
          </p>
          <p style={paragraph}>A verifier should be able to answer:</p>
          <Bullets items={["who acted", "on whose behalf", "under which authority", "with which constraints", "against which policy", "with which approval state", "producing which evidence", "resulting in which receipt", "with which accountability trail"]} />
        </Section>

        <Section title="Motivation">
          <p style={paragraph}>Agent payment and agentic commerce protocols are emerging before the market has matured. That is healthy at the product layer. Different protocols should explore payment movement, payment negotiation, checkout, mandate structure, agent recognition, and service provisioning.</p>
          <p style={paragraph}>The risk is that each protocol also invents its own private trust dialect.</p>
          <p style={paragraph}>If one system means mandate as a signed user intent, another means mandate as checkout consent, another means receipt as settlement proof, and another means receipt as verifier acceptance, then integrations technically work while trust does not compose.</p>
          <p style={paragraph}>Agentic commerce does not only need a way to move money. It needs a way to prove that a non-human actor was allowed to take a consequential action before the action happened.</p>
        </Section>

        <Section title="Non-goals">
          <Bullets items={["a new payment rail", "a new wallet standard", "a checkout protocol", "a replacement for AP2, ACP, TAP, x402, MPP, MCP, A2A, or OSP", "a universal policy language", "a custody model", "a compliance regime"]} />
        </Section>

        <Section title="Core objects">
          <div style={{ display: "grid", gap: 18 }}>
            {coreObjects.map((object) => (
              <div key={object.title} style={{ border: "1px solid rgba(26,22,20,0.12)", padding: 22, borderRadius: 8 }}>
                <h3 style={{ margin: "0 0 8px", fontSize: 18 }}>{object.title}</h3>
                <p style={{ ...paragraph, marginBottom: 12 }}>{object.body}</p>
                <Bullets items={object.items} />
              </div>
            ))}
          </div>
        </Section>

        <Section title="Action lifecycle">
          <ol style={{ paddingLeft: 22, margin: 0 }}>
            {lifecycle.map((item) => <li key={item} style={listItem}>{item}</li>)}
          </ol>
        </Section>

        <Section title="Verification rules">
          <Bullets items={verification} />
        </Section>

        <Section title="Security requirements">
          <Bullets items={security} />
        </Section>

        <Section title="Unix-shaped design">
          <p style={paragraph}>The trust substrate should be small enough to compose.</p>
          <p style={paragraph}>The primitive should not require every wallet, rail, checkout surface, merchant, agent runtime, and protocol to disappear into one platform. A good implementation should do one thing well:</p>
          <blockquote style={pull}>Take a proposed consequential action, bind it to authority, evaluate policy before execution, require approval when needed, emit evidence, and make the result verifiable by someone else.</blockquote>
          <p style={paragraph}>Everything around that should compose.</p>
        </Section>

        <Section title="Sardis mapping">
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 15 }}>
            <tbody>
              {[
                ["Principal", "Account, organization, owner, or funding authority"],
                ["Agent", "Agent identity and runtime registration"],
                ["Mandate", "Signed spending mandate"],
                ["Constraint", "Merchant, category, amount, period, rail, and approval rules"],
                ["Policy", "Execution-path policy engine"],
                ["Approval", "Approval queue and approval state transition"],
                ["Evidence", "Audit event, mandate hash, policy decision, quote, and payment object"],
                ["Receipt", "Payment receipt, settlement receipt, verifier receipt"],
                ["Action", "One-time payment object or proposed economic action"],
              ].map(([left, right]) => (
                <tr key={left}>
                  <th style={cellHead}>{left}</th>
                  <td style={cell}>{right}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ ...paragraph, marginTop: 22 }}>Sardis should be one implementation of the payment side of this trust substrate, not the owner of the substrate.</p>
        </Section>

        <Section title="Related work">
          <p style={paragraph}>{related.join(", ")}</p>
        </Section>
      </article>
    </main>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return <section style={{ marginTop: 48 }}><h2 style={heading}>{title}</h2>{children}</section>
}

function Bullets({ items }: { items: string[] }) {
  return <ul style={{ paddingLeft: 20, margin: 0 }}>{items.map((item) => <li key={item} style={listItem}>{item}</li>)}</ul>
}

const eyebrow = { fontSize: 12, letterSpacing: "0.1em", textTransform: "uppercase" as const, color: "rgba(26,22,20,0.42)", marginBottom: 14 }
const title = { fontSize: "clamp(34px, 6vw, 54px)", lineHeight: 1.04, letterSpacing: "-0.05em", margin: "0 0 24px" }
const lede = { fontSize: 20, lineHeight: 1.62, color: "rgba(26,22,20,0.68)", marginBottom: 30 }
const paragraph = { fontSize: 17, lineHeight: 1.76, color: "rgba(26,22,20,0.84)", margin: "0 0 18px" }
const heading = { fontSize: 24, lineHeight: 1.2, letterSpacing: "-0.03em", margin: "0 0 18px" }
const listItem = { marginBottom: 8, lineHeight: 1.6, color: "rgba(26,22,20,0.84)" }
const pull = { borderLeft: "2px solid #1A1614", paddingLeft: 20, margin: "22px 0", fontSize: 18, lineHeight: 1.58, fontWeight: 650 }
const cellHead = { textAlign: "left" as const, verticalAlign: "top" as const, borderTop: "1px solid rgba(26,22,20,0.12)", padding: "12px 16px 12px 0", width: "28%" }
const cell = { borderTop: "1px solid rgba(26,22,20,0.12)", padding: "12px 0", color: "rgba(26,22,20,0.78)", lineHeight: 1.5 }
