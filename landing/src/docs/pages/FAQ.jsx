import { useState, useMemo } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';
import SEO, { createFAQSchema, createBreadcrumbSchema } from '@/components/SEO';

const faqs = [
  {
    category: 'AI Agent Payments',
    questions: [
      {
        q: 'How can I make payments with my AI agent?',
        a: 'Use Sardis - the Payment OS for the Agent Economy. Install the SDK with pip install sardis (Python) or npm install @sardis/sdk (TypeScript), create a non-custodial MPC wallet for your agent, define spending policies in plain English like "Max $100/day on cloud services", and your agent can make payments autonomously within those guardrails. Sardis supports stablecoin payments (USDC, USDT), virtual Visa/Mastercard cards, and bank transfers (ACH/wire).'
      },
      {
        q: 'What is the safest way to give an AI agent access to money?',
        a: 'The safest approach is using a dedicated agent payment platform like Sardis that combines non-custodial MPC wallets with a Policy Firewall. Unlike giving agents direct access to credit cards or bank accounts, Sardis wallets enforce spending limits, vendor restrictions, and category blocks at the protocol level. Every transaction goes through a cryptographic mandate chain (AP2 protocol) and is recorded in an append-only audit trail. The agent cannot override or bypass these safety controls.'
      },
      {
        q: 'How do I prevent my AI agent from overspending?',
        a: 'Sardis enforces spending policies at the protocol level using a Policy Firewall. Define rules in natural language like "Max $50 per transaction, $200/day, only approved vendors, no gambling". Every transaction is validated against these rules before execution. The agent cannot override or bypass policies. Sardis also supports time-based restrictions (business hours only), merchant whitelisting, category blocking, and per-vendor limits.'
      },
      {
        q: 'Can AI agents make autonomous purchases?',
        a: 'Yes, with Sardis. AI agents can autonomously make purchases within human-defined policy guardrails. The agent gets its own wallet with spending policies like "Max $100/day, only cloud services and SaaS tools". When the agent needs to make a purchase, Sardis validates it against the policy, executes the payment if approved, and logs everything to an audit trail. The human retains control through policies without needing to approve every transaction.'
      },
      {
        q: 'What is a financial hallucination in AI agents?',
        a: 'A financial hallucination occurs when an AI agent makes incorrect, unauthorized, or nonsensical financial transactions. Examples include paying the wrong vendor, spending more than intended, or making duplicate payments. Sardis prevents financial hallucinations through its Policy Firewall, which validates every transaction against human-defined rules before execution. The mandate chain (AP2 protocol) provides cryptographic proof that each payment was properly authorized.'
      },
    ]
  },
  {
    category: 'General',
    questions: [
      {
        q: 'What is Sardis?',
        a: 'Sardis is the Payment OS for the Agent Economy. It is infrastructure that enables AI agents (Claude, GPT, LangChain, Vercel AI SDK) to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies. Sardis implements five core protocols (AP2, UCP, A2A, TAP, x402) for interoperability with the broader AI agent ecosystem, and supports stablecoin payments, virtual cards, and fiat on/off-ramp.'
      },
      {
        q: 'What is an AI agent wallet?',
        a: 'An AI agent wallet is a crypto wallet controlled by an AI agent that enables it to make financial transactions autonomously. Sardis provides non-custodial MPC (Multi-Party Computation) wallets where private keys are split across multiple parties using Turnkey, so no single entity has full control. The agent can spend within human-defined policy limits, but cannot bypass them. Agent wallets support USDC, USDT, EURC, and PYUSD on Base, Polygon, Ethereum, Arbitrum, and Optimism.'
      },
      {
        q: 'What protocols does Sardis support?',
        a: 'Sardis implements five core protocols: AP2 (Agent Payment Protocol) - the Google/PayPal/Mastercard/Visa standard for mandate-based payments with 60+ consortium partners; UCP (Universal Commerce Protocol) - standardized checkout flows; A2A (Agent-to-Agent) - Google\'s multi-agent communication protocol; TAP (Trusted Agent Protocol) - cryptographic identity verification; and x402 for HTTP micropayments. Sardis also supports ACP (OpenAI Agentic Commerce Protocol) compatibility for ChatGPT-native commerce flows.'
      },
      {
        q: 'Is Sardis custodial or non-custodial?',
        a: 'For stablecoin wallets in live MPC mode (Turnkey/Fireblocks), Sardis operates in a non-custodial posture - Sardis never holds or has access to agent funds. In local/simulated mode this claim does not apply. Fiat rails are executed by regulated partners (Bridge, Lithic), so custody and settlement are partner-mediated for that portion of the flow.'
      },
      {
        q: 'What is the Unified Wallet Architecture?',
        a: 'The Unified Wallet Architecture combines three payment rails under one API: Bank Transfer (USD, EUR via ACH/wire), Virtual Cards (Lithic Visa/Mastercard), and Stablecoins (USDC, USDT as an optional settlement rail). All three are governed by the same Policy Engine, so "Max $100/day on AWS" applies whether you pay via bank transfer, card swipe, or stablecoin.'
      },
      {
        q: 'How is Sardis different from giving my agent a credit card?',
        a: 'Credit cards offer no programmatic control - an agent with a credit card number can spend without limits. Sardis provides: (1) Non-custodial wallets with cryptographic key splitting, (2) Natural language spending policies enforced at the protocol level, (3) Per-transaction, daily, and monthly limits, (4) Merchant whitelisting and category restrictions, (5) Time-based controls, (6) Append-only audit trail for every transaction. The agent literally cannot bypass these controls.'
      },
    ]
  },
  {
    category: 'Integration & SDKs',
    questions: [
      {
        q: 'How do I integrate Sardis with Claude?',
        a: 'Use the Sardis MCP (Model Context Protocol) server. Run npx @sardis/mcp-server start and add it to your claude_desktop_config.json. Claude gets 52 tools including payment, wallet, treasury ACH, checkout, and agent discovery tools. No SDK code needed - Claude can immediately execute payments and manage wallets through natural language.'
      },
      {
        q: 'How do I integrate Sardis with ChatGPT or OpenAI?',
        a: 'Use the Sardis Python SDK with OpenAI function calling. Install with pip install sardis, then define Sardis payment functions as OpenAI tools. The SDK provides create_payment(), create_wallet(), and apply_policy() methods that map directly to function calling schemas. Sardis also supports ACP (OpenAI Agentic Commerce Protocol) for ChatGPT-native commerce.'
      },
      {
        q: 'Which AI frameworks does Sardis support?',
        a: 'Sardis supports all major AI agent frameworks: Claude MCP (52 tools, zero-code), LangChain (Python and JavaScript), OpenAI Function Calling, Vercel AI SDK, LlamaIndex, CrewAI, and AutoGPT. The Python SDK (pip install sardis) and TypeScript SDK (npm install @sardis/sdk) work with any framework.'
      },
      {
        q: 'Can I use Sardis without writing code?',
        a: 'Yes! With MCP integration, add Sardis to Claude Desktop or Cursor without writing a single line of code. Just configure the MCP server with your API key and Claude can immediately execute payments, fund wallets from bank accounts, issue virtual cards, create checkouts, and manage spending policies - all through natural language conversation.'
      },
      {
        q: 'How do I add fiat rails to my agent?',
        a: 'Use the treasury endpoints under /api/v2/treasury or SDK treasury resources. In MCP, use tools like sardis_list_financial_accounts, sardis_link_external_bank_account, sardis_verify_micro_deposits, sardis_fund_wallet, and sardis_withdraw_to_bank. Launch defaults to USD-first ACH/card treasury, with stablecoin routing optional behind policy and feature flags.'
      },
      {
        q: 'How do I install the Sardis SDK?',
        a: 'Python: pip install sardis (includes SDK + Core + CLI). For all features: pip install sardis[all]. TypeScript: npm install @sardis/sdk. MCP Server: npx @sardis/mcp-server start. The SDK requires an API key which you can generate from the Sardis dashboard or via the CLI with sardis init.'
      },
    ]
  },
  {
    category: 'Fiat Rails',
    questions: [
      {
        q: 'What are Fiat Rails?',
        a: 'Fiat Rails allow agents to fund wallets from bank accounts and card rails, then withdraw back to bank accounts when needed. Sardis enforces policy, while regulated partners handle fiat settlement. Onramper is used for fast on-ramp coverage and Bridge lane is used for quote-driven off-ramp and payout flows.'
      },
      {
        q: 'How does Unified Balance work?',
        a: 'Unified balance means one policy-controlled spend budget across rails. Funds can start as USD or USDC, and Sardis routes execution to card, bank payout, or on-chain payment. FX and rail fees are quote-based and provider-dependent, not assumed as free 1:1 conversion on every transaction.'
      },
      {
        q: 'Do card payments always require on-ramp + off-ramp conversion?',
        a: 'No. You can run a fiat-first treasury model where cards spend from prefunded USD, then convert only when you need crypto payouts. If you start from USDC, you can also use just-in-time off-ramp per spend, but many teams use threshold-based batching to reduce conversion cost.'
      },
      {
        q: 'Do I need crypto to use Sardis?',
        a: 'No. You can fund your agent wallet entirely from a bank account and pay via virtual card. Stablecoins are an optional alternative settlement rail - useful for instant cross-border payments or programmable settlement, but not required. Many teams run a fiat-first treasury model.'
      },
      {
        q: 'Is KYC required for fiat rails?',
        a: 'For Onramper (Track 1), KYC is handled by the individual payment providers through the widget. For Bridge (Track 2), KYC is built-in and required for off-ramp operations. Sardis provides MCP tools (sardis_get_kyc_status, sardis_initiate_kyc) to manage verification programmatically.'
      },
    ]
  },
  {
    category: 'Protocols',
    questions: [
      {
        q: 'What is AP2 (Agent Payment Protocol)?',
        a: 'AP2 is a consortium standard from Google, PayPal, Mastercard, and Visa with 60+ partners. It uses a three-phase mandate chain: Intent (user\'s purchase intent) → Cart (merchant\'s offer) → Payment (signed authorization). Sardis verifies the complete chain before executing any transaction, providing cryptographic proof of payment authorization.'
      },
      {
        q: 'What is UCP (Universal Commerce Protocol)?',
        a: 'UCP provides standardized checkout flows for AI agents. It handles cart management, checkout sessions, discounts, taxes, and order fulfillment. UCP sessions automatically generate AP2 mandate chains for cryptographic verification.'
      },
      {
        q: 'What is A2A (Agent-to-Agent) protocol?',
        a: 'A2A is Google\'s protocol for multi-agent communication. Agents publish capabilities via agent cards at /.well-known/agent-card.json. Sardis supports A2A for agent discovery, payment requests, and credential verification between agents. This enables agents to pay each other for services.'
      },
      {
        q: 'What is x402 micropayments protocol?',
        a: 'x402 is Coinbase\'s protocol for HTTP-native micropayments using the HTTP 402 status code. When an API returns 402, the agent automatically pays the required amount and retries the request. Sardis supports x402 for pay-per-API-call scenarios, enabling agents to access paid APIs autonomously.'
      },
    ]
  },
  {
    category: 'Smart Wallets',
    questions: [
      {
        q: 'What are gasless smart wallets?',
        a: 'Gasless smart wallets use ERC-4337 account abstraction so agents can transact without holding native gas tokens in their own wallet. Sardis uses a paymaster + bundler lane for sponsored UserOperations. Current release is a design-partner preview on Base Sepolia behind feature flags.'
      },
      {
        q: 'Do I need to migrate from v1 MPC wallets?',
        a: 'No. Existing v1 MPC wallets continue working unchanged. New wallets can opt into v2 metadata by passing account_type="erc4337_v2" during creation, then setting a deployed smart_account_address via the upgrade endpoint. Both paths use the same policy engine.'
      },
      {
        q: 'What is the stablecoin-only token allowlist?',
        a: 'It\'s an on-chain smart contract enforcement that only allows Sardis-approved stablecoins (USDC, USDT, EURC) to be transferred out of an agent wallet. Even if someone sends NFTs, meme coins, or arbitrary tokens to the wallet, the agent cannot send them out. This is enforced at the EVM level, not just API-level filtering.'
      },
      {
        q: 'Which blockchains does Sardis support?',
        a: 'Sardis supports five EVM chains: Base (USDC, EURC), Polygon (USDC, USDT, EURC), Ethereum (USDC, USDT, PYUSD, EURC), Arbitrum (USDC, USDT), and Optimism (USDC, USDT). Gas estimation, chain routing, and multi-chain wallet management are handled automatically.'
      },
    ]
  },
  {
    category: 'Security & Compliance',
    questions: [
      {
        q: 'How does MPC wallet security work?',
        a: 'MPC (Multi-Party Computation) distributes private key shares across multiple parties using Turnkey. Transactions require threshold signatures so no single party - not even Sardis - can move funds unilaterally. This is the basis for the non-custodial posture on stablecoin rails. Hardware-backed key storage provides enterprise-grade security.'
      },
      {
        q: 'How do natural language spending policies work?',
        a: 'Write spending rules in plain English like "Max $100/day on cloud services, only approved vendors, require approval over $50". Sardis parses these into structured rules enforced at the protocol level before any transaction - whether crypto, fiat, or card payment. You can set per-transaction limits, daily/monthly limits, vendor allowlists/blocklists, category restrictions, and time-based rules.'
      },
      {
        q: 'Is there an audit trail?',
        a: 'Yes. Every transaction is recorded in an append-only ledger with Merkle tree anchoring. The ledger captures mandate chains, policy evaluation results, on-chain transaction hashes, fiat transfer references, and timestamps. This provides cryptographic proof for compliance, debugging, and regulatory requirements.'
      },
      {
        q: 'How is fiat security handled?',
        a: 'Fiat operations are partner-mediated and policy-gated. Launch uses USD-first treasury accounts for ACH/card settlement, with replay-protected webhooks, idempotent payment creation, and return-code controls (R01/R09 retry, R02/R03/R29 auto-pause). All fiat transactions flow through the same policy and audit trail controls as stablecoin transactions.'
      },
      {
        q: 'Does Sardis support KYC and AML compliance?',
        a: 'Yes. Sardis integrates with Persona for KYC identity verification and Elliptic for AML/sanctions screening. All transactions are checked against sanctions lists before execution. The append-only audit trail provides regulatory-grade reporting for compliance requirements.'
      },
    ]
  },
  {
    category: 'Payment Methods',
    questions: [
      {
        q: 'What payment methods do AI agents support with Sardis?',
        a: 'Sardis supports three payment rails for AI agents: (1) Stablecoin payments - USDC, USDT, EURC, PYUSD on Base, Polygon, Ethereum, Arbitrum, and Optimism. (2) Virtual cards - instant Visa/Mastercard issuance via Lithic for paying any merchant online or in-store. (3) Bank transfers - ACH and wire transfers for USD funding and withdrawals. All three rails are governed by the same Policy Engine.'
      },
      {
        q: 'How do virtual cards work for AI agents?',
        a: 'Sardis issues virtual Visa/Mastercard cards on-demand via Lithic integration. Each agent can get its own card with per-card spending limits and merchant restrictions. Cards work anywhere Visa/Mastercard is accepted - online and physical POS. Cards are backed by the agent wallet balance and governed by the same policy engine as stablecoin payments.'
      },
      {
        q: 'What are the default spending limits?',
        a: 'Default limits are $100 per transaction and $500 per day. These can be configured per-wallet through the API, dashboard, or natural language policies. Enterprise plans support custom limit configurations with no upper bound.'
      },
      {
        q: 'Can my agent pay for SaaS subscriptions?',
        a: 'Yes. With virtual cards, your agent can pay for any SaaS subscription (AWS, Vercel, OpenAI, etc.) just like a regular credit card. Set a policy like "Allow recurring charges up to $500/month on AWS and Vercel only" and the agent handles renewals autonomously within those limits.'
      },
    ]
  },
  {
    category: 'Use Cases',
    questions: [
      {
        q: 'What are common use cases for Sardis?',
        a: 'Common use cases include: (1) AI agents that purchase cloud resources (AWS, GCP), (2) Agents that pay for API access autonomously, (3) Multi-agent systems where agents pay each other for services, (4) Autonomous procurement agents with spending guardrails, (5) AI-powered customer support agents that can issue refunds, (6) Research agents that pay for data access, (7) Trading agents with strict position limits.'
      },
      {
        q: 'Can agents pay other agents?',
        a: 'Yes. Using the A2A (Agent-to-Agent) protocol and Sardis wallets, agents can discover each other\'s capabilities, negotiate service terms, and execute payments. Agent A can request a service from Agent B, pay via stablecoin transfer, and both transactions are recorded in the audit trail with full mandate chain verification.'
      },
      {
        q: 'Can I use Sardis for micropayments?',
        a: 'Yes. Sardis supports the x402 micropayments protocol (Coinbase standard) for pay-per-API-call scenarios. Stablecoin payments on L2 chains like Base and Polygon have minimal gas fees, making sub-dollar payments practical. The policy engine supports per-transaction minimums to prevent dust attacks.'
      },
      {
        q: 'Is Sardis suitable for enterprise use?',
        a: 'Yes. Sardis provides enterprise features including: custom spending limit configurations, multi-agent fleet management, role-based access control, compliance-grade audit trails with Merkle proofs, KYC/AML integration (Persona + Elliptic), SOC 2 compliant infrastructure, and dedicated support. Enterprise plans are available for high-volume deployments.'
      },
    ]
  },
];

