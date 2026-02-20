import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';

export default function SardisV09MultiProviderFiat() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      <header className="not-prose mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-500">
            RELEASE
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
            FEATURED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Sardis v0.9.0: Multi-Provider Fiat Rails + AI Framework Integrations
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            February 20, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />7 min read
          </span>
        </div>
      </header>

      <p className="text-lg text-muted-foreground leading-relaxed">
        v0.9.0 is the biggest infrastructure release yet: Stripe Treasury + Issuing for fiat operations,
        Coinbase Onramp for zero-fee USDC purchases, a sub-ledger system for per-agent fiat balances,
        and integrations across every major AI framework — OpenAI, Gemini, Claude (MCP), and ChatGPT Actions.
      </p>

      <h2>Multi-Provider Fiat Architecture</h2>

      <p>
        Sardis now supports multiple fiat providers behind a unified abstraction layer. The new <code>RampRouter</code> automatically
        selects the best provider based on token type, direction, and fees — with automatic fallback when a provider fails.
      </p>

      <h3>Stripe Treasury</h3>
      <p>
        The new <code>StripeTreasuryProvider</code> gives Sardis a complete fiat backbone: financial accounts with
        real IBAN/account numbers, balance queries, outbound payments, and Treasury-to-Issuing fund transfers. This replaces
        the need for a separate banking partner — Stripe holds the money transmitter license, Sardis stays non-custodial.
      </p>
      <ul>
        <li>Financial account creation and management</li>
        <li>Real-time balance queries across available, pending, and reserved funds</li>
        <li>Outbound payments (ACH, wire) with automatic status tracking</li>
        <li>Treasury-to-Issuing fund transfers for card operations</li>
        <li>Webhook handling for all Treasury lifecycle events</li>
      </ul>

      <h3>Stripe Issuing</h3>
      <p>
        Virtual card issuance now runs on Stripe Issuing alongside the existing Lithic integration. The <code>StripeIssuingProvider</code> implements
        the full <code>CardProvider</code> ABC with real-time authorization webhooks for instant spending decisions.
      </p>
      <ul>
        <li>Full card lifecycle: create, update, freeze, terminate</li>
        <li>Per-card spending limits with automatic enforcement</li>
        <li>Real-time authorization webhook for policy-based approve/decline</li>
        <li>Automatic card-to-agent mapping in the sub-ledger</li>
      </ul>

      <h3>Coinbase Onramp</h3>
      <p>
        USDC purchases now route through Coinbase Onramp by default — <strong>0% fee</strong> for USDC on Base.
        The smart <code>RampRouter</code> automatically picks Coinbase for USDC and falls back to Bridge for other tokens.
      </p>

      <h2>Sub-Ledger System</h2>

      <p>
        The new <code>SubLedgerManager</code> tracks per-agent fiat balances within Sardis&apos;s single platform Treasury account.
        Every deposit, withdrawal, card funding, and settlement is recorded as a typed transaction with full audit trail.
      </p>
      <ul>
        <li>Per-agent balance tracking with asyncio-safe concurrent access</li>
        <li>Typed transactions: DEPOSIT, WITHDRAWAL, CARD_FUND, CARD_SETTLEMENT, CARD_REFUND, OFF_RAMP, ON_RAMP</li>
        <li>Treasury reconciliation to detect and flag drift between sub-ledger totals and actual Treasury balance</li>
        <li>Transaction history queries with time-range and type filtering</li>
      </ul>

      <h2>End-to-End Fiat Orchestrator</h2>

      <p>
        The <code>FiatPaymentOrchestrator</code> ties everything together: Treasury, Issuing, RampRouter, and SubLedger
        into complete payment flows with automatic rollback on failure.
      </p>
      <ul>
        <li><strong>Card payment:</strong> Check sub-ledger balance → fund virtual card → execute charge</li>
        <li><strong>Fiat deposit:</strong> Inbound payment → credit sub-ledger → optionally fund card</li>
        <li><strong>Fiat withdrawal:</strong> Debit sub-ledger → outbound payment via Treasury</li>
        <li><strong>Crypto-to-card:</strong> Off-ramp USDC → deposit to Treasury → fund card → ready for real-world spend</li>
      </ul>

      <h2>AI Framework Integrations</h2>

      <p>
        v0.9.0 ships payment tools for every major AI agent framework. One integration, every platform:
      </p>

      <h3>OpenClaw Skill</h3>
      <p>
        The <code>sardis-openclaw</code> package publishes a <code>SKILL.md</code> manifest that any OpenClaw-compatible
        agent can discover and use. Payment, policy, and card tools are all exposed as skill actions.
      </p>

      <h3>OpenAI Function Calling</h3>
      <p>
        <code>sardis-openai</code> provides strict-mode JSON schema tools for OpenAI&apos;s function calling API.
        Drop-in compatible with GPT-4, GPT-4o, and any model supporting tool use.
      </p>

      <h3>Google Gemini (ADK)</h3>
      <p>
        <code>sardis-adk</code> now includes Gemini <code>FunctionDeclaration</code> adapters. Same payment tools,
        native Google format — works with Gemini Pro, Ultra, and the Agent Development Kit.
      </p>

      <h3>MCP Fiat Tools</h3>
      <p>
        5 new MCP tools added to <code>sardis-mcp-server</code>: <code>fiat_deposit</code>, <code>fiat_withdraw</code>,
        <code>fiat_card_payment</code>, <code>fiat_balance</code>, and <code>fiat_crypto_to_card</code>. Works in
        Claude Desktop, Cursor, and any MCP-compatible client.
      </p>

      <h3>ChatGPT Actions</h3>
      <p>
        The new <code>/openapi-actions.yaml</code> spec exposes 8 API endpoints as ChatGPT Actions. Any custom GPT
        can now query balances, send payments, manage cards, and check policies — no code required.
      </p>

      <h2>What This Means</h2>

      <p>
        With v0.9.0, Sardis agents can operate in both crypto and fiat worlds simultaneously. An agent can hold USDC
        in its MPC wallet, convert to fiat via Coinbase, fund a virtual card via Stripe, and pay for real-world services —
        all governed by the same spending policy engine, KYA verification, and audit trail.
      </p>

      <p>
        The multi-framework integration means developers can add Sardis payment capabilities to any AI agent regardless
        of which framework or model they use. One payment infrastructure, every AI platform.
      </p>

      <div className="not-prose mt-10 p-6 bg-card/50 rounded-lg">
        <h3 className="font-bold font-display mb-3">Get Started</h3>
        <p className="text-sm text-muted-foreground mb-4">
          Upgrade to v0.9.0 and start using multi-provider fiat rails today.
        </p>
        <div className="flex flex-wrap gap-3">
          <code className="px-3 py-1.5 bg-background rounded text-sm">pip install sardis==0.9.0</code>
          <code className="px-3 py-1.5 bg-background rounded text-sm">npm install @sardis/sdk@latest</code>
        </div>
      </div>
    </article>
  );
}
