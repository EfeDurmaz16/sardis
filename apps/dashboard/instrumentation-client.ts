import * as Sentry from "@sentry/nextjs"

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN

if (dsn) {
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_VERCEL_ENV || process.env.NODE_ENV || "development",
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? "0.1"),
    replaysSessionSampleRate: 0,
    replaysOnErrorSampleRate: Number(process.env.NEXT_PUBLIC_SENTRY_REPLAY_ON_ERROR ?? "0.1"),
    integrations: [
      Sentry.replayIntegration({
        maskAllText: true,
        blockAllMedia: true,
      }),
    ],
    debug: false,
    ignoreErrors: [
      // Browser extension noise
      "ResizeObserver loop completed with undelivered notifications",
      "Non-Error promise rejection captured",
      // Routine 401 during session polling
      "Unauthorized",
    ],
  })
}

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart
