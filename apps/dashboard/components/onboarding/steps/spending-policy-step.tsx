"use client"

import { CheckCircle, ShieldCheck } from "@phosphor-icons/react"

import { Button } from "@/components/ui/button"
import {
  SPENDING_POLICY_TEMPLATES,
  type SpendingPolicyTemplateId,
} from "@/lib/sardis-api"
import type { StepContext } from "../onboarding-wizard"

export function SpendingPolicyStep({ ctx }: { ctx: StepContext }) {
  const meta = ctx.state.metadata as {
    agent_id?: string
    spending_policy_template?: SpendingPolicyTemplateId
  }

  const template = SPENDING_POLICY_TEMPLATES.find(
    (t) => t.id === meta.spending_policy_template,
  )

  if (!template || !meta.agent_id) {
    return (
      <div className="space-y-4">
        <div className="flex items-start gap-2 rounded border border-border bg-background/40 px-3 py-2 text-sm text-muted-foreground">
          <ShieldCheck className="mt-0.5 size-4 shrink-0" weight="regular" />
          <span>
            No spending policy is attached yet. Go back to the previous step to create
            your agent first.
          </span>
        </div>
        <div className="flex justify-end">
          <Button
            type="button"
            size="sm"
            variant="ghost"
            onClick={ctx.goSkip}
            disabled={ctx.pending}
          >
            Skip for now
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Your agent is guarded by the{" "}
        <span className="font-medium text-foreground">{template.label}</span> policy.
        Transactions above these caps are rejected by Sardis before they touch chain.
      </p>

      <div className="flex items-start gap-2 rounded border border-emerald-500/40 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
        <CheckCircle className="mt-0.5 size-4 shrink-0" weight="fill" />
        <span>Policy attached to agent {meta.agent_id}.</span>
      </div>

      <dl className="grid grid-cols-2 gap-2 text-xs">
        <Limit label="Per transaction" value={template.spending_limits.per_transaction} />
        <Limit label="Daily" value={template.spending_limits.daily} />
        <Limit label="Monthly" value={template.spending_limits.monthly} />
        <Limit label="Lifetime" value={template.spending_limits.total} />
      </dl>

      <div className="rounded border border-dashed border-border bg-background/40 px-3 py-2 text-xs text-muted-foreground">
        You can revise these caps, add merchant allow/blocklists, and layer mandates
        from the agent detail page after onboarding.
      </div>

      <div className="flex justify-end">
        <Button type="button" size="sm" onClick={ctx.goNext} disabled={ctx.pending}>
          Continue
        </Button>
      </div>
    </div>
  )
}

function Limit({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border bg-background/60 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="font-mono text-sm text-foreground">${value}</div>
    </div>
  )
}
