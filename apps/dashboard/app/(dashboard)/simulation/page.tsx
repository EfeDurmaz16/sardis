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
  CircleNotch,
} from "@phosphor-icons/react"
import { EmptyState } from "@/components/empty-state"
import { dashboardApiFetch } from "@/utils/dashboard-client"

type AgentOption = {
  agentId: string
  name: string
  walletId: string | null
}

type SimulationBootstrap = {
  agents: AgentOption[]
}

type SimulationResponse = {
  intent_id: string
  would_succeed: boolean
  failure_reasons: string[]
  policy_result?: {
    verdict?: string
    steps?: Array<{ step: string; result: string; reason?: string }>
  } | null
  compliance_result?: Record<string, unknown> | null
  cap_check?: Record<string, unknown> | null
  kill_switch_status?: Record<string, unknown> | null
}

type SimulationHistory = {
  id: string
  agent: string
  amount: string
  merchant: string
  result: "Approved" | "Blocked"
  matchedPolicies: number
  runAt: string
}

const resultConfig: Record<SimulationHistory["result"], { color: string; variant: "success" | "destructive" }> = {
  Approved: { color: "bg-success", variant: "success" },
  Blocked: { color: "bg-destructive", variant: "destructive" },
}

function formatRelativeTime(value: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "numeric",
    minute: "2-digit",
    month: "short",
    day: "numeric",
  }).format(new Date(value))
}

