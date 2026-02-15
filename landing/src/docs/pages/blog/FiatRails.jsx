import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2, CheckCircle2, ArrowRight, DollarSign, Wallet, CreditCard, Building2 } from "lucide-react";

export default function FiatRails() {
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
          <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            FEATURE
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-500">
            FIAT
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Fiat Rails: Bridging Traditional Banking to Agent Wallets
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 24, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />8 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Most businesses run on dollars, not tokens. Fiat Rails is the Sardis design-partner
          lane for bank funding, card spend, and payout orchestration with policy enforcement.
          Stablecoins remain available as an optional settlement rail.
        </p>

        <h2>The Bridge Problem</h2>
        <p>
          Until now, funding an agent wallet required crypto fluency. Users needed to:
        </p>
        <ul>
          <li>Buy USDC on an exchange</li>
          <li>Transfer to the correct chain</li>
          <li>Bridge if necessary</li>
          <li>Fund the agent wallet</li>
        </ul>
        <p>
          This friction blocks mainstream adoption. Enterprise finance teams do not want to
          manage crypto operations. They want to fund agents from existing banking workflows.
        </p>

        <h2>Fiat Rails in the current release</h2>
        <p>
          Fiat Rails uses provider integrations for settlement while Sardis enforces policy,
          idempotency, and auditability:
        </p>

        <div className="not-prose my-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-6 border border-border bg-card">
              <div className="w-12 h-12 border border-[var(--sardis-orange)] flex items-center justify-center mb-4">
                <Building2 className="w-6 h-6 text-[var(--sardis-orange)]" />
              </div>
              <h3 className="text-lg font-bold font-display mb-2">Bank → Wallet</h3>
              <p className="text-sm text-muted-foreground">
                Fund agent workflows via ACH, wire, or card with quote-driven conversion when needed.
              </p>
            </div>
            <div className="p-6 border border-border bg-card">
              <div className="w-12 h-12 border border-[var(--sardis-orange)] flex items-center justify-center mb-4">
                <Wallet className="w-6 h-6 text-[var(--sardis-orange)]" />
              </div>
              <h3 className="text-lg font-bold font-display mb-2">Unified Balance</h3>
              <p className="text-sm text-muted-foreground">
                One policy budget can power crypto payments, virtual cards, and bank payouts.
              </p>
            </div>
            <div className="p-6 border border-border bg-card">
              <div className="w-12 h-12 border border-[var(--sardis-orange)] flex items-center justify-center mb-4">
                <DollarSign className="w-6 h-6 text-[var(--sardis-orange)]" />
              </div>
              <h3 className="text-lg font-bold font-display mb-2">Wallet → Bank</h3>
              <p className="text-sm text-muted-foreground">
                Withdraw to USD with policy checks and compliance workflows.
              </p>
            </div>
          </div>
        </div>

        <h2>The Flow</h2>
        <p>
          Here's how funds flow through the Sardis ecosystem:
        </p>

        <div className="not-prose my-8 p-6 border border-border bg-muted/30 overflow-x-auto">
          <div className="flex items-center justify-center gap-3 min-w-[500px] font-mono text-sm">
            <div className="text-center">
              <div className="w-16 h-16 border-2 border-[var(--sardis-orange)] flex items-center justify-center mx-auto mb-2">
                <Building2 className="w-8 h-8" />
              </div>
              <div className="font-bold">Bank</div>
              <div className="text-xs text-muted-foreground">ACH/Wire/Card</div>
            </div>
            <ArrowRight className="w-6 h-6 text-[var(--sardis-orange)]" />
            <div className="text-center">
              <div className="w-16 h-16 border border-border flex items-center justify-center mx-auto mb-2 bg-muted">
                <span className="text-xs font-bold">BRIDGE</span>
              </div>
              <div className="font-bold">Bridge</div>
              <div className="text-xs text-muted-foreground">USD → USDC</div>
            </div>
            <ArrowRight className="w-6 h-6 text-[var(--sardis-orange)]" />
            <div className="text-center">
              <div className="w-20 h-20 border-2 border-[var(--sardis-orange)] flex items-center justify-center mx-auto mb-2 bg-[var(--sardis-orange)]/10">
                <Wallet className="w-10 h-10 text-[var(--sardis-orange)]" />
              </div>
              <div className="font-bold text-[var(--sardis-orange)]">Sardis Wallet</div>
              <div className="text-xs text-muted-foreground">MPC + Policy</div>
            </div>
            <ArrowRight className="w-6 h-6 text-[var(--sardis-orange)]" />
            <div className="text-center space-y-2">
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 border border-border flex items-center justify-center">
                  <CreditCard className="w-5 h-5" />
                </div>
                <span className="text-xs">Card</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 border border-border flex items-center justify-center">
                  <span className="text-xs font-bold">TX</span>
                </div>
                <span className="text-xs">Crypto</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-10 h-10 border border-border flex items-center justify-center">
                  <Building2 className="w-5 h-5" />
                </div>
                <span className="text-xs">Bank</span>
              </div>
            </div>
          </div>
        </div>

        <h2>Avoiding unnecessary conversion cost</h2>
        <p>
          We use three operating modes to avoid forced double conversion:
        </p>

        <div className="not-prose my-6">
          <div className="space-y-3">
            <div className="flex items-start gap-3 p-4 border border-border bg-card">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold font-display">Mode A: Fiat-first card treasury</div>
                <p className="text-sm text-muted-foreground mt-1">
                  Keep a USD treasury for cards and only convert when crypto payout is requested.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 border border-border bg-card">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold font-display">Mode B: Stablecoin-first JIT</div>
                <p className="text-sm text-muted-foreground mt-1">
                  Convert USDC to USD per spend when card usage is infrequent or highly variable.
                </p>
              </div>
            </div>
            <div className="flex items-start gap-3 p-4 border border-border bg-card">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
              <div>
                <div className="font-bold font-display">Mode C: Hybrid threshold refill</div>
                <p className="text-sm text-muted-foreground mt-1">
                  Maintain a USD buffer and top up in batches from stablecoins based on thresholds.
                </p>
              </div>
            </div>
          </div>
        </div>

        <h2>Implementation</h2>
        <p>
          We're releasing both Python and TypeScript SDKs for fiat operations:
        </p>

        <h3>Funding a Wallet</h3>
        <pre className="not-prose bg-[var(--sardis-ink)] p-4 overflow-x-auto">
          <code>{`import { SardisFiatRamp } from '@sardis/ramp'

const ramp = new SardisFiatRamp({
  sardisKey: process.env.SARDIS_API_KEY,
  bridgeKey: process.env.BRIDGE_API_KEY,
  environment: 'production'
})

// Fund wallet from bank
const funding = await ramp.fundWallet({
  walletId: 'wallet_abc123',
  amountUsd: 5000,
  method: 'bank'  // 'bank' | 'card' | 'crypto'
})

// Returns ACH instructions for bank transfer
console.log(funding.achInstructions)
// {
//   accountNumber: '9876543210',
//   routingNumber: '021000021',
//   bankName: 'Bridge Financial',
//   reference: 'SARDIS-abc123'
// }`}</code>
        </pre>

        <h3>Withdrawing to Bank</h3>
        <pre className="not-prose bg-[var(--sardis-ink)] p-4 overflow-x-auto">
          <code>{`// Withdraw requires policy approval
const withdrawal = await ramp.withdrawToBank({
  walletId: 'wallet_abc123',
  amountUsd: 2500,
  bankAccount: {
    accountHolderName: 'Acme Corp',
    accountNumber: '1234567890',
    routingNumber: '021000021',
    accountType: 'checking'
  }
})

// Policy engine checks:
// - Daily/weekly/monthly withdrawal limits
// - Destination whitelist (if configured)
// - Compliance flags

console.log(withdrawal)
// {
//   txHash: '0x...',
//   payoutId: 'payout_xyz',
//   estimatedArrival: Date,
//   fee: 12.50,
//   status: 'pending'
// }`}</code>
        </pre>

        <h3>Paying Merchants Directly</h3>
        <pre className="not-prose bg-[var(--sardis-ink)] p-4 overflow-x-auto">
          <code>{`// Pay a merchant in USD from crypto wallet
const payment = await ramp.payMerchantFiat({
  walletId: 'wallet_abc123',
  amountUsd: 499.99,
  merchant: {
    name: 'SaaS Provider Inc',
    category: 'software',
    bankAccount: {
      accountHolderName: 'SaaS Provider Inc',
      accountNumber: '...',
      routingNumber: '...'
    }
  }
})

// If policy requires approval:
// payment.status === 'pending_approval'
// payment.approvalRequest contains details

// If approved automatically:
// payment.status === 'completed'
// payment.paymentId, payment.fee available`}</code>
        </pre>

        <h2>Pricing model</h2>
        <p>
          Final pricing is provider and volume dependent. Sardis should show quotes before execution
          and apply platform spread only when policy allows it:
        </p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Route</th>
                <th className="text-left p-3 border-b border-border font-mono">Cost Pattern</th>
                <th className="text-left p-3 border-b border-border font-mono">Best Use</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="p-3 border-b border-border">Fiat-first card treasury</td>
                <td className="p-3 border-b border-border text-emerald-400">Single rail cost, no per-swipe off-ramp</td>
                <td className="p-3 border-b border-border text-muted-foreground">High recurring card spend</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">Stablecoin-first JIT card funding</td>
                <td className="p-3 border-b border-border text-yellow-400">Conversion on each refill event</td>
                <td className="p-3 border-b border-border text-muted-foreground">Crypto-native inflow</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">Hybrid threshold refill</td>
                <td className="p-3 border-b border-border text-emerald-400">Batched conversion, lower blended fee</td>
                <td className="p-3 border-b border-border text-muted-foreground">Most design partners</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">Direct stablecoin merchant pay</td>
                <td className="p-3 border-b border-border text-emerald-400">No fiat conversion</td>
                <td className="p-3 border-b border-border text-muted-foreground">Crypto-accepting merchants</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p>
          Production contracts should expose provider pass-through fee + Sardis platform fee as separate line items.
        </p>

        <h2>Compliance Built In</h2>
        <p>
          All fiat operations integrate with our existing compliance stack:
        </p>
        <ul>
          <li><strong>Persona</strong> for KYC verification</li>
          <li><strong>Elliptic</strong> for sanctions screening</li>
          <li><strong>Policy Engine</strong> for custom rules</li>
          <li><strong>Append-only Ledger</strong> for audit trails</li>
        </ul>

        <p>
          Withdrawals to new bank accounts trigger enhanced verification. Suspicious patterns
          are flagged before funds leave the system.
        </p>

        <h2>What's Next</h2>
        <p>
          Fiat Rails is available in sandbox and design-partner lanes. Production scale-up
          depends on partner onboarding milestones. On the roadmap:
        </p>
        <ul>
          <li><strong>International wires</strong> — SWIFT and SEPA support</li>
          <li><strong>Multi-currency</strong> — EUR, GBP, and more stablecoins</li>
          <li><strong>Recurring funding</strong> — Automated wallet top-ups</li>
          <li><strong>Instant settlements</strong> — RTP for US payouts</li>
        </ul>

        <h2>Get Started</h2>
        <p>
          Install the SDK and start integrating:
        </p>

        <pre className="not-prose bg-[var(--sardis-ink)] p-4 overflow-x-auto">
	          <code>{`# TypeScript
npm install @sardis/ramp

# Python
pip install sardis-ramp`}</code>
        </pre>

        <p>
          For enterprise pilots, reach out to <a href="mailto:efe@sardis.dev" className="text-[var(--sardis-orange)]">efe@sardis.dev</a>.
        </p>

        <hr />

        <p className="text-muted-foreground italic">
          Fiat rails use regulated partner infrastructure. Sardis handles wallet management,
          policy enforcement, and compliance controls. Partners handle the actual
          fiat movement.
        </p>
      </div>

      {/* Share */}
      <div className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <Link
            to="/docs/blog"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Blog
          </Link>
          <button
            onClick={() => {
              navigator.clipboard.writeText(window.location.href);
            }}
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
          >
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </div>
    </article>
  );
}
