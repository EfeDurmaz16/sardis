"use client"

import { useState } from "react"
import {
  Card,
  CardAction,
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
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Clock,
  CircleNotch,
  PaperPlaneTilt,
} from "@phosphor-icons/react"

type Method = "GET" | "POST" | "PUT" | "DELETE"

type Endpoint = {
  method: Method
  path: string
  description: string
  auth: boolean
}

type PlaygroundResult = {
  body: string
  statusLabel: string
  statusCode: number | null
}

const API_BASE_URL = process.env.NEXT_PUBLIC_SARDIS_API_BASE_URL ?? ""

const endpoints: Endpoint[] = [
  { method: "GET", path: "/api/v2/agents", description: "List agents", auth: true },
  { method: "GET", path: "/api/v2/transactions", description: "List transactions", auth: true },
  { method: "POST", path: "/api/v2/policies/check", description: "Dry-run a policy decision", auth: true },
  { method: "POST", path: "/api/v2/simulate", description: "Simulate a payment without executing it", auth: true },
  { method: "GET", path: "/api/v2/wallets", description: "List wallets", auth: true },
  { method: "GET", path: "/api/v2/reliability/providers", description: "Fetch provider scorecards", auth: false },
]

const methodColor: Record<Method, string> = {
  GET: "bg-success/10 text-success",
  POST: "bg-info/10 text-info",
  PUT: "bg-warning/10 text-warning",
  DELETE: "bg-destructive/10 text-destructive",
}

const defaultBodyByMethod: Record<Method, string> = {
  GET: "",
  POST: JSON.stringify(
    {
      agent_id: "agent_demo_123",
      amount: "25.00",
      currency: "USD",
      merchant_id: "merchant_demo",
    },
    null,
    2,
  ),
  PUT: JSON.stringify({ enabled: true }, null, 2),
  DELETE: "",
}

function resolveRequestUrl(path: string): string | null {
  if (/^https?:\/\//i.test(path)) {
    return path
  }

  if (!API_BASE_URL) {
    return null
  }

  const base = API_BASE_URL.endsWith("/") ? API_BASE_URL.slice(0, -1) : API_BASE_URL
  const normalizedPath = path.startsWith("/") ? path : `/${path}`
  return `${base}${normalizedPath}`
}

function formatResponseBody(payload: unknown): string {
  if (typeof payload === "string") {
    return payload
  }
  return JSON.stringify(payload, null, 2)
}

function getStatusLabel(status: number, statusText: string): string {
  return `${status} ${statusText || "Unknown"}`
}

function getStatusVariant(statusCode: number | null): "success" | "outline" | "destructive" {
  if (statusCode === null) {
    return "outline"
  }
  if (statusCode >= 200 && statusCode < 300) {
    return "success"
  }
  return "destructive"
}

