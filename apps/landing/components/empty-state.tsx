"use client"
import { type Icon } from "@phosphor-icons/react"
import { Button } from "@/components/ui/button"

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  actionLabel,
}: {
  icon: Icon
  title: string
  description: string
  action?: () => void
  actionLabel?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-12 h-12 rounded-xl bg-muted flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-muted-foreground" />
      </div>
      <h3 className="text-sm font-medium mb-1">{title}</h3>
      <p className="text-xs text-muted-foreground text-center max-w-sm mb-4">{description}</p>
      {action && actionLabel && (
        <Button variant="outline" size="sm" onClick={action}>{actionLabel}</Button>
      )}
    </div>
  )
}
