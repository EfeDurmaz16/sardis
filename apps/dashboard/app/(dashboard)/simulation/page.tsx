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
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Separator } from "@/components/ui/separator"
import {
  Play,
  CheckCircle,
  Warning,
  Clock,
  Shield,
  ArrowRight,
} from "@phosphor-icons/react"

type SimulationHistory = {
  id: string
  agent: string
  amount: string
  merchant: string
  result: "Approved" | "Blocked" | "Pending"
  matchedPolicies: number
  runAt: string
}

const recentSimulations: SimulationHistory[] = [
  { id: "SIM-001", agent: "Payment Router Alpha", amount: "$4,200", merchant: "AWS Services", result: "Approved", matchedPolicies: 3, runAt: "10 min ago" },
  { id: "SIM-002", agent: "Vendor Pay Agent", amount: "$12,500", merchant: "Acme Corp", result: "Blocked", matchedPolicies: 5, runAt: "25 min ago" },
  { id: "SIM-003", agent: "Treasury Sweep Bot", amount: "$850", merchant: "GitHub", result: "Approved", matchedPolicies: 2, runAt: "1 hr ago" },
  { id: "SIM-004", agent: "Expense Tracker v2", amount: "$7,800", merchant: "Unknown Vendor", result: "Blocked", matchedPolicies: 4, runAt: "2 hrs ago" },
  { id: "SIM-005", agent: "Payroll Distributor", amount: "$2,100", merchant: "Stripe", result: "Approved", matchedPolicies: 2, runAt: "3 hrs ago" },
]

const resultConfig: Record<SimulationHistory["result"], { color: string; variant: "success" | "destructive" | "warning" }> = {
  Approved: { color: "bg-success", variant: "success" },
  Blocked: { color: "bg-destructive", variant: "destructive" },
  Pending: { color: "bg-warning", variant: "warning" },
}

export default function SimulationPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Simulation</h1>
        <p className="text-sm text-muted-foreground">Test policies against simulated transactions</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Panel — Test Configuration */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Test Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Agent</label>
              <Select items={{ "payment-router": "Payment Router Alpha", "vendor-pay": "Vendor Pay Agent", "treasury-sweep": "Treasury Sweep Bot", "expense-tracker": "Expense Tracker v2", payroll: "Payroll Distributor" }}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select an agent" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="payment-router">Payment Router Alpha</SelectItem>
                  <SelectItem value="vendor-pay">Vendor Pay Agent</SelectItem>
                  <SelectItem value="treasury-sweep">Treasury Sweep Bot</SelectItem>
                  <SelectItem value="expense-tracker">Expense Tracker v2</SelectItem>
                  <SelectItem value="payroll">Payroll Distributor</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Amount</label>
              <Input type="text" placeholder="$5,000" defaultValue="$5,000" />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Merchant</label>
              <Input type="text" placeholder="Enter merchant name" defaultValue="AWS Services" />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Chain</label>
              <Select items={{ ethereum: "Ethereum", polygon: "Polygon", arbitrum: "Arbitrum", optimism: "Optimism" }}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select chain" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ethereum">Ethereum</SelectItem>
                  <SelectItem value="polygon">Polygon</SelectItem>
                  <SelectItem value="arbitrum">Arbitrum</SelectItem>
                  <SelectItem value="optimism">Optimism</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Transaction Type</label>
              <Select items={{ payment: "Payment", transfer: "Transfer", withdrawal: "Withdrawal", swap: "Swap" }}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="payment">Payment</SelectItem>
                  <SelectItem value="transfer">Transfer</SelectItem>
                  <SelectItem value="withdrawal">Withdrawal</SelectItem>
                  <SelectItem value="swap">Swap</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button className="w-full">
              <Play weight="fill" />
              Run Simulation
            </Button>
          </CardContent>
        </Card>

        {/* Right Panel — Simulation Results */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Simulation Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {/* Decision */}
            <div className="rounded-lg border bg-success/10 p-4">
              <div className="flex items-center gap-2">
                <CheckCircle weight="fill" className="h-5 w-5 text-success" />
                <span className="font-semibold text-success">Approved</span>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                Transaction meets all policy requirements. Amount is within agent spending limits and merchant is whitelisted.
              </p>
            </div>

            {/* Matching Policies */}
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Matching Policies</p>
              <div className="space-y-2">
                {[
                  { name: "Default Spending Limit", result: "Pass" },
                  { name: "AML Compliance Check", result: "Pass" },
                  { name: "Cross-chain Routing Policy", result: "Pass" },
                ].map((p) => (
                  <div key={p.name} className="flex items-center justify-between rounded-md border px-3 py-2">
                    <div className="flex items-center gap-2">
                      <Shield className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-sm">{p.name}</span>
                    </div>
                    <Badge variant="success">{p.result}</Badge>
                  </div>
                ))}
              </div>
            </div>

            <Separator />

            {/* Execution Timeline */}
            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Execution Timeline</p>
              <div className="space-y-3">
                {[
                  { step: "Policy evaluation started", time: "0ms", icon: Play },
                  { step: "Spending limit check", time: "12ms", icon: Shield },
                  { step: "Compliance verification", time: "45ms", icon: CheckCircle },
                  { step: "Routing policy applied", time: "62ms", icon: ArrowRight },
                  { step: "Decision: Approved", time: "78ms", icon: CheckCircle },
                ].map((item, i) => {
                  const Ico = item.icon
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted">
                        <Ico className="h-3 w-3 text-muted-foreground" />
                      </div>
                      <span className="flex-1 text-sm">{item.step}</span>
                      <span className="text-xs font-mono text-muted-foreground">{item.time}</span>
                    </div>
                  )
                })}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Simulations */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle>Recent Simulations</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">ID</TableHead>
                <TableHead>Agent</TableHead>
                <TableHead className="text-right">Amount</TableHead>
                <TableHead>Merchant</TableHead>
                <TableHead>Result</TableHead>
                <TableHead className="text-right">Matched Policies</TableHead>
                <TableHead>Run At</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {recentSimulations.map((sim) => {
                const rc = resultConfig[sim.result]
                return (
                  <TableRow key={sim.id}>
                    <TableCell className="pl-4">
                      <Badge variant="outline" className="font-mono">{sim.id}</Badge>
                    </TableCell>
                    <TableCell className="font-medium">{sim.agent}</TableCell>
                    <TableCell className="text-right tabular-nums">{sim.amount}</TableCell>
                    <TableCell className="text-muted-foreground">{sim.merchant}</TableCell>
                    <TableCell>
                      <span className="inline-flex items-center gap-1.5">
                        <span className={`h-1.5 w-1.5 rounded-full ${rc.color}`} />
                        {sim.result}
                      </span>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-muted-foreground">{sim.matchedPolicies}</TableCell>
                    <TableCell className="text-muted-foreground">{sim.runAt}</TableCell>
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