export default function ApiPlaygroundPage() {
  const [method, setMethod] = useState<Method>("POST")
  const [path, setPath] = useState("/api/v2/policies/check")
  const [authHeader, setAuthHeader] = useState("")
  const [requestBody, setRequestBody] = useState(defaultBodyByMethod.POST)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<PlaygroundResult | null>(null)
  const [responseTime, setResponseTime] = useState<number | null>(null)

  async function handleSend() {
    setLoading(true)
    setResult(null)
    setResponseTime(null)

    const requestUrl = resolveRequestUrl(path)
    if (!requestUrl) {
      setLoading(false)
      setResult({
        statusLabel: "Configuration required",
        statusCode: null,
        body: JSON.stringify(
          {
            error: "dashboard_api_base_url_not_configured",
            message: "Set NEXT_PUBLIC_SARDIS_API_BASE_URL to enable live playground requests.",
            path,
          },
          null,
          2,
        ),
      })
      return
    }

    const headers: HeadersInit = {
      Accept: "application/json",
    }
    if (authHeader.trim()) {
      headers.Authorization = authHeader.trim()
    }

    let body: string | undefined
    if (method !== "GET" && requestBody.trim()) {
      headers["Content-Type"] = "application/json"
      body = requestBody
    }

    const startedAt = performance.now()

    try {
      const response = await fetch(requestUrl, {
        method,
        headers,
        body,
      })
      const elapsed = Math.round(performance.now() - startedAt)
      const rawText = await response.text()
      let formatted = rawText

      if (rawText) {
        try {
          formatted = formatResponseBody(JSON.parse(rawText))
        } catch {
          formatted = rawText
        }
      } else {
        formatted = JSON.stringify({ message: "Empty response body" }, null, 2)
      }

      setResponseTime(elapsed)
      setResult({
        statusLabel: getStatusLabel(response.status, response.statusText),
        statusCode: response.status,
        body: formatted,
      })
    } catch (error) {
      const elapsed = Math.round(performance.now() - startedAt)
      setResponseTime(elapsed)
      setResult({
        statusLabel: "Network error",
        statusCode: null,
        body: JSON.stringify(
          {
            error: "request_failed",
            message: error instanceof Error ? error.message : "Unknown fetch error",
            request_url: requestUrl,
          },
          null,
          2,
        ),
      })
    } finally {
      setLoading(false)
    }
  }

  function applyEndpoint(endpoint: Endpoint) {
    setMethod(endpoint.method)
    setPath(endpoint.path)
    setRequestBody(defaultBodyByMethod[endpoint.method])
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">API Playground</h1>
        <p className="text-sm text-muted-foreground">
          Send real requests against the configured Sardis API. No mock responses are returned here.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
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
            <div className="rounded-lg border bg-muted/40 p-3 text-xs text-muted-foreground">
              <p>
                Base URL:{" "}
                <code className="font-mono">
                  {API_BASE_URL || "NEXT_PUBLIC_SARDIS_API_BASE_URL is not set"}
                </code>
              </p>
            </div>

            <div className="flex gap-2">
              <Select
                value={method}
                onValueChange={(value) => {
                  if (!value) return
                  const nextMethod = value as Method
                  setMethod(nextMethod)
                  setRequestBody(defaultBodyByMethod[nextMethod])
                }}
              >
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
                placeholder="/api/v2/policies/check"
                value={path}
                onChange={(event) => setPath(event.target.value)}
              />
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Headers</p>
              <div className="space-y-2">
                <div className="flex gap-2">
                  <Input className="flex-1" defaultValue="Authorization" readOnly />
                  <Input
                    className="flex-1"
                    placeholder="Bearer <token>"
                    value={authHeader}
                    onChange={(event) => setAuthHeader(event.target.value)}
                  />
                </div>
                <div className="flex gap-2">
                  <Input className="flex-1" defaultValue="Content-Type" readOnly />
                  <Input
                    className="flex-1"
                    value={method === "GET" ? "Not sent for GET" : "application/json"}
                    readOnly
                  />
                </div>
              </div>
            </div>

            <div className="space-y-1.5">
              <p className="text-xs font-medium text-muted-foreground">Body</p>
              <Textarea
                className="min-h-48 font-mono text-xs leading-relaxed"
                value={requestBody}
                onChange={(event) => setRequestBody(event.target.value)}
                placeholder='{"agent_id":"agent_demo_123"}'
                disabled={method === "GET"}
              />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="border-b">
            <CardTitle>Response</CardTitle>
            <CardAction>
              {result && (
                <div className="flex items-center gap-3">
                  <Badge variant={getStatusVariant(result.statusCode)}>
                    {result.statusLabel}
                  </Badge>
                  {responseTime !== null && (
                    <span className="flex items-center gap-1 text-xs text-muted-foreground">
                      <Clock className="h-3 w-3" />
                      {responseTime}ms
                    </span>
                  )}
                </div>
              )}
            </CardAction>
          </CardHeader>
          <CardContent className="pt-4">
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <CircleNotch className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : result ? (
              <pre className="overflow-x-auto rounded-lg border bg-muted/50 p-3 text-xs leading-relaxed">
                {result.body}
              </pre>
            ) : (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                Click Send to make a live request
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Canonical Endpoints</CardTitle>
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
              {endpoints.map((endpoint) => (
                <TableRow
                  key={`${endpoint.method}:${endpoint.path}`}
                  className="cursor-pointer"
                  onClick={() => applyEndpoint(endpoint)}
                >
                  <TableCell className="pl-4">
                    <span
                      className={`inline-flex items-center rounded-md px-2 py-0.5 text-xs font-mono font-semibold ${methodColor[endpoint.method]}`}
                    >
                      {endpoint.method}
                    </span>
                  </TableCell>
                  <TableCell className="font-mono text-xs">{endpoint.path}</TableCell>
                  <TableCell className="text-muted-foreground">{endpoint.description}</TableCell>
                  <TableCell>
                    {endpoint.auth ? (
                      <Badge variant="outline">Required</Badge>
                    ) : (
                      <Badge variant="outline">Optional</Badge>
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
