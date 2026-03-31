"use client"

import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
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
import { Progress } from "@/components/ui/progress"
import {
  Wallet,
  CurrencyDollar,
  ArrowDown,
  Clock,
} from "@phosphor-icons/react"
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu"
import { toast } from "sonner"
import { EmptyState } from "@/components/empty-state"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"

type WalletEntry = {
  name: string
  address: string
  chain: string
  balance: string
  pending: string
  lastTransaction: string
}

const initialWallets: WalletEntry[] = [
  { name: "Treasury Main", address: "0x1a2B...9f4E", chain: "Ethereum", balance: "$82,400", pending: "$0", lastTransaction: "2 min ago" },
  { name: "Payroll Vault", address: "0x3c8D...2a1F", chain: "Ethereum", balance: "$54,100", pending: "$0", lastTransaction: "30 min ago" },
  { name: "Agent Ops Fund", address: "0x7e5A...6b3C", chain: "Polygon", balance: "$42,800", pending: "$1,200", lastTransaction: "5 min ago" },
  { name: "Bridge Reserve", address: "0x9f1B...4d7E", chain: "Arbitrum", balance: "$31,600", pending: "$0", lastTransaction: "15 min ago" },
  { name: "Vendor Payments", address: "0x2d6C...8e5A", chain: "Polygon", balance: "$28,350", pending: "$0", lastTransaction: "1 hr ago" },
  { name: "Gas Station", address: "0x5b4E...1c9D", chain: "Base", balance: "$18,920", pending: "$0", lastTransaction: "8 min ago" },
  { name: "Yield Pool", address: "0x8a3F...7d2B", chain: "Optimism", balance: "$22,630", pending: "$3,500", lastTransaction: "4 min ago" },
  { name: "Settlement Buffer", address: "0x4c7D...5f8A", chain: "Base", balance: "$3,592", pending: "$0", lastTransaction: "2 hrs ago" },
]

const stats = [
  { label: "Total Balance", value: "$284,392", icon: CurrencyDollar },
  { label: "Wallets", value: "24", icon: Wallet },
  { label: "Avg Balance", value: "$11.8k", icon: ArrowDown },
  { label: "Pending Deposits", value: "2", icon: Clock },
]

const chainVariant: Record<string, "outline"> = {
  Ethereum: "outline",
  Polygon: "outline",
  Arbitrum: "outline",
  Optimism: "outline",
  Base: "outline",
}

const chainBalances = [
  { chain: "Ethereum", amount: "$136,500", percent: 48 },
  { chain: "Polygon", amount: "$71,150", percent: 25 },
  { chain: "Arbitrum", amount: "$31,600", percent: 11 },
  { chain: "Optimism", amount: "$22,630", percent: 8 },
  { chain: "Base", amount: "$22,512", percent: 8 },
]

type Deposit = {
  from: string
  amount: string
  chain: string
  time: string
}

const recentDeposits: Deposit[] = [
  { from: "Agent Ops Fund", amount: "+$1,200", chain: "Polygon", time: "5 min ago" },
  { from: "Yield Pool", amount: "+$3,500", chain: "Optimism", time: "4 min ago" },
  { from: "Treasury Main", amount: "+$10,000", chain: "Ethereum", time: "1 hr ago" },
  { from: "Gas Station", amount: "+$500", chain: "Base", time: "3 hrs ago" },
]

function parseCurrency(val: string): number {
  return parseFloat(val.replace(/[$,]/g, "")) || 0
}

