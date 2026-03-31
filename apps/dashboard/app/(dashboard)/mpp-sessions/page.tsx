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
  Users,
  CheckCircle,
  CurrencyDollar,
  Terminal,
} from "@phosphor-icons/react"

type Session = {
  id: string
  participants: number
  totalAmount: string
  chain: string
  status: "active" | "pending" | "completed" | "failed"
  created: string
  duration: string
}

const sessions: Session[] = [
  { id: "mpp_8f2a1b3c", participants: 5, totalAmount: "$24,500", chain: "Ethereum", status: "active", created: "Mar 27, 14:28", duration: "4m 12s" },
  { id: "mpp_4d7e9c1a", participants: 3, totalAmount: "$8,200", chain: "Polygon", status: "active", created: "Mar 27, 14:25", duration: "7m 30s" },
  { id: "mpp_6b3f2e8d", participants: 4, totalAmount: "$15,800", chain: "Arbitrum", status: "active", created: "Mar 27, 14:22", duration: "10m 05s" },
  { id: "mpp_1c5a7f4b", participants: 6, totalAmount: "$42,100", chain: "Ethereum", status: "pending", created: "Mar 27, 14:18", duration: "14m 22s" },
  { id: "mpp_9e2d6a8c", participants: 3, totalAmount: "$6,750", chain: "Polygon", status: "completed", created: "Mar 27, 13:45", duration: "18m 44s" },
  { id: "mpp_3a8b1f5e", participants: 4, totalAmount: "$19,300", chain: "Optimism", status: "completed", created: "Mar 27, 12:30", duration: "22m 11s" },
  { id: "mpp_7c4e2d9a", participants: 5, totalAmount: "$31,600", chain: "Ethereum", status: "completed", created: "Mar 27, 11:15", duration: "15m 38s" },
  { id: "mpp_2f6b8c3d", participants: 2, totalAmount: "$4,200", chain: "Arbitrum", status: "failed", created: "Mar 27, 10:50", duration: "8m 02s" },
]

const stats = [
  { label: "Active Sessions", value: "3", icon: Terminal },
  { label: "Completed Today", value: "12", icon: CheckCircle },
  { label: "Avg Participants", value: "4.2", icon: Users },
  { label: "Total Volume", value: "$89k", icon: CurrencyDollar },
]

const statusConfig: Record<Session["status"], { variant: "success" | "warning" | "secondary" | "destructive" }> = {
  active: { variant: "success" },
  pending: { variant: "warning" },
  completed: { variant: "secondary" },
  failed: { variant: "destructive" },
}

const chainVariant: Record<string, "default" | "secondary" | "outline"> = {
  Ethereum: "default",
  Polygon: "secondary",
  Arbitrum: "outline",
  Optimism: "secondary",
}

export default function MppSessionsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">MPP Sessions</h1>
        <p className="text-sm text-muted-foreground">Multi-party payment sessions across chains</p>
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
          <CardTitle>All Sessions</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Session ID</TableHead>
                <TableHead className="text-right">Participants</TableHead>
                <TableHead className="text-right">Total Amount</TableHead>
                <TableHead>Chain</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Duration</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {sessions.map((session) => {
                const st = statusConfig[session.status]
                return (
                  <TableRow key={session.id}>
                    <TableCell className="pl-4 font-mono text-xs">{session.id}</TableCell>
                    <TableCell className="text-right tabular-nums">
                      <Badge variant="outline">{session.participants}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium">{session.totalAmount}</TableCell>
                    <TableCell>
                      <Badge variant={chainVariant[session.chain] ?? "outline"}>{session.chain}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={st.variant}>
                        {session.status.charAt(0).toUpperCase() + session.status.slice(1)}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">{session.created}</TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">{session.duration}</TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
