import { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Sun, Moon, Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';

// Font imports - match LandingV2 premium design system
import '@fontsource/space-grotesk/600.css';
import '@fontsource/space-grotesk/700.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/500.css';
import '@fontsource/jetbrains-mono/400.css';

const navigation = [
  {
    title: 'Getting Started',
    items: [
      { name: 'Quick Start', href: '/docs/quickstart' },
      { name: 'Overview', href: '/docs/overview' },
      { name: 'Authentication', href: '/docs/authentication' },
      { name: 'Going to Production', href: '/docs/production-guide' },
    ],
  },
  {
    title: 'Core Features',
    items: [
      { name: 'Wallets', href: '/docs/wallets' },
      { name: 'Payments', href: '/docs/payments' },
      { name: 'Holds', href: '/docs/holds' },
      { name: 'Policies', href: '/docs/policies' },
      { name: 'Time-Based Policies', href: '/docs/time-based-policies' },
      { name: 'Merchant Categories', href: '/docs/merchant-categories' },
    ],
  },
  {
    title: 'Protocols',
    items: [
      { name: 'Protocol Stack', href: '/docs/protocols' },
      { name: 'AP2 (Payment)', href: '/docs/ap2' },
      { name: 'UCP (Commerce)', href: '/docs/ucp' },
      { name: 'A2A (Agent-to-Agent)', href: '/docs/a2a' },
      { name: 'TAP (Trusted Agent)', href: '/docs/tap' },
      { name: 'ACP (Commerce)', href: '/docs/acp' },
    ],
  },
  {
    title: 'SDKs & Tools',
    items: [
      { name: 'Python SDK', href: '/docs/sdk-python' },
      { name: 'TypeScript SDK', href: '/docs/sdk-typescript' },
      { name: 'MCP Server', href: '/docs/mcp-server' },
      { name: 'API Reference', href: '/docs/api-reference' },
      { name: 'Interactive API', href: '/docs/api-reference-interactive' },
    ],
  },
  {
    title: 'Framework Integrations',
    items: [
      { name: 'Overview', href: '/docs/integrations' },
      { name: 'LangChain', href: '/docs/integration-langchain' },
      { name: 'CrewAI', href: '/docs/integration-crewai' },
      { name: 'OpenAI Agents', href: '/docs/integration-openai-agents' },
      { name: 'Google ADK', href: '/docs/integration-adk' },
      { name: 'Anthropic Agent SDK', href: '/docs/integration-agent-sdk' },
      { name: 'Browser Use', href: '/docs/integration-browser-use' },
      { name: 'AutoGPT', href: '/docs/integration-autogpt' },
      { name: 'Composio', href: '/docs/integration-composio' },
      { name: 'n8n', href: '/docs/integration-n8n' },
    ],
  },
  {
    title: 'Resources',
    items: [
      { name: 'Architecture', href: '/docs/architecture' },
      { name: 'Blockchain Infrastructure', href: '/docs/blockchain-infrastructure' },
      { name: 'Whitepaper', href: '/docs/whitepaper' },
      { name: 'Security', href: '/docs/security' },
      { name: 'Runtime Guardrails', href: '/docs/runtime-guardrails' },
      { name: 'Deployment', href: '/docs/deployment' },
      { name: 'Troubleshooting', href: '/docs/troubleshooting' },
      { name: 'Why Sardis', href: '/docs/comparison' },
      { name: 'FAQ', href: '/docs/faq' },
      { name: 'Blog', href: '/docs/blog' },
      { name: 'Changelog', href: '/docs/changelog' },
    ],
  },
  {
    title: 'Legal',
    items: [
      { name: 'Terms of Service', href: '/docs/terms' },
      { name: 'Privacy Policy', href: '/docs/privacy' },
      { name: 'Acceptable Use', href: '/docs/acceptable-use' },
      { name: 'Risk Disclosures', href: '/docs/risk-disclosures' },
    ],
  },
];

function DarkModeToggle({ isDark, toggle }) {
  return (
    <button
      onClick={toggle}
      className="w-9 h-9 rounded-lg border border-[var(--landing-border)] hover:border-[var(--landing-accent)] transition-colors duration-200 flex items-center justify-center"
      aria-label="Toggle dark mode"
    >
      {isDark ? (
        <Sun className="w-4 h-4 text-[var(--landing-accent)]" />
      ) : (
        <Moon className="w-4 h-4 text-[var(--landing-text-secondary)]" />
      )}
    </button>
  );
}

export default function DocsLayout() {
  const location = useLocation();
  const [isDark, setIsDark] = useState(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    return savedTheme === 'dark' || (!savedTheme && prefersDark);
  });
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  const toggleDarkMode = () => {
    setIsDark(!isDark);
    if (isDark) {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('theme', 'light');
    } else {
      document.documentElement.classList.add('dark');
      localStorage.setItem('theme', 'dark');
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur-md border-b border-[var(--landing-border)]">
        <div className="flex items-center justify-between h-16 px-6">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-2.5">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
                <path d="M20 5H10a7 7 0 000 14h2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
                <path d="M8 23h10a7 7 0 000-14h-2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
              </svg>
              <span
                className="text-[20px] font-bold leading-none text-foreground"
                style={{ fontFamily: "'Space Grotesk', sans-serif" }}
              >
                Sardis
              </span>
            </Link>
            <div className="hidden md:flex items-center gap-1">
              <span
                className="text-[13px] text-[var(--landing-text-muted)]"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                /
              </span>
              <span
                className="text-[13px] text-[var(--landing-text-tertiary)]"
                style={{ fontFamily: "'JetBrains Mono', monospace" }}
              >
                docs
              </span>
            </div>
            <div className="hidden md:block h-5 w-px bg-[var(--landing-border)] mx-1" />
            <Link
              to="/"
              className="hidden md:block text-[13px] text-[var(--landing-text-muted)] hover:text-[var(--landing-text-secondary)] transition-colors duration-200"
              style={{ fontFamily: "'Inter', sans-serif" }}
            >
              Home
            </Link>
          </div>

          <div className="flex items-center gap-3">
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <button
              className="md:hidden w-9 h-9 rounded-lg border border-[var(--landing-border)] hover:border-[var(--landing-accent)] transition-colors duration-200 flex items-center justify-center"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-4 h-4" /> : <Menu className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </header>

      <div className="flex pt-16">
        {/* Sidebar */}
        <aside className={cn(
          "fixed left-0 top-16 bottom-0 w-64 border-r border-[var(--landing-border)] bg-background overflow-y-auto transition-transform duration-200 md:translate-x-0 z-40",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <nav className="p-5 space-y-6">
            {navigation.map((section, sectionIdx) => (
              <div key={section.title}>
                {sectionIdx > 0 && (
                  <div className="mb-5 border-t border-[var(--landing-border)]" />
                )}
                <h3
                  className="text-[11px] font-bold uppercase tracking-[0.1em] text-[var(--landing-text-muted)] mb-2.5 px-3"
                  style={{ fontFamily: "'JetBrains Mono', monospace" }}
                >
                  {section.title}
                </h3>
                <ul className="space-y-0.5">
                  {section.items.map((item) => {
                    const isActive = location.pathname === item.href;
                    return (
                      <li key={item.name}>
                        <Link
                          to={item.href}
                          onClick={() => setMobileMenuOpen(false)}
                          className={cn(
                            "block px-3 py-1.5 text-[13px] font-medium transition-colors duration-150 border-l-2 rounded-r-md",
                            isActive
                              ? "border-[var(--landing-accent)] text-[var(--landing-accent)] bg-[var(--landing-accent)]/5"
                              : "border-transparent text-[var(--landing-text-tertiary)] hover:text-foreground hover:bg-[var(--landing-border)]"
                          )}
                          style={{ fontFamily: "'Inter', sans-serif" }}
                        >
                          {item.name}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 md:ml-64 min-h-[calc(100vh-4rem)]">
          <div className="max-w-4xl mx-auto px-6 py-12 docs-content">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
    </div>
  );
}
