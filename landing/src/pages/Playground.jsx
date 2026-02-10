import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import SardisPlayground from '../components/SardisPlayground';

// Icons
const SunIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5"/>
    <line x1="12" y1="1" x2="12" y2="3"/>
    <line x1="12" y1="21" x2="12" y2="23"/>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
    <line x1="1" y1="12" x2="3" y2="12"/>
    <line x1="21" y1="12" x2="23" y2="12"/>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
  </svg>
);

const MoonIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
  </svg>
);

const ArrowLeftIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="19" y1="12" x2="5" y2="12"/>
    <polyline points="12 19 5 12 12 5"/>
  </svg>
);

const BookIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
    <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
  </svg>
);

const TerminalIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="4 17 10 11 4 5"/>
    <line x1="12" y1="19" x2="20" y2="19"/>
  </svg>
);

const GithubIcon = () => (
  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
  </svg>
);

// Code Examples for different frameworks
const CODE_EXAMPLES = {
  mcp: {
    label: 'Claude Desktop (MCP)',
    code: `// In Claude Desktop, just ask:
"Pay $20 to OpenAI for API credits"

// Sardis MCP Server handles:
// 1. Policy validation
// 2. MPC wallet signing
// 3. Virtual card generation
// 4. Transaction execution

// Response:
{
  "status": "success",
  "card": "4242 **** **** 7291",
  "tx_id": "tx_8f2d3a91"
}`
  },
  python: {
    label: 'Python SDK',
    code: `from sardis import Sardis

client = Sardis(api_key="sk_...")

# Create a payment with policy check
payment = client.payments.create(
    agent_id="agent_demo",
    amount=20.00,
    currency="USDC",
    recipient="openai.com",
    purpose="API credits"
)

print(f"TX: {payment.tx_hash}")
# TX: 0x7f4d...3a91`
  },
  typescript: {
    label: 'TypeScript SDK',
    code: `import { Sardis } from '@sardis/sdk';

const sardis = new Sardis({ apiKey: 'sk_...' });

// Execute payment with compliance
const payment = await sardis.payments.create({
  agentId: 'agent_demo',
  amount: 20.00,
  currency: 'USDC',
  recipient: 'openai.com',
  purpose: 'API credits'
});

console.log(\`TX: \${payment.txHash}\`);`
  },
  curl: {
    label: 'REST API',
    code: `curl -X POST https://sardis.sh/api/v2/payments \\
  -H "Authorization: Bearer sk_..." \\
  -H "Content-Type: application/json" \\
  -d '{
    "agent_id": "agent_demo",
    "amount": 2000,
    "currency": "USDC",
    "recipient": "openai.com",
    "purpose": "API credits"
  }'

# Response:
# {"tx_hash": "0x7f4d...3a91", "status": "confirmed"}`
  }
};

