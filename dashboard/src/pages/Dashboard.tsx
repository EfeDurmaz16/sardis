import { useState, useEffect } from 'react'
import { 
  Users, 
  ArrowRightLeft, 
  DollarSign, 
  Wallet,
  Activity,
  TrendingUp,
  Zap,
  Globe,
  Shield,
  Clock
} from 'lucide-react'
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell
} from 'recharts'
import clsx from 'clsx'
import StatCard from '../components/StatCard'
import { useAgents, useMerchants, useWebhooks } from '../hooks/useApi'

// Mock data for charts
const volumeData = [
  { date: 'Mon', value: 1200, transactions: 45 },
  { date: 'Tue', value: 1900, transactions: 72 },
  { date: 'Wed', value: 1500, transactions: 58 },
  { date: 'Thu', value: 2800, transactions: 105 },
  { date: 'Fri', value: 2400, transactions: 89 },
  { date: 'Sat', value: 1800, transactions: 67 },
  { date: 'Sun', value: 2200, transactions: 82 },
]

const transactionsByChain = [
  { chain: 'Base', count: 450, color: '#0052FF' },
  { chain: 'Polygon', count: 320, color: '#8247E5' },
  { chain: 'Ethereum', count: 180, color: '#627EEA' },
  { chain: 'Solana', count: 150, color: '#14F195' },
]

const paymentTypes = [
  { name: 'Agent → Merchant', value: 45, color: '#22c55e' },
  { name: 'Agent → Agent', value: 30, color: '#3b82f6' },
  { name: 'Holds/Pre-auth', value: 15, color: '#f59e0b' },
  { name: 'Refunds', value: 10, color: '#ef4444' },
]

// Simulated live transactions for demo
const generateLiveTransaction = () => {
  const agents = ['shopping_agent', 'data_buyer', 'compute_agent', 'research_ai', 'trading_bot']
  const merchants = ['GPU Cloud', 'Data API', 'Weather Service', 'Stock Feed', 'News API']
  const amounts = ['0.01', '0.05', '0.25', '1.00', '5.00', '10.00', '25.00']
  const statuses = ['completed', 'completed', 'completed', 'pending'] as const
  
  return {
    id: `tx_${Math.random().toString(36).substring(7)}`,
    agent: agents[Math.floor(Math.random() * agents.length)] + '_' + Math.random().toString(36).substring(7, 11),
    merchant: merchants[Math.floor(Math.random() * merchants.length)],
    amount: amounts[Math.floor(Math.random() * amounts.length)],
    status: statuses[Math.floor(Math.random() * statuses.length)],
    time: new Date().toLocaleTimeString(),
    chain: ['Base', 'Polygon', 'Ethereum'][Math.floor(Math.random() * 3)],
  }
}

