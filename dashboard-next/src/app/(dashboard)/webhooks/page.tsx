"use client";
import { useState } from 'react'
import { Plus, Webhook, Trash2, CheckCircle, XCircle, Play } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'
import { useWebhooks, useCreateWebhook, useDeleteWebhook } from '@/hooks/useApi'
import type { WebhookSubscription } from '@/types'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { ContextMenu, ContextMenuContent, ContextMenuItem, ContextMenuTrigger, ContextMenuSeparator } from "@/components/ui/context-menu"

const availableEvents = [
  'payment.completed',
  'payment.failed',
  'payment.initiated',
  'wallet.created',
  'wallet.funded',
  'limit.exceeded',
  'risk.alert',
]

export default function WebhooksPage() {
  const { data: webhooks = [], isLoading } = useWebhooks()
  const createWebhook = useCreateWebhook()
  const deleteWebhook = useDeleteWebhook()
  const [showCreate, setShowCreate] = useState(false)
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Webhooks</h1>
          <p className="text-gray-400 mt-1">
            Manage event subscriptions
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-sardis-500 text-white font-medium rounded-lg hover:bg-sardis-400 transition-colors glow-green-hover"
        >
          <Plus className="w-5 h-5" />
          Add Webhook
        </button>
      </div>
      
      {/* Webhooks List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-6 animate-pulse">
              <div className="h-4 bg-dark-100 rounded w-1/3 mb-2" />
              <div className="h-3 bg-dark-100 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : webhooks.length === 0 ? (
        <div className="card p-12 text-center">
          <Webhook className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-white mb-2">No webhooks configured</h3>
          <p className="text-gray-400 mb-4">
            Add a webhook to receive real-time event notifications
          </p>
          <button
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-sardis-500/10 text-sardis-400 rounded-lg hover:bg-sardis-500/20 transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add Webhook
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {webhooks.map((webhook) => (
            <WebhookCard
              key={webhook.subscription_id}
              webhook={webhook}
              onDelete={() => deleteWebhook.mutate(webhook.subscription_id)}
            />
          ))}
        </div>
      )}
      
      {/* Create Modal */}
      <CreateWebhookModal
        open={showCreate}
        onOpenChange={setShowCreate}
        onSubmit={async (data) => {
          await createWebhook.mutateAsync(data)
          setShowCreate(false)
        }}
        isLoading={createWebhook.isPending}
      />
    </div>
  )
}

function WebhookCard({
  webhook,
  onDelete
}: {
  webhook: WebhookSubscription
  onDelete: () => void
}) {
  return (
    <ContextMenu>
      <ContextMenuTrigger className="block">
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={clsx(
            'w-10 h-10 rounded-lg flex items-center justify-center',
            webhook.is_active ? 'bg-green-500/10' : 'bg-gray-500/10'
          )}>
            <Webhook className={clsx(
              'w-5 h-5',
              webhook.is_active ? 'text-green-500' : 'text-gray-500'
            )} />
          </div>
          <div>
            <p className="text-sm font-mono text-white">{webhook.url}</p>
            <p className="text-xs text-gray-500">
              ID: {webhook.subscription_id}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={clsx(
            'px-2 py-1 rounded text-xs font-medium',
            webhook.is_active
              ? 'bg-green-500/10 text-green-500'
              : 'bg-gray-500/10 text-gray-500'
          )}>
            {webhook.is_active ? 'Active' : 'Inactive'}
          </span>
        </div>
      </div>
      
      {/* Events */}
      <div className="flex flex-wrap gap-2 mb-4">
        {webhook.events?.map((event: string) => (
          <span
            key={event}
            className="px-2 py-1 bg-dark-100 rounded text-xs text-gray-400"
          >
            {event}
          </span>
        ))}
      </div>
      
      {/* Stats */}
      <div className="flex items-center justify-between pt-4 border-t border-dark-100">
        <div className="flex items-center gap-6 text-sm">
          <div className="flex items-center gap-2 text-gray-400">
            <CheckCircle className="w-4 h-4 text-green-500" />
            <span>{webhook.successful_deliveries || 0} delivered</span>
          </div>
          {(webhook.failed_attempts || 0) > 0 && (
            <div className="flex items-center gap-2 text-gray-400">
              <XCircle className="w-4 h-4 text-red-500" />
              <span>{webhook.failed_attempts || 0} failed</span>
            </div>
          )}
          {(webhook.last_triggered_at || webhook.last_delivery_at) && (
            <span className="text-gray-500">
              Last: {format(new Date(webhook.last_triggered_at || webhook.last_delivery_at || ''), 'MMM d, HH:mm')}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <button className="p-2 text-gray-400 hover:text-sardis-400 transition-colors">
            <Play className="w-4 h-4" />
          </button>
          <button 
            onClick={onDelete}
            className="p-2 text-gray-400 hover:text-red-500 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
      </ContextMenuTrigger>
      <ContextMenuContent>
        <ContextMenuItem onClick={() => navigator.clipboard.writeText(webhook.subscription_id)}>Copy Webhook ID</ContextMenuItem>
        <ContextMenuItem onClick={() => navigator.clipboard.writeText(webhook.url)}>Copy URL</ContextMenuItem>
        <ContextMenuSeparator />
        <ContextMenuItem onClick={onDelete} className="text-red-400">Delete Webhook</ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  )
}

function CreateWebhookModal({
  open,
  onOpenChange,
  onSubmit,
  isLoading
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSubmit: (data: { url: string; events: string[] }) => Promise<void>
  isLoading: boolean
}) {
  const [url, setUrl] = useState('')
  const [events, setEvents] = useState<string[]>(['payment.completed'])

  const toggleEvent = (event: string) => {
    if (events.includes(event)) {
      setEvents(events.filter(e => e !== event))
    } else {
      setEvents([...events, event])
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Add Webhook</DialogTitle>
        </DialogHeader>

        <form
          onSubmit={async (e) => {
            e.preventDefault()
            await onSubmit({ url, events })
          }}
          className="space-y-6"
        >
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Endpoint URL
            </label>
            <input
              type="url"
              required
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              className="w-full px-4 py-2 bg-dark-300 border border-dark-100 rounded-lg text-white focus:outline-none focus:border-sardis-500/50"
              placeholder="https://your-app.com/webhook"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-2">
              Events to Subscribe
            </label>
            <div className="grid grid-cols-2 gap-2">
              {availableEvents.map(event => (
                <button
                  key={event}
                  type="button"
                  onClick={() => toggleEvent(event)}
                  className={clsx(
                    'px-3 py-2 rounded-lg text-sm font-medium transition-all text-left',
                    events.includes(event)
                      ? 'bg-sardis-500/10 text-sardis-400 border border-sardis-500/30'
                      : 'bg-dark-300 text-gray-400 border border-dark-100 hover:border-dark-100'
                  )}
                >
                  {event}
                </button>
              ))}
            </div>
          </div>

          <DialogFooter className="flex gap-4 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => onOpenChange(false)}
              className="flex-1"
            >
              Cancel
            </Button>
            <button
              type="submit"
              disabled={isLoading || events.length === 0}
              className="flex-1 px-4 py-2 bg-sardis-500 text-white font-medium rounded-lg hover:bg-sardis-400 transition-colors disabled:opacity-50"
            >
              {isLoading ? 'Creating...' : 'Create Webhook'}
            </button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
