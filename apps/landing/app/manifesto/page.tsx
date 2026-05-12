import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "The Missing Substrate for Trustworthy Agents",
  description:
    "A founder thesis on Sardis, agent payments, fragmented protocols, Unix-shaped trust infrastructure, and the shared trust semantics underneath agentic commerce.",
  alternates: { canonical: "/manifesto" },
  openGraph: {
    title: "The Missing Substrate for Trustworthy Agents",
    description:
      "Sardis is not trying to own agent payments. It is trying to make the trust primitive underneath agentic commerce small, open, composable, and verifiable.",
    url: "https://sardis.sh/manifesto",
    type: "article",
    publishedTime: "2026-04-01T00:00:00Z",
    modifiedTime: "2026-05-12T00:00:00Z",
    authors: ["Efe Baran Durmaz"],
  },
}

const sections = [
  {
    title: "What changed my mind",
    body: [
      "I never used my own card for any of this. I knew from day one that was the wrong thing to do. But a lot of people did, and are still doing it. Around the same time I started, OpenAI pushed \"Buy it in ChatGPT\" and the whole agentic commerce pitch started getting louder everywhere. That was the signal that the wall was about to get hit. A lot.",
      "I did not have to wait long to see what that looked like in practice. In February, an OpenAI engineer's OpenClaw-based trading agent got a simple request (\"send 4 SOL for medical expenses\") and, through a quantity-parsing slip, sent 52.43 million tokens worth something like $600K. Nothing was wrong with the model. Nothing was wrong with the request. The failure was at the layer below: the agent had the authority to move everything, and a small misread was enough to trigger it. This is a category now, not an incident.",
      "So I moved up a level. Forget wrapping card rails. Build something agent-shaped: prepaid wallets per agent, on-ramp in, off-ramp out, spend caps, kill switches. Better. Much better than a card. The agent could no longer drain the principal's account because the principal's account was not connected. I spent a good chunk of autumn on that.",
      "And it was still not enough.",
      "A prepaid wallet solves the blast-radius problem and not the trust problem. An agent with a funded wallet can still loop. Can still get prompt-injected. Can still misread a quantity and spend everything in the wallet on one transaction. The wallet shrinks the damage; it does not prevent the class of bug. And the second you cap the wallet, you have given up the very autonomy you were trying to enable. The agent is no longer making real economic decisions, it is just drawing from a small pot you pre-approved.",
    ],
    pull: "What I wanted was an agent that could act autonomously without me having to pre-decide every decision. What I had built was a leash with a slightly longer rope.",
  },
  {
    title: "Why payments were the sharp edge",
    body: [
      "It is worth being specific, because the shape is not obvious and the existing infra assumes something very different.",
      "A human makes maybe a dozen deliberate purchases a day. An agent running a single task can make hundreds. A procurement agent polling five suppliers, a research agent hitting paid APIs per query, an infra agent provisioning cloud resources on demand, a trading agent reacting to ticks. All of these look like payment floods compared to human usage. Current estimates put agent-driven transactions at 10x to 1000x human frequency, with per-transaction amounts often in the cent-to-dollar range rather than tens-to-thousands. Card rails at 2.9% + $0.30 per charge are mathematically dead at this density. ACH at 1 to 3 business days is actually dead, the decision and the settlement live in different economic eras.",
      "What the rails have to carry is a different shape entirely: sub-second authorization, marginal fees close to zero on high-frequency flows, deterministic finality for small amounts, and escrow semantics when the stakes rise. Nobody is shipping all of that cleanly today. That is why Sardis treats the internal ledger as the primary rail and external rails as on/off-ramps. PayPal's shape, applied to machine commerce.",
      "But the deeper issue is not just rail performance. Payments are the first arena because mistakes are irreversible, frequent, and economically measurable. When an agent spends real money, the trust problem becomes visible immediately. Who is the agent. Who gave it authority. What was it allowed to do. What constraints applied. What evidence proves the decision was legitimate. Who is accountable if it was not.",
      "Money makes those questions impossible to avoid. It does not make them unique.",
      "The same shape appears in software, procurement, contracts, cloud infrastructure, healthcare, legal, and finance. Anywhere a non-human actor can take a consequential action, the system has to answer the same question: how do you allow autonomy without requiring blind trust?",
    ],
  },
  {
    title: "The git shape I could not stop thinking about",
    body: [
      "Around November I started noticing something that felt important. AI adoption inside software is enormous. Engineers give agents write access to their whole codebase and walk away. Trillion-dollar-adjacent industries, finance, healthcare, legal, procurement, are much more cautious. Orders of magnitude more cautious.",
      "The thing that makes software different is git. Every change is a commit. Every commit is reversible. Every merge is reviewable. Blame goes down to the line. If an agent ships something bad, you revert it. You know exactly what happened and exactly who did it, even when the \"who\" is a program.",
      "Outside of software, there is no git. An agent that pays a vendor does not leave a diff. An agent that signs a contract does not leave a rollback path. An agent that moves inventory does not leave a three-way merge. The reason AI has not flooded into these industries is not model capability. It is that the substrate does not let you undo, inspect, constrain, or verify enough of what happened.",
      "This was the point where I stopped thinking of Sardis as a payments company. Payments were just the sharpest place to see the real problem. The real problem was never only how agents move money. It was how non-human actors do irreversible things without requiring blind trust. The general shape is: how does a non-human actor do any consequential thing and leave evidence behind that makes the action safe to allow in the first place.",
    ],
  },
  {
    title: "The Unix shape underneath it",
    body: [
      "The model I keep coming back to is Unix.",
      "Unix did not win because it tried to become the only application. It won because it made small things compose. Files, pipes, processes, permissions, text streams. Each primitive was boring on its own. Together they gave builders a way to make systems without asking one platform to understand everything.",
      "That is the shape I want for agent trust.",
      "Sardis should not be the place where every agent, wallet, rail, merchant, and protocol disappears into one product. That would be the wrong instinct. Sardis should be one sharp piece in the path: take a proposed economic action, bind it to a mandate, run policy before execution, require approval when needed, emit evidence, and make the result verifiable by someone else.",
    ],
    pull: "Do one thing well: make consequential agent payments safe to allow before they happen. Everything around that should compose.",
  },
  {
    title: "What the thesis actually demands",
    body: [
      "Once I stopped thinking about this as \"agent payments,\" the same set of missing primitives kept reappearing everywhere.",
      "Trustworthy agents need reviewable state transitions instead of opaque side effects. They need attributable identity instead of \"some process somewhere did this.\" They need authority and delegation to be explicit rather than inferred after the fact. They need constraints that travel with the action, not policies trapped in a dashboard. They need approvals as first-class transitions, not ad hoc modal dialogs or settings-page toggles. They need evidence that survives the action. They need accountability that does not disappear when a workflow crosses a vendor boundary.",
      "They also need reputation and verification to become real primitives. Not vibes. Not screenshots. Not \"our system said it was fine.\" A third party should be able to look at an action and verify who acted, under which mandate, against which policy, with which approval, against which evidence.",
      "And they need all of those things to compose. That is the part people underestimate. It is not enough to have one protocol for tool use, another for communication, another for payments, another for identity, and another for approvals if the shared semantics between them stay implicit. That is where trustworthy systems break back into product glue.",
    ],
    pull: "Agent systems do not just need more APIs. They need a shared trust layer.",
  },
  {
    title: "Where Sardis sits in all this",
    body: [
      "Sardis is what you build when you realize money is just the most high-stakes version of an irreversible agent action, and the primitive underneath has to be better than \"give the agent a credential and hope.\"",
      "Sardis is not a card wrapper. It is not a prettier dashboard for agent spend. It is not just a prepaid wallet with stricter limits.",
      "A payment, in the model I ended up with, is a one-time object. It exists for a single transaction. It is minted when needed, expires in minutes, signed by three parties: principal, issuer, agent. It is bound to a specific merchant session and drawn from a specific pool of funds. You cannot steal it and use it elsewhere. You cannot replay it. You cannot hold it and spend it next week.",
      "Underneath the object is a mandate: a signed statement of exactly what the agent is allowed to do. Merchants, categories, amounts per transaction, amounts per period, approval thresholds, currency, rails. Between the mandate and the payment is a policy engine that lives on the execution path, not in a settings page. Every payment that crosses the system, from any SDK, any framework, any protocol, runs through the same checks in the same order. There is no fast lane that bypasses enforcement, because every fast lane I ever let myself build became the bug that mattered.",
      "Approvals are not interruptions bolted onto the side. They are part of the state machine. Evidence is not a log line for later. It is part of the action's legitimacy. Auditability is not a compliance export. It is how another system, another company, or another human can verify what happened without trusting Sardis as the narrator.",
      "That is the important distinction. One-time payment objects, signed mandates, policy on the path, approvals, evidence, auditability, no bypass, third-party verification. These are Sardis primitives today, but they are also examples of the broader trust substrate agentic commerce needs.",
    ],
  },
  {
    title: "Why the layer underneath cannot be owned",
    body: [
      "AI agents are starting to get some of their own primitives: identity, communication, tool use, payments, verification, versioned state. That is good. What is still missing is the layer where these primitives meet. Right now the shared semantics between them are still mostly implicit, hidden inside product-specific assumptions and glue code.",
      "That is part of why I started writing OAPS, an open standard for agentic primitives: intent, identity, authority, delegation, constraints, approvals, policy, evidence, and verification, expressed in a form other systems can verify, enforce, and build against. That missing layer is not a detail. It is the control surface. Without it, every company ends up with its own private dialect for trust. The words sound similar. The guarantees are not.",
      "Private trust semantics can work for demos. They can work inside closed ecosystems. They can work when one company controls the agent, the wallet, the merchant, the policy engine, the approval surface, and the audit log.",
      "They will not work for an economy.",
      "Agentic commerce will not mature if every company invents its own private language for who acted, who delegated authority, which constraints applied, what evidence was produced, and who is accountable. The primitive underneath has to be open, inspectable, portable, and independently verifiable. Otherwise the economy is not built on trust. It is built on vendor-specific claims about trust.",
      "Some of this fragmentation is natural. Early markets try many shapes before one of them hardens. That is healthy. The part I do not trust is when every company tries to make the shared primitive pass through its own vocabulary, its own SDK, its own dashboard, its own credential, and its own receipt format. At that point the market is not only experimenting. It is trying to own the thing that should become common.",
    ],
    pull: "The same trust primitive rebuilt three times under three brands is not infrastructure. It is ownership instinct wearing protocol clothing.",
  },
  {
    title: "What I think happens next",
    body: [
      "Agent payments is going to consolidate into a small number of serious product companies with real distribution, real bank partnerships, real liquidity, real compliance, and real regulatory posture. They will do things I am not good at and should not pretend to be good at.",
      "That is fine. This is not a call for one company to win agent payments. It is a call for the trust layer underneath agentic commerce to be built once, openly, and correctly.",
      "What I want is for the primitive underneath all of them to be the right shape. One-time payment objects. Signed mandates. Policy on the path. Approvals as part of the transition. Evidence that survives the action. Verifiable by anyone. Owned by no one.",
      "If that turns out to be the substrate the ecosystem settles on, I do not care whose logo is in the dashboard. I care that three years from now, when an agent I wrote is spending real money on my behalf while I am asleep, the primitive it is using is one I would have agreed to if I had been awake.",
      "That is why I am still building. If you are anywhere near this problem, tell me about it. efe@sardis.sh. I would rather compare notes than build parallel versions of the same thing.",
    ],
  },
]