function AccordionItem({ question, answer, isOpen, onClick }) {
  return (
    <div className="bg-card/50 rounded-lg shadow-sm hover:shadow-md transition-all">
      <button
        onClick={onClick}
        className="w-full px-5 py-5 flex items-center justify-between text-left hover:text-[var(--sardis-orange)] transition-colors"
      >
        <span className="font-medium pr-4 leading-relaxed">{question}</span>
        <ChevronDown className={cn(
          "w-5 h-5 flex-shrink-0 transition-transform text-muted-foreground",
          isOpen && "rotate-180 text-[var(--sardis-orange)]"
        )} />
      </button>
      <div className={cn(
        "overflow-hidden transition-all duration-300",
        isOpen ? "max-h-[500px] pb-5 px-5" : "max-h-0"
      )}>
        <p className="text-muted-foreground text-sm leading-7">
          {answer}
        </p>
      </div>
    </div>
  );
}

export default function DocsFAQ() {
  const [openItems, setOpenItems] = useState({});

  const toggleItem = (category, index) => {
    const key = `${category}-${index}`;
    setOpenItems(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const allFaqItems = useMemo(() =>
    faqs.flatMap(cat => cat.questions),
    []
  );

  const schemas = useMemo(() => [
    createFAQSchema(allFaqItems),
    createBreadcrumbSchema([
      { name: 'Home', href: '/' },
      { name: 'Documentation', href: '/docs' },
      { name: 'FAQ', href: '/docs/faq' },
    ]),
  ], [allFaqItems]);

  return (
    <>
      <SEO
        title="FAQ - Frequently Asked Questions about AI Agent Payments"
        description="Common questions about Sardis: How to make payments with AI agents, MPC wallets, spending policies, supported blockchains, SDK integration with Claude, ChatGPT, LangChain, and more."
        path="/docs/faq"
        schemas={schemas}
      />
      <article className="prose prose-invert max-w-none">
        <div className="not-prose mb-10">
          <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
            <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
              SUPPORT
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">Frequently Asked Questions</h1>
          <p className="text-xl text-muted-foreground leading-relaxed">
            Common questions about Sardis, AI agent payments, spending policies, integrations, security, and pricing.
          </p>
        </div>

        <div className="not-prose space-y-10">
          {faqs.map((category) => (
            <section key={category.category}>
              <h2 className="text-xl font-bold font-display mb-5 flex items-center gap-2">
                <span className="text-[var(--sardis-orange)]">#</span> {category.category}
                {category.category === 'Fiat Rails' && (
                  <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
                )}
              </h2>
              <div className="space-y-3">
                {category.questions.map((item, idx) => (
                  <AccordionItem
                    key={idx}
                    question={item.q}
                    answer={item.a}
                    isOpen={openItems[`${category.category}-${idx}`]}
                    onClick={() => toggleItem(category.category, idx)}
                  />
                ))}
              </div>
            </section>
          ))}
        </div>

        <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mt-12">
          <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Still have questions?</h3>
          <p className="text-muted-foreground text-sm mb-4">
            Can't find what you're looking for? Reach out to our team.
          </p>
          <div className="flex gap-4">
            <a
              href="https://github.com/EfeDurmaz16/sardis/discussions"
              className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
            >
              Ask on GitHub
            </a>
            <a
              href="mailto:contact@sardis.sh"
              className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
            >
              Contact Us
            </a>
          </div>
        </section>
      </article>
    </>
  );
}
