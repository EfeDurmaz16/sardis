import { useState, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Link } from 'react-router-dom';
import SardisPlayground from '../components/SardisPlayground';
import SardisLogo from '../components/SardisLogo';
import SEO, { createBreadcrumbSchema } from '@/components/SEO';

// ─── MCP Tool Catalog ───────────────────────────────────────────────
const MCP_TOOLS = [
  // Wallets
  { name: "create_wallet", category: "Wallets", desc: "Create a new agent wallet on any supported chain", method: "POST", path: "/wallets" },
  { name: "get_wallet", category: "Wallets", desc: "Retrieve wallet details including balance and policies", method: "GET", path: "/wallets/{id}" },
  { name: "list_wallets", category: "Wallets", desc: "List all wallets with optional filtering", method: "GET", path: "/wallets" },
  { name: "fund_wallet", category: "Wallets", desc: "Fund a wallet from treasury or external source", method: "POST", path: "/wallets/{id}/fund" },
  { name: "get_balance", category: "Wallets", desc: "Get real-time balance for a specific wallet", method: "GET", path: "/wallets/{id}/balance" },
  { name: "transfer", category: "Wallets", desc: "Transfer funds between wallets", method: "POST", path: "/wallets/transfer" },
  // Payments
  { name: "execute_payment", category: "Payments", desc: "Execute a payment through the policy engine", method: "POST", path: "/payments/execute" },
  { name: "get_payment", category: "Payments", desc: "Get payment status and details", method: "GET", path: "/payments/{id}" },
  { name: "list_payments", category: "Payments", desc: "List payment history with filters", method: "GET", path: "/payments" },
  { name: "execute_mandate", category: "Payments", desc: "Execute an AP2-compliant payment mandate", method: "POST", path: "/mandates/execute" },
  { name: "verify_mandate", category: "Payments", desc: "Verify an AP2 mandate chain before execution", method: "POST", path: "/mandates/verify" },
  { name: "refund_payment", category: "Payments", desc: "Initiate a refund for a completed payment", method: "POST", path: "/payments/{id}/refund" },
  // Policies
  { name: "create_policy", category: "Policies", desc: "Create a spending policy from natural language", method: "POST", path: "/policies" },
  { name: "update_policy", category: "Policies", desc: "Update an existing policy", method: "PATCH", path: "/policies/{id}" },
  { name: "evaluate_policy", category: "Policies", desc: "Test a transaction against active policies", method: "POST", path: "/policies/evaluate" },
  { name: "list_policies", category: "Policies", desc: "List all policies for a wallet or agent", method: "GET", path: "/policies" },
  { name: "parse_policy", category: "Policies", desc: "Parse natural language into structured policy rules", method: "POST", path: "/policies/parse" },
  { name: "delete_policy", category: "Policies", desc: "Remove a policy from a wallet", method: "DELETE", path: "/policies/{id}" },
  // Cards
  { name: "create_card", category: "Cards", desc: "Issue a virtual Visa card for an agent", method: "POST", path: "/cards" },
  { name: "get_card", category: "Cards", desc: "Get card details and spending summary", method: "GET", path: "/cards/{id}" },
  { name: "list_cards", category: "Cards", desc: "List all virtual cards", method: "GET", path: "/cards" },
  { name: "freeze_card", category: "Cards", desc: "Temporarily freeze a virtual card", method: "POST", path: "/cards/{id}/freeze" },
  { name: "set_card_limit", category: "Cards", desc: "Set spending limits on a virtual card", method: "PATCH", path: "/cards/{id}/limits" },
  { name: "card_transactions", category: "Cards", desc: "List transactions for a specific card", method: "GET", path: "/cards/{id}/transactions" },
  // Treasury
  { name: "fund_treasury", category: "Treasury", desc: "Fund treasury via ACH, wire, or card on-ramp", method: "POST", path: "/treasury/fund" },
  { name: "withdraw", category: "Treasury", desc: "Withdraw funds to an external bank account", method: "POST", path: "/treasury/withdraw" },
  { name: "get_treasury_balance", category: "Treasury", desc: "Get current treasury balance breakdown", method: "GET", path: "/treasury/balance" },
  { name: "list_treasury_txns", category: "Treasury", desc: "List treasury funding and withdrawal history", method: "GET", path: "/treasury/transactions" },
  // Holds
  { name: "create_hold", category: "Holds", desc: "Place a hold on funds for a pending transaction", method: "POST", path: "/holds" },
  { name: "release_hold", category: "Holds", desc: "Release a previously placed hold", method: "POST", path: "/holds/{id}/release" },
  { name: "capture_hold", category: "Holds", desc: "Capture (finalize) a held amount", method: "POST", path: "/holds/{id}/capture" },
  { name: "list_holds", category: "Holds", desc: "List all active and expired holds", method: "GET", path: "/holds" },
  // Invoices
  { name: "create_invoice", category: "Commerce", desc: "Create a payment invoice for a merchant", method: "POST", path: "/invoices" },
  { name: "get_invoice", category: "Commerce", desc: "Get invoice details and payment status", method: "GET", path: "/invoices/{id}" },
  { name: "pay_invoice", category: "Commerce", desc: "Pay an outstanding invoice", method: "POST", path: "/invoices/{id}/pay" },
  // Subscriptions
  { name: "create_subscription", category: "Commerce", desc: "Set up a recurring payment subscription", method: "POST", path: "/subscriptions" },
  { name: "cancel_subscription", category: "Commerce", desc: "Cancel an active subscription", method: "POST", path: "/subscriptions/{id}/cancel" },
  { name: "list_subscriptions", category: "Commerce", desc: "List all subscriptions for a wallet", method: "GET", path: "/subscriptions" },
  // Ledger
  { name: "get_ledger_entry", category: "Audit", desc: "Get a specific ledger entry with Merkle proof", method: "GET", path: "/ledger/{id}" },
  { name: "list_ledger", category: "Audit", desc: "Query the append-only audit ledger", method: "GET", path: "/ledger" },
  { name: "verify_receipt", category: "Audit", desc: "Verify a chain receipt against the Merkle tree", method: "POST", path: "/ledger/verify" },
  { name: "get_audit_trail", category: "Audit", desc: "Get the full audit trail for a transaction", method: "GET", path: "/audit/{tx_id}" },
  // Agents
  { name: "register_agent", category: "Agents", desc: "Register a new AI agent with identity credentials", method: "POST", path: "/agents" },
  { name: "get_agent", category: "Agents", desc: "Get agent profile and activity summary", method: "GET", path: "/agents/{id}" },
  { name: "list_agents", category: "Agents", desc: "List all registered agents", method: "GET", path: "/agents" },
  { name: "create_agent_group", category: "Agents", desc: "Create a multi-agent group with shared budget", method: "POST", path: "/agents/groups" },
  { name: "agent_approve", category: "Agents", desc: "Approve or reject a pending agent transaction", method: "POST", path: "/agents/{id}/approve" },
  // Compliance
  { name: "run_kyc", category: "Compliance", desc: "Run KYC verification via Persona", method: "POST", path: "/compliance/kyc" },
  { name: "screen_sanctions", category: "Compliance", desc: "Screen address against sanctions lists", method: "POST", path: "/compliance/sanctions" },
  { name: "compliance_status", category: "Compliance", desc: "Check compliance status for a wallet/agent", method: "GET", path: "/compliance/{id}" },
];

