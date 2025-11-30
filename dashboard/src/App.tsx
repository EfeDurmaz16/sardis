import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/Dashboard'
import AgentsPage from './pages/Agents'
import TransactionsPage from './pages/Transactions'
import WebhooksPage from './pages/Webhooks'
import SettingsPage from './pages/Settings'

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/transactions" element={<TransactionsPage />} />
        <Route path="/webhooks" element={<WebhooksPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}

export default App

