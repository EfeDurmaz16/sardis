"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Switch } from "@/components/ui/switch"
import { Separator } from "@/components/ui/separator"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Gear, Spinner } from "@phosphor-icons/react"
import { toast } from "sonner"
import { useSardis } from "@/hooks/use-sardis"

type OrgSettings = {
  orgName: string
  timezone: string
  emailNotifications: boolean
  slackNotifications: boolean
  webhookNotifications: boolean
  twoFactorAuth: boolean
  sessionTimeout: string
  ipAllowlist: boolean
}

export default function SettingsPage() {
  const { data: settings, loading } = useSardis<OrgSettings>("api/v2/organizations/settings")

  // Organization
  const [orgName, setOrgName] = useState("")
  const [savedOrgName, setSavedOrgName] = useState("")
  const [timezone, setTimezone] = useState("utc")
  const [savedTimezone, setSavedTimezone] = useState("utc")

  // Notifications
  const [emailNotif, setEmailNotif] = useState(true)
  const [savedEmailNotif, setSavedEmailNotif] = useState(true)
  const [slackNotif, setSlackNotif] = useState(true)
  const [savedSlackNotif, setSavedSlackNotif] = useState(true)
  const [webhookNotif, setWebhookNotif] = useState(false)
  const [savedWebhookNotif, setSavedWebhookNotif] = useState(false)

  // Security
  const [twoFa, setTwoFa] = useState(true)
  const [savedTwoFa, setSavedTwoFa] = useState(true)
  const [sessionTimeout, setSessionTimeout] = useState("30")
  const [savedSessionTimeout, setSavedSessionTimeout] = useState("30")
  const [ipAllowlist, setIpAllowlist] = useState(false)
  const [savedIpAllowlist, setSavedIpAllowlist] = useState(false)

  // Hydrate from API data
  useEffect(() => {
    if (settings) {
      setOrgName(settings.orgName ?? "")
      setSavedOrgName(settings.orgName ?? "")
      setTimezone(settings.timezone ?? "utc")
      setSavedTimezone(settings.timezone ?? "utc")
      setEmailNotif(settings.emailNotifications ?? true)
      setSavedEmailNotif(settings.emailNotifications ?? true)
      setSlackNotif(settings.slackNotifications ?? true)
      setSavedSlackNotif(settings.slackNotifications ?? true)
      setWebhookNotif(settings.webhookNotifications ?? false)
      setSavedWebhookNotif(settings.webhookNotifications ?? false)
      setTwoFa(settings.twoFactorAuth ?? true)
      setSavedTwoFa(settings.twoFactorAuth ?? true)
      setSessionTimeout(settings.sessionTimeout ?? "30")
      setSavedSessionTimeout(settings.sessionTimeout ?? "30")
      setIpAllowlist(settings.ipAllowlist ?? false)
      setSavedIpAllowlist(settings.ipAllowlist ?? false)
    }
  }, [settings])

  const hasChanges =
    orgName !== savedOrgName ||
    timezone !== savedTimezone ||
    emailNotif !== savedEmailNotif ||
    slackNotif !== savedSlackNotif ||
    webhookNotif !== savedWebhookNotif ||
    twoFa !== savedTwoFa ||
    sessionTimeout !== savedSessionTimeout ||
    ipAllowlist !== savedIpAllowlist

  function handleSave() {
    setSavedOrgName(orgName)
    setSavedTimezone(timezone)
    setSavedEmailNotif(emailNotif)
    setSavedSlackNotif(slackNotif)
    setSavedWebhookNotif(webhookNotif)
    setSavedTwoFa(twoFa)
    setSavedSessionTimeout(sessionTimeout)
    setSavedIpAllowlist(ipAllowlist)
    toast.success("Settings saved locally. API sync coming soon.")
  }

  if (loading) {
    return (
      <div className="space-y-6 max-w-3xl">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="text-sm text-muted-foreground">Manage your organization settings and preferences</p>
        </div>
        <div className="flex items-center justify-center py-16">
          <Spinner className="w-5 h-5 animate-spin text-muted-foreground" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="text-sm text-muted-foreground">
          Manage your organization settings and preferences
        </p>
      </div>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Organization</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <label className="text-sm font-medium">Organization Name</label>
              <Input value={orgName} onChange={(e) => setOrgName(e.target.value)} placeholder="Organization name" />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Timezone</label>
              <Select value={timezone} onValueChange={(v) => { if (v) setTimezone(v) }} items={{ utc: "UTC (Coordinated Universal Time)", est: "EST (Eastern Standard Time)", pst: "PST (Pacific Standard Time)", cet: "CET (Central European Time)", jst: "JST (Japan Standard Time)" }}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="UTC (Coordinated Universal Time)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="utc">UTC (Coordinated Universal Time)</SelectItem>
                  <SelectItem value="est">EST (Eastern Standard Time)</SelectItem>
                  <SelectItem value="pst">PST (Pacific Standard Time)</SelectItem>
                  <SelectItem value="cet">CET (Central European Time)</SelectItem>
                  <SelectItem value="jst">JST (Japan Standard Time)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Notifications</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">Email Notifications</p>
              <p className="text-xs text-muted-foreground">
                Receive alerts and updates via email
              </p>
            </div>
            <Switch checked={emailNotif} onCheckedChange={setEmailNotif} />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">Slack Notifications</p>
              <p className="text-xs text-muted-foreground">
                Send notifications to your Slack workspace
              </p>
            </div>
            <Switch checked={slackNotif} onCheckedChange={setSlackNotif} />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">Webhook Notifications</p>
              <p className="text-xs text-muted-foreground">
                Push events to your webhook endpoints
              </p>
            </div>
            <Switch checked={webhookNotif} onCheckedChange={setWebhookNotif} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b">
          <CardTitle>Security</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">Two-Factor Authentication</p>
              <p className="text-xs text-muted-foreground">
                Require 2FA for all team members
              </p>
            </div>
            <Switch checked={twoFa} onCheckedChange={setTwoFa} />
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">Session Timeout</p>
              <p className="text-xs text-muted-foreground">
                Automatically log out inactive sessions
              </p>
            </div>
            <Select value={sessionTimeout} onValueChange={(v) => { if (v) setSessionTimeout(v) }} items={{ "15": "15 minutes", "30": "30 minutes", "60": "1 hour", "120": "2 hours", "480": "8 hours" }}>
              <SelectTrigger className="w-36 shrink-0">
                <SelectValue placeholder="30 minutes" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="15">15 minutes</SelectItem>
                <SelectItem value="30">30 minutes</SelectItem>
                <SelectItem value="60">1 hour</SelectItem>
                <SelectItem value="120">2 hours</SelectItem>
                <SelectItem value="480">8 hours</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Separator />
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-sm font-medium">IP Allowlist</p>
              <p className="text-xs text-muted-foreground">
                Restrict access to specific IP addresses
              </p>
            </div>
            <Switch checked={ipAllowlist} onCheckedChange={setIpAllowlist} />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-2">
        {hasChanges && (
          <Button variant="outline" onClick={() => {
            setOrgName(savedOrgName)
            setTimezone(savedTimezone)
            setEmailNotif(savedEmailNotif)
            setSlackNotif(savedSlackNotif)
            setWebhookNotif(savedWebhookNotif)
            setTwoFa(savedTwoFa)
            setSessionTimeout(savedSessionTimeout)
            setIpAllowlist(savedIpAllowlist)
          }}>Discard Changes</Button>
        )}
        <Button onClick={handleSave} disabled={!hasChanges}>Save Changes</Button>
      </div>
    </div>
  )
}
