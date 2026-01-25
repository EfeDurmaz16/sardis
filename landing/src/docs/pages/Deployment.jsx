export default function DocsDeployment() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">
            OPERATIONS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Deployment Guide</h1>
        <p className="text-xl text-muted-foreground">
          Production deployment guidelines and infrastructure setup.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Prerequisites
        </h2>

        <div className="not-prose grid md:grid-cols-2 gap-4 mb-6">
          {[
            { name: 'PostgreSQL', version: '15+', desc: 'Primary database (Neon or Supabase recommended)' },
            { name: 'Redis', version: '7+', desc: 'Optional, for rate limiting and caching' },
            { name: 'Node.js', version: '18+', desc: 'For MCP server and TypeScript SDK' },
            { name: 'Python', version: '3.10+', desc: 'For API server and Python SDK' },
          ].map((item) => (
            <div key={item.name} className="p-4 border border-border">
              <div className="flex items-center justify-between mb-1">
                <h3 className="font-bold font-display">{item.name}</h3>
                <span className="text-xs font-mono text-muted-foreground">{item.version}</span>
              </div>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Environment Variables
        </h2>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Required - MPC Wallets
TURNKEY_API_PUBLIC_KEY=...
TURNKEY_API_PRIVATE_KEY=...
TURNKEY_ORGANIZATION_ID=org_...

# Required - Virtual Cards
LITHIC_API_KEY=...

# Required - Fiat Rails
BRIDGE_API_KEY=...

# Required - Compliance
PERSONA_API_KEY=...
PERSONA_TEMPLATE_ID=...
ELLIPTIC_API_KEY=...
ELLIPTIC_API_SECRET=...

# Smart Contracts (Base Sepolia - Already Deployed)
SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS=0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7
SARDIS_BASE_SEPOLIA_ESCROW_ADDRESS=0x5cf752B512FE6066a8fc2E6ce555c0C755aB5932

# Infrastructure
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# API Configuration
API_PORT=8000
API_HOST=0.0.0.0
LOG_LEVEL=info

# Security
JWT_SECRET=...
CORS_ORIGINS=https://your-domain.com`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Deployment Steps
        </h2>

        <div className="not-prose space-y-4">
          {[
            {
              step: '1',
              title: 'Database Setup',
              commands: [
                '# Create database',
                'createdb sardis_production',
                '',
                '# Run migrations',
                'python -m alembic upgrade head'
              ]
            },
            {
              step: '2',
              title: 'Deploy API Server',
              commands: [
                '# Install dependencies',
                'pip install -e packages/sardis-api',
                '',
                '# Start server (production)',
                'uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port 8000'
              ]
            },
            {
              step: '3',
              title: 'Deploy MCP Server',
              commands: [
                '# Install globally',
                'npm install -g @sardis/mcp-server',
                '',
                '# Or run via npx',
                'npx @sardis/mcp-server start'
              ]
            },
            {
              step: '4',
              title: 'Configure Turnkey Wallets',
              commands: [
                '# Initialize organization',
                'sardis-cli turnkey init',
                '',
                '# Create master wallet',
                'sardis-cli wallet create --name "Master Wallet"'
              ]
            },
            {
              step: '5',
              title: 'Verify Deployment',
              commands: [
                '# Health check',
                'curl https://api.your-domain.com/health',
                '',
                '# Expected response',
                '{"status": "healthy", "version": "1.0.0"}'
              ]
            },
          ].map((item) => (
            <div key={item.step} className="border border-border">
              <div className="flex items-center gap-3 px-4 py-3 border-b border-border bg-muted/30">
                <div className="w-6 h-6 border border-[var(--sardis-orange)] flex items-center justify-center font-mono font-bold text-[var(--sardis-orange)] text-sm">
                  {item.step}
                </div>
                <h3 className="font-bold font-display">{item.title}</h3>
              </div>
              <div className="p-4 bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] font-mono text-sm overflow-x-auto">
                <pre className="text-[var(--sardis-canvas)]">{item.commands.join('\n')}</pre>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Vercel Deployment
        </h2>
        <p className="text-muted-foreground mb-4">
          For the dashboard and landing page, deploy to Vercel:
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy to production
vercel --prod

# Configure domain
vercel domains add sardis.sh`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Monitoring
        </h2>

        <div className="not-prose grid md:grid-cols-3 gap-4">
          {[
            { name: 'Health Endpoint', path: '/health', desc: 'Basic liveness check' },
            { name: 'Metrics', path: '/metrics', desc: 'Prometheus-compatible metrics' },
            { name: 'API Docs', path: '/api/v2/docs', desc: 'OpenAPI documentation' },
          ].map((item) => (
            <div key={item.name} className="p-4 border border-border">
              <h3 className="font-bold font-display mb-1">{item.name}</h3>
              <code className="text-xs text-[var(--sardis-orange)] font-mono">{item.path}</code>
              <p className="text-sm text-muted-foreground mt-2">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Production Checklist</h3>
        <ul className="space-y-2">
          {[
            'Environment variables configured',
            'Database migrations applied',
            'Turnkey organization initialized',
            'SSL certificates configured',
            'Rate limiting enabled',
            'Monitoring and alerting set up',
            'Backup strategy implemented',
            'Incident response plan documented',
          ].map((item) => (
            <li key={item} className="flex items-center gap-3 text-sm">
              <span className="w-4 h-4 border border-border flex items-center justify-center text-xs">?</span>
              <span className="text-muted-foreground">{item}</span>
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
