import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

const faqs = [
  {
    category: 'General',
    questions: [
      {
        q: 'What is Sardis?',
        a: 'Sardis is a stablecoin execution layer for AI agents. It provides a secure, policy-controlled way for AI systems to execute financial transactions using MPC (Multi-Party Computation) wallets. This enables autonomous agents to pay for APIs, SaaS services, and other digital goods while preventing unauthorized spending.'
      },
      {
        q: 'What is Financial Hallucination Prevention?',
        a: 'Financial Hallucination Prevention is a core Sardis concept. Just as AI can "hallucinate" false information, it can also attempt unauthorized financial transactions. Sardis prevents this through cryptographic policy enforcement, spending limits, vendor allowlists, and real-time transaction validation.'
      },
      {
        q: 'Is Sardis custodial or non-custodial?',
        a: 'Sardis is fully non-custodial. Your funds are secured by MPC (Multi-Party Computation) wallets where key shares are distributed between you and Turnkey\'s infrastructure. Sardis never has custody of your funds - we only facilitate transaction signing when policy conditions are met.'
      },
    ]
  },
  {
    category: 'Integration',
    questions: [
      {
        q: 'Which AI frameworks does Sardis support?',
        a: 'Sardis supports all major AI frameworks including: LangChain (Python and JavaScript), OpenAI Function Calling, Vercel AI SDK, LlamaIndex, and Claude MCP. We also provide native SDKs for Python and TypeScript that work with any framework.'
      },
      {
        q: 'How do I integrate Sardis with Claude?',
        a: 'The easiest way is through our MCP (Model Context Protocol) server. Just run `npx @sardis/mcp-server start` and add it to your claude_desktop_config.json. Claude will automatically have access to sardis_pay, sardis_check_balance, and sardis_check_policy tools.'
      },
      {
        q: 'Can I use Sardis without any code?',
        a: 'Yes! With the MCP integration, you can add Sardis to Claude Desktop or Cursor without writing any code. Just configure the MCP server and Claude can immediately start making policy-controlled payments.'
      },
    ]
  },
  {
    category: 'Security',
    questions: [
      {
        q: 'How does MPC wallet security work?',
        a: 'MPC (Multi-Party Computation) distributes private key shares across multiple parties. In Sardis, key shares are held by you and Turnkey\'s infrastructure. Transactions require threshold signatures from multiple key shares, meaning no single party (including Sardis) can move funds without proper authorization.'
      },
      {
        q: 'What happens if an AI tries to exceed spending limits?',
        a: 'The transaction is immediately blocked at the policy layer. No funds can move without passing all policy checks including: per-transaction limits, daily/monthly limits, vendor allowlists, category restrictions, and time-based rules. All blocked transactions are logged for audit.'
      },
      {
        q: 'Is there an audit trail for transactions?',
        a: 'Yes. Every transaction is anchored to a Merkle tree with cryptographic proofs. The ledger records mandate details, policy evaluation results, chain transaction hashes, and timestamps. This provides a complete audit trail for compliance and debugging.'
      },
    ]
  },
  {
    category: 'Pricing & Limits',
    questions: [
      {
        q: 'What are the transaction fees?',
        a: 'Sardis charges a small platform fee on successful transactions plus network gas costs. During the beta period, platform fees are waived. See our pricing page for current rates.'
      },
      {
        q: 'What are the default spending limits?',
        a: 'Default limits are $100 per transaction and $500 per day. These can be configured per-wallet and per-agent through the dashboard or API. Enterprise plans support custom limit configurations.'
      },
      {
        q: 'Which stablecoins are supported?',
        a: 'Sardis currently supports USDC, USDT, PYUSD, and EURC across Base, Polygon, Ethereum, Arbitrum, and Optimism networks. More tokens and chains are added regularly.'
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
