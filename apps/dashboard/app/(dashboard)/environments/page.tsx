"use client"

import { useState } from "react"
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
import { Switch } from "@/components/ui/switch"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "@/components/ui/dialog"
import {
  Stack,
  Terminal,
  Gear,
} from "@phosphor-icons/react"

type Environment = {
  name: string
  status: "Running" | "Deploying" | "Stopped"
  apiUrl: string
  version: string
  lastDeploy: string
}

const environments: Environment[] = [
  {
    name: "Sandbox",
    status: "Running",
    apiUrl: "https://sandbox.sardis.io/v1",
    version: "v2.4.1",
    lastDeploy: "Mar 25, 2026 14:32 UTC",
  },
  {
    name: "Staging",
    status: "Running",
    apiUrl: "https://staging.sardis.io/v1",
    version: "v2.5.0-rc.2",
    lastDeploy: "Mar 26, 2026 09:15 UTC",
  },
  {
    name: "Production",
    status: "Running",
    apiUrl: "https://api.sardis.io/v1",
    version: "v2.4.1",
    lastDeploy: "Mar 22, 2026 18:00 UTC",
  },
]

const statusDot: Record<string, string> = {
  Running: "bg-success",
  Deploying: "bg-warning",
  Stopped: "bg-destructive",
}

type EnvVar = {
  key: string
  value: string
  environment: string
  lastModified: string
}

const envVars: EnvVar[] = [
  { key: "DATABASE_URL", value: "••••••••••••", environment: "Production", lastModified: "Mar 15, 2026" },
  { key: "REDIS_URL", value: "••••••••••••", environment: "Production", lastModified: "Mar 15, 2026" },
  { key: "STRIPE_SECRET_KEY", value: "••••••••••••", environment: "Production", lastModified: "Feb 28, 2026" },
  { key: "WEBHOOK_SECRET", value: "••••••••••••", environment: "Staging", lastModified: "Mar 20, 2026" },
  { key: "JWT_SECRET", value: "••••••••••••", environment: "Production", lastModified: "Jan 10, 2026" },
  { key: "SENTRY_DSN", value: "••••••••••••", environment: "Sandbox", lastModified: "Mar 1, 2026" },
]

const envBadgeVariant: Record<string, "default" | "secondary" | "outline"> = {
  Production: "outline",
  Staging: "outline",
  Sandbox: "outline",
}

const mockLogs: Record<string, string[]> = {
  Sandbox: [
    "[2026-03-28 09:01:12] INFO  Server started on port 3000",
    "[2026-03-28 09:02:34] INFO  Connected to database successfully",
    "[2026-03-28 09:05:18] WARN  Rate limit approaching for key demo_test_***",
    "[2026-03-28 09:08:42] INFO  Webhook delivered to https://hooks.example.com",
    "[2026-03-28 09:12:01] INFO  Health check passed - all systems operational",
  ],
  Staging: [
    "[2026-03-28 08:15:03] INFO  Deployment v2.5.0-rc.2 started",
    "[2026-03-28 08:15:45] INFO  Database migration completed (3 pending)",
    "[2026-03-28 08:16:12] INFO  Service mesh updated - 4 pods ready",
    "[2026-03-28 08:20:33] WARN  Memory usage at 72% on worker-2",
    "[2026-03-28 08:25:00] INFO  Deployment v2.5.0-rc.2 completed successfully",
  ],
  Production: [
    "[2026-03-28 07:00:00] INFO  Daily backup completed - 2.4 GB archived",
    "[2026-03-28 07:15:22] INFO  SSL certificate renewed for api.sardis.io",
    "[2026-03-28 08:00:01] INFO  Scheduled job: transaction reconciliation started",
    "[2026-03-28 08:12:44] INFO  Reconciliation completed - 0 discrepancies found",
    "[2026-03-28 09:00:00] INFO  Health check passed - latency p99: 42ms",
  ],
}

