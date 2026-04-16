"use client"

import { useCallback, useState } from "react"
import { AppSidebar } from "./app-sidebar"
import { AppHeader } from "./app-header"
import { CommandPalette } from "./command-palette"
import { KeyboardShortcuts } from "./keyboard-shortcuts"
import { OnboardingGate } from "./onboarding/onboarding-gate"

export function AppShell({ children }: { children: React.ReactNode }) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false)

  const toggleSidebarCollapsed = useCallback(() => {
    setSidebarCollapsed((prev) => !prev)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden">
      <OnboardingGate />
      <CommandPalette open={commandPaletteOpen} onOpenChange={setCommandPaletteOpen} />
      <KeyboardShortcuts onToggleSidebar={toggleSidebarCollapsed} />
      <AppSidebar
        open={sidebarOpen}
        onOpenChange={setSidebarOpen}
        collapsed={sidebarCollapsed}
        onCollapsedChange={setSidebarCollapsed}
      />
      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <AppHeader
          onMenuClick={() => setSidebarOpen(true)}
          onSearchClick={() => setCommandPaletteOpen(true)}
        />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
          {children}
        </main>
      </div>
    </div>
  )
}
