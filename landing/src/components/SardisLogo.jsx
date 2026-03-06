import { cn } from "@/lib/utils";

export default function SardisLogo({ className = "", size = "default", color }) {
  const sizeClasses = {
    small: "w-6 h-6",
    default: "w-8 h-8",
    large: "w-12 h-12",
  };

  const stroke = color || "currentColor";

  return (
    <svg
      viewBox="0 0 28 28"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={cn(sizeClasses[size], className)}
    >
      <path
        d="M20 5H10a7 7 0 000 14h2"
        stroke={stroke}
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M8 23h10a7 7 0 000-14h-2"
        stroke={stroke}
        strokeWidth="3"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