const CATEGORIES = [...new Set(MCP_TOOLS.map(t => t.category))];

const METHOD_COLORS = {
  GET: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  POST: "text-blue-500 border-blue-500/30 bg-blue-500/10",
  PATCH: "text-yellow-500 border-yellow-500/30 bg-yellow-500/10",
  DELETE: "text-red-500 border-red-500/30 bg-red-500/10",
};

// ─── Mock Request/Response Data ─────────────────────────────────────
const MOCK_RESPONSES = {
  create_wallet: {
    request: `{
  "name": "shopping-agent",
  "chain": "base",
  "token": "USDC",
  "policy": "Max $200/day, only SaaS vendors"
}`,
    response: `{
  "wallet_id": "wal_7f4d3a91b2c8",
  "address": "0x7a3b...f92e",
  "chain": "base",
  "token": "USDC",
  "balance": "0.00",
  "policy_id": "pol_a3f8c291",
  "status": "active",
  "created_at": "2026-02-15T10:30:00Z"
}`,
  },
  execute_payment: {
    request: `{
  "wallet_id": "wal_7f4d3a91b2c8",
  "to": "api.openai.com",
  "amount": "45.00",
  "purpose": "GPT-4 API credits",
  "token": "USDC"
}`,
    response: `{
  "payment_id": "pay_9c4da31b",
  "status": "completed",
  "amount": "45.00",
  "token": "USDC",
  "chain": "base",
  "tx_hash": "0x8f2d...3a91",
  "policy_result": "ALLOWED",
  "receipt": {
    "merkle_root": "0xab3f...c891",
    "block": 19847231
  }
}`,
  },
  create_policy: {
    request: `{
  "wallet_id": "wal_7f4d3a91b2c8",
  "rules": "Max $100 per transaction. Only SaaS and developer tools. Block crypto exchanges. Business hours only (9-5 EST)."
}`,
    response: `{
  "policy_id": "pol_b7e2f491",
  "parsed_rules": {
    "per_tx_limit": 10000,
    "daily_limit": null,
    "allowed_categories": ["saas", "devtools"],
    "blocked_categories": ["crypto"],
    "time_window": {
      "start": "09:00",
      "end": "17:00",
      "timezone": "America/New_York"
    }
  },
  "confidence": 0.97,
  "status": "active"
}`,
  },
  create_card: {
    request: `{
  "wallet_id": "wal_7f4d3a91b2c8",
  "type": "VIRTUAL",
  "spending_limit": 50000,
  "memo": "Agent shopping card"
}`,
    response: `{
  "card_id": "card_3f8c2a91",
  "last_four": "7291",
  "type": "VIRTUAL",
  "state": "OPEN",
  "spending_limit": 50000,
  "pan": "4242424242427291",
  "cvv": "831",
  "exp_month": 12,
  "exp_year": 2026
}`,
  },
  evaluate_policy: {
    request: `{
  "wallet_id": "wal_7f4d3a91b2c8",
  "amount": "500.00",
  "merchant": "amazon.com",
  "category": "retail"
}`,
    response: `{
  "decision": "BLOCKED",
  "reason": "Category 'retail' not in allowed list",
  "policy_id": "pol_b7e2f491",
  "rule_matched": "allowed_categories",
  "suggestion": "Add 'retail' to allowed categories or create an override"
}`,
  },
  fund_treasury: {
    request: `{
  "amount_minor": 100000,
  "method": "ACH_NEXT_DAY",
  "external_bank_token": "eba_123",
  "sec_code": "CCD"
}`,
    response: `{
  "transfer_id": "tfr_8a3c2f91",
  "amount_minor": 100000,
  "status": "PENDING",
  "method": "ACH_NEXT_DAY",
  "estimated_arrival": "2026-02-16T15:00:00Z"
}`,
  },
};

