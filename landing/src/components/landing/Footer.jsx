import { Link } from 'react-router-dom';

const footerColumns = [
  {
    header: 'Product',
    links: [
      { label: 'Documentation', to: '/docs' },
      { label: 'API Reference', to: '/docs/api-reference' },
      { label: 'MCP Server', to: '/docs/mcp-server' },
      { label: 'Playground', to: '/playground' },
      { label: 'Pricing', to: '/pricing' },
      { label: 'Enterprise', to: '/enterprise' },
      { label: 'Status', to: '/status' },
    ],
  },
  {
    header: 'Developers',
    links: [
      { label: 'GitHub', href: 'https://github.com/EfeDurmaz16/sardis', external: true },
      { label: 'Quickstart', to: '/docs/quickstart' },
      { label: 'Python SDK', to: '/docs/sdk-python' },
      { label: 'TypeScript SDK', to: '/docs/sdk-typescript' },
      { label: 'Integrations', to: '/docs/integrations' },
      { label: 'Blog', to: '/docs/blog' },
      { label: 'Changelog', to: '/docs/changelog' },
    ],
  },
  {
    header: 'Platform',
    links: [
      { label: 'Wallets', to: '/docs/wallets' },
      { label: 'Payments', to: '/docs/payments' },
      { label: 'Spending Policies', to: '/docs/policies' },
      { label: 'Spending Mandates', to: '/docs/spending-mandates' },
      { label: 'Security', to: '/docs/security' },
      { label: 'Architecture', to: '/docs/architecture' },
      { label: 'Whitepaper', to: '/docs/whitepaper' },
    ],
  },
  {
    header: 'Legal',
    links: [
      { label: 'Terms of Service', to: '/docs/terms' },
      { label: 'Privacy Policy', to: '/docs/privacy' },
      { label: 'Acceptable Use', to: '/docs/acceptable-use' },
      { label: 'Risk Disclosures', to: '/docs/risk-disclosures' },
      { label: 'Trust Center', to: '/docs/trust' },
    ],
  },
];

export default function Footer() {
  const linkStyle = {
    fontSize: '13px',
    fontFamily: "'Inter', sans-serif",
    color: 'var(--landing-text-ghost)',
  };

  return (
    <footer style={{ backgroundColor: 'var(--landing-bg)', borderTop: '1px solid var(--landing-border)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 pt-12 md:pt-16 pb-8">
        {/* Top grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-8 md:gap-12">
          {/* Column 1: Brand */}
          <div>
            <div className="flex items-center gap-2">
              <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                <path
                  d="M20 5H10a7 7 0 000 14h2"
                  stroke="var(--landing-text-muted)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                />
                <path
                  d="M8 23h10a7 7 0 000-14h-2"
                  stroke="var(--landing-text-muted)"
                  strokeWidth="3"
                  strokeLinecap="round"
                  fill="none"
                />
              </svg>
              <span
                className="text-[18px] font-semibold leading-none"
                style={{ fontFamily: "'Space Grotesk', system-ui, sans-serif", color: 'var(--landing-text-muted)' }}
              >
                Sardis
              </span>
            </div>
            <p
              className="mt-4 text-[13px] font-light max-w-[200px] leading-relaxed"
              style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-ghost)' }}
            >
              Payment infrastructure for autonomous agents.
            </p>
          </div>

          {/* Columns 2-4 */}
          {footerColumns.map((col) => (
            <div key={col.header}>
              <h3
                className="text-[11px] uppercase tracking-widest mb-4"
                style={{ fontFamily: "'JetBrains Mono', monospace", color: 'var(--landing-text-muted)' }}
              >
                {col.header}
              </h3>
              {col.links.map((link) =>
                link.external ? (
                  <a
                    key={link.label}
                    href={link.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="transition-colors mb-2.5 block"
                    style={linkStyle}
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--landing-text-tertiary)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--landing-text-ghost)'}
                  >
                    {link.label}
                  </a>
                ) : (
                  <Link
                    key={link.label}
                    to={link.to}
                    className="transition-colors mb-2.5 block"
                    style={linkStyle}
                    onMouseEnter={(e) => e.currentTarget.style.color = 'var(--landing-text-tertiary)'}
                    onMouseLeave={(e) => e.currentTarget.style.color = 'var(--landing-text-ghost)'}
                  >
                    {link.label}
                  </Link>
                )
              )}
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          className="mt-12 md:mt-16 pt-6 flex flex-col md:flex-row justify-between items-center gap-4"
          style={{ borderTop: '1px solid var(--landing-border)' }}
        >
          <span
            className="text-[12px]"
            style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-ghost)' }}
          >
            © 2026 Sardis
          </span>
          <div className="flex gap-6">
            {[
              { label: 'X', href: 'https://x.com/sardisHQ' },
              { label: 'GitHub', href: 'https://github.com/EfeDurmaz16/sardis' },
              { label: 'Discord', href: 'https://discord.gg/pUJTskfK' },
            ].map((social) => (
              <a
                key={social.label}
                href={social.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[12px] transition-colors"
                style={{ fontFamily: "'Inter', sans-serif", color: 'var(--landing-text-ghost)' }}
                onMouseEnter={(e) => e.currentTarget.style.color = 'var(--landing-text-tertiary)'}
                onMouseLeave={(e) => e.currentTarget.style.color = 'var(--landing-text-ghost)'}
              >
                {social.label}
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
