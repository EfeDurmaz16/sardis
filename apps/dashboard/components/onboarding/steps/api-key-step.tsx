"use client"

import { useCallback, useEffect, useState } from "react"
import { Copy, Warning } from "@phosphor-icons/react"

import { Button } from "@/components/ui/button"
import { ApiError, bootstrapApiKey, type BootstrapApiKeyResponse } from "@/lib/sardis-api"
import type { StepContext } from "../onboarding-wizard"

export function ApiKeyStep({ ctx }: { ctx: StepContext }) {
  const [bootstrapping, setBootstrapping] = useState(false)
  const [bootstrapped, setBootstrapped] = useState<BootstrapApiKeyResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [conflictAlready, setConflictAlready] = useState(false)
  const [confirmed, setConfirmed] = useState(false)
  const [copied, setCopied] = useState(false)

  const generate = useCallback(async () => {
    setBootstrapping(true)
    setError(null)
    try {
      const result = await bootstrapApiKey("Default API key")
      setBootstrapped(result)
    } catch (err) {
      if (err instanceof ApiError && err.statusCode === 409) {
        // Org already has at least one key (e.g. user re-ran the wizard).
        // Treat as a success path: no key to show, advance is allowed.
        setConflictAlready(true)
      } else {
        setError(err instanceof Error ? err.message : "Failed to generate API key")
      }
    } finally {
      setBootstrapping(false)
    }
  }, [])

  // Auto-trigger generation on first render of the step. The bootstrap
  // endpoint is idempotent-ish (409 on re-run) so this is safe.
  useEffect(() => {
    void generate()
    // We intentionally only run this once when the step mounts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const copyKey = useCallback(async () => {
    if (!bootstrapped) return
    try {
      await navigator.clipboard.writeText(bootstrapped.key)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      // Clipboard API can fail in insecure contexts; fall back to no-op.
    }
  }, [bootstrapped])

  const canAdvance = conflictAlready || (bootstrapped !== null && confirmed)

  return (
    <div className="space-y-4">
      {bootstrapping && !bootstrapped && (
        <div className="rounded border border-border bg-background/40 p-4 text-sm text-muted-foreground">
          Generating your sandbox API key…
        </div>
      )}

      {error && (
        <div className="rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {conflictAlready && !bootstrapped && (
        <div className="rounded border border-border bg-background/40 px-3 py-2 text-sm text-muted-foreground">
          You already have an API key. You can manage it from{" "}
          <span className="font-mono text-foreground">Settings → API keys</span>{" "}
          after onboarding.
        </div>
      )}

      {bootstrapped && (
        <>
          <div className="flex items-start gap-2 rounded border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm text-amber-600 dark:text-amber-400">
            <Warning className="mt-0.5 size-4 shrink-0" weight="regular" />
            <span>
              This is the only time you will see this key. Copy it now and store it
              somewhere safe.
            </span>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Your sandbox API key
            </label>
            <div className="flex items-center gap-2">
              <code className="flex-1 truncate rounded border border-border bg-background px-3 py-2 font-mono text-sm">
                {bootstrapped.key}
              </code>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={copyKey}
                aria-label="Copy API key"
              >
                <Copy className="size-4" weight="regular" />
                <span className="ml-1.5">{copied ? "Copied" : "Copy"}</span>
              </Button>
            </div>
            <div className="text-xs text-muted-foreground">
              Mode: <span className="font-mono text-foreground">{bootstrapped.mode}</span>
              {" · "}
              Name: <span className="font-mono text-foreground">{bootstrapped.name}</span>
            </div>
          </div>

          <label className="flex items-start gap-2 text-sm text-muted-foreground">
            <input
              type="checkbox"
              className="mt-0.5"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />
            <span>I have saved this key somewhere safe.</span>
          </label>
        </>
      )}

      <div className="flex justify-end">
        <Button
          type="button"
          size="sm"
          onClick={ctx.goNext}
          disabled={!canAdvance || ctx.pending}
        >
          Continue
        </Button>
      </div>
    </div>
  )
}
