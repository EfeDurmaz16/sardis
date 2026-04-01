import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "sonner"

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

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: "Sardis",
  url: "https://sardis.sh",
  description: "Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.",
  foundingDate: "2025",
  sameAs: [
    "https://github.com/EfeDurmaz16/sardis",
    "https://docs.sardis.sh",
  ],
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
          <TooltipProvider>
            {children}
            <Toaster richColors position="bottom-right" />
          </TooltipProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
