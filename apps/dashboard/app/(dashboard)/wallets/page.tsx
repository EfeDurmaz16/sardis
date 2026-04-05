"use client"

import { useEffect, useMemo, useState } from "react"
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
  Copy,
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
import { dashboardApiFetch } from "@/utils/dashboard-client"

type WalletBalance = {
  chain: string
  token: string
  balance: string
  address: string
}

type WalletSnapshot = {
  walletId: string
  agentId: string
  name: string
  primaryAddress: string | null
  primaryChain: string | null
  currency: string
  provider: string
  accountType: string
  isActive: boolean
  totalUsd: string | null
  totalEur: string | null
  limitPerTx: string
  limitTotal: string
  balances: WalletBalance[]
  pendingDeposits: number
  pendingAmountUsd: string
  lastActivityAt: string | null
  createdAt: string
  updatedAt: string
}

type ChainBalance = {
  chain: string
  amount: string
}

type DepositSummary = {
  walletId: string
  walletName: string
  depositId: string
  amount: string
  chain: string
  status: string
  detectedAt: string | null
  txHash: string
}

type WalletsResponse = {
  wallets: WalletSnapshot[]
  totals: {
    totalUsd: string
    walletCount: number
    averageBalanceUsd: string
    pendingDeposits: number
  }
  chainBalances: ChainBalance[]
  recentDeposits: DepositSummary[]
}

type ReceiveInfoResponse = {
  wallet_id: string
  addresses: Array<{
    chain: string
    address: string
    eip681_uri: string
    token: string
  }>
}

const chainVariant: Record<string, "outline"> = {
  ethereum: "outline",
  polygon: "outline",
  arbitrum: "outline",
  optimism: "outline",
  base: "outline",
  base_sepolia: "outline",
}

function parseMoney(value: string | null | undefined): number {
  if (!value) return 0
  const parsed = Number.parseFloat(value)
  return Number.isFinite(parsed) ? parsed : 0
}

function formatMoney(value: string | number | null | undefined): string {
  const amount = typeof value === "number" ? value : parseMoney(value)
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: amount >= 1000 ? 0 : 2,
    maximumFractionDigits: amount >= 1000 ? 0 : 2,
  }).format(amount)
}

function formatRelativeTime(value: string | null) {
  if (!value) return "No deposits yet"

  const deltaSeconds = Math.max(1, Math.floor((Date.now() - new Date(value).getTime()) / 1000))
  const buckets = [
    { limit: 60, divisor: 1, unit: "second" as const },
    { limit: 3600, divisor: 60, unit: "minute" as const },
    { limit: 86400, divisor: 3600, unit: "hour" as const },
  ]

  for (const bucket of buckets) {
    if (deltaSeconds < bucket.limit) {
      const amount = Math.floor(deltaSeconds / bucket.divisor)
      return `${amount} ${bucket.unit}${amount === 1 ? "" : "s"} ago`
    }
  }

  const days = Math.floor(deltaSeconds / 86400)
  return `${days} day${days === 1 ? "" : "s"} ago`
}

function formatDateTime(value: string | null) {
  if (!value) return "Unavailable"
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value))
}

function shortenAddress(value: string | null) {
  if (!value) return "Unavailable"
  if (value.length <= 14) return value
  return `${value.slice(0, 6)}...${value.slice(-4)}`
}

function normalizeChainLabel(value: string | null) {
  if (!value) return "Unknown"
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ")
}

