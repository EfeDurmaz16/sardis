import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "sonner"
import { CookieConsent } from "@/components/cookie-consent"
import { PostHogProvider } from "@/components/posthog-provider"

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] })
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] })

export const metadata: Metadata = {
  title: {
    default: "Sardis — Safe payments for AI agents",
    template: "%s | Sardis",
  },
  description: "Give your agents real spending power with built-in guardrails. Set policies in plain English, every transaction is verified before it hits the chain.",
  keywords: ["sardis", "agent payments", "AI agents", "stablecoin", "payment infrastructure", "MPC wallets", "spending policy"],
  authors: [{ name: "Sardis" }],
  metadataBase: new URL("https://sardis.sh"),
  alternates: { canonical: "/" },
  openGraph: {
    title: "Sardis — Safe payments for AI agents",
    description: "Give your agents real spending power with built-in guardrails. Set policies in plain English, every transaction is verified before it hits the chain.",
    url: "https://sardis.sh",
    siteName: "Sardis",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "Sardis — Safe payments for AI agents",
    description: "Give your agents real spending power with built-in guardrails.",
    creator: "@sardaborgan",
  },
  robots: {
    index: true,
    follow: true,
  },
}

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Sardis",
  url: "https://sardis.sh",
  description: "Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.",
  foundingDate: "2025",
  founder: {
    "@type": "Person",
    name: "Efe Baran Durmaz",
  },
  sameAs: [
    "https://github.com/EfeDurmaz16/sardis",
    "https://docs.sardis.sh",
    "https://x.com/sardisHQ",
    "https://pypi.org/project/sardis/",
    "https://www.npmjs.com/package/@sardis/sdk",
  ],
  knowsAbout: [
    "AI agent payments",
    "MPC wallets",
    "stablecoin payments",
    "spending policies",
    "agent economy",
  ],
}

const softwareApplicationJsonLd = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Sardis",
  url: "https://sardis.sh",
  applicationCategory: "FinanceApplication",
  operatingSystem: "Web, Any",
  description: "The Payment OS for the Agent Economy. Non-custodial MPC wallets with natural language spending policies for AI agents.",
  offers: [
    {
      "@type": "Offer",
      name: "Free",
      price: "0",
      priceCurrency: "USD",
      description: "Sandbox, 2 agents, testnet only",
    },
    {
      "@type": "Offer",
      name: "Starter",
      price: "199",
      priceCurrency: "USD",
      description: "Production, mainnet, 25 agents, unlimited tx",
    },
    {
      "@type": "Offer",
      name: "Enterprise",
      priceCurrency: "USD",
      description: "Unlimited agents, KYB + PEP, custom SLAs",
    },
  ],
  featureList: [
    "Non-custodial MPC wallets for AI agents",
    "Natural language spending policies",
    "Multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)",
    "Virtual Visa/Mastercard card issuance",
    "Fiat on/off-ramp via Coinbase Onramp",
    "52-tool MCP server for Claude Desktop, Cursor, Windsurf",
    "Python and TypeScript SDKs",
    "AP2 protocol support (Google, PayPal, Mastercard, Visa)",
    "Append-only audit trail with Merkle anchoring",
    "KYC/AML compliance (Persona, Elliptic)",
  ],
  author: {
    "@type": "Organization",
    name: "Sardis Labs, Inc.",
    url: "https://sardis.sh",
  },
}

