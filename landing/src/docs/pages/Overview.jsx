import { Link } from 'react-router-dom';
import SEO, { createBreadcrumbSchema } from '@/components/SEO';

export default function DocsOverview() {
  return (
    <>
      <SEO
        title="Documentation Overview"
        description="Sardis Payment OS documentation — MPC wallets, natural language spending policies, and payment infrastructure for AI agents. Supports Python, TypeScript, and MCP integrations."
        path="/docs/overview"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Overview' },
          ]),
        ]}
      />
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
            DOCUMENTATION
          </span>
          <span>Updated Feb 15, 2026</span>
          <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            95% COMPLETE
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Sardis Payment OS Documentation</h1>
        <p className="text-xl text-muted-foreground">
          Sardis is a Payment OS for the Agent Economy, providing AI agents with policy-controlled wallets
          and natural language spending policies to prevent financial hallucination errors.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Overview
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis enables AI agents (such as Claude, Cursor, and LangChain) to securely manage payments
          using programmable wallets and enforce real-time spending policies. The system prevents financial
          errors by acting as a policy firewall, ensuring agents cannot overspend or transact outside defined limits.
        </p>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis supports multiple payment rails — bank transfers (ACH/wire), virtual cards (Lithic), and stablecoins (USDC, USDT)
          as an optional settlement alternative. Compliance integrations run in staged lanes (for example Persona and Elliptic onboarding paths).
          No crypto knowledge required;
          agents can fund entirely from bank accounts. It integrates with popular agent frameworks using SDKs in Python and TypeScript.
        </p>
        <p className="text-muted-foreground leading-relaxed">
          The project follows an <strong className="text-foreground">Open Core licensing model</strong>,
          with open SDKs and proprietary infrastructure components.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Key Features
        </h2>
        <div className="grid md:grid-cols-2 gap-4 not-prose">
          {[
            { title: 'Live-MPC Non-Custodial Posture', desc: 'Applies on stablecoin rails when running in live MPC mode' },
            { title: 'Natural Language Policies', desc: 'Define spending rules in plain English' },
            { title: 'Financial Firewall', desc: 'Prevent hallucination errors in real-time' },
            { title: 'Instant Virtual Cards', desc: 'Issue cards on-demand via Lithic' },
            { title: 'Multi-Rail Settlement', desc: 'Bank transfer, virtual card, or stablecoins' },
            { title: 'Bank-First Funding', desc: 'Fund from bank accounts, withdraw to USD' },
            { title: 'Compliance Lanes', desc: 'Provider-integrated KYC/AML onboarding paths for regulated rails' },
            { title: 'Zero Integration Setup', desc: 'MCP server with 52 tools' },
          ].map((feature) => (
            <div key={feature.title} className="p-4 border border-border hover:border-[var(--sardis-orange)] transition-colors">
              <h3 className="font-bold font-display mb-1">{feature.title}</h3>
              <p className="text-sm text-muted-foreground">{feature.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Navigation
        </h2>
        <div className="not-prose grid md:grid-cols-3 gap-4">
          <Link to="/docs/quickstart" className="block p-4 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <h3 className="font-bold font-display mb-1 group-hover:text-[var(--sardis-orange)]">Quick Start →</h3>
            <p className="text-sm text-muted-foreground">Get up and running in 5 minutes</p>
          </Link>
          <Link to="/docs/sdk" className="block p-4 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <h3 className="font-bold font-display mb-1 group-hover:text-[var(--sardis-orange)]">SDK Reference →</h3>
            <p className="text-sm text-muted-foreground">Python and TypeScript SDKs</p>
          </Link>
          <Link to="/docs/architecture" className="block p-4 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <h3 className="font-bold font-display mb-1 group-hover:text-[var(--sardis-orange)]">Architecture →</h3>
            <p className="text-sm text-muted-foreground">System design and components</p>
          </Link>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Framework Integrations
        </h2>
        <div className="not-prose overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 font-mono font-bold text-muted-foreground">Framework</th>
                <th className="text-left py-3 px-4 font-mono font-bold text-muted-foreground">Language</th>
                <th className="text-left py-3 px-4 font-mono font-bold text-muted-foreground">Status</th>
              </tr>
            </thead>
            <tbody>
              {[
                { framework: 'Claude Desktop / Cursor', lang: 'MCP Server', status: 'STABLE' },
                { framework: 'LangChain', lang: 'Python', status: 'STABLE' },
                { framework: 'Vercel AI SDK', lang: 'TypeScript', status: 'STABLE' },
                { framework: 'OpenAI Functions / Swarm', lang: 'Python', status: 'STABLE' },
                { framework: 'LlamaIndex', lang: 'Python', status: 'BETA' },
              ].map((row) => (
                <tr key={row.framework} className="border-b border-border">
                  <td className="py-3 px-4 font-medium">{row.framework}</td>
                  <td className="py-3 px-4 text-muted-foreground font-mono">{row.lang}</td>
                  <td className="py-3 px-4">
                    <span className={`px-2 py-1 text-xs font-mono font-bold ${
                      row.status === 'STABLE'
                        ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30'
                        : 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/30'
                    }`}>
                      {row.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Need Help?</h3>
        <p className="text-muted-foreground text-sm mb-4">
          For support, consult the docs, check the examples folder, or open an issue on GitHub.
        </p>
        <div className="flex gap-3">
          <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noreferrer"
            className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] text-sm font-mono transition-colors">
            GitHub
          </a>
          <a href="mailto:efe@sardis.dev"
            className="px-4 py-2 bg-[var(--sardis-orange)] text-white text-sm font-mono hover:bg-[var(--sardis-orange)]/90 transition-colors">
            Contact
          </a>
        </div>
      </section>
    </article>
    </>
  );
}
