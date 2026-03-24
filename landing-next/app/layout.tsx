import type { Metadata, Viewport } from "next";
import { Analytics } from "@vercel/analytics/next";
import Script from "next/script";
import Navbar from "@/components/landing/Navbar";
import Footer from "@/components/landing/Footer";
import {
  SITE_NAME,
  SITE_URL,
  DEFAULT_OG_IMAGE,
  TWITTER_HANDLE,
  DEFAULT_DESCRIPTION,
  createOrganizationSchema,
  createWebSiteSchema,
  createSoftwareAppSchema,
} from "@/lib/metadata";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: `${SITE_NAME} - The Payment OS for the Agent Economy`,
    template: `%s | ${SITE_NAME}`,
  },
  description: DEFAULT_DESCRIPTION,
  keywords: [
    "AI agent payments",
    "agent wallets",
    "MPC wallets",
    "spending policies",
    "AI financial infrastructure",
    "autonomous payments",
    "Base",
    "USDC",
    "MCP server",
    "agent commerce",
  ],
  authors: [{ name: "Sardis", url: SITE_URL }],
  creator: "Sardis",
  publisher: "Sardis",
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-video-preview": -1,
      "max-image-preview": "large",
      "max-snippet": -1,
    },
  },
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    locale: "en_US",
    url: SITE_URL,
    title: `${SITE_NAME} - The Payment OS for the Agent Economy`,
    description: DEFAULT_DESCRIPTION,
    images: [
      {
        url: DEFAULT_OG_IMAGE,
        width: 1200,
        height: 630,
        alt: "Sardis AI agent payments platform",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    site: TWITTER_HANDLE,
    creator: TWITTER_HANDLE,
    title: `${SITE_NAME} - The Payment OS for the Agent Economy`,
    description: DEFAULT_DESCRIPTION,
    images: [DEFAULT_OG_IMAGE],
  },
  alternates: {
    canonical: SITE_URL,
  },
  icons: {
    icon: "/favicon.svg",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FAFAFA" },
    { media: "(prefers-color-scheme: dark)", color: "#08090A" },
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const orgSchema = createOrganizationSchema();
  const webSchema = createWebSiteSchema();
  const appSchema = createSoftwareAppSchema();

  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <head>
        <Script
          id="org-schema"
          type="application/ld+json"
          strategy="beforeInteractive"
        >
          {JSON.stringify(orgSchema)}
        </Script>
        <Script
          id="web-schema"
          type="application/ld+json"
          strategy="beforeInteractive"
        >
          {JSON.stringify(webSchema)}
        </Script>
        <Script
          id="app-schema"
          type="application/ld+json"
          strategy="beforeInteractive"
        >
          {JSON.stringify(appSchema)}
        </Script>
      </head>
      <body>
        <Navbar />
        {/* Spacer for fixed navbar */}
        <div className="h-[72px]" />
        {children}
        <Footer />
        <Analytics />
      </body>
    </html>
  );
}
