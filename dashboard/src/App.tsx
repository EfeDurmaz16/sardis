
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/Dashboard'
import AgentsPage from './pages/Agents'
import TransactionsPage from './pages/Transactions'
import HoldsPage from './pages/Holds'
import InvoicesPage from './pages/Invoices'
import WebhooksPage from './pages/Webhooks'
import SettingsPage from './pages/Settings'
import LoginPage from './pages/Login'
import DemoPage from './pages/Demo'
import { AuthProvider, useAuth } from './auth/AuthContext'

const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout>
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/holds" element={<HoldsPage />} />
                <Route path="/invoices" element={<InvoicesPage />} />
                <Route path="/webhooks" element={<WebhooksPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/demo" element={<DemoPage />} />
              </Routes>
            </Layout>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}

export default App
