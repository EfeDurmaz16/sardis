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

const METHOD_COLORS = {
  GET: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  POST: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  PUT: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  PATCH: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  DELETE: 'text-red-400 bg-red-500/10 border-red-500/30',
};

function EndpointList({ spec, loading }) {
  const [openGroups, setOpenGroups] = useState({});

  const endpointsByTag = {};
  if (spec?.paths) {
    for (const [path, methods] of Object.entries(spec.paths)) {
      for (const [method, details] of Object.entries(methods)) {
        if (['get', 'post', 'put', 'patch', 'delete'].includes(method)) {
          const tag = details.tags?.[0] || 'other';
          if (!endpointsByTag[tag]) endpointsByTag[tag] = [];
          endpointsByTag[tag].push({
            method: method.toUpperCase(),
            path,
            summary: details.summary || '',
          });
        }
      }
    }
  }

  const toggleGroup = (tag) => {
    setOpenGroups((prev) => ({ ...prev, [tag]: !prev[tag] }));
  };

  if (loading) {
    return (
      <div className="text-muted-foreground py-8 text-center">
        Loading API specification...
      </div>
    );
  }

  if (!spec) {
    return (
      <div className="space-y-6">
        <p className="text-muted-foreground text-sm">
          Could not load live spec. Showing known endpoint categories.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
          {Object.entries(TAG_DESCRIPTIONS).map(([tag, desc]) => (
            <div key={tag} className="p-4 border border-border hover:border-[var(--sardis-orange)]/50 transition-colors">
              <h4 className="font-bold capitalize font-display text-sm mb-1">{tag.replace(/-/g, ' ')}</h4>
              <p className="text-xs text-muted-foreground">{desc}</p>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const sortedTags = Object.entries(endpointsByTag).sort(([a], [b]) => a.localeCompare(b));

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6">
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

      {sortedTags.map(([tag, endpoints]) => {
        const isOpen = openGroups[tag] !== false; // default open
        return (
          <div key={tag} className="border border-border">
            <button
              onClick={() => toggleGroup(tag)}
              className="w-full p-4 border-b border-border bg-muted/30 flex items-center justify-between hover:bg-muted/50 transition-colors text-left"
            >
              <div>
                <h3 className="text-base font-bold font-display capitalize">
                  {tag.replace(/-/g, ' ')}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {TAG_DESCRIPTIONS[tag] || ''} &mdash; {endpoints.length} endpoint{endpoints.length !== 1 ? 's' : ''}
                </p>
              </div>
              <span className="text-muted-foreground text-sm ml-4 shrink-0">
                {isOpen ? '▲' : '▼'}
              </span>
            </button>
            {isOpen && (
              <div className="divide-y divide-border">
                {endpoints.map((ep, i) => (
                  <div
                    key={i}
                    className="px-4 py-2.5 flex items-center gap-3 hover:bg-muted/20 transition-colors"
                  >
                    <span
                      className={`px-2 py-0.5 text-xs font-mono font-bold border ${METHOD_COLORS[ep.method] || ''} min-w-[60px] text-center shrink-0`}
                    >
                      {ep.method}
                    </span>
                    <code className="text-sm font-mono text-foreground flex-1 min-w-0 truncate">
                      {ep.path}
                    </code>
                    <span className="text-xs text-muted-foreground hidden sm:block max-w-[280px] truncate shrink-0">
                      {ep.summary}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default function APIReferenceInteractive() {
  const apiUrl = process.env.VITE_API_URL || 'https://api.sardis.sh';
  const [activeTab, setActiveTab] = useState('interactive');
  const [iframeError, setIframeError] = useState(false);
  const [spec, setSpec] = useState(null);
  const [specUrl, setSpecUrl] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    const sources = [
      `${apiUrl}/api/v2/openapi.json`,
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
  }, [apiUrl]);

  const docsUrl = `${apiUrl}/api/v2/docs`;

  return (
    <article className="prose dark:prose-invert max-w-none">
      {/* Header */}
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            API
          </span>
          <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
            Interactive
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">API Reference</h1>
        <p className="text-xl text-muted-foreground">
          Interactive documentation powered by OpenAPI. Explore and test endpoints directly.
        </p>
      </div>

      {/* Base URL banner */}
      <section className="not-prose mb-6 p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 bg-[var(--sardis-orange)] rounded-full" />
          <span className="font-bold text-[var(--sardis-orange)]">BASE URL</span>
        </div>
        <code className="text-sm font-mono text-foreground">https://api.sardis.sh</code>
        <p className="text-sm text-muted-foreground mt-2">
          Authentication via{' '}
          <code className="text-xs bg-muted px-1 py-0.5">X-API-Key</code> header. Routes
          under <code className="text-xs bg-muted px-1 py-0.5">/api/v2/*</code>. Rate
          limit: 100 req/min.
        </p>
      </section>

      {/* Quick links */}
      <section className="not-prose mb-6 flex flex-wrap gap-3">
        <a
          href={specUrl || `${apiUrl}/api/v2/openapi.json`}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] transition-colors text-sm font-mono"
        >
          OpenAPI Spec (JSON)
        </a>
        <a
          href={docsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] transition-colors text-sm font-mono"
        >
          Open in new tab ↗
        </a>
      </section>

      {/* Tabs */}
      <div className="not-prose mb-6">
        <div className="flex gap-0 border border-border w-fit">
          <button
            onClick={() => setActiveTab('interactive')}
            className={`px-5 py-2 text-sm font-mono transition-colors ${
              activeTab === 'interactive'
                ? 'bg-[var(--sardis-orange)] text-black font-bold'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            Interactive
          </button>
          <button
            onClick={() => setActiveTab('endpoints')}
            className={`px-5 py-2 text-sm font-mono transition-colors border-l border-border ${
              activeTab === 'endpoints'
                ? 'bg-[var(--sardis-orange)] text-black font-bold'
                : 'text-muted-foreground hover:text-foreground hover:bg-muted/40'
            }`}
          >
            Endpoint List
          </button>
        </div>
      </div>

      {/* Tab content */}
      <div className="not-prose">
        {activeTab === 'interactive' && (
          <div>
            {iframeError ? (
              <div className="p-6 border border-border bg-muted/20 text-sm text-muted-foreground space-y-3">
                <p className="font-bold text-foreground">Could not load interactive docs.</p>
                <p>
                  The Swagger UI is available directly at{' '}
                  <a
                    href={docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline hover:text-foreground"
                  >
                    {docsUrl}
                  </a>
                </p>
                <p>
                  Switch to the{' '}
                  <button
                    onClick={() => setActiveTab('endpoints')}
                    className="underline hover:text-foreground"
                  >
                    Endpoint List
                  </button>{' '}
                  tab for a categorized reference.
                </p>
              </div>
            ) : (
              <div className="border border-border rounded overflow-hidden">
                <div className="px-4 py-2 bg-muted/30 border-b border-border flex items-center justify-between text-xs text-muted-foreground font-mono">
                  <span>{docsUrl}</span>
                  <a
                    href={docsUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:text-foreground transition-colors"
                  >
                    Open full page ↗
                  </a>
                </div>
                <iframe
                  src={docsUrl}
                  title="Sardis API Interactive Docs"
                  className="w-full border-0"
                  style={{ height: '800px' }}
                  onError={() => setIframeError(true)}
                />
              </div>
            )}
          </div>
        )}

        {activeTab === 'endpoints' && (
          <EndpointList spec={spec} loading={loading} />
        )}
      </div>
    </article>
  );
}
