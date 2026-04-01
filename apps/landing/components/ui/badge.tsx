import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "group/badge inline-flex h-4 w-fit shrink-0 items-center justify-center gap-0.5 overflow-hidden rounded-[3px] border border-transparent px-1.5 py-0 text-[10.5px] font-medium whitespace-nowrap transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 has-data-[icon=inline-end]:pr-1 has-data-[icon=inline-start]:pl-1 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-2.5!",
  {
    variants: {
      variant: {
        default:
          "bg-muted/80 text-secondary-foreground border-border [a]:hover:bg-muted",
        secondary:
          "bg-secondary text-secondary-foreground [a]:hover:bg-secondary/80",
        primary: "bg-primary text-primary-foreground [a]:hover:bg-primary/80",
        destructive:
          "bg-destructive/10 text-destructive border-destructive/20 dark:bg-destructive/20 dark:border-destructive/30 [a]:hover:bg-destructive/20",
        success:
          "bg-success-muted text-success border-success/15 dark:border-success/20 [a]:hover:bg-success-muted/80",
        warning:
          "bg-warning-muted text-warning border-warning/15 dark:border-warning/20 [a]:hover:bg-warning-muted/80",
        info:
          "bg-info-muted text-info border-info/15 dark:border-info/20 [a]:hover:bg-info-muted/80",
        outline:
          "border-border text-muted-foreground [a]:hover:bg-muted [a]:hover:text-foreground",
        ghost:
          "hover:bg-muted hover:text-muted-foreground dark:hover:bg-muted/50",
        link: "text-primary underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
