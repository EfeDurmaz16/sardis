"use client"

import { useMemo } from "react"
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
import {
  Anchor,
  LinkSimple,
  Clock,
  CheckCircle,
  Spinner,
} from "@phosphor-icons/react"
import { useSardis } from "@/hooks/use-sardis"
import { EmptyState } from "@/components/empty-state"

type AuditAnchor = {
  id: string
  block_number: string
  chain: string
  transactions_included: number
  merkle_root: string
  timestamp: string
  verified: boolean
}

const chainVariant: Record<string, "default" | "secondary" | "outline"> = {
  Ethereum: "default",
  Polygon: "secondary",
  Arbitrum: "outline",
  Optimism: "secondary",
  Base: "outline",
}

export default function AuditAnchorsPage() {
  const { data, loading, error, refetch } = useSardis<AuditAnchor[]>("api/v2/ledger/anchors")

  const anchors = data ?? []

  const stats = useMemo(() => {
    const total = anchors.length
    const uniqueChains = new Set(anchors.map(a => a.chain)).size
    const verifiedCount = anchors.filter(a => a.verified).length
    const verificationRate = total > 0 ? Math.round((verifiedCount / total) * 100) : 0
    const lastAnchor = anchors.length > 0 ? anchors[0].timestamp : "—"
    return [
      { label: "Total Anchors", value: String(total), icon: Anchor },
      { label: "Chains Anchored", value: String(uniqueChains), icon: LinkSimple },
      { label: "Last Anchor", value: lastAnchor, icon: Clock },
      { label: "Verification Rate", value: `${verificationRate}%`, icon: CheckCircle },
    ]
  }, [anchors])

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Audit Anchors</h1>
          <p className="text-sm text-muted-foreground">Cryptographic audit trail anchored to blockchains</p>
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
          <h1 className="text-2xl font-semibold tracking-tight">Audit Anchors</h1>
          <p className="text-sm text-muted-foreground">Cryptographic audit trail anchored to blockchains</p>
        </div>
        <EmptyState
          icon={Anchor}
          title="Audit anchors unavailable"
          description={error || "Audit anchors will appear here once the ledger starts recording and anchoring transactions on-chain."}
          action={refetch}
          actionLabel="Retry"
        />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Audit Anchors</h1>
        <p className="text-sm text-muted-foreground">Cryptographic audit trail anchored to blockchains</p>
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
          <CardTitle>Anchor History</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {anchors.length === 0 ? (
            <EmptyState
              icon={Anchor}
              title="No anchors yet"
              description="Anchor records will appear here as the ledger periodically commits Merkle roots on-chain."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">Anchor ID</TableHead>
                  <TableHead>Block Number</TableHead>
                  <TableHead>Chain</TableHead>
                  <TableHead className="text-right">Txns Included</TableHead>
                  <TableHead>Merkle Root</TableHead>
                  <TableHead>Timestamp</TableHead>
                  <TableHead>Verified</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {anchors.map((anchor) => (
                  <TableRow key={anchor.id}>
                    <TableCell className="pl-4"><Badge variant="outline" className="font-mono">{anchor.id}</Badge></TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{anchor.block_number}</TableCell>
                    <TableCell>
                      <Badge variant={chainVariant[anchor.chain] ?? "outline"}>{anchor.chain}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{anchor.transactions_included}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{anchor.merkle_root}</TableCell>
                    <TableCell className="text-muted-foreground">{anchor.timestamp}</TableCell>
                    <TableCell>
                      {anchor.verified ? (
                        <CheckCircle weight="fill" className="h-4 w-4 text-success" />
                      ) : (
                        <span className="h-4 w-4 text-destructive">&#10005;</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
