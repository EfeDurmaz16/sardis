"use client"

import { useState } from "react"
import { CheckCircle, Lightning, Warning, XCircle } from "@phosphor-icons/react"

import { Button } from "@/components/ui/button"
import {
  createMandate,
  validateMandate,
  type MandateValidationResult,
} from "@/lib/sardis-api"
import type { StepContext } from "../onboarding-wizard"

// Base Sepolia test recipient. Well-known burn-style address used in docs and
// smoke tests — ok to hardcode because this mandate never executes on-chain.
const TEST_RECIPIENT = "0x000000000000000000000000000000000000dEaD"
const TEST_AMOUNT_USDC = "10.00"
const TEST_AMOUNT_MINOR = 10_000_000 // 10 USDC in 6-decimal minor units
const TEST_DOMAIN = "sandbox.sardis.sh"

type Stage = "idle" | "creating" | "validating" | "done" | "error"

export function SandboxPaymentStep({ ctx }: { ctx: StepContext }) {
  const meta = ctx.state.metadata as { agent_id?: string }
  const agentId = meta.agent_id

  const [stage, setStage] = useState<Stage>("idle")
  const [result, setResult] = useState<MandateValidationResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [mandateId, setMandateId] = useState<string | null>(null)

  const runTest = async () => {
    if (!agentId) {
      setError("No agent on this onboarding state. Go back one step.")
      setStage("error")
      return
    }

    setError(null)
    setResult(null)
    setMandateId(null)
    setStage("creating")
    try {
      const mandate = await createMandate({
        subject: agentId,
        domain: TEST_DOMAIN,
        amount_minor: TEST_AMOUNT_MINOR,
        currency: "USDC",
        recipient: TEST_RECIPIENT,
        chain: "base_sepolia",
        memo: "Sardis onboarding test payment",
      })
      setMandateId(mandate.mandate_id)
      setStage("validating")

      const validation = await validateMandate(mandate.mandate_id)
      setResult(validation)
      setStage("done")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run test payment")
      setStage("error")
    }
  }

  const valid = result?.valid === true

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Run your first payment through Sardis end-to-end. We create a ${TEST_AMOUNT_USDC}{" "}
        USDC mandate and push it through the same policy and compliance pipeline every
        live payment uses.
      </p>

      <div className="rounded border border-border bg-background/40 p-3">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Test payment
        </div>
        <dl className="mt-2 grid grid-cols-2 gap-2 text-xs">
          <Row label="Amount" value={`$${TEST_AMOUNT_USDC} USDC`} />
          <Row label="Chain" value="base_sepolia" />
          <Row label="Recipient" value={TEST_RECIPIENT} mono />
          <Row label="Agent" value={agentId ?? "—"} mono />
        </dl>
      </div>

      {stage === "creating" && (
        <div className="flex items-start gap-2 rounded border border-border bg-background/40 px-3 py-2 text-sm text-muted-foreground">
          <Lightning className="mt-0.5 size-4 shrink-0" weight="regular" />
          <span>Creating mandate…</span>
        </div>
      )}

      {stage === "validating" && (
        <div className="flex items-start gap-2 rounded border border-border bg-background/40 px-3 py-2 text-sm text-muted-foreground">
          <Lightning className="mt-0.5 size-4 shrink-0" weight="regular" />
          <span>Running policy + compliance checks…</span>
        </div>
      )}

      {stage === "done" && valid && (
        <div className="space-y-2">
          <div className="flex items-start gap-2 rounded border border-emerald-500/40 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
            <CheckCircle className="mt-0.5 size-4 shrink-0" weight="fill" />
            <div className="space-y-0.5">
              <div>
                Payment passed policy and compliance. Your stack is ready for live
                transactions.
              </div>
              {mandateId && (
                <div className="font-mono text-xs opacity-80">mandate: {mandateId}</div>
              )}
            </div>
          </div>
          <CheckGrid result={result} />
        </div>
      )}

      {stage === "done" && !valid && result && (
        <div className="space-y-2">
          <div className="flex items-start gap-2 rounded border border-amber-500/40 bg-amber-500/5 px-3 py-2 text-sm text-amber-600 dark:text-amber-400">
            <Warning className="mt-0.5 size-4 shrink-0" weight="regular" />
            <div className="space-y-0.5">
              <div>
                Payment was rejected by{" "}
                {result.policy_check && !result.policy_check.allowed
                  ? "policy"
                  : "compliance"}
                . That is the whole point of Sardis — every payment gets checked before
                it moves.
              </div>
              {result.reason && <div className="text-xs opacity-80">{result.reason}</div>}
            </div>
          </div>
          <CheckGrid result={result} />
        </div>
      )}

      {stage === "error" && error && (
        <div className="flex items-start gap-2 rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          <XCircle className="mt-0.5 size-4 shrink-0" weight="regular" />
          <span>{error}</span>
        </div>
      )}

      <div className="flex justify-end gap-2">
        {stage !== "done" && (
          <Button
            type="button"
            size="sm"
            onClick={runTest}
            disabled={
              stage === "creating" || stage === "validating" || ctx.pending || !agentId
            }
          >
            {stage === "creating" || stage === "validating"
              ? "Running…"
              : stage === "error"
                ? "Try again"
                : "Run test payment"}
          </Button>
        )}
        {stage === "done" && (
          <Button type="button" size="sm" onClick={ctx.goNext} disabled={ctx.pending}>
            Continue
          </Button>
        )}
      </div>
    </div>
  )
}

function Row({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className={mono ? "truncate font-mono text-foreground" : "text-foreground"}>
        {value}
      </dd>
    </div>
  )
}

function CheckGrid({ result }: { result: MandateValidationResult | null }) {
  if (!result) return null
  const rows: Array<{ label: string; allowed: boolean | null; reason: string | null }> = [
    {
      label: "Policy",
      allowed: result.policy_check?.allowed ?? null,
      reason: result.policy_check?.reason ?? null,
    },
    {
      label: "Compliance",
      allowed: result.compliance_check?.allowed ?? null,
      reason: result.compliance_check?.reason ?? null,
    },
  ]
  return (
    <div className="grid grid-cols-2 gap-2">
      {rows.map((r) => (
        <div
          key={r.label}
          className="rounded border border-border bg-background/60 px-3 py-2 text-xs"
        >
          <div className="flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
              {r.label}
            </span>
            {r.allowed === true ? (
              <CheckCircle className="size-3.5 text-emerald-600" weight="fill" />
            ) : r.allowed === false ? (
              <XCircle className="size-3.5 text-amber-600" weight="fill" />
            ) : null}
          </div>
          <div className="mt-1 font-mono text-foreground">
            {r.allowed === true ? "allowed" : r.allowed === false ? "rejected" : "—"}
          </div>
          {r.reason && <div className="mt-0.5 text-[10px] text-muted-foreground">{r.reason}</div>}
        </div>
      ))}
    </div>
  )
}
