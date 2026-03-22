import { driver, type DriveStep } from "driver.js";
import "driver.js/dist/driver.css";

const TOUR_STEPS: DriveStep[] = [
  {
    element: '[data-tour="overview"]',
    popover: {
      title: "Dashboard Overview",
      description:
        "See your agent activity, transaction volume, and system health at a glance.",
      side: "right",
      align: "start",
    },
  },
  {
    element: '[data-tour="agents"]',
    popover: {
      title: "AI Agents",
      description:
        "Create and manage AI agents. Each agent gets its own wallet and spending policy.",
      side: "right",
      align: "start",
    },
  },
  {
    element: '[data-tour="mandates"]',
    popover: {
      title: "Spending Mandates",
      description:
        "Define spending rules in plain English. Sardis enforces them automatically before every transaction.",
      side: "right",
      align: "start",
    },
  },
  {
    element: '[data-tour="transactions"]',
    popover: {
      title: "Transactions",
      description:
        "Monitor every payment your agents make. Full audit trail with cryptographic evidence.",
      side: "right",
      align: "start",
    },
  },
  {
    element: '[data-tour="api-keys"]',
    popover: {
      title: "API Keys",
      description:
        "Your test API key is ready. Use it with the SDK to start making payments from your agents.",
      side: "right",
      align: "start",
    },
  },
  {
    element: '[data-tour="go-live"]',
    popover: {
      title: "Go Live",
      description:
        "When you're ready for real money, complete the checklist here to activate mainnet access.",
      side: "right",
      align: "start",
    },
  },
];

const STORAGE_KEY = "sardis_tour_completed";

export function shouldShowTour(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem(STORAGE_KEY) !== "true";
}

export function startDashboardTour() {
  const driverObj = driver({
    showProgress: true,
    animate: true,
    showButtons: ["next", "previous", "close"],
    popoverClass: "sardis-tour",
    steps: TOUR_STEPS,
    onDestroyStarted: () => {
      localStorage.setItem(STORAGE_KEY, "true");
      driverObj.destroy();
    },
  });

  // Small delay to let the layout render
  setTimeout(() => driverObj.drive(), 500);
}
