"use client"

import { useEffect, useCallback, useState } from "react"
import { useRouter } from "next/navigation"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog"

const CHORD_TIMEOUT = 1000

type ShortcutGroup = {
  title: string
  shortcuts: { keys: string[]; description: string }[]
}

const shortcutGroups: ShortcutGroup[] = [
  {
    title: "Navigation",
    shortcuts: [
      { keys: ["g", "o"], description: "Go to Overview" },
      { keys: ["g", "a"], description: "Go to Agents" },
      { keys: ["g", "t"], description: "Go to Transactions" },
      { keys: ["g", "m"], description: "Go to Mandates" },
      { keys: ["g", "w"], description: "Go to Wallets" },
      { keys: ["g", "s"], description: "Go to Settings" },
    ],
  },
  {
    title: "General",
    shortcuts: [
      { keys: ["["], description: "Toggle sidebar" },
      { keys: ["?"], description: "Show keyboard shortcuts" },
    ],
  },
]

const navigationMap: Record<string, string> = {
  o: "/",
  a: "/agents",
  t: "/transactions",
  m: "/mandates",
  w: "/wallets",
  s: "/settings",
}

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tagName = target.tagName.toLowerCase()
  if (tagName === "input" || tagName === "textarea" || tagName === "select") {
    return true
  }
  if (target.isContentEditable) return true
  return false
}

function ShortcutsHelpDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Keyboard Shortcuts</DialogTitle>
          <DialogDescription>
            Use these shortcuts to navigate quickly.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          {shortcutGroups.map((group) => (
            <div key={group.title}>
              <h4 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
                {group.title}
              </h4>
              <div className="space-y-1.5">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.description}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-sm text-foreground">
                      {shortcut.description}
                    </span>
                    <div className="flex items-center gap-1">
                      {shortcut.keys.map((key, i) => (
                        <span key={i} className="flex items-center gap-1">
                          {i > 0 && (
                            <span className="text-xs text-muted-foreground">
                              then
                            </span>
                          )}
                          <kbd className="inline-flex h-5 min-w-5 items-center justify-center rounded border bg-muted px-1.5 font-mono text-[11px] font-medium text-muted-foreground">
                            {key}
                          </kbd>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}

export function KeyboardShortcuts({
  onToggleSidebar,
}: {
  onToggleSidebar: () => void
}) {
  const router = useRouter()
  const [helpOpen, setHelpOpen] = useState(false)
  const [pendingChord, setPendingChord] = useState<string | null>(null)

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (isEditableTarget(e.target)) return

      // Don't capture shortcuts when modifier keys are held (except Shift for ?)
      if (e.ctrlKey || e.metaKey || e.altKey) return

      const key = e.key

      // Complete a pending chord
      if (pendingChord === "g") {
        setPendingChord(null)
        const route = navigationMap[key]
        if (route) {
          e.preventDefault()
          router.push(route)
        }
        return
      }

      // Start a chord
      if (key === "g") {
        setPendingChord("g")
        return
      }

      // Single-key shortcuts
      if (key === "[") {
        e.preventDefault()
        onToggleSidebar()
        return
      }

      if (key === "?") {
        e.preventDefault()
        setHelpOpen((prev) => !prev)
        return
      }
    },
    [pendingChord, router, onToggleSidebar]
  )

  // Clear pending chord after timeout
  useEffect(() => {
    if (!pendingChord) return
    const timer = setTimeout(() => {
      setPendingChord(null)
    }, CHORD_TIMEOUT)
    return () => clearTimeout(timer)
  }, [pendingChord])

  // Register global listener
  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [handleKeyDown])

  return <ShortcutsHelpDialog open={helpOpen} onOpenChange={setHelpOpen} />
}