const faqJsonLd = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "What is Sardis?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Sardis is the Payment OS for the Agent Economy. It provides non-custodial MPC wallets with natural language spending policies, enabling AI agents to make real financial transactions safely with cryptographic audit trails.",
      },
    },
    {
      "@type": "Question",
      name: "How does Sardis prevent financial hallucinations?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Sardis uses a Policy Firewall that evaluates every transaction against natural language spending policies before execution. Policies like 'max $100 per transaction, only approved merchants' are enforced on-chain, preventing agents from making unauthorized or hallucinated payments.",
      },
    },
    {
      "@type": "Question",
      name: "What chains does Sardis support?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Sardis supports Base, Polygon, Ethereum, Arbitrum, and Optimism. It handles USDC, USDT, EURC, and PYUSD stablecoin payments across all supported chains.",
      },
    },
    {
      "@type": "Question",
      name: "How does Sardis compare to Stripe for AI agents?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "While Stripe is designed for human-initiated payments, Sardis is purpose-built for autonomous AI agents. Sardis provides MPC wallets, natural language spending policies, and real-time policy enforcement that Stripe does not offer for agent-to-agent commerce.",
      },
    },
    {
      "@type": "Question",
      name: "Is Sardis non-custodial?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Sardis uses MPC (Multi-Party Computation) wallets via Turnkey. Private keys are never stored or accessible by Sardis. Agents sign transactions through distributed key shares.",
      },
    },
    {
      "@type": "Question",
      name: "What AI frameworks does Sardis integrate with?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Sardis integrates with CrewAI, LangChain, OpenAI Agents SDK, Vercel AI SDK, AutoGPT, Browser Use, Activepieces, and more. It also provides a 52-tool MCP server for Claude Desktop and Cursor.",
      },
    },
    {
      "@type": "Question",
      name: "What is the AP2 protocol?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "AP2 (Agent Payment Protocol) is a consortium standard from Google, PayPal, Mastercard, and Visa for agent-initiated payments. It defines a mandate chain: Intent, Cart, Payment. Sardis verifies the full mandate chain before executing any transaction.",
      },
    },
    {
      "@type": "Question",
      name: "How do spending policies work?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Spending policies are defined in plain English, such as 'max $500/day, only SaaS subscriptions, require approval above $200'. Sardis compiles these into on-chain rules that are evaluated in real-time before every transaction.",
      },
    },
    {
      "@type": "Question",
      name: "Does Sardis support virtual cards?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Yes. Sardis issues virtual Visa/Mastercard cards through Stripe Issuing, allowing AI agents to make payments on traditional merchant platforms that do not accept crypto.",
      },
    },
    {
      "@type": "Question",
      name: "What is the pricing for Sardis?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Sardis offers a free sandbox tier (2 agents, testnet), Starter at $199/mo (production, mainnet, 25 agents, unlimited transactions), and custom Enterprise plans (KYB, PEP screening, custom SLAs). Stablecoin checkout has 0% merchant fees.",
      },
    },
  ],
}

const productJsonLd = {
  "@context": "https://schema.org",
  "@type": "Product",
  name: "Sardis",
  description: "Payment OS for the Agent Economy — non-custodial MPC wallets with natural language spending policies for AI agents.",
  brand: {
    "@type": "Brand",
    name: "Sardis",
  },
  category: "Payment Infrastructure",
  offers: {
    "@type": "AggregateOffer",
    lowPrice: "0",
    highPrice: "199",
    priceCurrency: "USD",
    offerCount: 3,
  },
}

const howToJsonLd = {
  "@context": "https://schema.org",
  "@type": "HowTo",
  name: "How to set up AI agent payments with Sardis",
  description: "Get your AI agent making real payments in 4 steps.",
  step: [
    {
      "@type": "HowToStep",
      position: 1,
      name: "Install the SDK",
      text: "Install the Sardis SDK with pip install sardis (Python) or npm install @sardis/sdk (TypeScript).",
    },
    {
      "@type": "HowToStep",
      position: 2,
      name: "Create an agent wallet",
      text: "Create a non-custodial MPC wallet for your agent using client.agents.create(name='My Agent', chain='base').",
    },
    {
      "@type": "HowToStep",
      position: 3,
      name: "Define spending policies",
      text: "Set natural language policies like 'max $100 per transaction, only approved merchants, daily limit $500'.",
    },
    {
      "@type": "HowToStep",
      position: 4,
      name: "Execute payments",
      text: "Your agent can now make payments within policy guardrails. Every transaction is verified, executed, and recorded in the audit trail.",
    },
  ],
}

const speakableJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebPage",
  name: "Sardis — Safe payments for AI agents",
  speakable: {
    "@type": "SpeakableSpecification",
    cssSelector: ["h1", "[data-speakable='hero']", "[data-speakable='faq']"],
  },
  url: "https://sardis.sh",
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(softwareApplicationJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(productJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(howToJsonLd) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(speakableJsonLd) }}
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
          <TooltipProvider>
            {children}
            <PostHogProvider />
            <CookieConsent />
            <Toaster richColors position="bottom-right" />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
