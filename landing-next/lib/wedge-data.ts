export type WedgeFeature = {
  tag: string;
  title: string;
  body: string;
  stat: string;
};

export type WedgeData = {
  slug: string;
  title: string;
  metaTitle: string;
  description: string;
  subtitle: string;
  heroTitle: string;
  heroHighlight: string;
  heroDesc: string;
  features: WedgeFeature[];
};

export const wedges: WedgeData[] = [
  {
    slug: "secure-payments",
    title: "Secure AI Agent Payments",
    metaTitle: "Secure AI Agent Payments",
    description:
      "Spending mandates, 12-check policy engine, kill switches, and cryptographic audit trails. Sardis makes autonomous agent payments safe.",
    subtitle: "SECURE PAYMENTS",
    heroTitle: "Every dollar, every decision.",
    heroHighlight: "Cryptographic proof.",
    heroDesc:
      "Spending mandates, a 12-check enforcement pipeline, kill switches at 5 scopes, and signed attestation envelopes for every transaction. Sardis makes autonomous agent payments safe by design.",
    features: [
      {
        tag: "Spending Mandates",
        title: "Delegated financial authority",
        body: "Issue time-bound, amount-capped mandates to your agents. Every transaction requires a valid mandate chain before money moves.",
        stat: "0 unauthorized transactions",
      },
      {
        tag: "Policy Engine",
        title: "12-check enforcement pipeline",
        body: "Every payment passes through 12 independent checks: amount limits, merchant whitelist, time windows, velocity controls, sanctions screening, and more.",
        stat: "12 checks per transaction",
      },
      {
        tag: "Kill Switch",
        title: "Instant freeze across all agents",
        body: "One API call freezes every agent wallet in your organization. Sub-second propagation. No transactions slip through during investigation.",
        stat: "<100ms propagation",
      },
      {
        tag: "Audit Trail",
        title: "Cryptographic evidence for every dollar",
        body: "Append-only ledger with Merkle-anchored proofs. Every transaction, policy check, and approval is recorded with signed attestation envelopes.",
        stat: "Immutable proof",
      },
    ],
  },
  {
    slug: "api-payments",
    title: "AI Agent API Payments",
    metaTitle: "AI Agent API Payments",
    description:
      "Pay-per-request micropayments for AI APIs using x402, policy-controlled budgets, and automatic cost tracking for every agent.",
    subtitle: "API PAYMENTS",
    heroTitle: "Your agents call APIs.",
    heroHighlight: "Now they can pay for them.",
    heroDesc:
      "x402 micropayments, policy-controlled API budgets, and automatic cost tracking. Sardis enables pay-per-request for OpenAI, Anthropic, and any API your agents consume.",
    features: [
      {
        tag: "x402 Protocol",
        title: "HTTP-native micropayments",
        body: "Pay for API calls at the HTTP layer. No subscription management, no overage surprises. Your agent pays exactly what it uses.",
        stat: "Pay-per-request",
      },
      {
        tag: "Budget Controls",
        title: "Per-agent API spending limits",
        body: "Set daily, weekly, or monthly caps per agent per API. Automatically block calls when budgets are exhausted.",
        stat: "Zero overspend",
      },
      {
        tag: "Cost Tracking",
        title: "Real-time API cost attribution",
        body: "See exactly which agent spent how much on which API. Break down costs by model, endpoint, and time period.",
        stat: "100% attribution",
      },
      {
        tag: "Multi-Provider",
        title: "Works with every AI provider",
        body: "OpenAI, Anthropic, Google, Cohere, and any HTTP API. One payment layer across all your agent dependencies.",
        stat: "10+ providers",
      },
    ],
  },
  {
    slug: "global-payments",
    title: "Global AI Agent Payments",
    metaTitle: "Global AI Agent Payments",
    description:
      "Multi-chain USDC payments via CCTP v2 with fiat on/off-ramp. Your agents can pay vendors anywhere in the world, instantly.",
    subtitle: "GLOBAL PAYMENTS",
    heroTitle: "Your agents operate globally.",
    heroHighlight: "Their payments should too.",
    heroDesc:
      "Multi-chain USDC execution via CCTP v2, fiat on/off-ramp through Coinbase, and settlement across Ethereum, Polygon, Arbitrum, Optimism, and Tempo. One wallet, global reach.",
    features: [
      {
        tag: "Multi-Chain",
        title: "Execute on any EVM chain",
        body: "Primary execution on Tempo with funding from Ethereum, Polygon, Arbitrum, and Optimism via CCTP v2 unified addresses.",
        stat: "6+ chains",
      },
      {
        tag: "Fiat Bridge",
        title: "On-ramp and off-ramp",
        body: "Coinbase-hosted fiat on-ramp for ACH, wire, and card funding. Off-ramp to bank accounts for vendor settlement.",
        stat: "USD, EUR, GBP",
      },
      {
        tag: "Instant Settlement",
        title: "Sub-second finality on Tempo",
        body: "Sub-second block times on Tempo for near-instant payment confirmation. No waiting for slow L1 finality.",
        stat: "<2s settlement",
      },
      {
        tag: "Stablecoin Native",
        title: "USDC and EURC support",
        body: "Native stablecoin payments eliminate FX risk. USDC for USD, EURC for EUR. Circle-backed, fully reserved.",
        stat: "$0 FX fees",
      },
    ],
  },
];

export function getWedgeBySlug(slug: string): WedgeData | undefined {
  return wedges.find((w) => w.slug === slug);
}
