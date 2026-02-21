
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/Dashboard'
import AgentsPage from './pages/Agents'
import LoginPage from './pages/Login'
import DemoPage from './pages/Demo'
import CardsPage from './pages/Cards'
import ReconciliationPage from './pages/Reconciliation'
import PolicyPlaygroundPage from './pages/PolicyPlayground'
import LiveEventsPage from './pages/LiveEvents'
import ApprovalsPage from './pages/Approvals'
import AnalyticsPage from './pages/Analytics'
import GuardrailsPage from './pages/Guardrails'
import ConfidenceRouterPage from './pages/ConfidenceRouter'
import AuditAnchorsPage from './pages/AuditAnchors'
import AgentIdentityPage from './pages/AgentIdentity'
import GoalDriftPage from './pages/GoalDrift'
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
                <Route path="/demo" element={<DemoPage />} />
                <Route path="/agents" element={<AgentsPage />} />
                <Route path="/cards" element={<CardsPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/reconciliation" element={<ReconciliationPage />} />
                <Route path="/policies" element={<PolicyPlaygroundPage />} />
                <Route path="/approvals" element={<ApprovalsPage />} />
                <Route path="/events" element={<LiveEventsPage />} />
                <Route path="/guardrails" element={<GuardrailsPage />} />
                <Route path="/confidence-router" element={<ConfidenceRouterPage />} />
                <Route path="/audit-anchors" element={<AuditAnchorsPage />} />
                <Route path="/agent-identity" element={<AgentIdentityPage />} />
                <Route path="/goal-drift" element={<GoalDriftPage />} />
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
