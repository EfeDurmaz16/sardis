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
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  PaperPlaneTilt,
  Clock,
  CircleNotch,
} from "@phosphor-icons/react"

type Endpoint = {
  method: "GET" | "POST" | "PUT" | "DELETE"
  path: string
  description: string
  auth: boolean
}

const endpoints: Endpoint[] = [
  { method: "GET", path: "/api/v1/agents", description: "List all agents", auth: true },
  { method: "POST", path: "/api/v1/agents", description: "Create a new agent", auth: true },
  { method: "GET", path: "/api/v1/transactions", description: "List transactions", auth: true },
  { method: "POST", path: "/api/v1/transactions", description: "Create a transaction", auth: true },
  { method: "GET", path: "/api/v1/policies", description: "List all policies", auth: true },
  { method: "PUT", path: "/api/v1/policies/:id", description: "Update a policy", auth: true },
  { method: "GET", path: "/api/v1/wallets", description: "List wallets", auth: true },
  { method: "DELETE", path: "/api/v1/agents/:id", description: "Delete an agent", auth: true },
]

const methodColor: Record<string, string> = {
  GET: "bg-success/10 text-success",
  POST: "bg-info/10 text-info",
  PUT: "bg-warning/10 text-warning",
  DELETE: "bg-destructive/10 text-destructive",
}

const sampleRequestBody = `{
  "name": "Payment Router Beta",
  "chain": "ethereum",
  "mandate": {
    "limit": 10000,
    "period": "daily"
  },
  "status": "active"
}`

const mockResponse = `{
  "id": "agt_1a2b3c4d5e6f",
  "name": "Payment Router Beta",
  "chain": "ethereum",
  "wallet": "0x7e5A...6b3C",
  "balance": "$0.00",
  "mandate": {
    "limit": 10000,
    "period": "daily",
    "used": 0
  },
  "status": "active",
  "created_at": "2026-03-28T10:30:00Z"
}`

export default function ApiPlaygroundPage() {
  const [loading, setLoading] = useState(false)
  const [response, setResponse] = useState<string | null>(null)
  const [statusCode, setStatusCode] = useState<string | null>(null)
  const [responseTime, setResponseTime] = useState<number | null>(null)

  function handleSend() {
    setLoading(true)
    setResponse(null)
    setStatusCode(null)
    setResponseTime(null)

    setTimeout(() => {
      setLoading(false)
      setResponse(mockResponse)
      setStatusCode("200 OK")
      setResponseTime(124)
    }, 1000)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">API Playground</h1>
        <p className="text-sm text-muted-foreground">Explore and test API endpoints interactively</p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Left Panel — Request */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Request</CardTitle>
            <CardAction>
              <Button onClick={handleSend} disabled={loading}>
                {loading ? (
                  <CircleNotch className="h-4 w-4 animate-spin" />
                ) : (
                  <PaperPlaneTilt weight="fill" />
                )}
                {loading ? "Sending..." : "Send"}
              </Button>
            </CardAction>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="flex gap-2">
              <Select items={{ GET: "GET", POST: "POST", PUT: "PUT", DELETE: "DELETE" }}>
                <SelectTrigger className="w-28">
                  <SelectValue placeholder="POST" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GET">GET</SelectItem>
                  <SelectItem value="POST">POST</SelectItem>
                  <SelectItem value="PUT">PUT</SelectItem>
                  <SelectItem value="DELETE">DELETE</SelectItem>
                </SelectContent>
              </Select>
              <Input
                className="flex-1"
                placeholder="/api/v1/agents"
                defaultValue="/api/v1/agents"
              />
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Headers</p>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Input className="flex-1" defaultValue="Authorization" readOnly />
                  <Input className="flex-1" defaultValue="Bearer demo_live_redacted_3f8a" />
                </div>
                <div className="flex gap-2">
                  <Input className="flex-1" defaultValue="Content-Type" readOnly />
                  <Input className="flex-1" defaultValue="application/json" readOnly />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Body</p>
              <pre className="rounded-lg border bg-muted/50 p-3 text-xs font-mono overflow-x-auto leading-relaxed">
                {sampleRequestBody}
              </pre>
            </div>
          </CardContent>
        </Card>

        {/* Right Panel — Response */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Response</CardTitle>
            <CardAction>
              {statusCode && (
                <div className="flex items-center gap-3">
                  <Badge variant="success">
                    {statusCode}
                  </Badge>
                  <span className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="h-3 w-3" />
                    {responseTime}ms
                  </span>
                </div>
              )}
            </CardAction>
          </CardHeader>
          <CardContent className="pt-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <CircleNotch className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : response ? (
              <pre className="rounded-lg border bg-muted/50 p-3 text-xs font-mono overflow-x-auto leading-relaxed">
                {response}
              </pre>
            ) : (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                Click Send to make a request
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* API Endpoints */}
      <Card>
        <CardHeader className="border-b">
          <CardTitle>API Endpoints</CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Method</TableHead>
                <TableHead>Endpoint</TableHead>
                <TableHead>Description</TableHead>
                <TableHead>Auth</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {endpoints.map((ep, i) => (
                <TableRow key={i}>
                  <TableCell className="pl-4">
                    <span className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-mono font-semibold ${methodColor[ep.method]}`}>
                      {ep.method}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{ep.path}</TableCell>
                  <TableCell className="text-muted-foreground">{ep.description}</TableCell>
                  <TableCell>
                    {ep.auth && (
                      <Badge variant="outline">Required</Badge>
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
