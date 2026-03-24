import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center text-center px-4">
      <h1 className="mb-4 text-4xl font-bold tracking-tight">Sardis Docs</h1>
      <p className="mb-8 max-w-lg text-fd-muted-foreground">
        The Payment OS for the Agent Economy. Infrastructure enabling AI agents
        to make real financial transactions safely.
      </p>
      <div className="flex gap-4">
        <Link
          href="/docs"
          className="rounded-lg bg-fd-primary px-6 py-3 text-sm font-medium text-fd-primary-foreground transition-colors hover:bg-fd-primary/90"
        >
          Get Started
        </Link>
        <Link
          href="/docs/api"
          className="rounded-lg border border-fd-border px-6 py-3 text-sm font-medium text-fd-foreground transition-colors hover:bg-fd-muted"
        >
          API Reference
        </Link>
      </div>
    </main>
  );
}
