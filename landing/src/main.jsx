import { StrictMode, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import posthog from 'posthog-js'

const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY
if (POSTHOG_KEY) {
  posthog.init(POSTHOG_KEY, {
    api_host: import.meta.env.VITE_POSTHOG_HOST || 'https://us.i.posthog.com',
    capture_pageview: true,
    autocapture: true,
  })
}
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'
import './index.css'
import { Analytics } from '@vercel/analytics/react'

// ── Critical path: landing page loaded eagerly (LCP) ──
import LandingV2 from './pages/LandingV2.jsx'

// ── Everything else: lazy-loaded (code splitting) ──
const DocsLayout = lazy(() => import('./docs/DocsLayout.jsx'))
const DocsOverview = lazy(() => import('./docs/pages/Overview.jsx'))
const DocsQuickstart = lazy(() => import('./docs/pages/Quickstart.jsx'))
const DocsAuthentication = lazy(() => import('./docs/pages/Authentication.jsx'))
const DocsProductionGuide = lazy(() => import('./docs/pages/ProductionGuide.jsx'))
const DocsTrustCenter = lazy(() => import('./docs/pages/TrustCenter.jsx'))
const DocsSpendingMandates = lazy(() => import('./docs/pages/SpendingMandates.jsx'))
const DocsGetAPIKey = lazy(() => import('./docs/pages/GetAPIKey.jsx'))
// Protocols
const DocsProtocols = lazy(() => import('./docs/pages/Protocols.jsx'))
const DocsAP2 = lazy(() => import('./docs/pages/AP2.jsx'))
const DocsUCP = lazy(() => import('./docs/pages/UCP.jsx'))
const DocsA2A = lazy(() => import('./docs/pages/A2A.jsx'))
const DocsTAP = lazy(() => import('./docs/pages/TAP.jsx'))
const DocsACP = lazy(() => import('./docs/pages/ACP.jsx'))
// Core Features
const DocsWallets = lazy(() => import('./docs/pages/Wallets.jsx'))
const DocsPayments = lazy(() => import('./docs/pages/Payments.jsx'))
const DocsHolds = lazy(() => import('./docs/pages/Holds.jsx'))
const DocsPolicies = lazy(() => import('./docs/pages/Policies.jsx'))
const DocsTimeBasedPolicies = lazy(() => import('./docs/pages/TimeBasedPolicies.jsx'))
const DocsMerchantCategories = lazy(() => import('./docs/pages/MerchantCategories.jsx'))
// SDKs & Tools
const DocsSDKPython = lazy(() => import('./docs/pages/SDKPython.jsx'))
const DocsSDKTypeScript = lazy(() => import('./docs/pages/SDKTypeScript.jsx'))
const DocsMCPServer = lazy(() => import('./docs/pages/MCPServer.jsx'))
const DocsSDK = lazy(() => import('./docs/pages/SDK.jsx'))
const APIReference = lazy(() => import('./docs/pages/APIReference.jsx'))
// Framework Integrations
const DocsIntegrations = lazy(() => import('./docs/pages/Integrations.jsx'))
const DocsIntegrationLangChain = lazy(() => import('./docs/pages/IntegrationLangChain.jsx'))
const DocsIntegrationCrewAI = lazy(() => import('./docs/pages/IntegrationCrewAI.jsx'))
const DocsIntegrationADK = lazy(() => import('./docs/pages/IntegrationADK.jsx'))
const DocsIntegrationAgentSDK = lazy(() => import('./docs/pages/IntegrationAgentSDK.jsx'))
const DocsIntegrationBrowserUse = lazy(() => import('./docs/pages/IntegrationBrowserUse.jsx'))
const DocsIntegrationOpenAIAgents = lazy(() => import('./docs/pages/IntegrationOpenAIAgents.jsx'))
const DocsIntegrationComposio = lazy(() => import('./docs/pages/IntegrationComposio.jsx'))
const DocsIntegrationAutogpt = lazy(() => import('./docs/pages/IntegrationAutogpt.jsx'))
const DocsIntegrationN8N = lazy(() => import('./docs/pages/IntegrationN8N.jsx'))
// Resources
const DocsBlockchainInfrastructure = lazy(() => import('./docs/pages/BlockchainInfrastructure.jsx'))
const DocsArchitecture = lazy(() => import('./docs/pages/Architecture.jsx'))
const DocsWhitepaper = lazy(() => import('./docs/pages/Whitepaper.jsx'))
const DocsSecurity = lazy(() => import('./docs/pages/Security.jsx'))
const DocsFAQ = lazy(() => import('./docs/pages/FAQ.jsx'))
const DocsTroubleshooting = lazy(() => import('./docs/pages/Troubleshooting.jsx'))
const DocsComparison = lazy(() => import('./docs/pages/Comparison.jsx'))
const DocsBlog = lazy(() => import('./docs/pages/Blog.jsx'))
const DocsChangelog = lazy(() => import('./docs/pages/Changelog.jsx'))
const DocsRuntimeGuardrails = lazy(() => import('./docs/pages/RuntimeGuardrails.jsx'))
// Legal
const TermsOfService = lazy(() => import('./docs/pages/TermsOfService.jsx'))
const PrivacyPolicy = lazy(() => import('./docs/pages/PrivacyPolicy.jsx'))
const AcceptableUse = lazy(() => import('./docs/pages/AcceptableUse.jsx'))
const RiskDisclosures = lazy(() => import('./docs/pages/RiskDisclosures.jsx'))
// Blog posts
const IntroducingSardis = lazy(() => import('./docs/pages/blog/IntroducingSardis.jsx'))
const FinancialHallucination = lazy(() => import('./docs/pages/blog/FinancialHallucination.jsx'))
const MCPIntegration = lazy(() => import('./docs/pages/blog/MCPIntegration.jsx'))
const MPCWallets = lazy(() => import('./docs/pages/blog/MPCWallets.jsx'))
const SDKRelease = lazy(() => import('./docs/pages/blog/SDKRelease.jsx'))
const PolicyEngineDeepDive = lazy(() => import('./docs/pages/blog/PolicyEngineDeepDive.jsx'))
const SardisV05Protocols = lazy(() => import('./docs/pages/blog/SardisV05Protocols.jsx'))
const UnderstandingAP2 = lazy(() => import('./docs/pages/blog/UnderstandingAP2.jsx'))
const SardisV084PackagesLive = lazy(() => import('./docs/pages/blog/SardisV084PackagesLive.jsx'))
const SardisAIAgentPayments = lazy(() => import('./docs/pages/blog/SardisAIAgentPayments.jsx'))
const SpendingRulesExplainer = lazy(() => import('./docs/pages/blog/SpendingRulesExplainer.jsx'))
const AgentAccountability = lazy(() => import('./docs/pages/blog/AgentAccountability.jsx'))
// Standalone pages
const Playground = lazy(() => import('./pages/Playground.jsx'))
const Demo = lazy(() => import('./pages/Demo.jsx'))
const Enterprise = lazy(() => import('./pages/Enterprise.jsx'))
// Signup removed — using waitlist for now
const Pricing = lazy(() => import('./pages/Pricing.jsx'))
const Status = lazy(() => import('./pages/Status.jsx'))
// Solution pages
const AgentPlatformsPage = lazy(() => import('./pages/solutions/AgentPlatforms.jsx'))
const ProcurementPage = lazy(() => import('./pages/solutions/Procurement.jsx'))
const PayoutsPage = lazy(() => import('./pages/solutions/Payouts.jsx'))

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
    <BrowserRouter>
      <Analytics />
      <Suspense fallback={null}>
      <Routes>
        <Route path="/" element={<LandingV2 />} />
        {/* Hidden for prod: /v1 (legacy), /dashboard (mockup) */}
        <Route path="/playground" element={<Playground />} />
        <Route path="/demo" element={<Demo />} />
        <Route path="/enterprise" element={<Enterprise />} />
        <Route path="/solutions/agent-platforms" element={<AgentPlatformsPage />} />
        <Route path="/solutions/procurement" element={<ProcurementPage />} />
        <Route path="/solutions/payouts" element={<PayoutsPage />} />
        {/* Signup removed — using waitlist */}
        <Route path="/pricing" element={<Pricing />} />
        <Route path="/status" element={<Status />} />
        <Route path="/docs" element={<DocsLayout />}>
          <Route index element={<DocsOverview />} />
          <Route path="overview" element={<DocsOverview />} />
          <Route path="quickstart" element={<DocsQuickstart />} />
          <Route path="authentication" element={<DocsAuthentication />} />
          <Route path="production-guide" element={<DocsProductionGuide />} />
          <Route path="trust" element={<DocsTrustCenter />} />
          <Route path="spending-mandates" element={<DocsSpendingMandates />} />
          <Route path="get-api-key" element={<DocsGetAPIKey />} />
          {/* Protocols */}
          <Route path="protocols" element={<DocsProtocols />} />
          <Route path="ap2" element={<DocsAP2 />} />
          <Route path="ucp" element={<DocsUCP />} />
          <Route path="a2a" element={<DocsA2A />} />
          <Route path="tap" element={<DocsTAP />} />
          <Route path="acp" element={<DocsACP />} />
          {/* Core Features */}
          <Route path="wallets" element={<DocsWallets />} />
          <Route path="payments" element={<DocsPayments />} />
          <Route path="holds" element={<DocsHolds />} />
          <Route path="policies" element={<DocsPolicies />} />
          <Route path="time-based-policies" element={<DocsTimeBasedPolicies />} />
          <Route path="merchant-categories" element={<DocsMerchantCategories />} />
          {/* SDKs & Tools */}
          <Route path="sdk-python" element={<DocsSDKPython />} />
          <Route path="sdk-typescript" element={<DocsSDKTypeScript />} />
          <Route path="mcp-server" element={<DocsMCPServer />} />
          <Route path="sdk" element={<DocsSDK />} />
          <Route path="api-reference" element={<APIReference />} />
          {/* Framework Integrations */}
          <Route path="integrations" element={<DocsIntegrations />} />
          <Route path="integration-langchain" element={<DocsIntegrationLangChain />} />
          <Route path="integration-crewai" element={<DocsIntegrationCrewAI />} />
          <Route path="integration-adk" element={<DocsIntegrationADK />} />
          <Route path="integration-agent-sdk" element={<DocsIntegrationAgentSDK />} />
          <Route path="integration-browser-use" element={<DocsIntegrationBrowserUse />} />
          <Route path="integration-openai-agents" element={<DocsIntegrationOpenAIAgents />} />
          <Route path="integration-composio" element={<DocsIntegrationComposio />} />
          <Route path="integration-autogpt" element={<DocsIntegrationAutogpt />} />
          <Route path="integration-n8n" element={<DocsIntegrationN8N />} />
          {/* Resources */}
          <Route path="blockchain-infrastructure" element={<DocsBlockchainInfrastructure />} />
          <Route path="architecture" element={<DocsArchitecture />} />
          <Route path="whitepaper" element={<DocsWhitepaper />} />
          <Route path="security" element={<DocsSecurity />} />
          {/* Hidden for prod: deployment (staging URLs), provider-diligence (internal GitHub links), roadmap (stale) */}
          <Route path="faq" element={<DocsFAQ />} />
          <Route path="troubleshooting" element={<DocsTroubleshooting />} />
          <Route path="comparison" element={<DocsComparison />} />
          <Route path="runtime-guardrails" element={<DocsRuntimeGuardrails />} />
          <Route path="blog" element={<DocsBlog />} />
          <Route path="blog/introducing-sardis" element={<IntroducingSardis />} />
          <Route path="blog/financial-hallucination-prevention" element={<FinancialHallucination />} />
          <Route path="blog/mcp-integration" element={<MCPIntegration />} />
          <Route path="blog/mpc-wallets" element={<MPCWallets />} />
          <Route path="blog/sdk-v0-2-0" element={<SDKRelease />} />
          <Route path="blog/policy-engine-deep-dive" element={<PolicyEngineDeepDive />} />
          <Route path="blog/sardis-v0-5-protocols" element={<SardisV05Protocols />} />
          <Route path="blog/understanding-ap2" element={<UnderstandingAP2 />} />
          {/* Hidden for prod: internal release notes, false Lithic claims, deployment details */}
          <Route path="blog/sardis-v0-8-4-packages-live" element={<SardisV084PackagesLive />} />
          <Route path="blog/sardis-ai-agent-payments" element={<SardisAIAgentPayments />} />
          <Route path="blog/spending-rules-explained" element={<SpendingRulesExplainer />} />
          <Route path="blog/agent-accountability" element={<AgentAccountability />} />
          <Route path="changelog" element={<DocsChangelog />} />
          {/* Legal */}
          <Route path="terms" element={<TermsOfService />} />
          <Route path="privacy" element={<PrivacyPolicy />} />
          <Route path="acceptable-use" element={<AcceptableUse />} />
          <Route path="risk-disclosures" element={<RiskDisclosures />} />
        </Route>
      </Routes>
      </Suspense>
    </BrowserRouter>
    </HelmetProvider>
  </StrictMode>,
)
