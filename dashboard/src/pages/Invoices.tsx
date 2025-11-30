import { useState } from 'react'
import { Search, FileText, Plus, CheckCircle, Clock, XCircle, AlertTriangle, ExternalLink, Copy } from 'lucide-react'
import clsx from 'clsx'
import { format } from 'date-fns'

// Mock invoices data
const mockInvoices = [
  {
    invoice_id: 'inv_a1b2c3d4e5f6',
    merchant_id: 'merchant_gpu_provider',
    merchant_name: 'GPU Cloud Services',
    amount: '150.00',
    amount_paid: '150.00',
    currency: 'USDC',
    description: 'GPU Compute Hours - November 2024',
    status: 'paid' as const,
    created_at: new Date(Date.now() - 86400000).toISOString(),
    paid_at: new Date(Date.now() - 3600000).toISOString(),
    payer_agent_id: 'agent_compute_001',
    reference: 'INV-2024-001',
  },
  {
    invoice_id: 'inv_g7h8i9j0k1l2',
    merchant_id: 'merchant_data_api',
    merchant_name: 'DataStream API',
    amount: '49.99',
    amount_paid: '0.00',
    currency: 'USDC',
    description: 'Monthly API Subscription',
    status: 'pending' as const,
    created_at: new Date().toISOString(),
    paid_at: null,
    payer_agent_id: 'agent_data_fetcher',
    reference: 'SUB-NOV-2024',
  },
  {
    invoice_id: 'inv_m3n4o5p6q7r8',
    merchant_id: 'merchant_storage',
    merchant_name: 'Cloud Storage Inc',
    amount: '25.00',
    amount_paid: '10.00',
    currency: 'USDC',
    description: 'Storage allocation - partial payment',
    status: 'partial' as const,
    created_at: new Date(Date.now() - 172800000).toISOString(),
    paid_at: null,
    payer_agent_id: 'agent_backup_001',
    reference: 'STR-2024-Q4',
  },
  {
    invoice_id: 'inv_s9t0u1v2w3x4',
    merchant_id: 'merchant_old_service',
    merchant_name: 'Legacy Services',
    amount: '75.00',
    amount_paid: '0.00',
    currency: 'USDC',
    description: 'Cancelled service request',
    status: 'cancelled' as const,
    created_at: new Date(Date.now() - 604800000).toISOString(),
    paid_at: null,
    payer_agent_id: null,
    reference: 'CAN-001',
  },
  {
    invoice_id: 'inv_y5z6a7b8c9d0',
    merchant_id: 'merchant_compute',
    merchant_name: 'ComputeNow',
    amount: '200.00',
    amount_paid: '0.00',
    currency: 'USDC',
    description: 'Overdue compute invoice',
    status: 'overdue' as const,
    created_at: new Date(Date.now() - 1209600000).toISOString(),
    paid_at: null,
    payer_agent_id: 'agent_compute_002',
    reference: 'OVD-2024-001',
  },
]

type StatusFilter = 'all' | 'pending' | 'paid' | 'partial' | 'cancelled' | 'overdue'

