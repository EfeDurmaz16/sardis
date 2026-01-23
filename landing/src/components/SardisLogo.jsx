import { cn } from "@/lib/utils";

export default function SardisLogo({ className = "", size = "default" }) {
  const sizeClasses = {
    small: "w-6 h-6",
    default: "w-8 h-8",
    large: "w-12 h-12",
  };

  return (
    <svg
      viewBox="0 0 100 100"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(sizeClasses[size], className)}
    >
      {/* The Bracket Safe: Code brackets shielding the core */}
      <path
        d="M35 25 H25 V75 H35"
        stroke="var(--sardis-orange)"
        strokeWidth="10"
        fill="none"
        strokeLinecap="square"
      />
      <path
        d="M65 25 H75 V75 H65"
        stroke="var(--sardis-orange)"
        strokeWidth="10"
        fill="none"
        strokeLinecap="square"
      />
      <rect x="40" y="40" width="20" height="20" fill="var(--sardis-orange)" />
    </svg>
  );
}