export default function WalletsPage() {
  const [data, setData] = useState<WalletsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detailWallet, setDetailWallet] = useState<WalletSnapshot | null>(null)
  const [sheetOpen, setSheetOpen] = useState(false)
  const [receiveWallet, setReceiveWallet] = useState<WalletSnapshot | null>(null)
  const [receiveOpen, setReceiveOpen] = useState(false)
  const [receiveInfo, setReceiveInfo] = useState<ReceiveInfoResponse | null>(null)
  const [receiveLoading, setReceiveLoading] = useState(false)
  const [receiveError, setReceiveError] = useState<string | null>(null)

  async function loadWallets() {
    setLoading(true)
    setError(null)

    try {
      const response = await dashboardApiFetch<WalletsResponse>("/api/dashboard/wallets")
      setData(response)
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Failed to load wallets"
      setError(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadWallets()
  }, [])

  useEffect(() => {
    if (!receiveOpen || !receiveWallet) {
      setReceiveInfo(null)
      setReceiveError(null)
      return
    }

    const walletId = receiveWallet.walletId

    let cancelled = false

    async function loadReceiveInfo() {
      setReceiveLoading(true)
      setReceiveError(null)
      try {
        const response = await dashboardApiFetch<ReceiveInfoResponse>(
          `/api/dashboard/wallets/${walletId}/receive`,
        )
        if (!cancelled) {
          setReceiveInfo(response)
        }
      } catch (loadError) {
        const message = loadError instanceof Error ? loadError.message : "Failed to load receive addresses"
        if (!cancelled) {
          setReceiveError(message)
        }
      } finally {
        if (!cancelled) {
          setReceiveLoading(false)
        }
      }
    }

    void loadReceiveInfo()

    return () => {
      cancelled = true
    }
  }, [receiveOpen, receiveWallet])

  const stats = useMemo(() => {
    if (!data) {
      return [
        { label: "Total Balance", value: "—", icon: CurrencyDollar },
        { label: "Wallets", value: "—", icon: Wallet },
        { label: "Avg Balance", value: "—", icon: ArrowDown },
        { label: "Pending Deposits", value: "—", icon: Clock },
      ]
    }

    return [
      { label: "Total Balance", value: formatMoney(data.totals.totalUsd), icon: CurrencyDollar },
      { label: "Wallets", value: data.totals.walletCount.toString(), icon: Wallet },
      { label: "Avg Balance", value: formatMoney(data.totals.averageBalanceUsd), icon: ArrowDown },
      { label: "Pending Deposits", value: data.totals.pendingDeposits.toString(), icon: Clock },
    ]
  }, [data])

  const maxChainBalance = useMemo(() => {
    if (!data) return 0
    return data.chainBalances.reduce((max, item) => Math.max(max, parseMoney(item.amount)), 0)
  }, [data])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl md:text-2xl font-semibold tracking-tight">Wallets</h1>
        <p className="text-sm text-muted-foreground">Manage wallets and track balances across chains</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.label} size="sm">
              <CardContent className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-muted">
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{stat.label}</p>
                  <p className="text-lg font-semibold tracking-tight tabular-nums">{stat.value}</p>
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
          {loading ? (
            <div className="py-16 text-center text-sm text-muted-foreground">Loading wallets…</div>
          ) : error ? (
            <EmptyState
              icon={Wallet}
              title="Wallet data unavailable"
              description={error}
              action={() => void loadWallets()}
              actionLabel="Retry"
            />
          ) : !data || data.wallets.length === 0 ? (
            <EmptyState
              icon={Wallet}
              title="No wallets"
              description="Wallets will appear here once agents or treasury flows provision them."
            />
          ) : (
            <div className="overflow-x-auto">
            <Table className="min-w-[700px]">
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Wallet</TableHead>
                  <TableHead>Address</TableHead>
                  <TableHead>Chain</TableHead>
                  <TableHead className="text-right">Balance</TableHead>
                  <TableHead className="text-right">Pending</TableHead>
                  <TableHead>Last Activity</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.wallets.map((wallet) => (
                  <ContextMenu key={wallet.walletId}>
                    <ContextMenuTrigger render={<TableRow />}>
                      <TableCell className="pl-4">
                        <div>
                          <p className="font-medium">{wallet.name}</p>
                          <p className="text-xs text-muted-foreground">{wallet.walletId}</p>
                        </div>
                      </TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {shortenAddress(wallet.primaryAddress)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={chainVariant[wallet.primaryChain || ""] ?? "outline"}>
                          {normalizeChainLabel(wallet.primaryChain)}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {wallet.totalUsd === null ? "Unavailable" : formatMoney(wallet.totalUsd)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {wallet.pendingDeposits === 0 ? "—" : formatMoney(wallet.pendingAmountUsd)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatRelativeTime(wallet.lastActivityAt)}
                      </TableCell>
                    </ContextMenuTrigger>
                    <ContextMenuContent>
                      <ContextMenuItem
                        onClick={() => {
                          if (!wallet.primaryAddress) return
                          navigator.clipboard.writeText(wallet.primaryAddress)
                          toast.success("Wallet address copied")
                        }}
                        disabled={!wallet.primaryAddress}
                      >
                        Copy wallet address
                      </ContextMenuItem>
                      <ContextMenuSeparator />
                      <ContextMenuItem
                        onClick={() => {
                          setDetailWallet(wallet)
                          setSheetOpen(true)
                        }}
                      >
                        View details
                      </ContextMenuItem>
                      <ContextMenuItem
                        onClick={() => {
                          setReceiveWallet(wallet)
                          setReceiveOpen(true)
                        }}
                      >
                        Receive funds
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                ))}
              </TableBody>
            </Table>
            </div>
          )}
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Balance by Chain</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {!data || data.chainBalances.length === 0 ? (
              <p className="text-sm text-muted-foreground">No multi-chain balance data available.</p>
            ) : (
              data.chainBalances.map((chain) => {
                const amount = parseMoney(chain.amount)
                const percent = maxChainBalance > 0 ? Math.round((amount / maxChainBalance) * 100) : 0
                return (
                  <div key={chain.chain} className="space-y-1.5">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{normalizeChainLabel(chain.chain)}</span>
                      <span className="text-muted-foreground">{formatMoney(chain.amount)}</span>
                    </div>
                    <Progress value={percent} className="h-1" />
                  </div>
                )
              })
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Recent Deposits</CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            {!data || data.recentDeposits.length === 0 ? (
              <EmptyState
                icon={Clock}
                title="No deposits yet"
                description="Confirmed inbound deposits will appear here when the backend records them."
              />
            ) : (
              <div className="overflow-x-auto">
              <Table className="min-w-[500px]">
                <TableHeader>
                  <TableRow>
                    <TableHead className="pl-4">Wallet</TableHead>
                    <TableHead className="text-right">Amount</TableHead>
                    <TableHead>Chain</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Time</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recentDeposits.map((deposit) => (
                    <TableRow key={deposit.depositId}>
                      <TableCell className="pl-4">
                        <div>
                          <p className="font-medium">{deposit.walletName}</p>
                          <p className="text-xs text-muted-foreground">{shortenAddress(deposit.txHash)}</p>
                        </div>
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-success">
                        {formatMoney(deposit.amount)}
                      </TableCell>
                      <TableCell>
                        <Badge variant={chainVariant[deposit.chain] ?? "outline"}>
                          {normalizeChainLabel(deposit.chain)}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{deposit.status}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatRelativeTime(deposit.detectedAt)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{detailWallet?.name ?? "Wallet details"}</SheetTitle>
            <SheetDescription>Wallet metadata, balances, and operational limits</SheetDescription>
          </SheetHeader>
          {detailWallet && (
            <div className="space-y-5 px-4 pb-4">
              <div className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Wallet ID</p>
                  <p className="font-mono text-sm">{detailWallet.walletId}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Primary address</p>
                  <p className="font-mono text-sm">{detailWallet.primaryAddress ?? "Unavailable"}</p>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-muted-foreground">Provider</p>
                    <p className="text-sm">{detailWallet.provider}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Account type</p>
                    <p className="text-sm">{detailWallet.accountType}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Per-tx limit</p>
                    <p className="text-sm">{formatMoney(detailWallet.limitPerTx)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Total limit</p>
                    <p className="text-sm">{formatMoney(detailWallet.limitTotal)}</p>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Status</p>
                    <Badge variant={detailWallet.isActive ? "success" : "secondary"}>
                      {detailWallet.isActive ? "Active" : "Inactive"}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-xs text-muted-foreground">Last activity</p>
                    <p className="text-sm">{formatRelativeTime(detailWallet.lastActivityAt)}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Chain balances
                </p>
                {detailWallet.balances.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No on-chain balance snapshot available.</p>
                ) : (
                  <div className="space-y-2">
                    {detailWallet.balances.map((balance) => (
                      <div key={`${balance.chain}-${balance.token}`} className="rounded-lg border p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-sm font-medium">{normalizeChainLabel(balance.chain)}</p>
                            <p className="text-xs text-muted-foreground">{balance.token}</p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-medium">{formatMoney(balance.balance)}</p>
                            <p className="font-mono text-[11px] text-muted-foreground">
                              {shortenAddress(balance.address)}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="space-y-2">
                <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                  Lifecycle
                </p>
                <div className="rounded-lg border p-3 text-sm">
                  <p>Created: {formatDateTime(detailWallet.createdAt)}</p>
                  <p className="mt-1">Updated: {formatDateTime(detailWallet.updatedAt)}</p>
                </div>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>

      <Dialog open={receiveOpen} onOpenChange={setReceiveOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Receive funds</DialogTitle>
            <DialogDescription>
              Use a real receive address for {receiveWallet?.name}. This does not mint or fake balances.
            </DialogDescription>
          </DialogHeader>

          {receiveLoading ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Loading receive addresses…</div>
          ) : receiveError ? (
            <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive">
              {receiveError}
            </div>
          ) : !receiveInfo || receiveInfo.addresses.length === 0 ? (
            <div className="rounded-lg border p-4 text-sm text-muted-foreground">
              No receive addresses are available for this wallet.
            </div>
          ) : (
            <div className="space-y-3">
              {receiveInfo.addresses.map((addressInfo) => (
                <div key={`${addressInfo.chain}:${addressInfo.address}`} className="rounded-lg border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium">{normalizeChainLabel(addressInfo.chain)}</p>
                      <p className="text-xs text-muted-foreground">{addressInfo.token}</p>
                    </div>
                    <Badge variant="outline">{normalizeChainLabel(addressInfo.chain)}</Badge>
                  </div>
                  <p className="mt-3 break-all font-mono text-xs">{addressInfo.address}</p>
                  <div className="mt-3 flex gap-2">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(addressInfo.address)
                        toast.success("Receive address copied")
                      }}
                    >
                      <Copy className="h-3.5 w-3.5" />
                      Copy address
                    </Button>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(addressInfo.eip681_uri)
                        toast.success("Payment URI copied")
                      }}
                    >
                      Copy payment URI
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}

          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>Close</DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