function JsonLd() {
  const data = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: "The Missing Substrate for Trustworthy Agents",
    author: { "@type": "Person", name: "Efe Baran Durmaz" },
    datePublished: "2026-04-01",
    dateModified: "2026-05-12",
    url: "https://sardis.sh/manifesto",
    mainEntityOfPage: "https://sardis.sh/manifesto",
  }

  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }} />
}

export default function ManifestoPage() {
  return (
    <>
      <JsonLd />
      <main style={{ background: "#FDFBF7", color: "#1A1614", minHeight: "100vh" }}>
        <nav style={{ borderBottom: "1px solid rgba(26,22,20,0.08)", padding: "18px 24px" }}>
          <div style={{ maxWidth: 720, margin: "0 auto", display: "flex", justifyContent: "space-between" }}>
            <Link href="/" style={{ color: "inherit", textDecoration: "none", fontWeight: 700 }}>Sardis</Link>
            <Link href="/blog/agent-payments-fragmented-trust" style={{ color: "rgba(26,22,20,0.56)", textDecoration: "none", fontSize: 13 }}>Research note</Link>
          </div>
        </nav>
        <article style={{ maxWidth: 720, margin: "0 auto", padding: "64px 24px 96px" }}>
          <p style={{ fontSize: 12, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(26,22,20,0.42)", marginBottom: 14 }}>
            Manifesto · April 2026
          </p>
          <h1 style={{ fontSize: "clamp(36px, 7vw, 58px)", lineHeight: 1.02, letterSpacing: "-0.05em", margin: "0 0 18px" }}>
            The missing substrate for trustworthy agents.
          </h1>
          <p style={{ fontSize: 13, color: "rgba(26,22,20,0.5)", marginBottom: 44 }}>
            Efe Baran Durmaz · 20, writing from Ankara
          </p>
          <p style={lede}>
            The simplest way I can say it: I think AI agents are being held back, not by models, but by the fact that they cannot be trusted with money. The honest version of that sentence is longer. Here is the longer one.
          </p>
          {[
            "AI agents do not just have a capability problem. They have a trust problem.",
            "A year ago I started thinking about agent autonomy the way an infra person thinks about it. What is the actual, structural thing stopping this from working in production. Models kept getting better every month. Tool calling kept getting better. Browser use kept getting better. And yet every agent demo I watched ended at the same wall: the moment it needed to move money, a human had to step in. The agent could reason about a purchase, negotiate a rate, draft a contract, book a table. It could not actually pay for any of it without a credential somebody had handed it by hand.",
            "That bottleneck looked small from far away. The closer I looked, the more I thought it was the thing holding back a huge chunk of AI's economic value. An agent that reasons but cannot transact is a very expensive draft. The decision matters only if it lands.",
            "And now the market is rushing at that wall from every direction.",
            "New agent payment products. New protocols. New wallets. New rails. New commerce stacks. New abstractions for letting software buy things, sell things, provision things, and settle things. That is healthy at the product layer. Products should compete on UX, distribution, compliance, liquidity, wallets, rails, integrations, and developer experience.",
            "But if each system invents its own private semantics for who acted, who authorized it, under what constraints, with what evidence, and who is accountable, this does not become infrastructure. It becomes incompatible trust dialects.",
            "Even the public numbers are hard to read. One dashboard shows millions of transactions. Another shows much smaller filtered dollar flow. Another explorer shows thousands of agents and servers, but only a few thousand dollars of recent volume. That disagreement is not just analytics noise. It is a sign that the market has not agreed on what real agent commerce even means yet.",
            "Agent payment protocols are starting to appear for the right reason. The old web was not built for software actors that can discover, decide, and pay in the same loop. A server returning a machine-readable payment requirement is a good primitive. Per-request settlement is a good primitive. Payment-method negotiation is a good primitive. Cryptographic mandates are a good primitive.",
            "The problem is not that these protocols exist. The problem is that they are arriving as competing islands before the underlying trust layer has settled.",
            "One stack standardizes how an agent pays for an API call. Another standardizes checkout. Another standardizes payment-method negotiation. Another standardizes agent recognition. Another standardizes mandates. Each one may be technically reasonable in isolation. But if each one carries its own private meaning for identity, authority, constraints, approvals, evidence, receipts, and accountability, then the ecosystem does not get safer as it grows. It gets harder to verify.",
            "The missing layer is not another payment product. It is shared trust semantics.",
            "So I started where most people start. A payment rail wrapper. Something thin. Give an agent a way to move stablecoins, plug in an on-ramp and an off-ramp, call it a day. I was going to be done in a weekend.",
          ].map((text) => <p key={text} style={paragraph}>{text}</p>)}

          {sections.map((section) => (
            <section key={section.title} style={{ marginTop: 52 }}>
              <h2 style={heading}>{section.title}</h2>
              {section.body.map((text) => <p key={text} style={paragraph}>{text}</p>)}
              {section.pull ? <blockquote style={pull}>{section.pull}</blockquote> : null}
            </section>
          ))}
        </article>
      </main>
    </>
  )
}

const lede = {
  fontSize: 20,
  lineHeight: 1.62,
  color: "rgba(26,22,20,0.68)",
  marginBottom: 30,
}

const paragraph = {
  fontSize: 17,
  lineHeight: 1.78,
  color: "rgba(26,22,20,0.84)",
  margin: "0 0 22px",
}

const heading = {
  fontSize: 24,
  lineHeight: 1.2,
  letterSpacing: "-0.03em",
  margin: "0 0 20px",
}

const pull = {
  borderLeft: "2px solid #1A1614",
  paddingLeft: 22,
  margin: "30px 0",
  fontSize: 18,
  lineHeight: 1.58,
  fontWeight: 650,
  color: "#1A1614",
}
