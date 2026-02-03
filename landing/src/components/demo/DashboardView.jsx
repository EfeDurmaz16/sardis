import { motion, AnimatePresence } from 'framer-motion'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

const STATE_LABELS = {
  IDLE: 'Ready',
  INITIALIZING: 'Connecting...',
  PLANNING: 'AI Reasoning',
  SIGNING: 'MPC Signing',
  CONFIRMING: 'Broadcasting',
  SUCCESS: 'Complete',
}

function StatusIndicator({ state }) {
  const isActive = state !== 'IDLE' && state !== 'SUCCESS'
  const isSuccess = state === 'SUCCESS'
  return (
    <div className="flex items-center gap-2">
      <span
        className={`block h-2 w-2 ${
          isSuccess
            ? 'bg-emerald-400'
            : isActive
            ? 'animate-pulse-orange bg-[var(--sardis-orange)]'
            : 'bg-muted-foreground opacity-40'
        }`}
      />
      <span className="font-mono text-xs text-muted-foreground">
        {STATE_LABELS[state]}
      </span>
    </div>
  )
}

function VirtualCard({ balance, spent }) {
  const hasSpent = spent > 0
  return (
    <motion.div
      className={`relative overflow-hidden border border-border p-5 transition-colors bg-card`}
      animate={hasSpent ? { scale: [1, 1.02, 1] } : {}}
      transition={{ duration: 0.4 }}
    >
      {hasSpent && (
        <motion.div
          className="absolute inset-0 border border-[var(--sardis-orange)] opacity-60"
          initial={{ opacity: 0 }}
          animate={{ opacity: [0, 0.6, 0.3] }}
          transition={{ duration: 1.2 }}
        />
      )}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          Sardis Virtual Card
        </span>
        <Badge variant="outline" className="text-[10px]">
          ACTIVE
        </Badge>
      </div>
      <div className="mt-4 font-mono text-lg tracking-wider text-foreground">
        •••• •••• •••• 4291
      </div>
      <div className="mt-3 flex items-end justify-between">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Balance</div>
          <motion.div
            className="font-mono text-sm text-foreground"
            key={balance}
            initial={hasSpent ? { color: 'var(--sardis-orange)' } : false}
            animate={{ color: 'var(--foreground)' }}
            transition={{ duration: 1.5 }}
          >
            ${balance.toFixed(2)}
          </motion.div>
        </div>
        {hasSpent && (
          <motion.div
            className="text-right"
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Last Tx</div>
            <div className="font-mono text-sm text-[var(--sardis-orange)]">-${spent.toFixed(2)}</div>
          </motion.div>
        )}
        <div className="text-right">
          <div className="text-[10px] uppercase tracking-widest text-muted-foreground">Network</div>
          <div className="font-mono text-sm text-foreground">Base Sepolia</div>
        </div>
      </div>
    </motion.div>
  )
}

function PolicyMeter({ used, limit = 500 }) {
  const pct = (used / limit) * 100
  return (
    <div>
      <div className="mb-1.5 flex justify-between font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
        <span>Daily Spend</span>
        <span>${used} / ${limit}</span>
      </div>
      <div className="h-1.5 w-full bg-muted">
        <motion.div
          className="h-full bg-[var(--sardis-orange)]"
          initial={{ width: '24%' }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6 }}
        />
      </div>
    </div>
  )
}

export default function DashboardView({
  state,
  transaction,
  cardBalance,
  policyUsed,
  isRunning,
  onStart,
  onReset,
}) {
  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 lg:p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-foreground" style={{ fontFamily: 'var(--font-display)' }}>
            Agent Procurement
          </h2>
          <p className="text-xs text-muted-foreground">AI-initiated payment simulation</p>
        </div>
        <StatusIndicator state={state} />
      </div>

      {/* Action */}
      <div className="flex gap-2">
        <Button
          onClick={onStart}
          disabled={isRunning}
          className="flex-1"
        >
          {state === 'SUCCESS' ? 'Run Again' : isRunning ? 'Simulating...' : 'Start Simulation'}
        </Button>
        {state === 'SUCCESS' && (
          <Button variant="outline" onClick={onReset}>
            Reset
          </Button>
        )}
      </div>

      {/* Cards grid */}
      <div className="grid gap-4 sm:grid-cols-2">
        {/* Virtual Card */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground">
              Virtual Card
            </CardTitle>
          </CardHeader>
          <CardContent>
            <VirtualCard balance={cardBalance} spent={cardBalance < 500 ? 500 - cardBalance : 0} />
          </CardContent>
        </Card>

        {/* Policy */}
        <Card className="border-border bg-card">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground">
              Spending Policy
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <PolicyMeter used={policyUsed} />
            <div className="space-y-1.5 font-mono text-xs text-muted-foreground">
              <div className="flex justify-between">
                <span>Category</span>
                <span className="text-foreground">SaaS / API</span>
              </div>
              <div className="flex justify-between">
                <span>Max per tx</span>
                <span className="text-foreground">$100.00</span>
              </div>
              <div className="flex justify-between">
                <span>Approval</span>
                <span className="text-foreground">Autonomous</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Transaction history */}
      <Card className="border-border bg-card">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-widest text-muted-foreground">
            Transaction History
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-0">
            {/* Table header */}
            <div className="grid grid-cols-4 gap-2 border-b border-border pb-2 font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              <span>Recipient</span>
              <span>Amount</span>
              <span>Chain</span>
              <span>Tx Hash</span>
            </div>

            <AnimatePresence>
              {transaction && (
                <motion.div
                  initial={{ opacity: 0, y: 12 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.35 }}
                  className="grid grid-cols-4 gap-2 border-b border-border py-2.5 font-mono text-xs text-foreground"
                >
                  <span>{transaction.to}</span>
                  <span>{transaction.amount} {transaction.token}</span>
                  <span>{transaction.chain}</span>
                  <a
                    href={transaction.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="truncate text-[var(--sardis-orange)] hover:underline"
                  >
                    {transaction.hash}
                  </a>
                </motion.div>
              )}
            </AnimatePresence>

            {!transaction && (
              <div className="py-6 text-center font-mono text-xs text-muted-foreground opacity-40">
                No transactions yet
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
