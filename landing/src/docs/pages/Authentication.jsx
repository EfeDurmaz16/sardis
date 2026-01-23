export default function DocsAuthentication() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            GETTING STARTED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Authentication</h1>
        <p className="text-xl text-muted-foreground">
          How to authenticate with the Sardis API.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> API Keys
        </h2>
        <p className="text-muted-foreground mb-4">
          All API requests require authentication using an API key. Keys are prefixed to indicate their environment:
        </p>

        <div className="not-prose mb-6">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border font-mono">Prefix</th>
                <th className="px-4 py-2 text-left border-b border-border">Environment</th>
                <th className="px-4 py-2 text-left border-b border-border">Use Case</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sk_live_</td>
                <td className="px-4 py-2 border-b border-border">Production</td>
                <td className="px-4 py-2 border-b border-border text-muted-foreground">Real transactions</td>
              </tr>
              <tr>
                <td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sk_test_</td>
                <td className="px-4 py-2 border-b border-border">Testnet</td>
                <td className="px-4 py-2 border-b border-border text-muted-foreground">Development & testing</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Using Your API Key
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`curl https://api.sardis.sh/v2/wallets \\
  -H "Authorization: Bearer sk_test_..."`}</pre>
          </div>
        </div>

        <div className="not-prose space-y-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <div className="text-muted-foreground mb-2"># Python</div>
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient
client = SardisClient(api_key="sk_test_...")`}</pre>
          </div>

          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <div className="text-muted-foreground mb-2">// TypeScript</div>
            <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';
const client = new SardisClient({ apiKey: 'sk_test_...' });`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Rate Limits
        </h2>

        <div className="not-prose mb-6">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Plan</th>
                <th className="px-4 py-2 text-left border-b border-border">Requests/Min</th>
                <th className="px-4 py-2 text-left border-b border-border">Requests/Day</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="px-4 py-2 border-b border-border">Free</td>
                <td className="px-4 py-2 border-b border-border font-mono">60</td>
                <td className="px-4 py-2 border-b border-border font-mono">1,000</td>
              </tr>
              <tr>
                <td className="px-4 py-2 border-b border-border">Pro</td>
                <td className="px-4 py-2 border-b border-border font-mono">600</td>
                <td className="px-4 py-2 border-b border-border font-mono">50,000</td>
              </tr>
              <tr>
                <td className="px-4 py-2 border-b border-border">Enterprise</td>
                <td className="px-4 py-2 border-b border-border font-mono">Custom</td>
                <td className="px-4 py-2 border-b border-border font-mono">Custom</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="not-prose p-6 border border-red-500/30 bg-red-500/5">
        <h3 className="font-bold font-display mb-2 text-red-500">Security Warning</h3>
        <p className="text-muted-foreground text-sm">
          Never expose your API key in client-side code or public repositories.
        </p>
      </section>
    </article>
  );
}
