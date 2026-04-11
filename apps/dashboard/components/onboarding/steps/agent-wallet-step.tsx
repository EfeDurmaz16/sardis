"use client"

import { useState } from "react"
import { CheckCircle, Wallet } from "@phosphor-icons/react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import {
  createAgent,
  SPENDING_POLICY_TEMPLATES,
  type AgentApiRecord,
  type SpendingPolicyTemplateId,
} from "@/lib/sardis-api"
import type { StepContext } from "../onboarding-wizard"

export function AgentWalletStep({ ctx }: { ctx: StepContext }) {
  const existingMeta = ctx.state.metadata as {
    agent_id?: string
    wallet_id?: string
    spending_policy_template?: SpendingPolicyTemplateId
  }

  const alreadyProvisioned = Boolean(existingMeta.agent_id && existingMeta.wallet_id)

  const [agentName, setAgentName] = useState("My first agent")
  const [templateId, setTemplateId] = useState<SpendingPolicyTemplateId>(
    existingMeta.spending_policy_template ?? "balanced",
  )
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [created, setCreated] = useState<AgentApiRecord | null>(null)

  const chosenTemplate = SPENDING_POLICY_TEMPLATES.find((t) => t.id === templateId)!

  const provision = async () => {
    setCreating(true)
    setError(null)
    try {
      const agent = await createAgent({
        name: agentName.trim() || "My first agent",
        description: "Created during Sardis onboarding.",
        create_wallet: true,
        spending_limits: chosenTemplate.spending_limits,
        metadata: {
          created_via: "onboarding_wizard",
          spending_policy_template: templateId,
        },
      })
      setCreated(agent)
      await ctx.patchMetadata({
        agent_id: agent.agent_id,
        wallet_id: agent.wallet_id,
        spending_policy_template: templateId,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create agent")
    } finally {
      setCreating(false)
    }
  }

  const readyToContinue = alreadyProvisioned || created !== null

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        We will provision your first agent together with a non-custodial Turnkey MPC
        wallet, then attach a spending policy so the agent can never exceed its cap.
      </p>

      {alreadyProvisioned && !created && (
        <div className="flex items-start gap-2 rounded border border-emerald-500/40 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
          <CheckCircle className="mt-0.5 size-4 shrink-0" weight="fill" />
          <span>
            Agent <span className="font-mono">{existingMeta.agent_id}</span> is already
            provisioned. You can continue.
          </span>
        </div>
      )}

      {!alreadyProvisioned && (
        <>
          <div className="space-y-1.5">
            <label
              htmlFor="agent_name"
              className="text-xs font-medium uppercase tracking-wider text-muted-foreground"
            >
              Agent name
            </label>
            <Input
              id="agent_name"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="My first agent"
              disabled={creating || created !== null}
              maxLength={80}
            />
          </div>

          <div className="space-y-2">
            <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Spending policy template
            </div>
            <div className="grid gap-2">
              {SPENDING_POLICY_TEMPLATES.map((template) => {
                const selected = template.id === templateId
                return (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => setTemplateId(template.id)}
                    disabled={creating || created !== null}
                    className={cn(
                      "rounded border px-3 py-2.5 text-left transition-colors",
                      selected
                        ? "border-foreground bg-muted/40"
                        : "border-border bg-background/40 hover:border-foreground/50",
                      (creating || created !== null) && "cursor-not-allowed opacity-60",
                    )}
                    aria-pressed={selected}
                  >
                    <div className="flex items-center justify-between">
                      <div className="text-sm font-medium">{template.label}</div>
                      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">
                        {template.trust_level}
                      </div>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {template.description}
                    </p>
                    <dl className="mt-2 grid grid-cols-3 gap-2 text-[11px]">
                      <LimitCell label="Per tx" value={template.spending_limits.per_transaction} />
                      <LimitCell label="Daily" value={template.spending_limits.daily} />
                      <LimitCell label="Monthly" value={template.spending_limits.monthly} />
                    </dl>
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}

      {error && (
        <div className="rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {created && (
        <div className="flex items-start gap-2 rounded border border-emerald-500/40 bg-emerald-500/5 px-3 py-2 text-sm text-emerald-700 dark:text-emerald-400">
          <CheckCircle className="mt-0.5 size-4 shrink-0" weight="fill" />
          <div className="space-y-0.5">
            <div>Agent and wallet created.</div>
            <div className="font-mono text-xs opacity-80">
              agent: {created.agent_id}
              {created.wallet_id ? ` · wallet: ${created.wallet_id}` : ""}
            </div>
          </div>
        </div>
      )}

      <div className="flex justify-end gap-2">
        {!readyToContinue && (
          <Button
            type="button"
            size="sm"
            onClick={provision}
            disabled={creating || ctx.pending}
          >
            <Wallet className="mr-1.5 size-4" weight="regular" />
            {creating ? "Creating agent…" : "Create agent and wallet"}
          </Button>
        )}
        {readyToContinue && (
          <Button
            type="button"
            size="sm"
            onClick={ctx.goNext}
            disabled={ctx.pending}
          >
            Continue
          </Button>
        )}
      </div>
    </div>
  )
}

function LimitCell({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border/60 bg-background/60 px-2 py-1">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className="font-mono text-foreground">${value}</div>
    </div>
  )
}
