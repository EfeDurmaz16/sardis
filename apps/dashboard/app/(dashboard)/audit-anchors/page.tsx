"use client"

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
} from "@phosphor-icons/react"

type AuditAnchor = {
  id: string
  blockNumber: string
  chain: string
  transactionsIncluded: number
  merkleRoot: string
  timestamp: string
  verified: boolean
}

const anchors: AuditAnchor[] = [
  { id: "ANC-1892", blockNumber: "19,284,521", chain: "Ethereum", transactionsIncluded: 48, merkleRoot: "0x7a3b...e1f2", timestamp: "3 min ago", verified: true },
  { id: "ANC-1891", blockNumber: "54,821,003", chain: "Polygon", transactionsIncluded: 124, merkleRoot: "0x9c4d...b8a3", timestamp: "15 min ago", verified: true },
  { id: "ANC-1890", blockNumber: "182,493,201", chain: "Arbitrum", transactionsIncluded: 67, merkleRoot: "0x2e5f...d4c1", timestamp: "32 min ago", verified: true },
  { id: "ANC-1889", blockNumber: "19,284,498", chain: "Ethereum", transactionsIncluded: 51, merkleRoot: "0x6b1a...f5e8", timestamp: "1 hr ago", verified: true },
  { id: "ANC-1888", blockNumber: "112,847,332", chain: "Optimism", transactionsIncluded: 89, merkleRoot: "0x8d2c...a7b4", timestamp: "1.5 hrs ago", verified: true },
  { id: "ANC-1887", blockNumber: "3,921,847", chain: "Base", transactionsIncluded: 35, merkleRoot: "0x4f7e...c2d9", timestamp: "2 hrs ago", verified: true },
  { id: "ANC-1886", blockNumber: "54,820,891", chain: "Polygon", transactionsIncluded: 112, merkleRoot: "0x1c8a...e6f3", timestamp: "3 hrs ago", verified: true },
  { id: "ANC-1885", blockNumber: "182,492,984", chain: "Arbitrum", transactionsIncluded: 73, merkleRoot: "0x5d9b...a1c7", timestamp: "4 hrs ago", verified: true },
]

const stats = [
  { label: "Total Anchors", value: "1,892", icon: Anchor },
  { label: "Chains Anchored", value: "5", icon: LinkSimple },
  { label: "Last Anchor", value: "3m ago", icon: Clock },
  { label: "Verification Rate", value: "100%", icon: CheckCircle },
]

const chainVariant: Record<string, "default" | "secondary" | "outline"> = {
  Ethereum: "default",
  Polygon: "secondary",
  Arbitrum: "outline",
  Optimism: "secondary",
  Base: "outline",
}

export default function AuditAnchorsPage() {
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
                  <TableCell className="font-mono text-xs text-muted-foreground">{anchor.blockNumber}</TableCell>
                  <TableCell>
                    <Badge variant={chainVariant[anchor.chain] ?? "outline"}>{anchor.chain}</Badge>
                  </TableCell>
                  <TableCell className="text-right tabular-nums">{anchor.transactionsIncluded}</TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">{anchor.merkleRoot}</TableCell>
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
        </CardContent>
      </Card>
    </div>
  )
}
