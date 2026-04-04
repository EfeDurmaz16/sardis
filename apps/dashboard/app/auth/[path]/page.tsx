import { AuthView } from "@daveyplate/better-auth-ui"
import { authViewPaths } from "@daveyplate/better-auth-ui/server"

export const dynamicParams = false

export function generateStaticParams() {
  return Object.values(authViewPaths).map((path) => ({ path }))
}

export default async function AuthPage({ params }: { params: Promise<{ path: string }> }) {
  const { path } = await params

  return (
    <main className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="w-14 h-14 flex items-center justify-center mx-auto mb-5">
            <svg width="40" height="40" viewBox="0 0 28 28" fill="none">
              <path d="M20 5H10a7 7 0 000 14h2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
              <path d="M8 23h10a7 7 0 000-14h-2" stroke="currentColor" strokeWidth="3" strokeLinecap="round" fill="none" />
            </svg>
          </div>
        </div>
        <AuthView path={path} />
      </div>
    </main>
  )
}
