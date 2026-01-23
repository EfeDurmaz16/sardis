import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const faqs = [
  {
    category: 'General',
    questions: [
      {
        q: 'What is Sardis?',
        a: 'Sardis is the Payment OS for the Agent Economy. It provides non-custodial MPC wallets with natural language spending policies, enabling AI agents to make secure financial transactions. Sardis implements industry-standard protocols (AP2, UCP, A2A, TAP) for interoperability with the broader AI agent ecosystem.'
      },
      {
        q: 'What protocols does Sardis support?',
        a: 'Sardis implements: AP2 (Agent Payment Protocol) - the Google/PayPal/Mastercard/Visa standard for mandate-based payments; UCP (Universal Commerce Protocol) - standardized checkout flows; A2A (Agent-to-Agent) - Google\'s multi-agent communication protocol; TAP (Trust Anchor Protocol) - cryptographic identity verification; and x402 for HTTP micropayments.'
      },
      {
        q: 'Is Sardis custodial or non-custodial?',
        a: 'Sardis is fully non-custodial. Your funds are secured by MPC (Multi-Party Computation) wallets via Turnkey. Key shares are distributed - Sardis never has custody of your funds. Transactions only execute when policy conditions are met and proper cryptographic authorization is provided.'
      },
      {
        q: 'What is Financial Hallucination Prevention?',
        a: 'Just as AI can hallucinate facts, it can attempt unauthorized transactions. Sardis prevents this through: cryptographic mandate chains (AP2), spending policies with vendor allowlists, real-time policy enforcement, and comprehensive audit trails. Every transaction requires verifiable authorization.'
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
        a: 'Use our MCP (Model Context Protocol) server. Run `npx @sardis/mcp-server start` and add it to your claude_desktop_config.json. Claude gets 36+ tools including sardis_pay, sardis_create_checkout, sardis_discover_agent, and more.'
      },
      {
        q: 'Which AI frameworks does Sardis support?',
        a: 'Sardis supports: Claude MCP (36+ tools), LangChain (Python and JavaScript), OpenAI Function Calling, Vercel AI SDK, and LlamaIndex. Our Python and TypeScript SDKs work with any framework.'
      },
      {
        q: 'Can I use Sardis without any code?',
        a: 'Yes! With MCP integration, add Sardis to Claude Desktop or Cursor without writing code. Just configure the MCP server with your API key and Claude can immediately execute payments, create checkouts, and manage wallets.'
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
        a: 'Policies are enforced at the protocol level before any transaction. You can set: per-transaction limits, daily/monthly limits, vendor allowlists/blocklists, category restrictions, and time-based rules. Policies can be defined programmatically or in natural language.'
      },
      {
        q: 'Is there an audit trail?',
        a: 'Yes. Every transaction is recorded in an append-only ledger with Merkle tree anchoring. The ledger captures: mandate chains, policy evaluation results, on-chain transaction hashes, and timestamps. This provides cryptographic proof for compliance and debugging.'
      },
    ]
  },
  {
    category: 'Tokens & Chains',
    questions: [
      {
        q: 'Which stablecoins are supported?',
        a: 'USDC (all chains), USDT (Polygon, Ethereum, Arbitrum, Optimism), EURC (Base, Polygon, Ethereum), and PYUSD (Ethereum). More tokens are added regularly.'
      },
      {
        q: 'Which chains are supported?',
        a: 'Base (primary), Polygon, Ethereum, Arbitrum, and Optimism. Base is recommended for lowest fees. All chains support USDC. See the documentation for token availability per chain.'
      },
      {
        q: 'What are the default spending limits?',
        a: 'Default limits are $100 per transaction and $500 per day. These can be configured per-wallet through the API or dashboard. Enterprise plans support custom limit configurations.'
      },
    ]
  },
];

function AccordionItem({ question, answer, isOpen, onClick }) {
  return (
    <div className="border-b border-border last:border-0">
      <button
        onClick={onClick}
        className="w-full py-4 flex items-center justify-between text-left hover:text-[var(--sardis-orange)] transition-colors"
      >
        <span className="font-medium pr-4">{question}</span>
        <ChevronDown className={cn(
          "w-5 h-5 flex-shrink-0 transition-transform",
          isOpen && "rotate-180"
        )} />
      </button>
      <div className={cn(
        "overflow-hidden transition-all duration-300",
        isOpen ? "max-h-96 pb-4" : "max-h-0"
      )}>
        <p className="text-muted-foreground text-sm leading-relaxed">
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
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            SUPPORT
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Frequently Asked Questions</h1>
        <p className="text-xl text-muted-foreground">
          Common questions about Sardis, integrations, security, and pricing.
        </p>
      </div>

      <div className="not-prose space-y-8">
        {faqs.map((category) => (
          <section key={category.category}>
            <h2 className="text-xl font-bold font-display mb-4 flex items-center gap-2">
              <span className="text-[var(--sardis-orange)]">#</span> {category.category}
            </h2>
            <div className="border border-border divide-y divide-border">
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
            href="https://github.com/anthropics/sardis/discussions"
            className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
          >
            Ask on GitHub
          </a>
          <a
            href="mailto:support@sardis.network"
            className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
          >
            Email Support
          </a>
        </div>
      </section>
    </article>
  );
}