export default function InvoicesPage() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  
  const filteredInvoices = mockInvoices.filter(inv => {
    const matchesSearch = 
      inv.invoice_id.toLowerCase().includes(search.toLowerCase()) ||
      inv.merchant_name.toLowerCase().includes(search.toLowerCase()) ||
      inv.description?.toLowerCase().includes(search.toLowerCase()) ||
      inv.reference?.toLowerCase().includes(search.toLowerCase())
    
    const matchesStatus = statusFilter === 'all' || inv.status === statusFilter
    
    return matchesSearch && matchesStatus
  })
  
  const totalOutstanding = mockInvoices
    .filter(i => i.status === 'pending' || i.status === 'partial' || i.status === 'overdue')
    .reduce((sum, i) => sum + (parseFloat(i.amount) - parseFloat(i.amount_paid)), 0)
  
  const totalReceived = mockInvoices
    .reduce((sum, i) => sum + parseFloat(i.amount_paid), 0)
  
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
        return <CheckCircle className="w-4 h-4" />
      case 'pending':
        return <Clock className="w-4 h-4" />
      case 'partial':
        return <AlertTriangle className="w-4 h-4" />
      case 'cancelled':
        return <XCircle className="w-4 h-4" />
      case 'overdue':
        return <AlertTriangle className="w-4 h-4" />
      default:
        return <FileText className="w-4 h-4" />
    }
  }
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    // Could add a toast notification here
  }
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Invoices</h1>
          <p className="text-gray-400 mt-1">
            Manage merchant invoices and payment requests
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2.5 bg-sardis-500 text-dark-400 rounded-lg font-medium hover:bg-sardis-400 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Create Invoice
        </button>
      </div>
      
      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="text-sm text-gray-400">Total Invoices</p>
          <p className="text-2xl font-bold text-white">
            {mockInvoices.length}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Outstanding</p>
          <p className="text-2xl font-bold text-yellow-500 mono-numbers">
            ${totalOutstanding.toFixed(2)}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Received</p>
          <p className="text-2xl font-bold text-green-500 mono-numbers">
            ${totalReceived.toFixed(2)}
          </p>
        </div>
        <div className="card p-4">
          <p className="text-sm text-gray-400">Overdue</p>
          <p className="text-2xl font-bold text-red-500">
            {mockInvoices.filter(i => i.status === 'overdue').length}
          </p>
        </div>
      </div>
      
      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" />
          <input
            type="text"
            placeholder="Search invoices..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-dark-200 border border-dark-100 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-sardis-500/50"
          />
        </div>
        
        <div className="flex gap-2 flex-wrap">
          {(['all', 'pending', 'paid', 'partial', 'overdue', 'cancelled'] as StatusFilter[]).map(status => (
            <button
              key={status}
              onClick={() => setStatusFilter(status)}
              className={clsx(
                'px-4 py-2 rounded-lg text-sm font-medium transition-colors capitalize',
                statusFilter === status
                  ? 'bg-sardis-500 text-dark-400'
                  : 'bg-dark-200 text-gray-400 hover:bg-dark-100'
              )}
            >
              {status}
            </button>
          ))}
        </div>
      </div>
      
      {/* Invoices Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {filteredInvoices.map((invoice) => (
          <div 
            key={invoice.invoice_id} 
            className={clsx(
              'card p-6 hover:border-sardis-500/30 transition-colors',
              invoice.status === 'overdue' && 'border-red-500/30'
            )}
          >
            <div className="flex items-start justify-between mb-4">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-lg font-semibold text-white">
                    {invoice.merchant_name}
                  </h3>
                  <span className={clsx(
                    'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                    invoice.status === 'paid' && 'bg-green-500/10 text-green-500',
                    invoice.status === 'pending' && 'bg-yellow-500/10 text-yellow-500',
                    invoice.status === 'partial' && 'bg-blue-500/10 text-blue-500',
                    invoice.status === 'cancelled' && 'bg-gray-500/10 text-gray-500',
                    invoice.status === 'overdue' && 'bg-red-500/10 text-red-500'
                  )}>
                    {getStatusIcon(invoice.status)}
                    {invoice.status}
                  </span>
                </div>
                <p className="text-sm text-gray-400 mt-1">{invoice.description}</p>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-white mono-numbers">
                  ${invoice.amount}
                </p>
                <p className="text-sm text-gray-400">{invoice.currency}</p>
              </div>
            </div>
            
            <div className="border-t border-dark-100 pt-4 mt-4">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">Invoice ID</p>
                  <div className="flex items-center gap-2">
                    <p className="text-white font-mono text-xs">{invoice.invoice_id}</p>
                    <button 
                      onClick={() => copyToClipboard(invoice.invoice_id)}
                      className="text-gray-500 hover:text-white"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                </div>
                <div>
                  <p className="text-gray-500">Reference</p>
                  <p className="text-white">{invoice.reference || '-'}</p>
                </div>
                <div>
                  <p className="text-gray-500">Created</p>
                  <p className="text-white">{format(new Date(invoice.created_at), 'MMM d, yyyy')}</p>
                </div>
                <div>
                  <p className="text-gray-500">Paid</p>
                  <p className={clsx(
                    parseFloat(invoice.amount_paid) > 0 ? 'text-green-500' : 'text-gray-400'
                  )}>
                    {parseFloat(invoice.amount_paid) > 0 
                      ? `$${invoice.amount_paid}` 
                      : 'Not yet'}
                  </p>
                </div>
              </div>
              
              {/* Progress bar for partial payments */}
              {invoice.status === 'partial' && (
                <div className="mt-4">
                  <div className="flex justify-between text-xs text-gray-400 mb-1">
                    <span>Payment Progress</span>
                    <span>
                      {Math.round((parseFloat(invoice.amount_paid) / parseFloat(invoice.amount)) * 100)}%
                    </span>
                  </div>
                  <div className="w-full h-2 bg-dark-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ 
                        width: `${(parseFloat(invoice.amount_paid) / parseFloat(invoice.amount)) * 100}%` 
                      }}
                    />
                  </div>
                </div>
              )}
              
              {/* Actions */}
              {invoice.status === 'pending' && (
                <div className="flex gap-2 mt-4">
                  <button className="flex-1 px-4 py-2 bg-sardis-500/10 text-sardis-500 rounded-lg text-sm font-medium hover:bg-sardis-500/20 transition-colors">
                    Send Reminder
                  </button>
                  <button className="px-4 py-2 bg-dark-200 text-gray-400 rounded-lg text-sm font-medium hover:bg-dark-100 transition-colors">
                    <ExternalLink className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
      
      {filteredInvoices.length === 0 && (
        <div className="card p-12 text-center">
          <FileText className="w-12 h-12 text-gray-600 mx-auto mb-4" />
          <p className="text-gray-400">No invoices found</p>
        </div>
      )}
      
      {/* Create Invoice Modal (simplified placeholder) */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="card p-6 w-full max-w-md">
            <h2 className="text-xl font-bold text-white mb-4">Create Invoice</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Amount (USDC)</label>
                <input 
                  type="number" 
                  className="w-full px-4 py-2 bg-dark-200 border border-dark-100 rounded-lg text-white"
                  placeholder="0.00"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Description</label>
                <textarea 
                  className="w-full px-4 py-2 bg-dark-200 border border-dark-100 rounded-lg text-white"
                  rows={3}
                  placeholder="Invoice description..."
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Request from Agent (optional)</label>
                <input 
                  type="text" 
                  className="w-full px-4 py-2 bg-dark-200 border border-dark-100 rounded-lg text-white"
                  placeholder="agent_id"
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button 
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-dark-200 text-gray-400 rounded-lg font-medium hover:bg-dark-100"
                >
                  Cancel
                </button>
                <button className="flex-1 px-4 py-2 bg-sardis-500 text-dark-400 rounded-lg font-medium hover:bg-sardis-400">
                  Create Invoice
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