export default function EnvironmentsPage() {
  const [logsDialogOpen, setLogsDialogOpen] = useState(false)
  const [configDialogOpen, setConfigDialogOpen] = useState(false)
  const [selectedEnv, setSelectedEnv] = useState<Environment | null>(null)

  const [configApiUrl, setConfigApiUrl] = useState("")
  const [configTimeout, setConfigTimeout] = useState("30")
  const [configDebug, setConfigDebug] = useState(false)

  function openLogs(env: Environment) {
    setSelectedEnv(env)
    setLogsDialogOpen(true)
  }

  function openConfigure(env: Environment) {
    setSelectedEnv(env)
    setConfigApiUrl(env.apiUrl)
    setConfigTimeout("30")
    setConfigDebug(false)
    setConfigDialogOpen(true)
  }

  function handleSaveConfig() {
    setConfigDialogOpen(false)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Environments</h1>
        <p className="text-sm text-muted-foreground">
          Manage your deployment environments and configuration
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {environments.map((env) => (
          <Card key={env.name}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <span className={`h-1.5 w-1.5 rounded-full ${statusDot[env.status]}`} />
                {env.name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <div>
                  <p className="text-xs text-muted-foreground">API URL</p>
                  <code className="text-xs font-mono text-muted-foreground">{env.apiUrl}</code>
                </div>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs text-muted-foreground">Version</p>
                    <Badge variant="outline" className="mt-0.5 text-[10px]">
                      {env.version}
                    </Badge>
                  </div>
                  <div className="text-right">
                    <p className="text-xs text-muted-foreground">Last Deploy</p>
                    <p className="text-xs text-muted-foreground">{env.lastDeploy}</p>
                  </div>
                </div>
              </div>
              <div className="flex gap-2 pt-1">
                <Button variant="outline" size="sm" className="flex-1" onClick={() => openLogs(env)}>
                  <Terminal className="h-3.5 w-3.5" />
                  View Logs
                </Button>
                <Button variant="outline" size="sm" className="flex-1" onClick={() => openConfigure(env)}>
                  <Gear className="h-3.5 w-3.5" />
                  Configure
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* View Logs Dialog */}
      <Dialog open={logsDialogOpen} onOpenChange={setLogsDialogOpen}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>Logs - {selectedEnv?.name}</DialogTitle>
            <DialogDescription>
              Recent log entries for the {selectedEnv?.name} environment.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-lg border bg-muted/50 p-3 max-h-64 overflow-y-auto">
            <pre className="text-xs font-mono leading-relaxed whitespace-pre-wrap">
              {selectedEnv && (mockLogs[selectedEnv.name] ?? []).join("\n")}
            </pre>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              Close
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Configure Dialog */}
      <Dialog open={configDialogOpen} onOpenChange={setConfigDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Configure - {selectedEnv?.name}</DialogTitle>
            <DialogDescription>
              Update the configuration for the {selectedEnv?.name} environment.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">API URL</label>
              <Input
                value={configApiUrl}
                onChange={(e) => setConfigApiUrl(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Timeout (seconds)</label>
              <Input
                type="number"
                value={configTimeout}
                onChange={(e) => setConfigTimeout(e.target.value)}
              />
            </div>
            <div className="flex items-center justify-between">
              <label className="text-sm font-medium">Debug Mode</label>
              <Switch checked={configDebug} onCheckedChange={setConfigDebug} size="sm" />
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              Cancel
            </DialogClose>
            <Button onClick={handleSaveConfig}>Save Configuration</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Card>
        <CardHeader className="border-b">
          <CardTitle className="flex items-center gap-2">
            <Stack className="h-4 w-4 text-muted-foreground" />
            Environment Variables
          </CardTitle>
        </CardHeader>
        <CardContent className="px-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="pl-4">Key</TableHead>
                <TableHead>Value</TableHead>
                <TableHead>Environment</TableHead>
                <TableHead>Last Modified</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {envVars.map((v, i) => (
                <TableRow key={i}>
                  <TableCell className="pl-4">
                    <code className="font-mono text-xs font-medium">{v.key}</code>
                  </TableCell>
                  <TableCell>
                    <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground">
                      {v.value}
                    </code>
                  </TableCell>
                  <TableCell>
                    <Badge variant={envBadgeVariant[v.environment] ?? "outline"}>
                      {v.environment}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{v.lastModified}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  )
}
