"use client"

import { useState, useMemo } from "react"
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
  Spinner,
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
import { useSardis } from "@/hooks/use-sardis"
import { EmptyState } from "@/components/empty-state"

type VirtualCard = {
  id: string
  masked_number: string
  full_number: string
  cardholder: string
  limit: number
  spent: number
  status: "active" | "frozen" | "expired"
  chain: string
}

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
  const { data, loading, error, refetch } = useSardis<VirtualCard[]>("api/v2/cards")

  const cards = data ?? []

  const [revealedCards, setRevealedCards] = useState<Set<string>>(new Set())
  const [paymentCard, setPaymentCard] = useState<VirtualCard | null>(null)
  const [paymentOpen, setPaymentOpen] = useState(false)

  const stats = useMemo(() => {
    const activeCount = cards.filter(c => c.status === "active").length
    const totalLimit = cards.reduce((sum, c) => sum + c.limit, 0)
    const totalSpent = cards.reduce((sum, c) => sum + c.spent, 0)
    const utilization = totalLimit > 0 ? Math.round((totalSpent / totalLimit) * 100) : 0
    return [
      { label: "Active Cards", value: String(activeCount), icon: CreditCard },
      { label: "Total Limit", value: `$${totalLimit.toLocaleString()}`, icon: CurrencyDollar },
      { label: "Monthly Spend", value: `$${totalSpent.toLocaleString()}`, icon: Lightning },
      { label: "Utilization", value: `${utilization}%`, icon: ChartPie },
    ]
  }, [cards])

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

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Virtual Cards</h1>
          <p className="text-sm text-muted-foreground">Manage virtual cards assigned to your AI agents</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Virtual Cards</h1>
          <p className="text-sm text-muted-foreground">Manage virtual cards assigned to your AI agents</p>
        </div>
        <EmptyState
          icon={CreditCard}
          title="Virtual cards unavailable"
          description={error || "Virtual cards will appear here once they are provisioned via the Stripe Issuing integration."}
          action={refetch}
          actionLabel="Retry"
        />
      </div>
    )
  }

  if (cards.length === 0) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Virtual Cards</h1>
          <p className="text-sm text-muted-foreground">Manage virtual cards assigned to your AI agents</p>
        </div>
        <EmptyState
          icon={CreditCard}
          title="No virtual cards"
          description="Virtual cards will appear here once they are provisioned for your agents."
        />
      </div>
    )
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
                      <span className="font-mono text-base tracking-wider">{revealedCards.has(card.id) ? card.full_number : card.masked_number}</span>
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
              Pay using card {paymentCard?.masked_number} ({paymentCard?.cardholder})
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={async (e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const merchant = (formData.get("merchant") as string).trim()
              const amount = (formData.get("amount") as string).trim()
              if (!merchant || !amount || !paymentCard) return
              try {
                const res = await fetch(`/api/sardis/api/v2/cards/virtual/${paymentCard.id}/payment`, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    merchant,
                    amount: parseFloat(amount),
                  }),
                })
                if (!res.ok) throw new Error("Failed")
                toast.success(`Payment of $${amount} to ${merchant} processed`)
                setPaymentOpen(false)
                refetch()
              } catch {
                toast.error("Failed to process payment")
              }
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
