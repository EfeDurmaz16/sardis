import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Pricing — Sardis",
  description: "Free sandbox, Starter at $199/mo, and custom Enterprise plans. Stablecoin checkout has 0% merchant fees.",
  alternates: { canonical: "/pricing" },
  openGraph: {
    title: "Pricing — Sardis",
    description: "Free sandbox, Starter at $199/mo, and custom Enterprise plans.",
    url: "https://sardis.sh/pricing",
    type: "website",
  },
}

export default function PricingLayout({ children }: { children: React.ReactNode }) {
  return children
}
