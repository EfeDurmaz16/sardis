import { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { useSardisDemo } from '@/components/demo/useSardisDemo'
import TerminalView from '@/components/demo/TerminalView'
import DashboardView from '@/components/demo/DashboardView'

export default function Demo() {
  const demo = useSardisDemo()
  const [showTerminal, setShowTerminal] = useState(false)

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      {/* Nav */}
      <header className="flex items-center justify-between border-b border-border px-4 py-3 lg:px-8">
        <Link to="/" className="font-mono text-sm font-semibold text-foreground hover:text-[var(--sardis-orange)] transition-colors">
          ← sardis.sh
        </Link>
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
            Live Demo
          </span>
          <span className="block h-1.5 w-1.5 bg-emerald-400" />
        </div>
      </header>

      {/* Mobile toggle */}
      <div className="flex border-b border-border lg:hidden">
        <button
          onClick={() => setShowTerminal(false)}
          className={`flex-1 py-2 text-center font-mono text-xs uppercase tracking-widest transition-colors ${
            !showTerminal ? 'bg-[var(--sardis-orange)] text-[var(--sardis-ink)]' : 'text-muted-foreground'
          }`}
        >
          Dashboard
        </button>
        <button
          onClick={() => setShowTerminal(true)}
          className={`flex-1 border-l border-border py-2 text-center font-mono text-xs uppercase tracking-widest transition-colors ${
            showTerminal ? 'bg-[var(--sardis-orange)] text-[var(--sardis-ink)]' : 'text-muted-foreground'
          }`}
        >
          Terminal
        </button>
      </div>

      {/* Split view */}
      <div className="flex flex-1 overflow-hidden">
        {/* Terminal - left (desktop) */}
        <motion.div
          className="hidden lg:block lg:w-[35%] lg:border-r lg:border-border"
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3 }}
        >
          <TerminalView logs={demo.logs} state={demo.state} />
        </motion.div>

        {/* Dashboard - right (desktop) */}
        <motion.div
          className="hidden lg:block lg:w-[65%]"
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.3, delay: 0.1 }}
        >
          <DashboardView
            state={demo.state}
            transaction={demo.transaction}
            cardBalance={demo.cardBalance}
            policyUsed={demo.policyUsed}
            isRunning={demo.isRunning}
            onStart={demo.state === 'SUCCESS' ? demo.reset : demo.runDemo}
            onReset={demo.reset}
          />
        </motion.div>

        {/* Mobile: show one at a time */}
        <div className="flex-1 lg:hidden">
          {showTerminal ? (
            <TerminalView logs={demo.logs} state={demo.state} />
          ) : (
            <DashboardView
              state={demo.state}
              transaction={demo.transaction}
              cardBalance={demo.cardBalance}
              policyUsed={demo.policyUsed}
              isRunning={demo.isRunning}
              onStart={demo.state === 'SUCCESS' ? demo.reset : demo.runDemo}
              onReset={demo.reset}
            />
          )}
        </div>
      </div>
    </div>
  )
}
