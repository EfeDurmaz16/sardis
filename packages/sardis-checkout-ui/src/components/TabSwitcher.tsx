import { cn } from "@/lib/cn";

interface TabSwitcherProps {
  active: "wallet" | "fund";
  onChange: (tab: "wallet" | "fund") => void;
}

export default function TabSwitcher({ active, onChange }: TabSwitcherProps) {
  return (
    <div className="flex bg-[var(--checkout-bg)] rounded-lg p-1 mb-6">
      <button
        onClick={() => onChange("wallet")}
        className={cn(
          "flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors",
          active === "wallet"
            ? "bg-white text-[var(--checkout-primary)] shadow-sm"
            : "text-[var(--checkout-muted)] hover:text-[var(--checkout-secondary)]",
        )}
      >
        Pay from Wallet
      </button>
      <button
        onClick={() => onChange("fund")}
        className={cn(
          "flex-1 py-2 px-4 text-sm font-medium rounded-md transition-colors",
          active === "fund"
            ? "bg-white text-[var(--checkout-primary)] shadow-sm"
            : "text-[var(--checkout-muted)] hover:text-[var(--checkout-secondary)]",
        )}
      >
        Fund &amp; Pay
      </button>
    </div>
  );
}