export default function SimulationPage() {
  const [agents, setAgents] = useState<AgentOption[]>([])
  const [loadingAgents, setLoadingAgents] = useState(true)
  const [agentError, setAgentError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState("")
  const [amount, setAmount] = useState("5000")
  const [merchant, setMerchant] = useState("AWS Services")
  const [chain, setChain] = useState("base")
  const [transactionType, setTransactionType] = useState("payment")
  const [result, setResult] = useState<SimulationResponse | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [history, setHistory] = useState<SimulationHistory[]>([])

  useEffect(() => {
    let cancelled = false

    async function loadAgents() {
      setLoadingAgents(true)
      setAgentError(null)
      try {
        const response = await dashboardApiFetch<SimulationBootstrap>("/api/dashboard/simulation")
        if (cancelled) return
        setAgents(response.agents)
        if (!selectedAgent && response.agents[0]) {
          setSelectedAgent(response.agents[0].agentId)
        }
      } catch (loadError) {
        if (cancelled) return
        const message = loadError instanceof Error ? loadError.message : "Failed to load agents"
        setAgentError(message)
      } finally {
        if (!cancelled) {
          setLoadingAgents(false)
        }
      }
    }

    void loadAgents()

    return () => {
      cancelled = true
    }
  }, [])

  const selectedAgentRecord = useMemo(
    () => agents.find((agent) => agent.agentId === selectedAgent) || null,
    [agents, selectedAgent],
  )

  async function runSimulation() {
    if (!selectedAgent) {
      setSubmitError("Select an agent before running a simulation.")
      return
    }

    setIsSubmitting(true)
    setSubmitError(null)

    try {
      const response = await dashboardApiFetch<SimulationResponse>("/api/dashboard/simulation", {
        method: "POST",
        body: JSON.stringify({
          amount,
          currency: "USDC",
          chain,
          sender_agent_id: selectedAgent,
          source: transactionType,
          recipient_address: merchant,
        }),
      })

      setResult(response)
      const nextResult: SimulationHistory["result"] = response.would_succeed ? "Approved" : "Blocked"
      setHistory((current) => [
        {
          id: response.intent_id,
          agent: selectedAgentRecord?.name || selectedAgent,
          amount: `$${Number.parseFloat(amount || "0").toLocaleString("en-US")}`,
          merchant,
          result: nextResult,
          matchedPolicies: response.policy_result?.steps?.length || 0,
          runAt: new Date().toISOString(),
        },
        ...current,
      ].slice(0, 10))
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : "Simulation failed"
      setSubmitError(message)
      setResult(null)
    } finally {
      setIsSubmitting(false)
    }
  }

  const timeline = useMemo(() => {
    if (!result) return []

    const steps = result.policy_result?.steps || []
    return [
      { step: "Simulation request received", time: "0ms", icon: Play },
      ...steps.map((entry, index) => ({
        step: `${entry.step} — ${entry.result}${entry.reason ? ` (${entry.reason})` : ""}`,
        time: `${(index + 1) * 15}ms`,
        icon: entry.result === "fail" ? Warning : Shield,
      })),
      {
        step: result.would_succeed ? "Decision: Approved" : "Decision: Blocked",
        time: `${(steps.length + 1) * 15}ms`,
        icon: result.would_succeed ? CheckCircle : Warning,
      },
    ]
  }, [result])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Simulation</h1>
        <p className="text-sm text-muted-foreground">Dry-run payment policies against the live Sardis simulation API</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Test Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {agentError && (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive">
                {agentError}
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Agent</label>
              <Select value={selectedAgent} onValueChange={(value) => value && setSelectedAgent(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={loadingAgents ? "Loading agents…" : "Select an agent"} />
                </SelectTrigger>
                <SelectContent>
                  {agents.map((agent) => (
                    <SelectItem key={agent.agentId} value={agent.agentId}>
                      {agent.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Amount</label>
              <Input type="number" min="0" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Recipient or merchant</label>
              <Input value={merchant} onChange={(event) => setMerchant(event.target.value)} />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Chain</label>
              <Select value={chain} onValueChange={(value) => value && setChain(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select chain" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="base">Base</SelectItem>
                  <SelectItem value="ethereum">Ethereum</SelectItem>
                  <SelectItem value="polygon">Polygon</SelectItem>
                  <SelectItem value="arbitrum">Arbitrum</SelectItem>
                  <SelectItem value="optimism">Optimism</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-medium text-muted-foreground">Source rail</label>
              <Select value={transactionType} onValueChange={(value) => value && setTransactionType(value)}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="a2a">A2A</SelectItem>
                  <SelectItem value="ap2">AP2</SelectItem>
                  <SelectItem value="checkout">Checkout</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Button className="w-full" onClick={() => void runSimulation()} disabled={isSubmitting || loadingAgents}>
              {isSubmitting ? (
                <CircleNotch className="h-4 w-4 animate-spin" />
              ) : (
                <Play weight="fill" />
              )}
              {isSubmitting ? "Running…" : "Run Simulation"}
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Simulation Results</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            {submitError ? (
              <div className="rounded-lg border border-destructive/20 bg-destructive/5 p-4">
                <div className="flex items-center gap-2">
                  <Warning className="h-5 w-5 text-destructive" />
                  <span className="font-semibold text-destructive">Simulation failed</span>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{submitError}</p>
              </div>
            ) : result ? (
              <>
                <div className={`rounded-lg border p-4 ${result.would_succeed ? "bg-success/10" : "bg-destructive/10"}`}>
                  <div className="flex items-center gap-2">
                    {result.would_succeed ? (
                      <CheckCircle weight="fill" className="h-5 w-5 text-success" />
                    ) : (
                      <Warning className="h-5 w-5 text-destructive" />
                    )}
                    <span className={`font-semibold ${result.would_succeed ? "text-success" : "text-destructive"}`}>
                      {result.would_succeed ? "Approved" : "Blocked"}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {result.failure_reasons.length > 0
                      ? result.failure_reasons.join(" • ")
                      : "Simulation completed without policy, compliance, or kill-switch failures."}
                  </p>
                </div>

                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-muted-foreground">Matching Policies</p>
                  <div className="space-y-2">
                    {(result.policy_result?.steps || []).length === 0 ? (
                      <p className="text-sm text-muted-foreground">No detailed policy steps were returned.</p>
                    ) : (
                      (result.policy_result?.steps || []).map((step) => (
                        <div key={step.step} className="flex items-center justify-between rounded-md border px-3 py-2">
                          <div className="flex items-center gap-2">
                            <Shield className="h-3.5 w-3.5 text-muted-foreground" />
                            <span className="text-sm">{step.step}</span>
                          </div>
                          <Badge variant={step.result === "fail" ? "destructive" : "success"}>
                            {step.result}
                          </Badge>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <Separator />

                <div className="space-y-1.5">
                  <p className="text-xs font-medium text-muted-foreground">Execution Timeline</p>
                  <div className="space-y-3">
                    {timeline.map((item, index) => {
                      const Icon = item.icon
                      return (
                        <div key={`${item.step}-${index}`} className="flex items-center gap-3">
                          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-muted">
                            <Icon className="h-3 w-3 text-muted-foreground" />
                          </div>
                          <span className="flex-1 text-sm">{item.step}</span>
                          <span className="text-xs font-mono text-muted-foreground">{item.time}</span>
                        </div>
                      )
                    })}
                  </div>
                </div>
              </>
            ) : (
              <EmptyState
                icon={Play}
                title="No simulation run yet"
                description="Run a real dry-run request to see policy, compliance, and kill-switch output."
              />
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Recent Simulations</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          {history.length === 0 ? (
            <EmptyState
              icon={Clock}
              title="No session history"
              description="Simulation history is recorded for this browser session after you run a live dry-run."
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="pl-4">ID</TableHead>
                  <TableHead>Agent</TableHead>
                  <TableHead className="text-right">Amount</TableHead>
                  <TableHead>Recipient</TableHead>
                  <TableHead>Result</TableHead>
                  <TableHead className="text-right">Matched Policies</TableHead>
                  <TableHead>Run At</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {history.map((simulation) => {
                  const config = resultConfig[simulation.result]
                  return (
                    <TableRow key={simulation.id}>
                      <TableCell className="pl-4">
                        <Badge variant="outline" className="font-mono">{simulation.id}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{simulation.agent}</TableCell>
                      <TableCell className="text-right tabular-nums">{simulation.amount}</TableCell>
                      <TableCell className="text-muted-foreground">{simulation.merchant}</TableCell>
                      <TableCell>
                        <span className="inline-flex items-center gap-1.5">
                          <span className={`h-1.5 w-1.5 rounded-full ${config.color}`} />
                          {simulation.result}
                        </span>
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {simulation.matchedPolicies}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {formatRelativeTime(simulation.runAt)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
