import { Metadata } from "next"

export const metadata: Metadata = { title: "Overview" }

export default function Layout({ children }: { children: React.ReactNode }) {
  return children
}
