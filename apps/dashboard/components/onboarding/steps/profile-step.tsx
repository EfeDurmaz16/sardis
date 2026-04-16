"use client"

import { useState } from "react"
import { useForm } from "react-hook-form"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { authClient } from "@/lib/auth-client"
import type { StepContext } from "../onboarding-wizard"

const USE_CASES = [
  { value: "agent_payments", label: "AI agent payments" },
  { value: "merchant_checkout", label: "Merchant checkout" },
  { value: "automated_workflows", label: "Automated workflows" },
  { value: "other", label: "Other" },
] as const

type UseCaseValue = (typeof USE_CASES)[number]["value"]

type ProfileForm = {
  display_name: string
  company_name: string
  use_case: UseCaseValue | ""
}

export function ProfileStep({ ctx }: { ctx: StepContext }) {
  const [error, setError] = useState<string | null>(null)
  const existingMeta = (ctx.state.metadata ?? {}) as {
    display_name?: string
    company_name?: string
    use_case?: UseCaseValue
  }

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<ProfileForm>({
    defaultValues: {
      display_name: existingMeta.display_name ?? "",
      company_name: existingMeta.company_name ?? "",
      use_case: existingMeta.use_case ?? "",
    },
  })

  const useCaseValue = watch("use_case")

  const onSubmit = handleSubmit(async (values) => {
    setError(null)
    try {
      // Persist the display name to the better-auth `name` column so it
      // is reflected in the session immediately and survives across
      // dashboard pages. Other onboarding fields (company_name, use_case)
      // are wizard metadata and live on the user_onboarding row.
      await authClient.updateUser({ name: values.display_name })

      await ctx.patchMetadata({
        display_name: values.display_name,
        company_name: values.company_name,
        use_case: values.use_case,
      })

      ctx.goNext()
    } catch (err) {
      console.error("[onboarding/profile] save failed", err)
      setError(err instanceof Error ? err.message : "Failed to save profile")
    }
  })

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <Field
        id="display_name"
        label="Your name"
        error={errors.display_name?.message}
      >
        <Input
          id="display_name"
          autoComplete="name"
          placeholder="Jane Builder"
          {...register("display_name", {
            required: "Required",
            minLength: { value: 2, message: "At least 2 characters" },
            maxLength: { value: 80, message: "Too long" },
          })}
        />
      </Field>

      <Field
        id="company_name"
        label="Company"
        error={errors.company_name?.message}
      >
        <Input
          id="company_name"
          autoComplete="organization"
          placeholder="Acme Robotics"
          {...register("company_name", {
            required: "Required",
            maxLength: { value: 120, message: "Too long" },
          })}
        />
      </Field>

      <Field id="use_case" label="What will you build?" error={errors.use_case?.message}>
        <Select
          value={useCaseValue || undefined}
          onValueChange={(val) =>
            setValue("use_case", val as UseCaseValue, { shouldValidate: true })
          }
        >
          <SelectTrigger id="use_case">
            <SelectValue placeholder="Pick one" />
          </SelectTrigger>
          <SelectContent>
            {USE_CASES.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <input
          type="hidden"
          {...register("use_case", { required: "Pick a use case" })}
        />
      </Field>

      {error && (
        <div className="rounded border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="flex justify-end">
        <Button
          type="submit"
          size="sm"
          disabled={isSubmitting || ctx.pending}
        >
          {isSubmitting ? "Saving…" : "Save and continue"}
        </Button>
      </div>
    </form>
  )
}

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string
  label: string
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </label>
      {children}
      {error && <div className="text-xs text-destructive">{error}</div>}
    </div>
  )
}
