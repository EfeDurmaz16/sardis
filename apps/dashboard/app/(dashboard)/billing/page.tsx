"use client"

import { useState } from "react"
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
} from "@phosphor-icons/react"
import { toast } from "sonner"

type Invoice = {
  date: string
  description: string
  amount: string
  status: "Paid" | "Pending"
}

const invoices: Invoice[] = [
  { date: "Mar 1, 2026", description: "Pro Plan - Monthly", amount: "$299.00", status: "Paid" },
  { date: "Feb 1, 2026", description: "Pro Plan - Monthly", amount: "$299.00", status: "Paid" },
  { date: "Jan 1, 2026", description: "Pro Plan - Monthly", amount: "$299.00", status: "Paid" },
  { date: "Dec 1, 2025", description: "Pro Plan - Monthly", amount: "$299.00", status: "Paid" },
  { date: "Nov 1, 2025", description: "Pro Plan - Monthly + Overage", amount: "$347.50", status: "Paid" },
]

const usage = [
  { label: "API Calls", used: "12,847", limit: "50,000", percent: 26 },
  { label: "Agents", used: "24", limit: "50", percent: 48 },
  { label: "Storage", used: "2.1 GB", limit: "10 GB", percent: 21 },
]

export default function BillingPage() {
  const [dialogOpen, setDialogOpen] = useState(false)
  const [cardNumber, setCardNumber] = useState("**** **** **** 4242")
  const [expiry, setExpiry] = useState("12/27")
  const [cardName, setCardName] = useState("")

  function handleUpdate() {
    toast.success("Payment method updated")
    setDialogOpen(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="text-sm text-muted-foreground">
          Manage your subscription, usage, and payment methods
        </p>
      </div>

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
                <p className="text-lg font-semibold">Pro Plan</p>
                <p className="text-sm text-muted-foreground">Billed monthly</p>
              </div>
              <p className="text-2xl font-bold tracking-tight tabular-nums">
                $299<span className="text-sm font-normal text-muted-foreground">/mo</span>
              </p>
            </div>
            <Separator />
            <div className="space-y-3">
              {usage.map((u) => (
                <div key={u.label} className="space-y-1.5">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{u.label}</span>
                    <span className="font-medium tabular-nums">
                      {u.used} <span className="text-muted-foreground font-normal">/ {u.limit}</span>
                    </span>
                  </div>
                  <Progress value={u.percent} />
                </div>
              ))}
            </div>
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
            <div className="flex items-center gap-4 rounded-lg border p-4">
              <div className="flex h-10 w-14 items-center justify-center rounded-md bg-muted">
                <CreditCard className="h-5 w-5 text-muted-foreground" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium">Visa ending in 4242</p>
                <p className="text-xs text-muted-foreground">Expires 12/27</p>
              </div>
              <Button variant="outline" size="sm" onClick={() => setDialogOpen(true)}>
                Update
              </Button>
            </div>
            <div className="rounded-lg border border-dashed p-4 text-center">
              <p className="text-sm text-muted-foreground">
                Next billing date: <span className="font-medium text-foreground">April 1, 2026</span>
              </p>
            </div>
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
              {invoices.map((inv, i) => (
                <TableRow key={i}>
                  <TableCell className="pl-4 text-muted-foreground">{inv.date}</TableCell>
                  <TableCell className="font-medium">{inv.description}</TableCell>
                  <TableCell className="text-right tabular-nums">{inv.amount}</TableCell>
                  <TableCell>
                    <Badge variant={inv.status === "Paid" ? "success" : "warning"}>
                      {inv.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" className="text-xs">
                      Download
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
