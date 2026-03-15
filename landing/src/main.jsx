import { StrictMode } from 'react'
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
import DocsLayout from './docs/DocsLayout.jsx'
import DocsOverview from './docs/pages/Overview.jsx'
import DocsQuickstart from './docs/pages/Quickstart.jsx'
import DocsAuthentication from './docs/pages/Authentication.jsx'
import DocsProductionGuide from './docs/pages/ProductionGuide.jsx'
// Protocols
import DocsProtocols from './docs/pages/Protocols.jsx'
import DocsAP2 from './docs/pages/AP2.jsx'
import DocsUCP from './docs/pages/UCP.jsx'
import DocsA2A from './docs/pages/A2A.jsx'
import DocsTAP from './docs/pages/TAP.jsx'
import DocsACP from './docs/pages/ACP.jsx'
// Core Features
import DocsWallets from './docs/pages/Wallets.jsx'
import DocsPayments from './docs/pages/Payments.jsx'
import DocsHolds from './docs/pages/Holds.jsx'
import DocsPolicies from './docs/pages/Policies.jsx'
import DocsTimeBasedPolicies from './docs/pages/TimeBasedPolicies.jsx'
import DocsMerchantCategories from './docs/pages/MerchantCategories.jsx'
// SDKs & Tools
import DocsSDKPython from './docs/pages/SDKPython.jsx'
import DocsSDKTypeScript from './docs/pages/SDKTypeScript.jsx'
import DocsMCPServer from './docs/pages/MCPServer.jsx'
import DocsSDK from './docs/pages/SDK.jsx'
import APIReference from './docs/pages/APIReference.jsx'
// Framework Integrations
import DocsIntegrations from './docs/pages/Integrations.jsx'
import DocsIntegrationLangChain from './docs/pages/IntegrationLangChain.jsx'
import DocsIntegrationCrewAI from './docs/pages/IntegrationCrewAI.jsx'
import DocsIntegrationADK from './docs/pages/IntegrationADK.jsx'
import DocsIntegrationAgentSDK from './docs/pages/IntegrationAgentSDK.jsx'
import DocsIntegrationBrowserUse from './docs/pages/IntegrationBrowserUse.jsx'
import DocsIntegrationOpenAIAgents from './docs/pages/IntegrationOpenAIAgents.jsx'
import DocsIntegrationComposio from './docs/pages/IntegrationComposio.jsx'
import DocsIntegrationAutogpt from './docs/pages/IntegrationAutogpt.jsx'
import DocsIntegrationN8N from './docs/pages/IntegrationN8N.jsx'
// Resources
import DocsBlockchainInfrastructure from './docs/pages/BlockchainInfrastructure.jsx'
import DocsArchitecture from './docs/pages/Architecture.jsx'
import DocsWhitepaper from './docs/pages/Whitepaper.jsx'
import DocsSecurity from './docs/pages/Security.jsx'
import DocsFAQ from './docs/pages/FAQ.jsx'
import DocsTroubleshooting from './docs/pages/Troubleshooting.jsx'
import DocsComparison from './docs/pages/Comparison.jsx'
import DocsBlog from './docs/pages/Blog.jsx'
import DocsChangelog from './docs/pages/Changelog.jsx'
import DocsRuntimeGuardrails from './docs/pages/RuntimeGuardrails.jsx'
// Legal
import TermsOfService from './docs/pages/TermsOfService.jsx'
import PrivacyPolicy from './docs/pages/PrivacyPolicy.jsx'
import AcceptableUse from './docs/pages/AcceptableUse.jsx'
import RiskDisclosures from './docs/pages/RiskDisclosures.jsx'
// Blog posts
import IntroducingSardis from './docs/pages/blog/IntroducingSardis.jsx'
import FinancialHallucination from './docs/pages/blog/FinancialHallucination.jsx'
import MCPIntegration from './docs/pages/blog/MCPIntegration.jsx'
import MPCWallets from './docs/pages/blog/MPCWallets.jsx'
import SDKRelease from './docs/pages/blog/SDKRelease.jsx'
import PolicyEngineDeepDive from './docs/pages/blog/PolicyEngineDeepDive.jsx'
import SardisV05Protocols from './docs/pages/blog/SardisV05Protocols.jsx'
import UnderstandingAP2 from './docs/pages/blog/UnderstandingAP2.jsx'
import SardisV084PackagesLive from './docs/pages/blog/SardisV084PackagesLive.jsx'
import SardisAIAgentPayments from './docs/pages/blog/SardisAIAgentPayments.jsx'
// Standalone pages
import Playground from './pages/Playground.jsx'
import Demo from './pages/Demo.jsx'
import Enterprise from './pages/Enterprise.jsx'
import LandingV2 from './pages/LandingV2.jsx'
// Signup removed — using waitlist for now
import Pricing from './pages/Pricing.jsx'
import Status from './pages/Status.jsx'
// Solution pages
import AgentPlatformsPage from './pages/solutions/AgentPlatforms.jsx'
import ProcurementPage from './pages/solutions/Procurement.jsx'
import PayoutsPage from './pages/solutions/Payouts.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <HelmetProvider>
    <BrowserRouter>
      <Analytics />
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
          <Route path="changelog" element={<DocsChangelog />} />
          {/* Legal */}
          <Route path="terms" element={<TermsOfService />} />
          <Route path="privacy" element={<PrivacyPolicy />} />
          <Route path="acceptable-use" element={<AcceptableUse />} />
          <Route path="risk-disclosures" element={<RiskDisclosures />} />
        </Route>
      </Routes>
    </BrowserRouter>
    </HelmetProvider>
  </StrictMode>,
)