// Fallback for tools without specific mock data
const DEFAULT_RESPONSE = {
  request: `{
  "id": "example_id"
}`,
  response: `{
  "status": "success",
  "message": "Operation completed"
}`,
};

// ─── Code Examples ──────────────────────────────────────────────────
const CODE_EXAMPLES = {
  mcp: {
    label: 'MCP (Claude)',
    filename: 'claude-desktop',
    code: `// In Claude Desktop, just ask naturally:
"Create a wallet for my shopping agent on Base
 with a $200/day limit, only SaaS vendors"

// Sardis MCP Server translates to:
// → create_wallet + create_policy
// → 2 tool calls, zero code

// Then:
"Pay OpenAI $45 for API credits"

// → evaluate_policy → execute_payment
// → Virtual card issued automatically`
  },
  python: {
    label: 'Python',
    filename: 'agent.py',
    code: `from sardis import SardisClient

client = SardisClient(api_key="sk_...")

# Create wallet with natural language policy
wallet = client.wallets.create(
    name="shopping-agent",
    chain="base",
    token="USDC",
    policy="Max $200/day, only SaaS vendors"
)

# Execute payment — policy checked automatically
result = wallet.pay(
    to="openai.com",
    amount="45.00",
    purpose="API credits"
)

print(f"Payment: {result.payment_id}")
print(f"Card: {result.card.last_four}")`
  },
  typescript: {
    label: 'TypeScript',
    filename: 'agent.ts',
    code: `import { SardisClient } from '@sardis/sdk'

const client = new SardisClient({ apiKey: 'sk_...' })

const wallet = await client.wallets.create({
  name: 'shopping-agent',
  chain: 'base',
  token: 'USDC',
  policy: 'Max $200/day, only SaaS vendors'
})

const payment = await client.payments.execute({
  walletId: wallet.id,
  to: 'api.openai.com',
  amount: '45.00',
  purpose: 'API credits'
})

console.log(\`TX: \${payment.tx_hash}\`)`
  },
  curl: {
    label: 'cURL',
    filename: 'terminal',
    code: `curl -X POST https://api.sardis.sh/v2/payments/execute \\
  -H "X-API-Key: sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "wallet_id": "wal_7f4d3a91b2c8",
    "to": "api.openai.com",
    "amount": "45.00",
    "token": "USDC",
    "purpose": "API credits"
  }'

# → {"payment_id":"pay_9c4d","status":"completed"}`
  }
};

