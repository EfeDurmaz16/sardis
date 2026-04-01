"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import { ArrowLeft, Lightning, Robot, ShieldCheck, Wallet } from "@phosphor-icons/react"
import { AuthRequiredError, createAgent } from "@/lib/sardis-api"

export default function NewAgentPage() {
  const router = useRouter()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [preferredChain, setPreferredChain] = useState("base")
  const [perTxLimit, setPerTxLimit] = useState("100")
  const [dailyLimit, setDailyLimit] = useState("1000")
  const [autoWallet, setAutoWallet] = useState(true)
  const [enableMandate, setEnableMandate] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  async function handleCreate() {
    if (!name.trim()) {
      toast.error("Agent name is required")
      return
    }

    setSubmitting(true)

    try {
      const created = await createAgent({
        name: name.trim(),
        description: description.trim() || undefined,
        create_wallet: autoWallet,
        metadata: {
          preferred_chain: preferredChain,
        },
        spending_limits: enableMandate
          ? {
              per_transaction: perTxLimit || "0",
              daily: dailyLimit || "0",
            }
          : undefined,
      })

      toast.success(`Agent "${created.name}" created`)
      router.push("/agents")
      router.refresh()
    } catch (error) {
      if (error instanceof AuthRequiredError) {
        toast.error("Sign in to Sardis before creating agents")
      } else {
        toast.error(error instanceof Error ? error.message : "Failed to create agent")
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Create Agent</h1>
          <p className="text-sm text-muted-foreground">Create a real agent record in the canonical Sardis API.</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Robot className="h-4 w-4" /> Agent Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Agent Name</label>
            <Input value={name} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setName(event.target.value)} placeholder="e.g. Infrastructure Agent" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea value={description} onChange={(event: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(event.target.value)} placeholder="What does this agent do?" rows={3} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Wallet className="h-4 w-4" /> Wallet Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Preferred chain</label>
            <Select value={preferredChain} onValueChange={(value) => value && setPreferredChain(value)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="base">Base</SelectItem>
                <SelectItem value="polygon">Polygon</SelectItem>
                <SelectItem value="arbitrum">Arbitrum</SelectItem>
                <SelectItem value="optimism">Optimism</SelectItem>
                <SelectItem value="ethereum">Ethereum</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              Stored as agent metadata for downstream wallet setup. Actual wallet network provisioning depends on the configured backend wallet manager.
            </p>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Auto-create wallet</p>
              <p className="text-xs text-muted-foreground">Ask the API to provision a wallet when the agent is created.</p>
            </div>
            <Switch checked={autoWallet} onCheckedChange={setAutoWallet} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="h-4 w-4" /> Spending Limits
          </CardTitle>
          <CardDescription>Default spending limits sent directly to the live agent API.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Enable spending mandate</p>
              <p className="text-xs text-muted-foreground">Persist per-transaction and daily caps with the new agent.</p>
            </div>
            <Switch checked={enableMandate} onCheckedChange={setEnableMandate} />
          </div>
          {enableMandate ? (
            <>
              <Separator />
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Per-transaction limit ($)</label>
                  <Input type="number" min="0" value={perTxLimit} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setPerTxLimit(event.target.value)} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Daily limit ($)</label>
                  <Input type="number" min="0" value={dailyLimit} onChange={(event: React.ChangeEvent<HTMLInputElement>) => setDailyLimit(event.target.value)} />
                </div>
              </div>
            </>
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Lightning className="h-4 w-4" /> Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="mb-4 flex flex-wrap gap-2">
            <Badge variant="outline">{preferredChain}</Badge>
            {autoWallet ? <Badge variant="outline">Auto-wallet</Badge> : null}
            {enableMandate ? <Badge variant="outline">${perTxLimit || "0"}/tx</Badge> : null}
            {enableMandate ? <Badge variant="outline">${dailyLimit || "0"}/day</Badge> : null}
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => router.back()}>Cancel</Button>
            <Button onClick={() => void handleCreate()} disabled={submitting}>
              {submitting ? "Creating..." : "Create Agent"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
