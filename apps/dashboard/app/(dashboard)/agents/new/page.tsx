"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { toast } from "sonner"
import { ArrowLeft, Robot, Wallet, ShieldCheck, Lightning } from "@phosphor-icons/react"

export default function NewAgentPage() {
  const router = useRouter()

  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [chain, setChain] = useState("base")
  const [perTxLimit, setPerTxLimit] = useState("100")
  const [dailyLimit, setDailyLimit] = useState("1000")
  const [autoWallet, setAutoWallet] = useState(true)
  const [enableMandate, setEnableMandate] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  function handleCreate() {
    if (!name.trim()) { toast.error("Agent name is required"); return }
    setSubmitting(true)
    setTimeout(() => {
      toast.success(`Agent "${name}" created successfully`)
      router.push("/agents")
    }, 800)
  }

  return (
    <div className="max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Button variant="outline" size="icon" className="h-8 w-8" onClick={() => router.back()}>
          <ArrowLeft className="w-4 h-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Create Agent</h1>
          <p className="text-sm text-muted-foreground">Deploy a new AI agent with payment capabilities</p>
        </div>
      </div>

      {/* Basic Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Robot className="w-4 h-4" /> Agent Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Agent Name</label>
            <Input value={name} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setName(e.target.value)} placeholder="e.g. Infrastructure Agent" />
          </div>
          <div className="space-y-2">
            <label className="text-sm font-medium">Description</label>
            <Textarea value={description} onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setDescription(e.target.value)} placeholder="What does this agent do?" rows={3} />
          </div>
        </CardContent>
      </Card>

      {/* Wallet Config */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Wallet className="w-4 h-4" /> Wallet Configuration
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium">Deployment Chain</label>
            <Select value={chain} onValueChange={(v) => v && setChain(v)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="base">Base</SelectItem>
                <SelectItem value="polygon">Polygon</SelectItem>
                <SelectItem value="arbitrum">Arbitrum</SelectItem>
                <SelectItem value="optimism">Optimism</SelectItem>
                <SelectItem value="ethereum">Ethereum</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Auto-create wallet</p>
              <p className="text-xs text-muted-foreground">Automatically provision a USDC wallet on deployment</p>
            </div>
            <Switch checked={autoWallet} onCheckedChange={setAutoWallet} />
          </div>
        </CardContent>
      </Card>

      {/* Spending Limits */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck className="w-4 h-4" /> Spending Limits
          </CardTitle>
          <CardDescription>Set default spending constraints for this agent</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium">Enable spending mandate</p>
              <p className="text-xs text-muted-foreground">Require a mandate to authorize payments</p>
            </div>
            <Switch checked={enableMandate} onCheckedChange={setEnableMandate} />
          </div>
          {enableMandate && (
            <>
              <Separator />
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Per-transaction limit ($)</label>
                  <Input type="number" value={perTxLimit} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setPerTxLimit(e.target.value)} />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Daily limit ($)</label>
                  <Input type="number" value={dailyLimit} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDailyLimit(e.target.value)} />
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Summary + Submit */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <Lightning className="w-4 h-4" /> Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-2 mb-4">
            <Badge variant="outline">{chain}</Badge>
            {autoWallet && <Badge variant="outline">Auto-wallet</Badge>}
            {enableMandate && <Badge variant="outline">${perTxLimit}/tx</Badge>}
            {enableMandate && <Badge variant="outline">${dailyLimit}/day</Badge>}
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => router.back()}>Cancel</Button>
            <Button onClick={handleCreate} disabled={submitting}>
              {submitting ? "Creating..." : "Create Agent"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
