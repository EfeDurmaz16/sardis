"use client"

import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  CreditCard,
  CurrencyDollar,
  ChartPie,
  Lightning,
} from "@phosphor-icons/react"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"

type VirtualCard = {
  id: string
  maskedNumber: string
  fullNumber: string
  cardholder: string
  limit: number
  spent: number
  status: "active" | "frozen" | "expired"
  chain: string
}

const cards: VirtualCard[] = [
  { id: "vc-001", maskedNumber: "•••• 4242", fullNumber: "4539 1234 5678 4242", cardholder: "Payment Router Alpha", limit: 25000, spent: 8200, status: "active", chain: "Ethereum" },
  { id: "vc-002", maskedNumber: "•••• 5173", fullNumber: "4539 8765 4321 5173", cardholder: "Expense Tracker v2", limit: 15000, spent: 6800, status: "active", chain: "Polygon" },
  { id: "vc-003", maskedNumber: "•••• 8391", fullNumber: "4539 2468 1357 8391", cardholder: "Treasury Sweep Bot", limit: 50000, spent: 12400, status: "active", chain: "Ethereum" },
  { id: "vc-004", maskedNumber: "•••• 2957", fullNumber: "4539 9753 8642 2957", cardholder: "Vendor Pay Agent", limit: 20000, spent: 4300, status: "frozen", chain: "Arbitrum" },
  { id: "vc-005", maskedNumber: "•••• 6614", fullNumber: "4539 1597 5384 6614", cardholder: "Subscription Manager", limit: 10000, spent: 7800, status: "active", chain: "Polygon" },
  { id: "vc-006", maskedNumber: "•••• 3028", fullNumber: "4539 7531 9264 3028", cardholder: "Payroll Distributor", limit: 30000, spent: 2500, status: "active", chain: "Optimism" },
]

const stats = [
  { label: "Active Cards", value: "12", icon: CreditCard },
  { label: "Total Limit", value: "$150,000", icon: CurrencyDollar },
  { label: "Monthly Spend", value: "$42,000", icon: Lightning },
  { label: "Utilization", value: "28%", icon: ChartPie },
]

const statusConfig: Record<VirtualCard["status"], { color: string; label: string }> = {
  active: { color: "bg-success", label: "Active" },
  frozen: { color: "bg-warning", label: "Frozen" },
  expired: { color: "bg-destructive", label: "Expired" },
}

const chainVariant: Record<string, "default" | "secondary" | "outline"> = {
  Ethereum: "default",
  Polygon: "secondary",
  Arbitrum: "outline",
  Optimism: "secondary",
}

export default function VirtualCardsPage() {
  const [revealedCards, setRevealedCards] = useState<Set<string>>(new Set())
  const [paymentCard, setPaymentCard] = useState<VirtualCard | null>(null)
  const [paymentOpen, setPaymentOpen] = useState(false)

  function toggleReveal(id: string) {
    setRevealedCards((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Virtual Cards</h1>
        <p className="text-sm text-muted-foreground">Manage virtual cards assigned to your AI agents</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => {
          const Ico = s.icon
          return (
            <Card key={s.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Ico className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{s.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{s.value}</p>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {cards.map((card) => {
          const st = statusConfig[card.status]
          const utilization = Math.round((card.spent / card.limit) * 100)
          return (
            <ContextMenu key={card.id}>
              <ContextMenuTrigger>
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span className="font-mono text-base tracking-wider">{revealedCards.has(card.id) ? card.fullNumber : card.maskedNumber}</span>
                      <span className="inline-flex items-center gap-1.5 text-xs font-normal">
                        <span className={`h-1.5 w-1.5 rounded-full ${st.color}`} />
                        {st.label}
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="text-sm font-medium">{card.cardholder}</div>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>Spent ${card.spent.toLocaleString()} of ${card.limit.toLocaleString()}</span>
                      <span>{utilization}%</span>
                    </div>
                    <Progress value={utilization} className="h-1.5" />
                    <div className="flex items-center justify-between pt-1">
                      <Badge variant={chainVariant[card.chain] ?? "outline"}>{card.chain}</Badge>
                      <span className="text-xs text-muted-foreground font-mono">{card.id}</span>
                    </div>
                  </CardContent>
                </Card>
              </ContextMenuTrigger>
              <ContextMenuContent>
                <ContextMenuItem onClick={() => { navigator.clipboard.writeText(card.id); toast.success("Copied to clipboard") }}>
                  Copy ID
                </ContextMenuItem>
                <ContextMenuSeparator />
                <ContextMenuItem onClick={() => toggleReveal(card.id)}>
                  {revealedCards.has(card.id) ? "Hide Details" : "Reveal Details"}
                </ContextMenuItem>
                <ContextMenuItem onClick={() => { setPaymentCard(card); setPaymentOpen(true) }}>Make Payment</ContextMenuItem>
              </ContextMenuContent>
            </ContextMenu>
          )
        })}
      </div>

      {/* Make Payment Dialog */}
      <Dialog open={paymentOpen} onOpenChange={setPaymentOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Make Payment</DialogTitle>
            <DialogDescription>
              Pay using card {paymentCard?.maskedNumber} ({paymentCard?.cardholder})
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const merchant = (formData.get("merchant") as string).trim()
              const amount = (formData.get("amount") as string).trim()
              if (!merchant || !amount) return
              toast.success(`Payment of $${amount} to ${merchant} processed on ${paymentCard?.maskedNumber}`)
              setPaymentOpen(false)
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Merchant</p>
              <Input name="merchant" placeholder="Merchant name" required />
            </div>
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Amount ($)</p>
              <Input name="amount" type="number" step="0.01" min="0" placeholder="0.00" required />
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Pay</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
