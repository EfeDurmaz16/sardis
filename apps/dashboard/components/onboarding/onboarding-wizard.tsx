"use client"

import { useCallback, useMemo, useState } from "react"
import { ArrowRight, Check, X } from "@phosphor-icons/react"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { cn } from "@/lib/utils"
import {
  ONBOARDING_STEPS,
  type OnboardingState,
  type OnboardingStep,
  updateOnboarding,
} from "@/lib/sardis-api"
import { ProfileStep } from "./steps/profile-step"
import { ApiKeyStep } from "./steps/api-key-step"
import { KycStep } from "./steps/kyc-step"
import { AgentWalletStep } from "./steps/agent-wallet-step"
import { SpendingPolicyStep } from "./steps/spending-policy-step"

export type StepContext = {
  state: OnboardingState
  pending: boolean
  goNext: () => void
  goSkip: () => void
  patchMetadata: (patch: Record<string, unknown>) => Promise<void>
}

type StepRegistryEntry = {
  hidesWizardContinue?: boolean
  render: (ctx: StepContext) => React.ReactNode
}

const STEP_REGISTRY: Partial<Record<OnboardingStep, StepRegistryEntry>> = {
  profile: {
    hidesWizardContinue: true,
    render: (ctx) => <ProfileStep ctx={ctx} />,
  },
  api_key: {
    hidesWizardContinue: true,
    render: (ctx) => <ApiKeyStep ctx={ctx} />,
  },
  kyc: {
    hidesWizardContinue: true,
    render: (ctx) => <KycStep ctx={ctx} />,
  },
  agent_wallet: {
    hidesWizardContinue: true,
    render: (ctx) => <AgentWalletStep ctx={ctx} />,
  },
  spending_policy: {
    hidesWizardContinue: true,
    render: (ctx) => <SpendingPolicyStep ctx={ctx} />,
  },
}

const STEP_LABELS: Record<OnboardingStep, string> = {
  profile: "Profile",
  api_key: "API key",
  kyc: "Identity",
  agent_wallet: "Agent wallet",
  spending_policy: "Spending policy",
  sandbox_payment: "Test payment",
  tour_ready: "Tour",
}

const STEP_DESCRIPTIONS: Record<OnboardingStep, string> = {
  profile: "Tell us who you are so receipts and audit trails can be attributed.",
  api_key: "Generate a sandbox API key to start integrating.",
  kyc: "Verify your identity to unlock live mainnet transactions.",
  agent_wallet: "Provision a non-custodial MPC wallet for your first agent.",
  spending_policy: "Set guardrails before you let an agent move money.",
  sandbox_payment: "Run a test payment end-to-end against the sandbox.",
  tour_ready: "You are ready. Take a quick tour of the dashboard.",
}

type OnboardingWizardProps = {
  initialState: OnboardingState
  open: boolean
  onOpenChange: (open: boolean) => void
  onComplete: () => void
}

