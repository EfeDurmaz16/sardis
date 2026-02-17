import { Helmet } from 'react-helmet-async';

const SITE_NAME = 'Sardis';
const SITE_URL = 'https://sardis.sh';
const DEFAULT_OG_IMAGE = 'https://sardis.sh/og-image.png';
const TWITTER_HANDLE = '@sardisHQ';

/**
 * SEO component for per-page meta tags and structured data.
 * Supports: title, description, canonical, OG, Twitter, and JSON-LD schemas.
 */
export default function SEO({
  title,
  description,
  path = '/',
  type = 'website',
  article = null,
  schemas = [],
  noindex = false,
}) {
  const fullTitle = title ? `${title} | ${SITE_NAME}` : `${SITE_NAME} - The Payment OS for the Agent Economy`;
  const canonicalUrl = `${SITE_URL}${path}`;

  return (
    <Helmet>
      <title>{fullTitle}</title>
      <meta name="description" content={description} />
      <link rel="canonical" href={canonicalUrl} />
      {noindex && <meta name="robots" content="noindex, nofollow" />}

      {/* Open Graph */}
      <meta property="og:type" content={type} />
      <meta property="og:url" content={canonicalUrl} />
      <meta property="og:title" content={fullTitle} />
      <meta property="og:description" content={description} />
      <meta property="og:site_name" content={SITE_NAME} />
      <meta property="og:image" content={DEFAULT_OG_IMAGE} />

      {/* Article-specific OG */}
      {article && <meta property="article:published_time" content={article.publishedDate} />}
      {article && <meta property="article:author" content="Sardis" />}

      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:site" content={TWITTER_HANDLE} />
      <meta name="twitter:title" content={fullTitle} />
      <meta name="twitter:description" content={description} />
      <meta name="twitter:image" content={DEFAULT_OG_IMAGE} />

      {/* JSON-LD Structured Data */}
      {schemas.map((schema, i) => (
        <script key={i} type="application/ld+json">
          {JSON.stringify(schema)}
        </script>
      ))}
    </Helmet>
  );
}

// ─── Schema Generators ────────────────────────────────────────

export function createOrganizationSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'Sardis',
    url: SITE_URL,
    logo: `${SITE_URL}/favicon.svg`,
    description: 'The Payment OS for the Agent Economy. Non-custodial MPC wallets with natural language spending policies for AI agents.',
    foundingDate: '2024',
    sameAs: [
      'https://x.com/sardisHQ',
      'https://github.com/EfeDurmaz16/sardis',
      'https://discord.gg/XMA9JwDJ',
    ],
    contactPoint: {
      '@type': 'ContactPoint',
      email: 'contact@sardis.sh',
      contactType: 'customer support',
    },
  };
}

export function createWebSiteSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Sardis',
    url: SITE_URL,
    description: 'The Payment OS for the Agent Economy',
    potentialAction: {
      '@type': 'SearchAction',
      target: `${SITE_URL}/docs?q={search_term_string}`,
      'query-input': 'required name=search_term_string',
    },
  };
}

export function createSoftwareAppSchema() {
  return {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Sardis',
    applicationCategory: 'FinanceApplication',
    operatingSystem: 'Web',
    url: SITE_URL,
    description: 'The Payment OS for the Agent Economy. Give your AI agents non-custodial MPC wallets with natural language spending policies. Prevent financial hallucinations with programmable trust.',
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
    author: createOrganizationSchema(),
    featureList: [
      'Non-custodial MPC wallets for AI agents',
      'Natural language spending policies',
      'Multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)',
      'Virtual Visa/Mastercard card issuance',
      'Fiat on/off-ramp (ACH, wire, card)',
      'AP2, TAP, UCP, A2A, x402 protocol support',
      'MCP server with 50+ tools for Claude',
      'Python and TypeScript SDKs',
      'Append-only audit trail with Merkle tree anchoring',
      'ERC-4337 gasless smart wallets',
    ],
  };
}

export function createFAQSchema(faqItems) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: faqItems.map((item) => ({
      '@type': 'Question',
      name: item.q,
      acceptedAnswer: {
        '@type': 'Answer',
        text: item.a,
      },
    })),
  };
}

export function createArticleSchema({ title, description, path, publishedDate, modifiedDate }) {
  return {
    '@context': 'https://schema.org',
    '@type': 'TechArticle',
    headline: title,
    description: description,
    url: `${SITE_URL}${path}`,
    datePublished: publishedDate,
    dateModified: modifiedDate || publishedDate,
    author: createOrganizationSchema(),
    publisher: createOrganizationSchema(),
    mainEntityOfPage: {
      '@type': 'WebPage',
      '@id': `${SITE_URL}${path}`,
    },
  };
}

export function createHowToSchema({ name, description, steps }) {
  return {
    '@context': 'https://schema.org',
    '@type': 'HowTo',
    name,
    description,
    step: steps.map((step, i) => ({
      '@type': 'HowToStep',
      position: i + 1,
      name: step.name,
      text: step.text,
    })),
  };
}

export function createBreadcrumbSchema(items) {
  return {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: items.map((item, i) => ({
      '@type': 'ListItem',
      position: i + 1,
      name: item.name,
      item: item.href ? `${SITE_URL}${item.href}` : undefined,
    })),
  };
}
