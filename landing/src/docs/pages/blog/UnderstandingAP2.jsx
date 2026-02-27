import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function UnderstandingAP2() {
  return (
    <article className="prose prose-invert max-w-none">
      {/* Back link */}
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      {/* Header */}
      <header className="not-prose mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 text-xs font-mono bg-blue-500/10 border border-blue-500/30 text-blue-500">
            TECHNICAL
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
            FEATURED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Understanding AP2: The Industry Standard for Agent Payments
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 20, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />8 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          AP2 (Agent Payment Protocol) is the Google, PayPal, Mastercard, and Visa consortium
          standard for AI agent transactions. Learn how the Intent → Cart → Payment mandate
          chain provides cryptographic proof of authorization for every transaction.
        </p>

        <h2>Why AP2 Exists</h2>
        <p>
          When AI agents started making purchases in 2024, the payments industry faced a
          fundamental question: how do you authorize a transaction when there's no human
          clicking "Confirm"?
        </p>
        <p>
          Traditional payment flows rely on human presence - someone enters their card,
          reviews the amount, and explicitly approves. But agents operate autonomously.
          They need a way to prove that a purchase was authorized by a human without
          requiring that human to be present at the moment of transaction.
        </p>
        <p>
          AP2 was developed by a consortium of Google, PayPal, Mastercard, and Visa to
          solve exactly this problem. It introduces a cryptographic "mandate chain" that
          traces authorization from human intent to executed payment.
        </p>

        <h2>The Mandate Chain</h2>
        <p>
          AP2's core innovation is the mandate chain: a series of signed messages that
          create an unbroken trail of authorization. The chain has three components:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`┌────────────────────────────────────────────────────────────┐
│                    AP2 MANDATE CHAIN                       │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  ┌──────────┐      ┌──────────┐      ┌──────────┐         │
│  │  INTENT  │ ───▶ │   CART   │ ───▶ │ PAYMENT  │         │
│  │          │      │          │      │          │         │
│  │ "Buy API │      │ $29.99   │      │ Tx hash  │         │
│  │  credits │      │ OpenAI   │      │ 0xabc... │         │
│  │  <$50"   │      │ Credits  │      │          │         │
│  └──────────┘      └──────────┘      └──────────┘         │
│       │                 │                 │                │
│       ▼                 ▼                 ▼                │
│   [Signed by       [Signed by       [Signed by            │
│    Human/Policy]    Agent]           Wallet]              │
│                                                            │
└────────────────────────────────────────────────────────────┘`}
          </pre>
        </div>

        <h3>1. Intent Mandate</h3>
        <p>
          The Intent is where human authorization begins. It's a signed statement of what
          the agent is allowed to purchase. Intents can be:
        </p>
        <ul>
          <li><strong>Explicit:</strong> "Buy exactly this item for this price"</li>
          <li><strong>Bounded:</strong> "Spend up to $50 on cloud services"</li>
          <li><strong>Policy-based:</strong> "Follow spending policy XYZ" (Sardis's approach)</li>
        </ul>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`{
  "type": "ap2.intent",
  "version": "1.0",
  "issuer": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
  "agent": "did:key:z6Mkf5rGMoatrSj1f4CyvuHBeXJELe9RPdzo2PKGNCKVtZxP",
  "constraints": {
    "max_amount": "50.00",
    "currency": "USD",
    "categories": ["cloud_services", "developer_tools"],
    "expires_at": "2026-01-25T00:00:00Z"
  },
  "signature": "eyJhbGciOiJFZERTQSJ9..."
}`}
          </pre>
        </div>

        <h3>2. Cart Mandate</h3>
        <p>
          When the agent finds something to purchase, it creates a Cart Mandate. This
          specifies exactly what will be bought and must fall within the Intent's constraints.
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`{
  "type": "ap2.cart",
  "version": "1.0",
  "intent_ref": "ap2:intent:abc123",
  "agent": "did:key:z6Mkf5rGMoatrSj1f4CyvuHBeXJELe9RPdzo2PKGNCKVtZxP",
  "merchant": "openai.com",
  "items": [
    {
      "description": "API Credits",
      "amount": "29.99",
      "currency": "USD",
      "category": "cloud_services"
    }
  ],
  "total": "29.99",
  "signature": "eyJhbGciOiJFZERTQSJ9..."
}`}
          </pre>
        </div>

        <h3>3. Payment Mandate</h3>
        <p>
          The final step executes the actual transfer of funds. The Payment Mandate
          references the Cart and includes the cryptographic proof of execution.
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`{
  "type": "ap2.payment",
  "version": "1.0",
  "cart_ref": "ap2:cart:def456",
  "wallet": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD68",
  "chain": "base",
  "token": "USDC",
  "amount": "29990000",
  "tx_hash": "0xabc123...",
  "signature": "eyJhbGciOiJFZERTQSJ9..."
}`}
          </pre>
        </div>

        <h2>How Sardis Implements AP2</h2>
        <p>
          Sardis acts as the "Intent layer" in the AP2 stack. When you create a spending
          policy, Sardis generates and manages Intent Mandates on your behalf.
        </p>

        <div className="not-prose p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mb-6">
          <div className="flex gap-3">
            <div className="text-[var(--sardis-orange)] mt-0.5">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <div className="font-bold text-[var(--sardis-orange)] mb-1">Policy = Intent</div>
              <div className="text-sm text-muted-foreground">
                Your natural language policy ("Max $50/day on approved vendors") becomes
                a structured AP2 Intent that's cryptographically signed and verifiable
                by any party in the payment chain.
              </div>
            </div>
          </div>
        </div>

        <p>The flow works like this:</p>

        <ol>
          <li>You create a wallet with a spending policy</li>
          <li>Sardis generates a long-lived Intent Mandate from your policy</li>
          <li>When the agent makes a purchase, Sardis creates the Cart Mandate</li>
          <li>Sardis verifies Cart against Intent constraints</li>
          <li>If valid, Sardis executes the Payment Mandate via MPC signing</li>
        </ol>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`from sardis import Sardis

client = Sardis(api_key="sk_...")

# This creates an AP2 Intent Mandate under the hood
wallet = client.wallets.create(
    name="shopping-agent",
    chain="base",
    policy="Max $50/day, only openai.com and anthropic.com"
)

# This creates Cart + Payment Mandates
result = wallet.pay(
    to="0x...",
    amount="29.99",
    token="USDC",
    merchant="openai.com",
    memo="API credits"
)

# Access the full mandate chain
print(result.ap2_chain)
# {
#   "intent": "ap2:intent:abc123",
#   "cart": "ap2:cart:def456",
#   "payment": "ap2:payment:ghi789"
# }`}
          </pre>
        </div>

        <h2>Verification and Disputes</h2>
        <p>
          The mandate chain enables third-party verification. Merchants, payment processors,
          and compliance systems can independently verify that a transaction was authorized
          by following the chain of signatures.
        </p>
        <p>
          In case of disputes, the mandate chain provides irrefutable proof:
        </p>
        <ul>
          <li><strong>Intent:</strong> Proves human authorization existed</li>
          <li><strong>Cart:</strong> Proves the agent selected this specific purchase</li>
          <li><strong>Payment:</strong> Proves the wallet executed the transfer</li>
        </ul>
        <p>
          If any link in the chain is missing or invalid, the transaction can be
          flagged and reversed. This is why AP2 is becoming the standard for
          regulated agent transactions.
        </p>

        <h2>TAP Integration</h2>
        <p>
          AP2 works hand-in-hand with TAP (Trusted Agent Protocol) for identity verification.
          While AP2 handles payment authorization, TAP verifies that the agent making the
          request is who it claims to be.
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`┌─────────────────────────────────────────────────┐
│              FULL VERIFICATION STACK            │
├─────────────────────────────────────────────────┤
│                                                 │
│  TAP: "Is this really Agent X?"                 │
│    │                                            │
│    ▼                                            │
│  AP2: "Is Agent X authorized for this?"         │
│    │                                            │
│    ▼                                            │
│  Sardis: "Does this pass Agent X's policy?"     │
│    │                                            │
│    ▼                                            │
│  Execute: Sign and broadcast transaction        │
│                                                 │
└─────────────────────────────────────────────────┘`}
          </pre>
        </div>

        <h2>Getting Started</h2>
        <p>
          If you're using Sardis, you're already using AP2. Every transaction through
          our SDK or MCP server automatically generates a compliant mandate chain.
        </p>
        <p>
          For advanced use cases where you need to inspect or manually construct
          mandates, check out our <Link to="/docs/ap2" className="text-[var(--sardis-orange)]">AP2 documentation</Link>.
        </p>
        <p>
          The agent economy needs trust infrastructure. AP2 provides that trust through
          cryptographic proof, and Sardis makes it accessible through simple APIs and
          natural language policies.
        </p>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Team
          </div>
          <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors">
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </footer>
    </article>
  );
}
