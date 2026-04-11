import type { Metadata } from "next"
import { Geist, Geist_Mono } from "next/font/google"
import "./globals.css"
import { ThemeProvider } from "@/components/theme-provider"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "sonner"
import { Providers } from "./providers"
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
  keywords: ["sardis", "agent payments", "AI agents", "stablecoin", "payment infrastructure"],
  authors: [{ name: "Sardis" }],
  openGraph: {
    title: "Sardis — Safe payments for AI agents",
    description: "Give your agents real spending power with built-in guardrails.",
    type: "website",
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${geistSans.variable} ${geistMono.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="light" enableSystem disableTransitionOnChange>
          <Providers>
            <TooltipProvider>
              {children}
              <PostHogProvider />
              <CookieConsent />
              <Toaster richColors position="bottom-right" />
            </TooltipProvider>
          </Providers>
        </ThemeProvider>
      </body>
    </html>
  )
}
