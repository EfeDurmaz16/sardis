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
import {
  Stack,
  Terminal,
  Gear,
} from "@phosphor-icons/react"
import { EmptyState } from "@/components/empty-state"
import { dashboardApiFetch } from "@/utils/dashboard-client"

type EnvironmentResponse = {
  proxy: {
    baseUrl: string
    apiKeyConfigured: boolean
    browserBaseUrlConfigured: boolean
  }
  upstream: {
    lightweight: {
      status?: string
      service?: string
      version?: string
    }
    deep: {
      status?: string
      components?: Record<string, { status?: string; [key: string]: unknown }>
      critical_failures?: Array<{ component: string; detail: string }>
      non_critical_failures?: Array<{ component: string; detail: string }>
    }
  }
}

function statusColor(status: string | undefined) {
  if (status === "healthy" || status === "ready" || status === "alive") return "bg-success"
  if (status === "partial" || status === "degraded") return "bg-warning"
  if (status === "unconfigured") return "bg-muted"
  return "bg-destructive"
}

export default function EnvironmentsPage() {
  const [data, setData] = useState<EnvironmentResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function load() {
      setLoading(true)
      setError(null)
      try {
        const response = await dashboardApiFetch<EnvironmentResponse>("/api/dashboard/environments")
        if (!cancelled) {
          setData(response)
        }
      } catch (loadError) {
        if (!cancelled) {
          const message = loadError instanceof Error ? loadError.message : "Failed to load environment status"
          setError(message)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    void load()

    return () => {
      cancelled = true
    }
  }, [])

  const componentRows = useMemo(() => {
    const components = data?.upstream.deep.components || {}
    return Object.entries(components).sort(([left], [right]) => left.localeCompare(right))
  }, [data])

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Environments</h1>
        <p className="text-sm text-muted-foreground">
          Truthful dashboard proxy and upstream API status. No synthetic deploy logs are shown here.
        </p>
      </div>

      {loading ? (
        <Card>
          <CardContent className="py-16 text-center text-sm text-muted-foreground">
            Loading environment status…
          </CardContent>
        </Card>
      ) : error ? (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={Stack}
              title="Environment status unavailable"
              description={error}
            />
          </CardContent>
        </Card>
      ) : !data ? (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={Stack}
              title="No environment data"
              description="The dashboard could not resolve any proxy or upstream status."
            />
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <span className={`h-1.5 w-1.5 rounded-full ${statusColor(data.upstream.lightweight.status)}`} />
                  Upstream API
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Base URL</p>
                  <code className="text-xs font-mono text-muted-foreground">{data.proxy.baseUrl}</code>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Lightweight health</p>
                    <Badge variant="outline" className="mt-0.5 text-[10px]">
                      {data.upstream.lightweight.status || "unreachable"}
                    </Badge>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Version</p>
                    <p className="text-xs text-muted-foreground">
                      {data.upstream.lightweight.version || "Unavailable"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-muted-foreground" />
                  Deep health
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Overall status</p>
                  <Badge variant="outline" className="mt-0.5 text-[10px]">
                    {data.upstream.deep.status || "unreachable"}
                  </Badge>
                </div>
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Failures</p>
                  <p className="text-sm">
                    Critical: {data.upstream.deep.critical_failures?.length || 0}
                  </p>
                  <p className="text-sm">
                    Non-critical: {data.upstream.deep.non_critical_failures?.length || 0}
                  </p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Gear className="h-4 w-4 text-muted-foreground" />
                  Dashboard proxy
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">Server API key</p>
                  <Badge variant={data.proxy.apiKeyConfigured ? "success" : "destructive"}>
                    {data.proxy.apiKeyConfigured ? "Configured" : "Missing"}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-xs text-muted-foreground">Browser API base override</p>
                  <Badge variant={data.proxy.browserBaseUrlConfigured ? "outline" : "secondary"}>
                    {data.proxy.browserBaseUrlConfigured ? "Configured" : "Not set"}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="border-b">
              <CardTitle>Upstream Components</CardTitle>
            </CardHeader>
            <CardContent className="px-0">
              {componentRows.length === 0 ? (
                <EmptyState
                  icon={Stack}
                  title="No component details"
                  description="Deep health did not return any component map."
                />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="pl-4">Component</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Details</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {componentRows.map(([component, detail]) => (
                      <TableRow key={component}>
                        <TableCell className="pl-4 font-medium">{component}</TableCell>
                        <TableCell>
                          <Badge variant="outline">{detail.status || "unknown"}</Badge>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          <code>{JSON.stringify(detail)}</code>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