export default function DashboardPage() {
  const { data: agents = [] } = useAgents()
  const { data: merchants = [] } = useMerchants()
  const { data: webhooks = [] } = useWebhooks()
  
  // Live transaction feed state
  const [liveTransactions, setLiveTransactions] = useState<ReturnType<typeof generateLiveTransaction>[]>([])
  const [txPerSecond, setTxPerSecond] = useState(0)
  const [totalVolume24h, setTotalVolume24h] = useState(12450)
  
  // Simulate live transactions
  useEffect(() => {
    const interval = setInterval(() => {
      const newTx = generateLiveTransaction()
      setLiveTransactions(prev => [newTx, ...prev.slice(0, 9)])
      setTxPerSecond(prev => Math.max(0, prev + (Math.random() > 0.5 ? 1 : -1)))
      setTotalVolume24h(prev => prev + parseFloat(newTx.amount))
    }, 2000 + Math.random() * 3000)
    
    return () => clearInterval(interval)
  }, [])
  
  const activeAgents = agents.filter((a: any) => a.is_active).length
  
  return (
    <div className="space-y-8">
      {/* Header with Live Indicator */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white font-display">Dashboard</h1>
          <p className="text-gray-400 mt-1">
            Monitor your AI agent payment network
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
            <span className="text-sm text-gray-400">Live</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-dark-200 rounded-full">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm text-white mono-numbers">{txPerSecond.toFixed(1)} tx/s</span>
          </div>
        </div>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Active Agents"
          value={agents.length || 12}
          change={`${activeAgents || 8} online`}
          changeType="positive"
          icon={<Users className="w-6 h-6" />}
        />
        <StatCard
          title="Volume (24h)"
          value={`$${totalVolume24h.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          change="+12.5%"
          changeType="positive"
          icon={<DollarSign className="w-6 h-6" />}
        />
        <StatCard
          title="Transactions"
          value="1,247"
          change="+8.2% from yesterday"
          changeType="positive"
          icon={<ArrowRightLeft className="w-6 h-6" />}
        />
        <StatCard
          title="Merchants"
          value={merchants.length || 24}
          change={`${webhooks.length || 12} webhooks`}
          changeType="neutral"
          icon={<Wallet className="w-6 h-6" />}
        />
      </div>
      
      {/* Live Transaction Feed + Stats */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Live Feed */}
        <div className="lg:col-span-2 card p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-sardis-400" />
              <h2 className="text-lg font-semibold text-white">Live Transaction Feed</h2>
            </div>
            <span className="text-xs text-gray-500">Updates automatically</span>
          </div>
          
          <div className="space-y-2 max-h-[320px] overflow-y-auto custom-scrollbar">
            {liveTransactions.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                Waiting for transactions...
              </div>
            ) : (
              liveTransactions.map((tx, i) => (
                <div 
                  key={tx.id}
                  className={clsx(
                    "flex items-center justify-between p-3 rounded-lg transition-all duration-500",
                    i === 0 ? "bg-sardis-500/10 border border-sardis-500/30" : "bg-dark-200/50"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <div className={clsx(
                      "w-2 h-2 rounded-full",
                      tx.status === 'completed' ? 'bg-green-500' : 'bg-yellow-500 animate-pulse'
                    )} />
                    <div>
                      <p className="text-sm font-medium text-white">{tx.agent}</p>
                      <p className="text-xs text-gray-500">→ {tx.merchant}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs px-2 py-0.5 bg-dark-300 text-gray-400 rounded">
                      {tx.chain}
                    </span>
                    <div className="text-right">
                      <p className="text-sm font-medium text-sardis-400 mono-numbers">${tx.amount}</p>
                      <p className="text-xs text-gray-500">{tx.time}</p>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
        
        {/* Quick Stats */}
        <div className="space-y-6">
          {/* Payment Types Pie */}
          <div className="card p-6">
            <h3 className="text-sm font-medium text-gray-400 mb-4">Payment Types</h3>
            <div className="h-40">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={paymentTypes}
                    cx="50%"
                    cy="50%"
                    innerRadius={40}
                    outerRadius={60}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {paymentTypes.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ 
                      background: '#1e293b', 
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      fontSize: '12px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="grid grid-cols-2 gap-2 mt-2">
              {paymentTypes.map((type, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: type.color }} />
                  <span className="text-xs text-gray-400">{type.name}</span>
                </div>
              ))}
            </div>
          </div>
          
          {/* Network Health */}
          <div className="card p-6">
            <h3 className="text-sm font-medium text-gray-400 mb-4">Network Health</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-gray-300">Base</span>
                </div>
                <span className="text-xs text-green-500">Healthy</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-gray-300">Polygon</span>
                </div>
                <span className="text-xs text-green-500">Healthy</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Globe className="w-4 h-4 text-green-500" />
                  <span className="text-sm text-gray-300">Ethereum</span>
                </div>
                <span className="text-xs text-green-500">Healthy</span>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Shield className="w-4 h-4 text-blue-500" />
                  <span className="text-sm text-gray-300">Risk Engine</span>
                </div>
                <span className="text-xs text-blue-500">Active</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Volume Chart */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">Transaction Volume</h2>
              <p className="text-sm text-gray-400">Last 7 days</p>
            </div>
            <div className="flex items-center gap-2 text-sardis-400">
              <TrendingUp className="w-5 h-5" />
              <span className="text-sm font-medium">+24.5%</span>
            </div>
          </div>
          
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={volumeData}>
                <defs>
                  <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis 
                  dataKey="date" 
                  stroke="#64748b" 
                  fontSize={12}
                  tickLine={false}
                />
                <YAxis 
                  stroke="#64748b" 
                  fontSize={12}
                  tickLine={false}
                  tickFormatter={(value) => `$${value}`}
                />
                <Tooltip 
                  contentStyle={{ 
                    background: '#1e293b', 
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                  labelStyle={{ color: '#94a3b8' }}
                />
                <Area 
                  type="monotone" 
                  dataKey="value" 
                  stroke="#22c55e" 
                  strokeWidth={2}
                  fillOpacity={1} 
                  fill="url(#colorValue)" 
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
        
        {/* Transactions by Chain */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold text-white">By Chain</h2>
              <p className="text-sm text-gray-400">Transaction distribution</p>
            </div>
            <Activity className="w-5 h-5 text-gray-400" />
          </div>
          
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={transactionsByChain} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" horizontal={false} />
                <XAxis type="number" stroke="#64748b" fontSize={12} tickLine={false} />
                <YAxis 
                  type="category" 
                  dataKey="chain" 
                  stroke="#64748b" 
                  fontSize={12}
                  tickLine={false}
                  width={80}
                />
                <Tooltip 
                  contentStyle={{ 
                    background: '#1e293b', 
                    border: '1px solid #334155',
                    borderRadius: '8px'
                  }}
                  cursor={{ fill: 'rgba(34, 197, 94, 0.1)' }}
                />
                <Bar 
                  dataKey="count" 
                  fill="#22c55e"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      
      {/* Recent Activity with better styling */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">Recent Activity</h2>
          <button className="text-sm text-sardis-400 hover:text-sardis-300">View all →</button>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-xs text-gray-500 uppercase">
                <th className="pb-3 font-medium">Status</th>
                <th className="pb-3 font-medium">Agent</th>
                <th className="pb-3 font-medium">Type</th>
                <th className="pb-3 font-medium">Amount</th>
                <th className="pb-3 font-medium">Chain</th>
                <th className="pb-3 font-medium">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-100">
              {[
                { status: 'completed', agent: 'shopping_agent_001', type: 'payment', amount: '$25.50', chain: 'Base', time: '2 min ago' },
                { status: 'completed', agent: 'data_buyer_demo', type: 'hold', amount: '$100.00', chain: 'Polygon', time: '5 min ago' },
                { status: 'completed', agent: 'automation_agent', type: 'payment', amount: '$8.00', chain: 'Base', time: '12 min ago' },
                { status: 'pending', agent: 'budget_optimizer', type: 'payment', amount: '$45.00', chain: 'Ethereum', time: '18 min ago' },
                { status: 'completed', agent: 'research_ai_003', type: 'refund', amount: '$12.00', chain: 'Base', time: '25 min ago' },
              ].map((row, i) => (
                <tr key={i} className="hover:bg-dark-200/50 transition-colors">
                  <td className="py-3">
                    <span className={clsx(
                      "inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium",
                      row.status === 'completed' && "bg-green-500/10 text-green-500",
                      row.status === 'pending' && "bg-yellow-500/10 text-yellow-500"
                    )}>
                      <div className={clsx(
                        "w-1.5 h-1.5 rounded-full",
                        row.status === 'completed' && "bg-green-500",
                        row.status === 'pending' && "bg-yellow-500 animate-pulse"
                      )} />
                      {row.status}
                    </span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-white font-mono">{row.agent}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-gray-400 capitalize">{row.type}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-sardis-400 font-medium mono-numbers">{row.amount}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-xs px-2 py-0.5 bg-dark-200 text-gray-400 rounded">{row.chain}</span>
                  </td>
                  <td className="py-3">
                    <span className="text-sm text-gray-500 flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {row.time}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