const Playground = () => {
  const [isDark, setIsDark] = useState(true);
  const [activeTab, setActiveTab] = useState('mcp');

  useEffect(() => {
    // Check system preference
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

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="sticky top-0 z-50 backdrop-blur-md bg-background/80 border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left: Back & Logo */}
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors"
              >
                <ArrowLeftIcon />
                <span className="text-sm hidden sm:inline">Back</span>
              </Link>
              <div className="h-6 w-px bg-border" />
              <Link to="/" className="flex items-center gap-2">
                <span className="text-xl font-bold tracking-tight text-foreground" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
                  sardis<span className="text-[var(--sardis-orange)]">.</span>sh
                </span>
              </Link>
            </div>

            {/* Center: Title */}
            <div className="hidden md:flex items-center gap-2">
              <TerminalIcon />
              <span className="font-mono text-sm text-muted-foreground">Interactive Playground</span>
            </div>

            {/* Right: Links */}
            <div className="flex items-center gap-3">
              <Link
                to="/docs"
                className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <BookIcon />
                <span className="hidden sm:inline">Docs</span>
              </Link>
              <a
                href="https://github.com/EfeDurmaz16/sardis"
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground transition-colors"
              >
                <GithubIcon />
              </a>
              <button
                onClick={toggleTheme}
                className="p-2 text-muted-foreground hover:text-foreground transition-colors"
                aria-label="Toggle theme"
              >
                {isDark ? <SunIcon /> : <MoonIcon />}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
            Try Sardis <span className="text-[var(--sardis-orange)]">Live</span>
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Experience how AI agents execute payments with built-in policy guardrails.
            No signup required - this is a live simulation of the Sardis payment flow.
          </p>
        </motion.div>

        {/* Interactive Playground */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="mb-16"
        >
          <SardisPlayground />
        </motion.div>

        {/* How It Works */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="mb-16"
        >
          <h2 className="text-2xl font-bold mb-8 text-center" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
            How It Works
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { step: '1', title: 'Agent Request', desc: 'AI agent calls sardis.pay() with payment details' },
              { step: '2', title: 'Policy Check', desc: 'Sardis validates against spending policies in real-time' },
              { step: '3', title: 'MPC Signing', desc: 'Non-custodial MPC wallet signs the transaction' },
              { step: '4', title: 'Execution', desc: 'Payment executes on-chain with full audit trail' },
            ].map((item, i) => (
              <div key={i} className="relative">
                <div className="bg-card border border-border p-6 h-full">
                  <div className="w-10 h-10 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 flex items-center justify-center mb-4">
                    <span className="text-[var(--sardis-orange)] font-bold font-mono">{item.step}</span>
                  </div>
                  <h3 className="font-semibold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>{item.title}</h3>
                  <p className="text-sm text-muted-foreground">{item.desc}</p>
                </div>
                {i < 3 && (
                  <div className="hidden md:block absolute top-1/2 -right-3 w-6 h-0.5 bg-border" />
                )}
              </div>
            ))}
          </div>
        </motion.section>

        {/* Code Examples */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="mb-16"
        >
          <h2 className="text-2xl font-bold mb-8 text-center" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
            Integrate in Minutes
          </h2>

          {/* Tabs */}
          <div className="flex flex-wrap justify-center gap-2 mb-6">
            {Object.entries(CODE_EXAMPLES).map(([key, { label }]) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`px-4 py-2 text-sm font-mono transition-all border ${
                  activeTab === key
                    ? 'bg-[var(--sardis-orange)] text-white border-[var(--sardis-orange)]'
                    : 'bg-card text-muted-foreground border-border hover:border-[var(--sardis-orange)] hover:text-foreground'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Code Block */}
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border overflow-hidden max-w-3xl mx-auto">
            <div className="px-4 py-2 bg-[#1f1e1c] border-b border-border flex items-center justify-between">
              <span className="text-[var(--sardis-canvas)]/50 text-xs font-mono">
                {CODE_EXAMPLES[activeTab].label}
              </span>
              <button
                onClick={() => navigator.clipboard.writeText(CODE_EXAMPLES[activeTab].code)}
                className="text-xs text-[var(--sardis-canvas)]/50 hover:text-[var(--sardis-orange)] transition-colors"
              >
                Copy
              </button>
            </div>
            <pre className="p-4 overflow-x-auto text-sm">
              <code className="text-[var(--sardis-canvas)] font-mono whitespace-pre">
                {CODE_EXAMPLES[activeTab].code}
              </code>
            </pre>
          </div>
        </motion.section>

        {/* Key Features */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="mb-16"
        >
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                title: 'Non-Custodial',
                desc: 'MPC wallets via Turnkey - you control the keys, not us.',
                icon: '🔐'
              },
              {
                title: 'Policy Guardrails',
                desc: 'Natural language spending limits prevent financial hallucinations.',
                icon: '🛡️'
              },
              {
                title: 'Multi-Chain',
                desc: 'Base, Polygon, Ethereum, Arbitrum, Optimism - one API.',
                icon: '⛓️'
              },
            ].map((feature, i) => (
              <div key={i} className="bg-card border border-border p-6 hover:border-[var(--sardis-orange)]/50 transition-colors">
                <span className="text-3xl mb-4 block">{feature.icon}</span>
                <h3 className="font-semibold mb-2" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>{feature.title}</h3>
                <p className="text-sm text-muted-foreground">{feature.desc}</p>
              </div>
            ))}
          </div>
        </motion.section>

        {/* CTA */}
        <motion.section
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="text-center py-12 bg-card border border-border"
        >
          <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Geist, system-ui, sans-serif' }}>
            Ready to Build?
          </h2>
          <p className="text-muted-foreground mb-6 max-w-md mx-auto">
            Get started with our SDKs and let your AI agents transact safely.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              to="/docs/quickstart"
              className="px-6 py-3 bg-[var(--sardis-orange)] text-white font-medium hover:bg-[var(--sardis-orange)]/90 transition-colors"
            >
              Read the Docs
            </Link>
            <a
              href="https://github.com/EfeDurmaz16/sardis"
              target="_blank"
              rel="noopener noreferrer"
              className="px-6 py-3 border border-border text-foreground font-medium hover:border-[var(--sardis-orange)] transition-colors flex items-center gap-2"
            >
              <GithubIcon />
              Star on GitHub
            </a>
          </div>
        </motion.section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-sm text-muted-foreground">
              2026 Sardis. The Payment OS for the Agent Economy.
            </div>
            <div className="flex items-center gap-6 text-sm">
              <Link to="/docs" className="text-muted-foreground hover:text-foreground transition-colors">
                Documentation
              </Link>
              <a href="https://github.com/EfeDurmaz16/sardis" className="text-muted-foreground hover:text-foreground transition-colors">
                GitHub
              </a>
              <a href="https://x.com/sardaborsa" className="text-muted-foreground hover:text-foreground transition-colors">
                Twitter
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Playground;
