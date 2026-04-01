import { useEffect, useMemo, useState } from "react";

const CANONICAL_LANDING_URL = "https://sardis.sh";
const CANONICAL_DASHBOARD_URL = "https://app.sardis.sh";
const REDIRECT_DELAY_SECONDS = 6;

function resolveLegacyLandingTarget(location) {
  const { pathname, search, hash } = location;
  const normalizedPath = pathname.replace(/\/+$/, "") || "/";

  if (normalizedPath === "/dashboard" || normalizedPath === "/signup") {
    return `${CANONICAL_DASHBOARD_URL}${search}${hash}`;
  }

  return `${CANONICAL_LANDING_URL}${search}${hash}`;
}

function App() {
  const targetUrl = useMemo(() => resolveLegacyLandingTarget(window.location), []);
  const [secondsRemaining, setSecondsRemaining] = useState(REDIRECT_DELAY_SECONDS);

  useEffect(() => {
    document.title = "Sardis Legacy Landing Deprecated";

    const countdown = window.setInterval(() => {
      setSecondsRemaining((current) => {
        if (current <= 1) {
          window.clearInterval(countdown);
          return 0;
        }
        return current - 1;
      });
    }, 1000);

    const redirect = window.setTimeout(() => {
      window.location.replace(targetUrl);
    }, REDIRECT_DELAY_SECONDS * 1000);

    return () => {
      window.clearInterval(countdown);
      window.clearTimeout(redirect);
    };
  }, [targetUrl]);

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center px-6 py-16">
        <p className="mb-4 text-xs font-semibold uppercase tracking-[0.24em] text-muted-foreground">
          Legacy Surface Deprecated
        </p>
        <h1 className="text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
          This landing app has moved to the canonical Next.js surface.
        </h1>
        <p className="mt-6 max-w-2xl text-lg leading-8 text-muted-foreground">
          This Vite app is now a compatibility shell only. Users should use the canonical landing at
          {" "}
          <a className="underline decoration-border underline-offset-4" href={CANONICAL_LANDING_URL}>
            sardis.sh
          </a>
          {" "}
          and the canonical dashboard at
          {" "}
          <a className="underline decoration-border underline-offset-4" href={CANONICAL_DASHBOARD_URL}>
            app.sardis.sh
          </a>
          .
        </p>

        <div className="mt-8 rounded-2xl border border-border bg-card p-6 shadow-sm">
          <p className="text-sm font-medium text-foreground">Redirect target</p>
          <p className="mt-2 break-all text-sm text-muted-foreground">{targetUrl}</p>
          <p className="mt-4 text-sm text-muted-foreground">
            Automatic redirect in {secondsRemaining}s.
          </p>

          <div className="mt-6 flex flex-wrap gap-3">
            <a
              className="inline-flex items-center justify-center rounded-full bg-foreground px-5 py-3 text-sm font-medium text-background"
              href={targetUrl}
            >
              Continue to canonical surface
            </a>
            <a
              className="inline-flex items-center justify-center rounded-full border border-border px-5 py-3 text-sm font-medium text-foreground"
              href={CANONICAL_LANDING_URL}
            >
              Open landing home
            </a>
            <a
              className="inline-flex items-center justify-center rounded-full border border-border px-5 py-3 text-sm font-medium text-foreground"
              href={CANONICAL_DASHBOARD_URL}
            >
              Open dashboard home
            </a>
          </div>
        </div>

        <section className="mt-8 rounded-2xl border border-border bg-background/60 p-6">
          <h2 className="text-sm font-semibold uppercase tracking-[0.2em] text-muted-foreground">
            Developer Note
          </h2>
          <p className="mt-3 text-sm leading-7 text-muted-foreground">
            New product work should not land in this directory. Use
            {" "}
            <code>apps/landing</code>
            {" "}
            for the canonical marketing surface and
            {" "}
            <code>apps/dashboard</code>
            {" "}
            for the canonical application shell.
          </p>
        </section>
      </div>
    </main>
  );
}

export default App
