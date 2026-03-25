export const SITE_NAME = "Sardis";
export const SITE_URL = "https://www.sardis.sh";
export const DEFAULT_OG_IMAGE = "https://www.sardis.sh/og-image.png";
export const TWITTER_HANDLE = "@sardisHQ";
export const DEFAULT_DESCRIPTION =
  "AI agents can reason, but they cannot be trusted with money. Sardis is how they earn that trust. Non-custodial wallets, spending policies, on-chain payments on Tempo with multi-chain funding.";

// JSON-LD Schema generators

export function createOrganizationSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "Organization",
    name: "Sardis",
    url: SITE_URL,
    logo: `${SITE_URL}/favicon.svg`,
    description:
      "The Payment OS for the Agent Economy. Non-custodial MPC wallets with natural language spending policies for AI agents.",
    foundingDate: "2024",
    sameAs: [
      "https://x.com/sardisHQ",
      "https://github.com/EfeDurmaz16/sardis",
      "https://discord.gg/pUJTskfK",
    ],
    contactPoint: {
      "@type": "ContactPoint",
      email: "contact@sardis.sh",
      contactType: "customer support",
    },
  };
}

export function createWebSiteSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "WebSite",
    name: "Sardis",
    url: SITE_URL,
    description: "The Payment OS for the Agent Economy",
    potentialAction: {
      "@type": "SearchAction",
      target: `${SITE_URL}/docs?q={search_term_string}`,
      "query-input": "required name=search_term_string",
    },
  };
}

export function createSoftwareAppSchema() {
  return {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: "Sardis",
    applicationCategory: "FinanceApplication",
    operatingSystem: "Web",
    url: SITE_URL,
    description:
      "The Payment OS for the Agent Economy. Give your AI agents non-custodial MPC wallets with natural language spending policies. Prevent financial hallucinations with programmable trust.",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
    author: createOrganizationSchema(),
    featureList: [
      "Non-custodial MPC wallets for AI agents",
      "Natural language spending policies",
      "Execution on Tempo, multi-chain funding via CCTP v2 (Ethereum, Polygon, Arbitrum, Optimism)",
      "Virtual Visa/Mastercard card issuance",
      "Fiat on/off-ramp (ACH, wire, card)",
      "AP2, TAP, UCP, A2A, x402 protocol support",
      "MCP server with 52 tools for Claude",
      "Python and TypeScript SDKs",
      "Append-only audit trail with Merkle tree anchoring",
      "ERC-4337 gasless smart wallets",
    ],
  };
}

export function createBreadcrumbSchema(
  items: { name: string; href?: string }[]
) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: items.map((item, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: item.name,
      item: item.href ? `${SITE_URL}${item.href}` : undefined,
    })),
  };
}

export function createFAQSchema(faqItems: { q: string; a: string }[]) {
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqItems.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };
}
