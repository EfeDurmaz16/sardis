import { Metadata } from "next"

export const metadata: Metadata = {
  title: "Sardis — Safe Payments for AI Agents",
  description: "The payment OS for the agent economy. Set rules, let agents transact, verify everything.",
}

export default function LandingLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
