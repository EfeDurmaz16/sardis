import { AccountView } from "@daveyplate/better-auth-ui"
import { accountViewPaths } from "@daveyplate/better-auth-ui/server"
import Link from "next/link"
import { Button } from "@/components/ui/button"

export const dynamicParams = false

export function generateStaticParams() {
  return Object.values(accountViewPaths).map((path) => ({ path }))
}

export default async function AccountPage({ params }: { params: Promise<{ path: string }> }) {
  const { path } = await params

  return (
    <main className="mx-auto max-w-3xl py-8 px-4 md:px-8">
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/">← Back to Dashboard</Link>
        </Button>
      </div>
      <div className="[&_[data-slot=card]]:max-w-none">
        <AccountView path={path} />
      </div>
    </main>
  )
}