export function OnboardingWizard({
  initialState,
  open,
  onOpenChange,
  onComplete,
}: OnboardingWizardProps) {
  const [state, setState] = useState<OnboardingState>(initialState)
  const [pending, setPending] = useState(false)

  const steps = state.steps?.length ? state.steps : [...ONBOARDING_STEPS]
  const currentIndex = useMemo(
    () => Math.max(0, steps.indexOf(state.current_step)),
    [steps, state.current_step],
  )
  const currentStep = steps[currentIndex] ?? steps[0]
  const isTerminal = currentStep === "tour_ready"
  const skipped = new Set<OnboardingStep>(state.metadata?.skipped ?? [])

  const persist = useCallback(
    async (nextStep: OnboardingStep, opts?: { skip?: boolean }) => {
      setPending(true)
      try {
        const next = await updateOnboarding({
          current_step: nextStep,
          skipped: opts?.skip ? [currentStep] : undefined,
          mark_complete: nextStep === "tour_ready",
        })
        setState(next)
        if (nextStep === "tour_ready") {
          onComplete()
        }
      } catch (err) {
        console.error("[onboarding] failed to update state", err)
      } finally {
        setPending(false)
      }
    },
    [currentStep, onComplete],
  )

  const goNext = useCallback(() => {
    const next = steps[currentIndex + 1] ?? "tour_ready"
    void persist(next)
  }, [currentIndex, persist, steps])

  const goSkip = useCallback(() => {
    const next = steps[currentIndex + 1] ?? "tour_ready"
    void persist(next, { skip: true })
  }, [currentIndex, persist, steps])

  const patchMetadata = useCallback(
    async (patch: Record<string, unknown>) => {
      setPending(true)
      try {
        const next = await updateOnboarding({ metadata_patch: patch })
        setState(next)
      } finally {
        setPending(false)
      }
    },
    [],
  )

  const stepCtx: StepContext = useMemo(
    () => ({ state, pending, goNext, goSkip, patchMetadata }),
    [state, pending, goNext, goSkip, patchMetadata],
  )

  const registryEntry = STEP_REGISTRY[currentStep]

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-base font-medium">
            Welcome to Sardis
          </DialogTitle>
          <DialogDescription className="text-sm text-muted-foreground">
            A few quick steps before your first agent transaction.
          </DialogDescription>
        </DialogHeader>

        <ProgressDots
          steps={steps}
          currentIndex={currentIndex}
          skipped={skipped}
          completedAt={state.completed_at}
        />

        <div className="mt-4 rounded border border-border bg-muted/20 p-5">
          <div className="text-xs uppercase tracking-wider text-muted-foreground">
            Step {currentIndex + 1} of {steps.length}
          </div>
          <div className="mt-1 text-base font-medium">
            {STEP_LABELS[currentStep]}
          </div>
          <p className="mt-2 text-sm text-muted-foreground">
            {STEP_DESCRIPTIONS[currentStep]}
          </p>

          <div className="mt-5">
            {registryEntry ? registryEntry.render(stepCtx) : <StepBody step={currentStep} />}
          </div>
        </div>

        <div className="mt-5 flex items-center justify-between gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={pending}
          >
            Close
          </Button>
          <div className="flex items-center gap-2">
            {!isTerminal && (
              <Button
                variant="ghost"
                size="sm"
                onClick={goSkip}
                disabled={pending}
              >
                Skip
              </Button>
            )}
            {!registryEntry?.hidesWizardContinue && (
              <Button size="sm" onClick={goNext} disabled={pending}>
                {isTerminal ? "Finish" : "Continue"}
                <ArrowRight className="ml-1.5 size-4" weight="regular" />
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

// ─── Progress dots ────────────────────────────────────────────────────────

type ProgressDotsProps = {
  steps: OnboardingStep[]
  currentIndex: number
  skipped: Set<OnboardingStep>
  completedAt: string | null
}

function ProgressDots({ steps, currentIndex, skipped, completedAt }: ProgressDotsProps) {
  return (
    <ol className="mt-4 flex items-center gap-2" aria-label="Onboarding progress">
      {steps.map((step, idx) => {
        const isCurrent = idx === currentIndex && !completedAt
        const isDone = completedAt ? true : idx < currentIndex
        const isSkipped = skipped.has(step)
        return (
          <li key={step} className="flex items-center gap-2">
            <span
              aria-current={isCurrent ? "step" : undefined}
              className={cn(
                "flex size-6 items-center justify-center rounded-full border text-[11px] font-medium",
                isDone && "border-foreground bg-foreground text-background",
                isCurrent && "border-foreground text-foreground",
                !isDone && !isCurrent && "border-border text-muted-foreground",
              )}
              title={STEP_LABELS[step]}
            >
              {isDone ? (
                <Check className="size-3" weight="bold" />
              ) : isSkipped ? (
                <X className="size-3" weight="bold" />
              ) : (
                idx + 1
              )}
            </span>
            {idx < steps.length - 1 && (
              <span className="h-px w-6 bg-border" aria-hidden />
            )}
          </li>
        )
      })}
    </ol>
  )
}

// ─── Step body placeholders ──────────────────────────────────────────────
//
// Real per-step content is filled in by tasks #3-#6. Until then each step
// renders a stub with the step name so the wizard is fully navigable
// end-to-end.

function StepBody({ step }: { step: OnboardingStep }) {
  return (
    <div className="rounded border border-dashed border-border bg-background/40 p-4 text-sm text-muted-foreground">
      Step content for <span className="font-mono text-foreground">{step}</span> will be filled in
      by a follow-up task.
    </div>
  )
}
