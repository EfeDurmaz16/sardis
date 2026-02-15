import { useEffect, useState } from 'react';

const TAG_DESCRIPTIONS = {
  wallets: 'Create, manage, and fund agent wallets',
  mandates: 'Payment mandate lifecycle management',
  transactions: 'Transaction status and history',
  holds: 'Pre-authorization holds (reserve funds)',
  approvals: 'Human-in-the-loop approval workflows',
  cards: 'Virtual card issuance and management',
  policies: 'Natural language spending policy engine',
  compliance: 'KYC verification and sanctions screening',
  ramp: 'Fiat on-ramp and off-ramp operations',
  checkout: 'Agentic checkout flow',
  agents: 'AI agent identity and configuration',
  ledger: 'Append-only transaction ledger',
  treasury: 'Fiat-first treasury accounts and ACH lifecycle',
  webhooks: 'Webhook subscription management',
  marketplace: 'A2A service discovery',
  ap2: 'Agent Payment Protocol v2',
  auth: 'Authentication and API keys',
  'api-keys': 'API key management',
  admin: 'Administrative operations',
  health: 'Health check endpoints',
  mvp: 'Minimum Viable Protocol',
};

export default function APIReference() {
  const [spec, setSpec] = useState(null);
  const [specUrl, setSpecUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const sources = [
      'https://api.sardis.sh/api/v2/openapi.json',
      '/openapi.json',
    ];

    const loadSpec = async () => {
      for (const url of sources) {
        try {
          const response = await fetch(url);
          if (!response.ok) continue;
          const data = await response.json();
          if (!cancelled) {
            setSpec(data);
            setSpecUrl(url);
            setLoading(false);
          }
          return;
        } catch {
          // try next source
        }
      }
      if (!cancelled) setLoading(false);
    };

    void loadSpec();
    return () => {
      cancelled = true;
    };
  }, []);

  const endpointsByTag = {};
  if (spec?.paths) {
    for (const [path, methods] of Object.entries(spec.paths)) {
      for (const [method, details] of Object.entries(methods)) {
        if (['get', 'post', 'put', 'patch', 'delete'].includes(method)) {
          const tag = details.tags?.[0] || 'other';
          if (!endpointsByTag[tag]) endpointsByTag[tag] = [];
          endpointsByTag[tag].push({ method: method.toUpperCase(), path, summary: details.summary || '' });
        }
      }
    }
  }

  const methodColors = {
    GET: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
    POST: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    PUT: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
    PATCH: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
    DELETE: 'text-red-400 bg-red-500/10 border-red-500/30',
  };

  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            API
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">API Reference</h1>
        <p className="text-xl text-muted-foreground">
          Complete REST API documentation for the Sardis platform.
        </p>
      </div>

      <section className="not-prose mb-8 p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 bg-[var(--sardis-orange)] rounded-full"></span>
          <span className="font-bold text-[var(--sardis-orange)]">BASE URL</span>
        </div>
        <code className="text-sm font-mono text-foreground">https://api.sardis.sh</code>
        <p className="text-sm text-muted-foreground mt-2">
          Authentication via <code className="text-xs bg-muted px-1 py-0.5">X-API-Key</code> header. API routes are under <code className="text-xs bg-muted px-1 py-0.5">/api/v2/*</code>. Rate limit: 100 req/min.
        </p>
        <p className="text-sm text-muted-foreground mt-2">
          Browser docs: <a className="underline hover:text-foreground" href="https://api.sardis.sh/api/v2/docs" target="_blank" rel="noopener noreferrer">https://api.sardis.sh/api/v2/docs</a>
        </p>
      </section>

      <section className="not-prose mb-8 flex flex-wrap gap-3">
        <a
          href={specUrl || 'https://api.sardis.sh/api/v2/openapi.json'}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] transition-colors text-sm font-mono"
        >
          OpenAPI Spec (JSON)
        </a>
      </section>

      <section className="not-prose mb-8 p-4 border border-border bg-muted/20">
        <h2 className="text-lg font-bold font-display mb-3">Treasury ACH Endpoints (USD-first)</h2>
        <ul className="space-y-2 text-sm text-muted-foreground font-mono">
          <li>POST /api/v2/treasury/account-holders/sync</li>
          <li>GET /api/v2/treasury/financial-accounts</li>
          <li>POST /api/v2/treasury/external-bank-accounts</li>
          <li>POST /api/v2/treasury/external-bank-accounts/{'{token}'}/verify-micro-deposits</li>
          <li>POST /api/v2/treasury/fund</li>
          <li>POST /api/v2/treasury/withdraw</li>
          <li>GET /api/v2/treasury/payments/{'{payment_token}'}</li>
          <li>GET /api/v2/treasury/balances</li>
        </ul>
      </section>

      {loading ? (
        <div className="not-prose text-muted-foreground">Loading API specification...</div>
      ) : !spec ? (
        <div className="not-prose text-muted-foreground">Failed to load API specification.</div>
      ) : (
        <div className="not-prose space-y-8">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <div className="p-4 border border-border">
              <div className="text-2xl font-bold text-[var(--sardis-orange)]">
                {Object.keys(spec.paths || {}).length}
              </div>
              <div className="text-sm text-muted-foreground">Endpoints</div>
            </div>
            <div className="p-4 border border-border">
              <div className="text-2xl font-bold text-[var(--sardis-orange)]">
                {Object.keys(endpointsByTag).length}
              </div>
              <div className="text-sm text-muted-foreground">Categories</div>
            </div>
            <div className="p-4 border border-border">
              <div className="text-2xl font-bold text-[var(--sardis-orange)]">v2.0</div>
              <div className="text-sm text-muted-foreground">API Version</div>
            </div>
            <div className="p-4 border border-border">
              <div className="text-2xl font-bold text-[var(--sardis-orange)]">REST</div>
              <div className="text-sm text-muted-foreground">Protocol</div>
            </div>
          </div>

          {Object.entries(endpointsByTag)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([tag, endpoints]) => (
            <div key={tag} className="border border-border">
              <div className="p-4 border-b border-border bg-muted/30">
                <h3 className="text-lg font-bold font-display capitalize">{tag.replace(/-/g, ' ')}</h3>
                <p className="text-sm text-muted-foreground">
                  {TAG_DESCRIPTIONS[tag] || ''} — {endpoints.length} endpoint{endpoints.length !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="divide-y divide-border">
                {endpoints.map((ep, i) => (
                  <div key={i} className="px-4 py-2 flex items-center gap-3 hover:bg-muted/20 transition-colors">
                    <span className={`px-2 py-0.5 text-xs font-mono font-bold border ${methodColors[ep.method] || ''} min-w-[60px] text-center`}>
                      {ep.method}
                    </span>
                    <code className="text-sm font-mono text-foreground flex-1">{ep.path}</code>
                    <span className="text-xs text-muted-foreground hidden sm:block max-w-[300px] truncate">
                      {ep.summary}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
