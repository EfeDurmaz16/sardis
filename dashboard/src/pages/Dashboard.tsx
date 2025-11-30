import { 
  Users, 
  ArrowRightLeft, 
  DollarSign, 
  Wallet,
  Activity,
  TrendingUp
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
  Bar
} from 'recharts'
import StatCard from '../components/StatCard'
import { useAgents, useMerchants, useWebhooks } from '../hooks/useApi'

// Mock data for charts
const volumeData = [
  { date: 'Mon', value: 1200 },
  { date: 'Tue', value: 1900 },
  { date: 'Wed', value: 1500 },
  { date: 'Thu', value: 2800 },
  { date: 'Fri', value: 2400 },
  { date: 'Sat', value: 1800 },
  { date: 'Sun', value: 2200 },
]

const transactionsByChain = [
  { chain: 'Base', count: 450, color: '#0052FF' },
  { chain: 'Polygon', count: 320, color: '#8247E5' },
  { chain: 'Ethereum', count: 180, color: '#627EEA' },
  { chain: 'Solana', count: 150, color: '#14F195' },
]

export default function DashboardPage() {
  const { data: agents = [] } = useAgents()
  const { data: merchants = [] } = useMerchants()
  const { data: webhooks = [] } = useWebhooks()
  
  const activeAgents = agents.filter((a: any) => a.is_active).length
  const totalVolume = '$12,450.00'
  
  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white font-display">Dashboard</h1>
        <p className="text-gray-400 mt-1">
          Monitor your AI agent payment network
        </p>
      </div>
      
      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <StatCard
          title="Total Agents"
          value={agents.length}
          change={`${activeAgents} active`}
          changeType="positive"
          icon={<Users className="w-6 h-6" />}
        />
        <StatCard
          title="Volume (24h)"
          value={totalVolume}
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
          value={merchants.length}
          change={`${webhooks.length} webhooks`}
          changeType="neutral"
          icon={<Wallet className="w-6 h-6" />}
        />
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
      
      {/* Recent Activity */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Recent Activity</h2>
        
        <div className="space-y-4">
          {[
            { type: 'payment', agent: 'shopping_agent_001', amount: '$25.50', time: '2 min ago', status: 'completed' },
            { type: 'register', agent: 'data_buyer_demo', amount: '$100.00', time: '5 min ago', status: 'completed' },
            { type: 'payment', agent: 'automation_agent', amount: '$8.00', time: '12 min ago', status: 'completed' },
            { type: 'payment', agent: 'budget_optimizer', amount: '$45.00', time: '18 min ago', status: 'pending' },
            { type: 'webhook', agent: 'payment.completed', amount: '', time: '20 min ago', status: 'delivered' },
          ].map((activity, i) => (
            <div 
              key={i} 
              className="flex items-center justify-between py-3 border-b border-dark-100 last:border-0"
            >
              <div className="flex items-center gap-4">
                <div className={`status-dot ${activity.status === 'completed' || activity.status === 'delivered' ? 'success' : 'pending'}`} />
                <div>
                  <p className="text-sm font-medium text-white">{activity.agent}</p>
                  <p className="text-xs text-gray-500">{activity.type}</p>
                </div>
              </div>
              <div className="text-right">
                {activity.amount && (
                  <p className="text-sm font-medium text-sardis-400 mono-numbers">{activity.amount}</p>
                )}
                <p className="text-xs text-gray-500">{activity.time}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

