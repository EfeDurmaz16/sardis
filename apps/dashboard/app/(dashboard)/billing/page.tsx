"use client"

import { useState, useMemo } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardAction,
} from "@/components/ui/card"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import {
  CurrencyDollar,
  CreditCard,
  FileText,
  Spinner,
} from "@phosphor-icons/react"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { useSardis } from "@/hooks/use-sardis"

type Invoice = {
  id: string
  date: string
  description: string
  amount: number | string
  status: string
  download_url?: string | null
}

type BillingPlan = {
  name: string
  price: number
  interval: string
  next_billing_date: string | null
  payment_method?: {
    brand: string
    last4: string
    exp_month: number
    exp_year: number
  } | null
  usage?: {
    label: string
    used: number
    limit: number
  }[]
}

function formatCurrency(value: number | string): string {
  const num = typeof value === "string" ? parseFloat(value) : value
  if (!Number.isFinite(num)) return "$0.00"
  return `$${num.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

export default function BillingPage() {
  const { data: invoicesRaw, loading: invoicesLoading } = useSardis<Invoice[] | Record<string, unknown>>("api/v2/billing/invoices")
  const { data: plan, loading: planLoading } = useSardis<BillingPlan>("api/v2/billing/plan")
  const invoiceList = Array.isArray(invoicesRaw) ? invoicesRaw : []

  const [dialogOpen, setDialogOpen] = useState(false)
  const [cardNumber, setCardNumber] = useState("")
  const [expiry, setExpiry] = useState("")
  const [cardName, setCardName] = useState("")

  const loading = invoicesLoading || planLoading

  // Compute usage percentages from plan data
  const usageItems = useMemo(() => {
    if (!plan?.usage || !Array.isArray(plan.usage)) return []
    return plan.usage.map((u: { label: string; used: number; limit: number }) => ({
      label: u.label,
      used: u.used,
      limit: u.limit,
      percent: u.limit > 0 ? Math.round((u.used / u.limit) * 100) : 0,
    }))
  }, [plan])

  function handleUpdate() {
    // TODO: POST to API to update payment method
    toast.success("Payment method updated")
    setDialogOpen(false)
    setCardNumber("")
    setExpiry("")
    setCardName("")
  }

  const planName = plan?.name ?? "Free"
  const planPrice = plan?.price ?? 0
  const planInterval = plan?.interval ?? "mo"
  const paymentMethod = plan?.payment_method ?? null
  const nextBilling = plan?.next_billing_date ?? null

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Manage your subscription, usage, and payment methods
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      ) : (
      <>
      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <CurrencyDollar className="h-4 w-4 text-muted-foreground" />
              Current Plan
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="text-lg font-semibold">{planName}</p>
                <p className="text-sm text-muted-foreground">
                  {planPrice > 0 ? `Billed ${planInterval === "year" ? "annually" : "monthly"}` : "No active subscription"}
                </p>
              </div>
              {planPrice > 0 && (
                <p className="text-2xl font-bold tracking-tight tabular-nums">
                  {formatCurrency(planPrice)}
                  <span className="text-sm font-normal text-muted-foreground">/{planInterval}</span>
                </p>
              )}
            </div>
            {usageItems.length > 0 && (
              <>
                <Separator />
                <div className="space-y-3">
                  {usageItems.map((u) => (
                    <div key={u.label} className="space-y-1.5">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{u.label}</span>
                        <span className="font-medium tabular-nums">
                          {u.used.toLocaleString()}{" "}
                          <span className="text-muted-foreground font-normal">/ {u.limit.toLocaleString()}</span>
                        </span>
                      </div>
                      <Progress value={u.percent} />
                    </div>
                  ))}
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-4 w-4 text-muted-foreground" />
              Payment Method
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {paymentMethod ? (
              <div className="flex items-center gap-4 rounded-lg border p-4">
                <div className="flex h-10 w-14 items-center justify-center rounded-md bg-muted">
                  <CreditCard className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">
                    {paymentMethod.brand} ending in {paymentMethod.last4}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    Expires {String(paymentMethod.exp_month).padStart(2, "0")}/{String(paymentMethod.exp_year).slice(-2)}
                  </p>
                </div>
                <Button variant="outline" size="sm" onClick={() => window.open("https://billing.stripe.com/p/login/sardis", "_blank")}>
                  Manage
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-4 rounded-lg border border-dashed p-4">
                <div className="flex h-10 w-14 items-center justify-center rounded-md bg-muted">
                  <CreditCard className="h-5 w-5 text-muted-foreground" />
                </div>
                <div className="flex-1">
                  <p className="text-sm text-muted-foreground">Payment methods are managed through Stripe</p>
                </div>
                <Button variant="outline" size="sm" onClick={() => toast.info("Upgrade to a paid plan to add a payment method")}>
                  Add
                </Button>
              </div>
            )}
            {nextBilling ? (
              <div className="rounded-lg border border-dashed p-4 text-center">
                <p className="text-sm text-muted-foreground">
                  Next billing date:{" "}
                  <span className="font-medium text-foreground">
                    {new Date(nextBilling).toLocaleDateString("en-US", {
                      month: "long",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                </p>
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      {/* Update Payment Method Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Update Payment Method</DialogTitle>
            <DialogDescription>
              Enter your new card details below.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Card Number</label>
              <Input
                placeholder="**** **** **** 4242"
                value={cardNumber}
                onChange={(e) => setCardNumber(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Expiry Date</label>
              <Input
                placeholder="MM/YY"
                value={expiry}
                onChange={(e) => setExpiry(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Cardholder Name</label>
              <Input
                placeholder="John Doe"
                value={cardName}
                onChange={(e) => setCardName(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              Cancel
            </DialogClose>
            <Button onClick={handleUpdate}>Update</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-muted-foreground" />
            Billing History
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {invoiceList.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No invoices"
              description="Your billing history will appear here once you have an active subscription"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Date</TableHead>
                <TableHead>Description</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Invoice</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {invoiceList.map((inv) => (
                <TableRow key={inv.id}>
                  <TableCell className="pl-4 text-muted-foreground">
                    {new Date(inv.date).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </TableCell>
                  <TableCell className="font-medium">{inv.description}</TableCell>
                  <TableCell className="text-right tabular-nums">
                    {formatCurrency(inv.amount)}
                  </TableCell>
                  <TableCell>
                    <Badge variant={inv.status.toLowerCase() === "paid" ? "success" : "warning"}>
                      {inv.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {inv.download_url ? (
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs"
                        onClick={() => window.open(inv.download_url!, "_blank")}
                      >
                        Download
                      </Button>
                    ) : (
                      <span className="text-xs text-muted-foreground">--</span>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>
      </>
      )}
    </div>
  )
}
