"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Fingerprint, Key, Trash2, Pencil, Plus, Shield, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { authClient } from "@/lib/auth-client"

type Passkey = {
  id: string
  name: string | null
  credentialID: string
  deviceType: string
  backedUp: boolean
  createdAt: string
  transports: string[] | null
}

export default function SecuritySettingsPage() {
  const [passkeys, setPasskeys] = useState<Passkey[]>([])
  const [loading, setLoading] = useState(true)

  // Add passkey dialog
  const [addOpen, setAddOpen] = useState(false)
  const [addName, setAddName] = useState("")
  const [adding, setAdding] = useState(false)

  // Rename dialog
  const [renameOpen, setRenameOpen] = useState(false)
  const [renameId, setRenameId] = useState<string | null>(null)
  const [renameName, setRenameName] = useState("")
  const [renaming, setRenaming] = useState(false)

  // Delete dialog
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [deleteName, setDeleteName] = useState("")
  const [deleting, setDeleting] = useState(false)

  const loadPasskeys = useCallback(async () => {
    try {
      const { data, error } = await authClient.passkey.listUserPasskeys()
      if (error) {
        console.error("Failed to load passkeys:", error)
        return
      }
      if (data) setPasskeys(data as Passkey[])
    } catch (err) {
      console.error("Failed to load passkeys:", err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPasskeys()
  }, [loadPasskeys])

  async function handleAdd() {
    setAdding(true)
    try {
      const { error } = await authClient.passkey.addPasskey({
        name: addName.trim() || undefined,
      })
      if (error) {
        toast.error(error.message || "Failed to add passkey")
        return
      }
      toast.success("Passkey added successfully")
      setAddOpen(false)
      setAddName("")
      await loadPasskeys()
    } catch (err) {
      toast.error("Failed to add passkey. Make sure your device supports passkeys.")
    } finally {
      setAdding(false)
    }
  }

  async function handleRename() {
    if (!renameId || !renameName.trim()) return
    setRenaming(true)
    try {
      const { error } = await authClient.passkey.updatePasskey({
        id: renameId,
        name: renameName.trim(),
      })
      if (error) {
        toast.error(error.message || "Failed to rename passkey")
        return
      }
      toast.success("Passkey renamed")
      setRenameOpen(false)
      setRenameId(null)
      setRenameName("")
      await loadPasskeys()
    } catch (err) {
      toast.error("Failed to rename passkey")
    } finally {
      setRenaming(false)
    }
  }

  async function handleDelete() {
    if (!deleteId) return
    setDeleting(true)
    try {
      const { error } = await authClient.passkey.deletePasskey({
        id: deleteId,
      })
      if (error) {
        toast.error(error.message || "Failed to delete passkey")
        return
      }
      toast.success("Passkey deleted")
      setDeleteOpen(false)
      setDeleteId(null)
      setDeleteName("")
      await loadPasskeys()
    } catch (err) {
      toast.error("Failed to delete passkey")
    } finally {
      setDeleting(false)
    }
  }

  function openRenameDialog(passkey: Passkey) {
    setRenameId(passkey.id)
    setRenameName(passkey.name || "")
    setRenameOpen(true)
  }

  function openDeleteDialog(passkey: Passkey) {
    setDeleteId(passkey.id)
    setDeleteName(passkey.name || "Unnamed passkey")
    setDeleteOpen(true)
  }

  function formatDate(dateStr: string) {
    try {
      return new Date(dateStr).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Security</h1>
        <p className="text-sm text-muted-foreground">
          Manage passkeys and authentication methods for your account
        </p>
      </div>

      <Card>
        <CardHeader className="border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-muted-foreground" />
              <CardTitle>Passkeys</CardTitle>
            </div>
            {passkeys.length > 0 && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => setAddOpen(true)}
              >
                <Plus className="w-3.5 h-3.5" />
                Add passkey
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent className="pt-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
            </div>
          ) : passkeys.length === 0 ? (
            /* Empty state */
            <div className="flex flex-col items-center text-center py-12 px-4">
              <div className="rounded-full bg-muted p-3 mb-4">
                <Fingerprint className="w-6 h-6 text-muted-foreground" />
              </div>
              <h3 className="text-sm font-medium mb-1">No passkeys registered</h3>
              <p className="text-xs text-muted-foreground max-w-sm mb-6">
                Passkeys let you sign in with biometrics or a security key instead of a password.
                They are phishing-resistant and work across your devices.
              </p>
              <Button onClick={() => setAddOpen(true)}>
                <Plus className="w-3.5 h-3.5" />
                Add your first passkey
              </Button>
            </div>
          ) : (
            /* Passkey list */
            <div className="space-y-0">
              {passkeys.map((pk, idx) => (
                <div key={pk.id}>
                  {idx > 0 && <Separator className="my-3" />}
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="rounded-md bg-muted p-2 mt-0.5">
                        <Key className="w-3.5 h-3.5 text-muted-foreground" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">
                          {pk.name || "Unnamed passkey"}
                        </p>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <Badge variant="outline">
                            {pk.deviceType === "singleDevice"
                              ? "Platform"
                              : pk.deviceType === "multiDevice"
                                ? "Cross-platform"
                                : pk.deviceType}
                          </Badge>
                          {pk.backedUp && (
                            <Badge variant="outline">
                              Synced
                            </Badge>
                          )}
                        </div>
                        <p className="text-xs text-muted-foreground mt-1.5">
                          Added {formatDate(pk.createdAt)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => openRenameDialog(pk)}
                        title="Rename"
                      >
                        <Pencil className="w-3.5 h-3.5" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => openDeleteDialog(pk)}
                        title="Delete"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Add Passkey Dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add passkey</DialogTitle>
            <DialogDescription>
              Register a new passkey for passwordless sign-in.
              You can optionally give it a name to identify it later.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="passkey-name">
              Name (optional)
            </label>
            <Input
              id="passkey-name"
              value={addName}
              onChange={(e) => setAddName(e.target.value)}
              placeholder="e.g. MacBook Pro, iPhone"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleAdd()
              }}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={adding}>
              Cancel
            </Button>
            <Button onClick={handleAdd} disabled={adding}>
              {adding && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Register passkey
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Rename Passkey Dialog */}
      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rename passkey</DialogTitle>
            <DialogDescription>
              Give this passkey a new name to help identify it.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="rename-input">
              Name
            </label>
            <Input
              id="rename-input"
              value={renameName}
              onChange={(e) => setRenameName(e.target.value)}
              placeholder="Enter a name"
              onKeyDown={(e) => {
                if (e.key === "Enter") handleRename()
              }}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameOpen(false)} disabled={renaming}>
              Cancel
            </Button>
            <Button onClick={handleRename} disabled={renaming || !renameName.trim()}>
              {renaming && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete passkey</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &ldquo;{deleteName}&rdquo;?
              You will no longer be able to sign in with this passkey.
              This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteOpen(false)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
