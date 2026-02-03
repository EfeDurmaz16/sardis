import { useEffect, useRef, useState } from 'react'

function TypewriterLine({ text, speed = 12 }) {
  const [displayed, setDisplayed] = useState('')
  const idx = useRef(0)

  useEffect(() => {
    idx.current = 0
    setDisplayed('')
    const interval = setInterval(() => {
      idx.current += 1
      setDisplayed(text.slice(0, idx.current))
      if (idx.current >= text.length) clearInterval(interval)
    }, speed)
    return () => clearInterval(interval)
  }, [text, speed])

  const isSuccess = text.includes('✓')
  const isError = text.includes('✗')
  const isBracket = text.match(/^\[([^\]]+)\]/)
  const prefix = isBracket ? isBracket[0] : ''
  const rest = isBracket ? displayed.slice(prefix.length) : displayed

  return (
    <div className="leading-relaxed">
      {isBracket ? (
        <>
          <span className="text-[var(--sardis-orange)] opacity-80">{displayed.slice(0, prefix.length)}</span>
          <span className={isSuccess ? 'text-emerald-400' : isError ? 'text-red-400' : 'text-[var(--sardis-canvas)] opacity-70'}>
            {rest}
          </span>
        </>
      ) : (
        <span className="text-[var(--sardis-canvas)] opacity-70">{displayed}</span>
      )}
    </div>
  )
}

export default function TerminalView({ logs, state }) {
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [logs])

  return (
    <div className="flex h-full flex-col border border-border bg-[var(--sardis-ink)]">
      {/* Title bar */}
      <div className="flex items-center gap-2 border-b border-border px-4 py-2.5">
        <div className="flex gap-1.5">
          <span className="block h-2.5 w-2.5 bg-[#ff5f57]" />
          <span className="block h-2.5 w-2.5 bg-[#febc2e]" />
          <span className="block h-2.5 w-2.5 bg-[#28c840]" />
        </div>
        <span className="ml-2 font-mono text-xs text-[var(--sardis-canvas)] opacity-50">
          sardis-core — agent session
        </span>
        {state !== 'IDLE' && state !== 'SUCCESS' && (
          <span className="ml-auto inline-block h-1.5 w-1.5 animate-pulse-orange bg-[var(--sardis-orange)]" />
        )}
      </div>

      {/* Log output */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed"
      >
        {logs.length === 0 && (
          <div className="text-[var(--sardis-canvas)] opacity-30">
            <span>$ sardis simulate --chain base-sepolia</span>
            <span className="animate-blink-cursor ml-0.5">▋</span>
          </div>
        )}
        {logs.map((log, i) => (
          <TypewriterLine key={`${log.ts}-${i}`} text={log.text} />
        ))}
        {state !== 'IDLE' && state !== 'SUCCESS' && logs.length > 0 && (
          <span className="animate-blink-cursor text-[var(--sardis-orange)]">▋</span>
        )}
      </div>
    </div>
  )
}
