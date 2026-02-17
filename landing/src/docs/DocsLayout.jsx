import { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { Sun, Moon, Menu, X } from 'lucide-react';
import { cn } from '@/lib/utils';
import SardisLogo from '@/components/SardisLogo';

const navigation = [
  {
    title: 'Getting Started',
    items: [
      { name: 'Overview', href: '/docs/overview' },
      { name: 'Quick Start', href: '/docs/quickstart' },
      { name: 'Authentication', href: '/docs/authentication' },
    ],
  },
  {
    title: 'Protocols',
    items: [
      { name: 'Protocol Stack', href: '/docs/protocols' },
      { name: 'AP2 (Payment)', href: '/docs/ap2' },
      { name: 'UCP (Commerce)', href: '/docs/ucp' },
      { name: 'A2A (Agent-to-Agent)', href: '/docs/a2a' },
      { name: 'TAP (Trust Anchor)', href: '/docs/tap' },
      { name: 'ACP (Commerce)', href: '/docs/acp' },
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
    title: 'SDKs & Tools',
    items: [
      { name: 'Python SDK', href: '/docs/sdk-python' },
      { name: 'TypeScript SDK', href: '/docs/sdk-typescript' },
      { name: 'MCP Server', href: '/docs/mcp-server' },
      { name: 'API Reference', href: '/docs/api-reference' },
    ],
  },
  {
    title: 'Resources',
    items: [
      { name: 'Architecture', href: '/docs/architecture' },
      { name: 'Blockchain Infrastructure', href: '/docs/blockchain-infrastructure' },
      { name: 'Whitepaper', href: '/docs/whitepaper' },
      { name: 'Security', href: '/docs/security' },
      { name: 'Deployment', href: '/docs/deployment' },
      { name: 'Why Sardis', href: '/docs/comparison' },
      { name: 'FAQ', href: '/docs/faq' },
      { name: 'Blog', href: '/docs/blog' },
      { name: 'Changelog', href: '/docs/changelog' },
      { name: 'Roadmap', href: '/docs/roadmap' },
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
      className="w-10 h-10 border border-border hover:border-[var(--sardis-orange)] transition-colors flex items-center justify-center"
      aria-label="Toggle dark mode"
    >
      {isDark ? (
        <Sun className="w-5 h-5 text-[var(--sardis-orange)]" />
      ) : (
        <Moon className="w-5 h-5 text-foreground" />
      )}
    </button>
  );
}

export default function DocsLayout() {
  const location = useLocation();
  const [isDark, setIsDark] = useState(true);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    if (savedTheme === 'dark' || (!savedTheme && prefersDark)) {
      setIsDark(true);
      document.documentElement.classList.add('dark');
    } else {
      setIsDark(false);
      document.documentElement.classList.remove('dark');
    }
  }, []);

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
      <header className="fixed top-0 left-0 right-0 z-50 bg-background/95 backdrop-blur-sm border-b border-border">
        <div className="flex items-center justify-between h-16 px-6">
          <div className="flex items-center gap-6">
            <Link to="/" className="flex items-center gap-3 font-bold text-xl tracking-tight font-display">
              <SardisLogo />
              <span>Sardis</span>
            </Link>
            <span className="text-muted-foreground font-mono text-sm">/docs</span>
          </div>

          <div className="flex items-center gap-4">
            <DarkModeToggle isDark={isDark} toggle={toggleDarkMode} />
            <button
              className="md:hidden w-10 h-10 border border-border flex items-center justify-center"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            >
              {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </header>

      <div className="flex pt-16">
        {/* Sidebar */}
        <aside className={cn(
          "fixed left-0 top-16 bottom-0 w-64 border-r border-border bg-background overflow-y-auto transition-transform md:translate-x-0 z-40",
          mobileMenuOpen ? "translate-x-0" : "-translate-x-full"
        )}>
          <nav className="p-6 space-y-8">
            {navigation.map((section) => (
              <div key={section.title}>
                <h3 className="text-xs font-bold uppercase tracking-widest text-muted-foreground mb-3 font-mono">
                  {section.title}
                </h3>
                <ul className="space-y-1">
                  {section.items.map((item) => (
                    <li key={item.name}>
                      <Link
                        to={item.href}
                        onClick={() => setMobileMenuOpen(false)}
                        className={cn(
                          "block px-3 py-2 text-sm font-medium transition-colors border-l-2",
                          location.pathname === item.href
                            ? "border-[var(--sardis-orange)] text-[var(--sardis-orange)] bg-[var(--sardis-orange)]/5"
                            : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                        )}
                      >
                        {item.name}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="flex-1 md:ml-64 min-h-[calc(100vh-4rem)]">
          <div className="max-w-4xl mx-auto px-6 py-12">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile overlay */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
    </div>
  );
}
