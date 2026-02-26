import SEO, { createBreadcrumbSchema } from '@/components/SEO';

const sheets = [
  {
    provider: 'Stripe',
    summary: 'Card issuing fallback rail, enterprise distribution fit, funding and PAN model due diligence.',
    href: 'https://github.com/EfeDurmaz16/sardis/blob/main/docs/marketing/diligence-response-sheet-stripe-q1-2026.md',
  },
  {
    provider: 'Lithic',
    summary: 'Primary issuer candidate with real-time auth controls and fail-closed policy alignment.',
    href: 'https://github.com/EfeDurmaz16/sardis/blob/main/docs/marketing/diligence-response-sheet-lithic-q1-2026.md',
  },
  {
    provider: 'Rain',
    summary: 'Stablecoin-native card and money movement stack with API/commercial readiness checks.',
    href: 'https://github.com/EfeDurmaz16/sardis/blob/main/docs/marketing/diligence-response-sheet-rain-q1-2026.md',
  },
  {
    provider: 'Bridge',
    summary: 'Stablecoin treasury/connectivity layer with issuer interoperability and settlement constraints.',
    href: 'https://github.com/EfeDurmaz16/sardis/blob/main/docs/marketing/diligence-response-sheet-bridge-q1-2026.md',
  },
];

export default function DocsProviderDiligence() {
  return (
    <>
      <SEO
        title="Provider Diligence"
        description="Stripe, Lithic, Rain, and Bridge diligence response sheets for Sardis funding rails, PAN posture, compliance split, and go/no-go criteria."
        path="/docs/provider-diligence"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Provider Diligence' },
          ]),
        ]}
      />
      <article className="prose prose-invert max-w-none">
        <div className="not-prose mb-8">
          <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
            <span className="px-2 py-1 bg-amber-500/10 border border-amber-500/30 text-amber-500">DILIGENCE</span>
            <span>Issuer + Funding Partners</span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">Provider Diligence Sheets</h1>
          <p className="text-xl text-muted-foreground">
            One-page response sheets for Stripe, Lithic, Rain, and Bridge covering funding model, compliance ownership, and operational go/no-go criteria.
          </p>
        </div>

        <section className="grid gap-4 md:grid-cols-2 not-prose">
          {sheets.map((item) => (
            <a
              key={item.provider}
              href={item.href}
              target="_blank"
              rel="noreferrer"
              className="border border-border bg-card p-5 hover:border-[var(--sardis-orange)] transition-colors"
            >
              <h2 className="text-xl font-semibold font-display mb-2">{item.provider}</h2>
              <p className="text-sm text-muted-foreground leading-relaxed">{item.summary}</p>
              <p className="text-xs font-mono mt-4 text-[var(--sardis-orange)]">Open response sheet →</p>
            </a>
          ))}
        </section>
      </article>
    </>
  );
}