// ─── Icons ──────────────────────────────────────────────────────────
const ChevronIcon = ({ open }) => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" style={{ transform: open ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 150ms' }}>
    <polyline points="4 2 8 6 4 10" />
  </svg>
);

const SearchIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
  </svg>
);

const CopyIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="9" y="9" width="13" height="13" rx="2" /><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
  </svg>
);

const CheckIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="20 6 9 17 4 12" />
  </svg>
);

// ─── Copy Button ────────────────────────────────────────────────────
function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors p-1"
      title="Copy"
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
    </button>
  );
}

// ─── Tool Detail Panel ──────────────────────────────────────────────
function ToolDetail({ tool }) {
  const [activePane, setActivePane] = useState('request');
  const mock = MOCK_RESPONSES[tool.name] || DEFAULT_RESPONSE;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.2 }}
      className="border border-border bg-card overflow-hidden"
    >
      {/* Tool header */}
      <div className="px-5 py-4 border-b border-border">
        <div className="flex items-center gap-3 mb-2">
          <span className={`px-2 py-0.5 text-[10px] font-bold font-mono border ${METHOD_COLORS[tool.method]}`}>
            {tool.method}
          </span>
          <code className="text-sm font-mono text-foreground">/v2{tool.path}</code>
        </div>
        <p className="text-sm text-muted-foreground">{tool.desc}</p>
      </div>

      {/* Request / Response toggle */}
      <div className="flex border-b border-border">
        {['request', 'response'].map(pane => (
          <button
            key={pane}
            onClick={() => setActivePane(pane)}
            className={`flex-1 px-4 py-2 text-xs font-mono font-bold uppercase tracking-wider transition-colors ${
              activePane === pane
                ? 'text-[var(--sardis-orange)] border-b-2 border-[var(--sardis-orange)] bg-[var(--sardis-orange)]/5'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            {pane === 'request' ? 'Request Body' : 'Response'}
          </button>
        ))}
      </div>

      {/* Code pane */}
      <div className="relative">
        <div className="absolute top-2 right-2 z-10">
          <CopyButton text={activePane === 'request' ? mock.request : mock.response} />
        </div>
        <pre className="p-4 bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] text-[var(--sardis-canvas)] font-mono text-xs leading-relaxed overflow-x-auto max-h-64">
          <code>{activePane === 'request' ? mock.request : mock.response}</code>
        </pre>
      </div>
    </motion.div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────
export default function Playground() {
  const [isDark, setIsDark] = useState(true);
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState(null);
  const [selectedTool, setSelectedTool] = useState(MCP_TOOLS.find(t => t.name === 'execute_payment'));
  const [codeTab, setCodeTab] = useState('mcp');
  const [expandedCategories, setExpandedCategories] = useState(new Set(CATEGORIES));

  useEffect(() => {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const stored = localStorage.getItem('sardis-theme');
    const dark = stored ? stored === 'dark' : prefersDark;
    setIsDark(dark);
    document.documentElement.classList.toggle('dark', dark);
  }, []);

  const toggleTheme = () => {
    const newDark = !isDark;
    setIsDark(newDark);
    document.documentElement.classList.toggle('dark', newDark);
    localStorage.setItem('sardis-theme', newDark ? 'dark' : 'light');
  };

  const filteredTools = useMemo(() => {
    let tools = MCP_TOOLS;
    if (search) {
      const q = search.toLowerCase();
      tools = tools.filter(t =>
        t.name.toLowerCase().includes(q) ||
        t.desc.toLowerCase().includes(q) ||
        t.category.toLowerCase().includes(q)
      );
    }
    if (activeCategory) {
      tools = tools.filter(t => t.category === activeCategory);
    }
    return tools;
  }, [search, activeCategory]);

  const groupedTools = useMemo(() => {
    const groups = {};
    filteredTools.forEach(t => {
      if (!groups[t.category]) groups[t.category] = [];
      groups[t.category].push(t);
    });
    return groups;
  }, [filteredTools]);

  const toggleCategory = (cat) => {
    setExpandedCategories(prev => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  };

  return (
    <div className="min-h-screen bg-background text-foreground font-sans">
      <SEO
        title="AI Agent Payments Playground"
        description="Explore Sardis AI agent payment tools, policy enforcement flows, and integration examples for MCP, Python, and TypeScript."
        path="/playground"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Playground' },
          ]),
        ]}
      />
      {/* ── Header ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-background/80 border-b border-border">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-14">
            <div className="flex items-center gap-4">
              <Link to="/" className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
                <span className="text-sm hidden sm:inline">Back</span>
              </Link>
              <div className="h-5 w-px bg-border" />
              <Link to="/" className="flex items-center gap-2">
                <SardisLogo size="small" />
                <span className="font-bold text-foreground font-display">Sardis</span>
              </Link>
            </div>

            <div className="hidden md:flex items-center gap-2 font-mono text-xs text-muted-foreground">
              <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse" />
              Developer Playground
            </div>

            <div className="flex items-center gap-3">
              <Link to="/docs" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-mono">Docs</Link>
              <Link to="/dashboard" className="text-sm text-muted-foreground hover:text-foreground transition-colors font-mono">Dashboard</Link>
              <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noopener noreferrer" className="text-muted-foreground hover:text-foreground transition-colors">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
              </a>
              <button onClick={toggleTheme} className="p-2 text-muted-foreground hover:text-foreground transition-colors" aria-label="Toggle theme">
                {isDark ? (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* ── Hero ───────────────────────────────────────────────── */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-10"
        >
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-3xl md:text-4xl font-bold tracking-tight font-display mb-2">
                Developer <span className="text-[var(--sardis-orange)]">Playground</span>
              </h1>
              <p className="text-muted-foreground max-w-lg">
                Explore {MCP_TOOLS.length} MCP tools, test the policy engine live, and integrate in minutes.
              </p>
            </div>
            <div className="flex gap-3">
              <span className="px-3 py-1.5 border border-border text-xs font-mono text-muted-foreground">
                {MCP_TOOLS.length} tools
              </span>
              <span className="px-3 py-1.5 border border-border text-xs font-mono text-muted-foreground">
                {CATEGORIES.length} categories
              </span>
              <span className="px-3 py-1.5 border border-emerald-600/30 text-xs font-mono text-emerald-600">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full inline-block mr-1.5 animate-pulse" />
                SIMULATED
              </span>
            </div>
          </div>
        </motion.div>

        {/* ── Interactive Demo ───────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05 }}
          className="mb-16"
        >
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 border border-[var(--sardis-orange)] flex items-center justify-center">
              <span className="text-[var(--sardis-orange)] font-bold font-mono text-xs">01</span>
            </div>
            <h2 className="text-lg font-semibold font-display">Live Policy Engine</h2>
            <span className="text-xs text-muted-foreground font-mono">Try a transaction against the spending firewall</span>
          </div>
          <SardisPlayground />
        </motion.section>

        {/* ── MCP Tool Explorer ─────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-16"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 border border-[var(--sardis-orange)] flex items-center justify-center">
              <span className="text-[var(--sardis-orange)] font-bold font-mono text-xs">02</span>
            </div>
            <h2 className="text-lg font-semibold font-display">MCP Tool Explorer</h2>
            <span className="text-xs text-muted-foreground font-mono">Browse all available tools</span>
          </div>

          <div className="grid lg:grid-cols-[340px_1fr] gap-6">
            {/* Left: Tool list */}
            <div className="border border-border bg-card overflow-hidden flex flex-col max-h-[700px]">
              {/* Search */}
              <div className="p-3 border-b border-border">
                <div className="relative">
                  <div className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                    <SearchIcon />
                  </div>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search tools..."
                    className="w-full pl-9 pr-3 py-2 bg-muted border border-border text-sm font-mono text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-[var(--sardis-orange)] transition-colors"
                  />
                </div>
              </div>

              {/* Category filter pills */}
              <div className="px-3 py-2 border-b border-border flex flex-wrap gap-1.5">
                <button
                  onClick={() => setActiveCategory(null)}
                  className={`px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider border transition-colors ${
                    !activeCategory
                      ? 'bg-[var(--sardis-orange)] text-white border-[var(--sardis-orange)]'
                      : 'text-muted-foreground border-border hover:border-[var(--sardis-orange)] hover:text-foreground'
                  }`}
                >
                  All ({MCP_TOOLS.length})
                </button>
                {CATEGORIES.map(cat => {
                  const count = MCP_TOOLS.filter(t => t.category === cat).length;
                  return (
                    <button
                      key={cat}
                      onClick={() => setActiveCategory(activeCategory === cat ? null : cat)}
                      className={`px-2 py-1 text-[10px] font-mono font-bold uppercase tracking-wider border transition-colors ${
                        activeCategory === cat
                          ? 'bg-[var(--sardis-orange)] text-white border-[var(--sardis-orange)]'
                          : 'text-muted-foreground border-border hover:border-[var(--sardis-orange)] hover:text-foreground'
                      }`}
                    >
                      {cat} ({count})
                    </button>
                  );
                })}
              </div>

              {/* Tool list */}
              <div className="overflow-y-auto flex-1">
                {Object.entries(groupedTools).map(([category, tools]) => (
                  <div key={category}>
                    <button
                      onClick={() => toggleCategory(category)}
                      className="w-full px-4 py-2 flex items-center justify-between text-xs font-mono font-bold uppercase tracking-wider text-muted-foreground hover:text-foreground bg-muted/50 border-b border-border transition-colors"
                    >
                      <span>{category}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-muted-foreground">{tools.length}</span>
                        <ChevronIcon open={expandedCategories.has(category)} />
                      </div>
                    </button>
                    <AnimatePresence>
                      {expandedCategories.has(category) && (
                        <motion.div
                          initial={{ height: 0 }}
                          animate={{ height: 'auto' }}
                          exit={{ height: 0 }}
                          transition={{ duration: 0.15 }}
                          className="overflow-hidden"
                        >
                          {tools.map(tool => (
                            <button
                              key={tool.name}
                              onClick={() => setSelectedTool(tool)}
                              className={`w-full px-4 py-2.5 flex items-start gap-3 text-left border-b border-border/50 transition-colors ${
                                selectedTool?.name === tool.name
                                  ? 'bg-[var(--sardis-orange)]/5 border-l-2 border-l-[var(--sardis-orange)]'
                                  : 'hover:bg-muted/50'
                              }`}
                            >
                              <span className={`px-1.5 py-0.5 text-[9px] font-bold font-mono border shrink-0 mt-0.5 ${METHOD_COLORS[tool.method]}`}>
                                {tool.method}
                              </span>
                              <div className="min-w-0">
                                <div className="text-sm font-mono text-foreground truncate">{tool.name}</div>
                                <div className="text-[11px] text-muted-foreground truncate">{tool.desc}</div>
                              </div>
                            </button>
                          ))}
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                ))}
                {filteredTools.length === 0 && (
                  <div className="p-6 text-center text-sm text-muted-foreground font-mono">
                    No tools match "{search}"
                  </div>
                )}
              </div>
            </div>

            {/* Right: Tool detail */}
            <div className="space-y-4">
              <AnimatePresence mode="wait">
                {selectedTool ? (
                  <ToolDetail key={selectedTool.name} tool={selectedTool} />
                ) : (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="border border-dashed border-border p-12 flex items-center justify-center text-muted-foreground font-mono text-sm"
                  >
                    Select a tool from the list to view details
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Quick-try hint */}
              {selectedTool && (
                <div className="p-4 border border-border bg-muted/30">
                  <div className="flex items-start gap-3">
                    <div className="w-6 h-6 border border-[var(--sardis-orange)]/30 flex items-center justify-center shrink-0 mt-0.5">
                      <span className="text-[var(--sardis-orange)] text-xs">?</span>
                    </div>
                    <div>
                      <p className="text-sm text-foreground font-medium mb-1">Try it with MCP</p>
                      <p className="text-xs text-muted-foreground font-mono">
                        npx @sardis/mcp-server start --mode simulated
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Then ask Claude: "Use the <span className="text-[var(--sardis-orange)]">{selectedTool.name}</span> tool"
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </motion.section>

        {/* ── Code Examples ──────────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="mb-16"
        >
          <div className="flex items-center gap-3 mb-6">
            <div className="w-8 h-8 border border-[var(--sardis-orange)] flex items-center justify-center">
              <span className="text-[var(--sardis-orange)] font-bold font-mono text-xs">03</span>
            </div>
            <h2 className="text-lg font-semibold font-display">Integrate in Minutes</h2>
          </div>

          <div className="border border-border overflow-hidden max-w-4xl">
            {/* Tab bar */}
            <div className="bg-muted px-4 py-0 border-b border-border flex items-center gap-0">
              {Object.entries(CODE_EXAMPLES).map(([key, { label }]) => (
                <button
                  key={key}
                  onClick={() => setCodeTab(key)}
                  className={`px-4 py-3 text-xs font-mono font-bold transition-colors border-b-2 ${
                    codeTab === key
                      ? 'text-[var(--sardis-orange)] border-[var(--sardis-orange)]'
                      : 'text-muted-foreground border-transparent hover:text-foreground'
                  }`}
                >
                  {label}
                </button>
              ))}
              <div className="flex-1" />
              <span className="text-[10px] text-muted-foreground font-mono mr-2">{CODE_EXAMPLES[codeTab].filename}</span>
              <CopyButton text={CODE_EXAMPLES[codeTab].code} />
            </div>

            {/* Code */}
            <pre className="p-5 bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] overflow-x-auto">
              <code className="text-[var(--sardis-canvas)] font-mono text-sm leading-relaxed whitespace-pre">
                {CODE_EXAMPLES[codeTab].code}
              </code>
            </pre>
          </div>
        </motion.section>

        {/* ── Quick Stats ────────────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-16"
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {[
              { label: "CHAINS", value: "5", sub: "Base, Polygon, Ethereum, Arbitrum, Optimism" },
              { label: "TOKENS", value: "5", sub: "USDC, USDT, EURC, PYUSD, DAI" },
              { label: "PROTOCOLS", value: "5", sub: "AP2, UCP, A2A, TAP, x402" },
              { label: "PACKAGES", value: "27", sub: "npm + PyPI + meta" },
            ].map((stat, i) => (
              <div key={i} className="p-5 border border-border hover:border-[var(--sardis-orange)] transition-colors">
                <div className="text-[10px] font-bold tracking-[0.2em] text-muted-foreground mb-1 font-mono">{stat.label}</div>
                <div className="text-2xl font-bold text-foreground font-display">{stat.value}</div>
                <div className="text-xs text-muted-foreground font-mono">{stat.sub}</div>
              </div>
            ))}
          </div>
        </motion.section>

        {/* ── CTA ────────────────────────────────────────────────── */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="border border-border p-8 md:p-12 text-center mb-8"
        >
          <h2 className="text-2xl font-bold font-display mb-3">Ready to Build?</h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Get started with our SDKs and let your AI agents transact safely.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/docs/quickstart"
              className="px-6 py-3 bg-[var(--sardis-orange)] text-white font-medium hover:bg-[var(--sardis-orange)]/90 transition-colors font-display"
            >
              Read the Docs
            </Link>
            <a
              href="https://github.com/EfeDurmaz16/sardis"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 border border-border text-foreground font-medium hover:border-[var(--sardis-orange)] transition-colors flex items-center gap-2 font-display"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
              Star on GitHub
            </a>
          </div>
        </motion.section>
      </main>

      {/* ── Footer ──────────────────────────────────────────────── */}
      <footer className="border-t border-border">
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-xs text-muted-foreground font-mono">
              2026 Sardis. The Payment OS for the Agent Economy.
            </div>
            <div className="flex items-center gap-6 text-xs">
              <Link to="/docs" className="text-muted-foreground hover:text-foreground transition-colors">Docs</Link>
              <a href="https://github.com/EfeDurmaz16/sardis" className="text-muted-foreground hover:text-foreground transition-colors">GitHub</a>
              <a href="https://x.com/sardisHQ" className="text-muted-foreground hover:text-foreground transition-colors">Twitter</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