function formatCurrency(val: number): string {
  return "$" + val.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

export default function WalletsPage() {
  const [wallets, setWallets] = useState<WalletEntry[]>(initialWallets)
  const [detailWallet, setDetailWallet] = useState<WalletEntry | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [fundWallet, setFundWallet] = useState<WalletEntry | null>(null)
  const [fundOpen, setFundOpen] = useState(false)

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Wallets</h1>
        <p className="text-sm text-muted-foreground">Manage wallets and track balances across chains</p>
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

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Wallet Overview</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {wallets.length === 0 ? (
            <EmptyState
              icon={Wallet}
              title="No wallets"
              description="Wallets are created automatically when you create agents"
            />
          ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Wallet Name</TableHead>
                <TableHead>Address</TableHead>
                <TableHead>Chain</TableHead>
                <TableHead className="text-right">Balance</TableHead>
                <TableHead className="text-right">Pending</TableHead>
                <TableHead>Last Transaction</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {wallets.map((w) => (
                <ContextMenu key={w.name}>
                  <ContextMenuTrigger render={<TableRow />}>
                    <TableCell className="pl-4 font-medium">{w.name}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{w.address}</TableCell>
                    <TableCell>
                      <Badge variant={chainVariant[w.chain] ?? "outline"}>{w.chain}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{w.balance}</TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{w.pending === "$0" ? "--" : w.pending}</TableCell>
                    <TableCell className="text-muted-foreground">{w.lastTransaction}</TableCell>
                  </ContextMenuTrigger>
                  <ContextMenuContent>
                    <ContextMenuItem onClick={() => { navigator.clipboard.writeText(w.address); toast.success("Copied to clipboard") }}>
                      Copy Wallet ID
                    </ContextMenuItem>
                    <ContextMenuSeparator />
                    <ContextMenuItem onClick={() => { setDetailWallet(w); setSheetOpen(true) }}>View Details</ContextMenuItem>
                    <ContextMenuItem onClick={() => { setFundWallet(w); setFundOpen(true) }}>Fund</ContextMenuItem>
                  </ContextMenuContent>
                </ContextMenu>
              ))}
            </TableBody>
          </Table>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Balance by Chain</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {chainBalances.map((c) => (
              <div key={c.chain} className="space-y-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="font-medium">{c.chain}</span>
                  <span className="text-muted-foreground">{c.amount} ({c.percent}%)</span>
                </div>
                <Progress value={c.percent} className="h-1" />
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Recent Deposits</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Wallet</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Chain</TableHead>
                  <TableHead>Time</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {recentDeposits.map((d, i) => (
                  <TableRow key={i}>
                    <TableCell className="pl-4 font-medium">{d.from}</TableCell>
                    <TableCell className="text-right tabular-nums text-success">{d.amount}</TableCell>
                    <TableCell>
                      <Badge variant={chainVariant[d.chain] ?? "outline"}>{d.chain}</Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{d.time}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Wallet Details Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{detailWallet?.name}</SheetTitle>
            <SheetDescription>Wallet details and chain info</SheetDescription>
          </SheetHeader>
          {detailWallet && (
            <div className="space-y-4 px-4">
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Address</p>
                  <p className="font-mono text-sm">{detailWallet.address}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Chain</p>
                  <p className="text-sm">{detailWallet.chain}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Balance</p>
                  <p className="text-sm font-medium">{detailWallet.balance}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Pending</p>
                  <p className="text-sm">{detailWallet.pending === "$0" ? "None" : detailWallet.pending}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Last Transaction</p>
                  <p className="text-sm">{detailWallet.lastTransaction}</p>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      {/* Fund Wallet Dialog */}
      <Dialog open={fundOpen} onOpenChange={setFundOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Fund Wallet</DialogTitle>
            <DialogDescription>
              Add funds to {fundWallet?.name}
            </DialogDescription>
          </DialogHeader>
          <form
            onSubmit={(e) => {
              e.preventDefault()
              const formData = new FormData(e.currentTarget)
              const amount = parseFloat((formData.get("amount") as string).trim())
              if (!amount || amount <= 0) return
              setWallets((prev) =>
                prev.map((w) =>
                  w.address === fundWallet?.address
                    ? { ...w, balance: formatCurrency(parseCurrency(w.balance) + amount) }
                    : w
                )
              )
              toast.success(`Funded ${fundWallet?.name} with $${amount.toLocaleString()}`)
              setFundOpen(false)
            }}
            className="space-y-4"
          >
            <div className="space-y-1.5">
              <p className="text-sm font-medium">Amount ($)</p>
              <Input name="amount" type="number" step="0.01" min="0" placeholder="0.00" required />
            </div>
            <DialogFooter>
              <DialogClose render={<Button variant="outline" />}>Cancel</DialogClose>
              <Button type="submit">Fund</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
