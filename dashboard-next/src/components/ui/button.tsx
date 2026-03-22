import { forwardRef } from "react";
import { cn } from "@/lib/utils";
export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> { variant?: string; size?: string; asChild?: boolean; }
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(({ className, children, ...props }, ref) => (
  <button ref={ref} className={cn("inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50", className)} {...props}>{children}</button>
));
Button.displayName = "Button";
