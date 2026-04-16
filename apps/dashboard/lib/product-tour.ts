"use client"

// Product tour driven by driver.js (https://driverjs.com/).
// The tour highlights sidebar nav items that are always rendered on every
// dashboard page, so the user doesn't need to navigate between routes during
// the tour. Each step targets a `data-tour-id` attribute on the nav link in
// apps/dashboard/components/app-sidebar.tsx.
//
// We dynamically import driver.js so it never runs on the server (the library
// touches `document` at module init time).

const TOUR_STORAGE_KEY = "sardis:tour-completed"

export function isTourCompleted(): boolean {
  if (typeof window === "undefined") return true
  try {
    return window.localStorage.getItem(TOUR_STORAGE_KEY) === "true"
  } catch {
    return true
  }
}

export function markTourCompleted(): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(TOUR_STORAGE_KEY, "true")
  } catch {
    // ignore quota / private mode errors
  }
}

export function resetTour(): void {
  if (typeof window === "undefined") return
  try {
    window.localStorage.removeItem(TOUR_STORAGE_KEY)
  } catch {
    // ignore
  }
}

type TourStep = {
  selector: string
  title: string
  description: string
}

const TOUR_STEPS: TourStep[] = [
  {
    selector: '[data-tour-id="nav-overview"]',
    title: "Command center",
    description:
      "Overview is your home. Balances, recent agent activity, and anything that needs attention all land here.",
  },
  {
    selector: '[data-tour-id="nav-api-keys"]',
    title: "API keys",
    description:
      "Rotate, scope, and revoke keys. Every key you create here is scoped to this workspace and auditable.",
  },
  {
    selector: '[data-tour-id="nav-wallets"]',
    title: "Agent wallets",
    description:
      "Non-custodial MPC wallets for each agent. Balances, addresses across chains, and transaction history live here.",
  },
  {
    selector: '[data-tour-id="nav-mandates"]',
    title: "Policies and mandates",
    description:
      "Every payment an agent makes is checked against a policy. Set spending caps, approval rules, and merchant allowlists here.",
  },
  {
    selector: '[data-tour-id="nav-ledger"]',
    title: "Transaction ledger",
    description:
      "Append-only audit trail of every payment, anchored on-chain. This is what your auditors, finance team, and regulators will ask for.",
  },
  {
    selector: '[data-tour-id="nav-webhooks"]',
    title: "Webhooks",
    description:
      "Wire Sardis events (payment executed, policy violation, approval needed) into your own app. Signed with HMAC.",
  },
]

export async function startProductTour(options: { onFinish?: () => void } = {}) {
  if (typeof window === "undefined") return

  const { driver } = await import("driver.js")
  await import("driver.js/dist/driver.css")

  // Skip any steps whose selector can't be resolved on the current page.
  // Keeps the tour coherent if a nav item is hidden behind a collapsed
  // section or a permission gate.
  const resolvedSteps = TOUR_STEPS.filter((step) =>
    document.querySelector(step.selector),
  ).map((step) => ({
    element: step.selector,
    popover: {
      title: step.title,
      description: step.description,
      side: "right" as const,
      align: "start" as const,
    },
  }))

  if (resolvedSteps.length === 0) {
    markTourCompleted()
    options.onFinish?.()
    return
  }

  const driverObj = driver({
    showProgress: true,
    animate: true,
    overlayOpacity: 0.65,
    stagePadding: 4,
    stageRadius: 6,
    popoverClass: "sardis-driver-popover",
    steps: resolvedSteps,
    onDestroyStarted: () => {
      // Called on Close click, Escape, or Done. Persist and close.
      markTourCompleted()
      driverObj.destroy()
      options.onFinish?.()
    },
  })

  driverObj.drive()
}
