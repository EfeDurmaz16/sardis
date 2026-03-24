export default function SocialProof() {
  const partners = [
    {
      name: 'Coinbase',
      svg: (
        <svg viewBox="0 0 200 40" fill="none" className="h-5 md:h-6 w-auto" aria-hidden="true">
          <circle cx="20" cy="20" r="18" stroke="currentColor" strokeWidth="2.5" fill="none" />
          <path d="M14 20a6 6 0 1 1 12 0 6 6 0 0 1-12 0z" stroke="currentColor" strokeWidth="2" fill="none" />
          <text x="46" y="26" fill="currentColor" fontSize="18" fontWeight="600" fontFamily="'Inter', sans-serif">Coinbase</text>
        </svg>
      ),
    },
    {
      name: 'Base',
      svg: (
        <svg viewBox="0 0 120 40" fill="none" className="h-5 md:h-6 w-auto" aria-hidden="true">
          <circle cx="20" cy="20" r="16" fill="currentColor" opacity="0.12" />
          <circle cx="20" cy="20" r="16" stroke="currentColor" strokeWidth="2" fill="none" />
          <text x="12" y="25" fill="currentColor" fontSize="14" fontWeight="700" fontFamily="'Space Grotesk', sans-serif">B</text>
          <text x="44" y="26" fill="currentColor" fontSize="18" fontWeight="600" fontFamily="'Inter', sans-serif">Base</text>
        </svg>
      ),
    },
    {
      name: 'Circle',
      svg: (
        <svg viewBox="0 0 130 40" fill="none" className="h-5 md:h-6 w-auto" aria-hidden="true">
          <circle cx="20" cy="20" r="14" stroke="currentColor" strokeWidth="2.5" fill="none" />
          <circle cx="20" cy="20" r="7" stroke="currentColor" strokeWidth="2" fill="none" />
          <text x="42" y="26" fill="currentColor" fontSize="18" fontWeight="600" fontFamily="'Inter', sans-serif">Circle</text>
        </svg>
      ),
    },
    {
      name: 'Stripe',
      svg: (
        <svg viewBox="0 0 130 40" fill="none" className="h-5 md:h-6 w-auto" aria-hidden="true">
          <path d="M10 14c0-2 2-4 6-4 3 0 6 1.5 6 5 0 6-12 4-12 10 0 3 3 5 7 5 3 0 5-1 6-2" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" fill="none" />
          <text x="36" y="26" fill="currentColor" fontSize="18" fontWeight="600" fontFamily="'Inter', sans-serif">Stripe</text>
        </svg>
      ),
    },
    {
      name: 'Anthropic MCP',
      svg: (
        <svg viewBox="0 0 190 40" fill="none" className="h-5 md:h-6 w-auto" aria-hidden="true">
          <path d="M10 28L20 12l10 16M14 22h12" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
          <text x="44" y="26" fill="currentColor" fontSize="16" fontWeight="600" fontFamily="'Inter', sans-serif">Anthropic MCP</text>
        </svg>
      ),
    },
  ];

  return (
    <div className="w-full" style={{ borderTop: '1px solid var(--landing-border)', borderBottom: '1px solid var(--landing-border)' }}>
      <div className="max-w-[1440px] mx-auto px-5 md:px-12 xl:px-20 py-8">
        <div className="flex flex-wrap items-center justify-center gap-4 md:gap-12">
          <div
            className="text-[12px] md:text-[13px] leading-4 font-light whitespace-nowrap"
            style={{ fontFamily: "'Inter', system-ui, sans-serif", color: 'var(--landing-text-muted)' }}
          >
            Trusted by teams building on
          </div>
          <div className="flex flex-wrap items-center gap-6 md:gap-10">
            {partners.map((partner) => (
              <div
                key={partner.name}
                className="transition-opacity duration-200 opacity-40 hover:opacity-80"
                style={{ color: 'var(--landing-text-secondary)' }}
                role="img"
                aria-label={partner.name}
              >
                {partner.svg}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
