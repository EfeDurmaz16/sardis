import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const faqs = [
  {
    category: 'General',
    questions: [
      {
        q: 'What is Sardis?',
        a: 'Sardis is the Payment OS for the Agent Economy. It provides a unified wallet abstraction combining non-custodial MPC wallets, fiat rails, and virtual cards—all governed by natural language spending policies. Sardis implements five core protocols (AP2, UCP, A2A, TAP, x402) for interoperability with the broader AI agent ecosystem.'
      },
      {
        q: 'What protocols does Sardis support?',
        a: 'Sardis implements five core protocols: AP2 (Agent Payment Protocol) - the Google/PayPal/Mastercard/Visa standard for mandate-based payments; UCP (Universal Commerce Protocol) - standardized checkout flows; A2A (Agent-to-Agent) - Google\'s multi-agent communication protocol; TAP (Trust Anchor Protocol) - cryptographic identity verification; and x402 for HTTP micropayments. Sardis also supports ACP (OpenAI Agentic Commerce Protocol) compatibility for ChatGPT-native commerce flows.'
      },
      {
        q: 'Is Sardis custodial or non-custodial?',
        a: 'Sardis is fully non-custodial. Your funds are secured by MPC (Multi-Party Computation) wallets via Turnkey. Key shares are distributed - Sardis never has custody of your funds. Transactions only execute when policy conditions are met and proper cryptographic authorization is provided.'
      },
      {
        q: 'What is the Unified Wallet Architecture?',
        a: 'The Unified Wallet Architecture combines three payment rails under one API: Bank Transfer (USD, EUR via ACH/wire), Virtual Cards (Lithic), and Stablecoins (USDC, USDT as an optional settlement rail). All three are governed by the same Policy Engine, so "Max $100/day on AWS" applies whether you pay via bank transfer, card swipe, or stablecoin.'
      },
    ]
  },
  {
    category: 'Fiat Rails',
    questions: [
      {
        q: 'What are Fiat Rails?',
        a: 'Fiat Rails (v0.6) allow agents to fund wallets from bank accounts (on-ramp) and withdraw back to bank accounts (off-ramp). We use a dual-track provider strategy: Onramper for quick go-live (30+ payment providers, widget integration) and Bridge for enterprise (built-in KYC, lower fees at scale).'
      },
      {
        q: 'How does Unified Balance work?',
        a: 'Sardis treats USDC and USD as equivalent at 1:1 parity—like Coinbase Exchange. When you deposit either crypto (USDC) or fiat (USD), both appear as a single unified balance. Your agent can then spend from this balance via crypto payments OR virtual card payments, with automatic conversion happening seamlessly. For example: deposit $500 USDC, spend $100 via virtual card (auto-converts USDC→USD), remaining balance: $400.'
      },
      {
        q: 'What is the difference between Onramper and Bridge?',
        a: 'Onramper is Track 1 for quick go-live: 30+ aggregated payment providers, no KYB for sandbox, 2-3 day integration via widget. Bridge is Track 2 for enterprise: full on-ramp AND off-ramp, built-in KYC verification, lower fees at scale, and compliance-first design. You can start with Onramper and migrate to Bridge as you scale.'
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
        a: 'AP2 is a consortium standard from Google, PayPal, Mastercard, and Visa. It uses a three-phase mandate chain: Intent (user\'s purchase intent) → Cart (merchant\'s offer) → Payment (signed authorization). Sardis verifies the complete chain before executing any transaction.'
      },
      {
        q: 'What is UCP (Universal Commerce Protocol)?',
        a: 'UCP provides standardized checkout flows for AI agents. It handles cart management, checkout sessions, discounts, taxes, and order fulfillment. UCP sessions automatically generate AP2 mandate chains for cryptographic verification.'
      },
      {
        q: 'What is A2A (Agent-to-Agent) protocol?',
        a: 'A2A is Google\'s protocol for multi-agent communication. Agents publish capabilities via agent cards at /.well-known/agent-card.json. Sardis supports A2A for agent discovery, payment requests, and credential verification between agents.'
      },
    ]
  },
  {
    category: 'Integration',
    questions: [
      {
        q: 'How do I integrate Sardis with Claude?',
        a: 'Use our MCP (Model Context Protocol) server. Run `npx @sardis/mcp-server start` and add it to your claude_desktop_config.json. Claude gets 46 tools including payment, wallet, fiat, checkout, and agent discovery tools.'
      },
      {
        q: 'Which AI frameworks does Sardis support?',
        a: 'Sardis supports: Claude MCP (46 tools), LangChain (Python and JavaScript), OpenAI Function Calling, Vercel AI SDK, and LlamaIndex. Our Python and TypeScript SDKs work with any framework.'
      },
      {
        q: 'Can I use Sardis without any code?',
        a: 'Yes! With MCP integration, add Sardis to Claude Desktop or Cursor without writing code. Just configure the MCP server with your API key and Claude can immediately execute payments, fund wallets from bank accounts, create checkouts, and manage wallets.'
      },
      {
        q: 'How do I add fiat rails to my agent?',
        a: 'Install the sardis-ramp SDK (pip install sardis-ramp or npm install @sardis/ramp), configure your Onramper or Bridge API key, and use the FiatRamp class. For MCP users, 8 new fiat tools are available: sardis_fund_wallet, sardis_withdraw_to_bank, sardis_link_bank_account, and more.'
      },
    ]
  },
  {
    category: 'Security',
    questions: [
      {
        q: 'How does MPC wallet security work?',
        a: 'MPC distributes private key shares across parties. In Sardis, key shares are held by you and Turnkey\'s infrastructure. Transactions require threshold signatures - no single party (including Sardis) can move funds. This provides non-custodial security with enterprise-grade signing infrastructure.'
      },
      {
        q: 'How do spending policies work?',
        a: 'Policies are enforced at the protocol level before any transaction—whether crypto, fiat, or card payment. You can set: per-transaction limits, daily/monthly limits, vendor allowlists/blocklists, category restrictions, and time-based rules. Policies can be defined programmatically or in natural language.'
      },
      {
        q: 'Is there an audit trail?',
        a: 'Yes. Every transaction is recorded in an append-only ledger with Merkle tree anchoring. The ledger captures: mandate chains, policy evaluation results, on-chain transaction hashes, fiat transfer references, and timestamps. This provides cryptographic proof for compliance and debugging.'
      },
      {
        q: 'How is fiat security handled?',
        a: 'Fiat operations go through licensed providers (Onramper, Bridge) with built-in compliance. KYC verification is required for off-ramp. Bank account linking uses secure tokenization. All fiat transactions are subject to the same Policy Engine rules as crypto transactions.'
      },
    ]
  },
  {
    category: 'Payment Methods',
    questions: [
      {
        q: 'What payment methods are supported?',
        a: 'Sardis supports three payment rails: (1) Bank Transfer — fund from any bank account via ACH or wire, withdraw back to USD. (2) Virtual Cards — issue Visa/Mastercard cards on-demand via Lithic for paying any merchant. (3) Stablecoins — optionally settle via USDC, USDT, EURC, or PYUSD on supported networks. All three rails are governed by the same Policy Engine.'
      },
      {
        q: 'Do I need crypto to use Sardis?',
        a: 'No. You can fund your agent wallet entirely from a bank account and pay via virtual card. Stablecoins are an optional alternative settlement rail — useful for instant cross-border payments or programmable settlement, but not required.'
      },
      {
        q: 'What are the default spending limits?',
        a: 'Default limits are $100 per transaction and $500 per day. These can be configured per-wallet through the API or dashboard. Enterprise plans support custom limit configurations.'
      },
      {
        q: 'How does unified balance work across rails?',
        a: 'Sardis treats all funding sources as a single unified balance. Whether you deposit via bank transfer or stablecoins, your agent sees one balance and can spend via any rail — virtual card, bank transfer, or stablecoin. Conversion happens automatically at 1:1 parity for USD-backed stablecoins.'
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

  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-10">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            SUPPORT
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Frequently Asked Questions</h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Common questions about Sardis, fiat rails, integrations, security, and pricing.
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
  );
}
