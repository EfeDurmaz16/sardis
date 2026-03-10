
import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import DashboardPage from './pages/Dashboard'
import AgentsPage from './pages/Agents'
import LoginPage from './pages/Login'
import OnboardingPage from './pages/Onboarding'
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
import EnterpriseSupportPage from './pages/EnterpriseSupport'
import StripeIssuingDemoPage from './pages/StripeIssuingDemo'
import KillSwitchPage from './pages/KillSwitch'
import EvidencePage from './pages/Evidence'
import PoliciesPage from './pages/Policies'
import MerchantsPage from './pages/Merchants'
import SimulationPage from './pages/Simulation'
import AnomalyDashboardPage from './pages/AnomalyDashboard'
import BillingPage from './pages/Billing'
import APIKeysPage from './pages/APIKeys'
import WebhookManagerPage from './pages/WebhookManager'
import SettingsPage from './pages/Settings'
import AlertPreferencesPage from './pages/AlertPreferences'
import LiveLaneOnboardingPage from './pages/LiveLaneOnboarding'
import PolicyManagerPage from './pages/PolicyManager'
import ControlCenterPage from './pages/ControlCenter'
import WorkflowTemplatesPage from './pages/WorkflowTemplates'
import PolicyAnalyticsPage from './pages/PolicyAnalytics'
import CounterpartiesPage from './pages/Counterparties'
import { AuthProvider, useAuth } from './auth/AuthContext'

// Requires auth only — used for the onboarding route itself to avoid redirect loops
const AuthRequired = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  return <>{children}</>;
};

// Requires auth and redirects to onboarding when the user has no agents yet
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated, needsOnboarding } = useAuth();
  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }
  if (needsOnboarding) {
    return <Navigate to="/onboarding" />;
  }
  return <>{children}</>;
};

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/onboarding"
        element={
          <AuthRequired>
            <OnboardingPage />
          </AuthRequired>
        }
      />
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
                <Route path="/enterprise-support" element={<EnterpriseSupportPage />} />
                <Route path="/stripe-issuing" element={<StripeIssuingDemoPage />} />
                <Route path="/kill-switch" element={<KillSwitchPage />} />
                <Route path="/evidence" element={<EvidencePage />} />
                <Route path="/policy-management" element={<PoliciesPage />} />
                <Route path="/merchants" element={<MerchantsPage />} />
                <Route path="/simulation" element={<SimulationPage />} />
                <Route path="/anomaly" element={<AnomalyDashboardPage />} />
                <Route path="/billing" element={<BillingPage />} />
                <Route path="/api-keys" element={<APIKeysPage />} />
                <Route path="/webhooks" element={<WebhookManagerPage />} />
                <Route path="/settings" element={<SettingsPage />} />
                <Route path="/alert-preferences" element={<AlertPreferencesPage />} />
                <Route path="/go-live" element={<LiveLaneOnboardingPage />} />
                <Route path="/policy-manager" element={<PolicyManagerPage />} />
                <Route path="/control-center" element={<ControlCenterPage />} />
                <Route path="/templates" element={<WorkflowTemplatesPage />} />
                <Route path="/policy-analytics" element={<PolicyAnalyticsPage />} />
                <Route path="/counterparties" element={<CounterpartiesPage />} />
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
