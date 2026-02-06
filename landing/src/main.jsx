import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import DocsLayout from './docs/DocsLayout.jsx'
import DocsOverview from './docs/pages/Overview.jsx'
import DocsQuickstart from './docs/pages/Quickstart.jsx'
import DocsAuthentication from './docs/pages/Authentication.jsx'
// Protocols
import DocsProtocols from './docs/pages/Protocols.jsx'
import DocsAP2 from './docs/pages/AP2.jsx'
import DocsUCP from './docs/pages/UCP.jsx'
import DocsA2A from './docs/pages/A2A.jsx'
import DocsTAP from './docs/pages/TAP.jsx'
// Core Features
import DocsWallets from './docs/pages/Wallets.jsx'
import DocsPayments from './docs/pages/Payments.jsx'
import DocsHolds from './docs/pages/Holds.jsx'
import DocsPolicies from './docs/pages/Policies.jsx'
// SDKs & Tools
import DocsSDKPython from './docs/pages/SDKPython.jsx'
import DocsSDKTypeScript from './docs/pages/SDKTypeScript.jsx'
import DocsMCPServer from './docs/pages/MCPServer.jsx'
import DocsSDK from './docs/pages/SDK.jsx'
// Resources
import DocsArchitecture from './docs/pages/Architecture.jsx'
import DocsWhitepaper from './docs/pages/Whitepaper.jsx'
import DocsSecurity from './docs/pages/Security.jsx'
import DocsDeployment from './docs/pages/Deployment.jsx'
import DocsFAQ from './docs/pages/FAQ.jsx'
import DocsBlog from './docs/pages/Blog.jsx'
import DocsChangelog from './docs/pages/Changelog.jsx'
import DocsRoadmap from './docs/pages/Roadmap.jsx'
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
import MCP36Tools from './docs/pages/blog/MCP36Tools.jsx'
import WhySardis from './docs/pages/blog/WhySardis.jsx'
import FiatRails from './docs/pages/blog/FiatRails.jsx'
import SardisV07ProductionHardening from './docs/pages/blog/SardisV07ProductionHardening.jsx'
import SardisV081ProtocolConformance from './docs/pages/blog/SardisV081ProtocolConformance.jsx'
// Standalone pages
import Playground from './pages/Playground.jsx'
import Demo from './pages/Demo.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/playground" element={<Playground />} />
        <Route path="/demo" element={<Demo />} />
        <Route path="/docs" element={<DocsLayout />}>
          <Route index element={<DocsOverview />} />
          <Route path="overview" element={<DocsOverview />} />
          <Route path="quickstart" element={<DocsQuickstart />} />
          <Route path="authentication" element={<DocsAuthentication />} />
          {/* Protocols */}
          <Route path="protocols" element={<DocsProtocols />} />
          <Route path="ap2" element={<DocsAP2 />} />
          <Route path="ucp" element={<DocsUCP />} />
          <Route path="a2a" element={<DocsA2A />} />
          <Route path="tap" element={<DocsTAP />} />
          {/* Core Features */}
          <Route path="wallets" element={<DocsWallets />} />
          <Route path="payments" element={<DocsPayments />} />
          <Route path="holds" element={<DocsHolds />} />
          <Route path="policies" element={<DocsPolicies />} />
          {/* SDKs & Tools */}
          <Route path="sdk-python" element={<DocsSDKPython />} />
          <Route path="sdk-typescript" element={<DocsSDKTypeScript />} />
          <Route path="mcp-server" element={<DocsMCPServer />} />
          <Route path="sdk" element={<DocsSDK />} />
          {/* Resources */}
          <Route path="architecture" element={<DocsArchitecture />} />
          <Route path="whitepaper" element={<DocsWhitepaper />} />
          <Route path="security" element={<DocsSecurity />} />
          <Route path="deployment" element={<DocsDeployment />} />
          <Route path="faq" element={<DocsFAQ />} />
          <Route path="blog" element={<DocsBlog />} />
          <Route path="blog/introducing-sardis" element={<IntroducingSardis />} />
          <Route path="blog/financial-hallucination-prevention" element={<FinancialHallucination />} />
          <Route path="blog/mcp-integration" element={<MCPIntegration />} />
          <Route path="blog/mpc-wallets" element={<MPCWallets />} />
          <Route path="blog/sdk-v0-2-0" element={<SDKRelease />} />
          <Route path="blog/policy-engine-deep-dive" element={<PolicyEngineDeepDive />} />
          <Route path="blog/sardis-v0-5-protocols" element={<SardisV05Protocols />} />
          <Route path="blog/understanding-ap2" element={<UnderstandingAP2 />} />
          <Route path="blog/mcp-36-tools" element={<MCP36Tools />} />
          <Route path="blog/why-sardis" element={<WhySardis />} />
          <Route path="blog/fiat-rails" element={<FiatRails />} />
          <Route path="blog/sardis-v0-7-production-hardening" element={<SardisV07ProductionHardening />} />
          <Route path="blog/sardis-v0-8-1-protocol-conformance" element={<SardisV081ProtocolConformance />} />
          <Route path="changelog" element={<DocsChangelog />} />
          <Route path="roadmap" element={<DocsRoadmap />} />
          {/* Legal */}
          <Route path="terms" element={<TermsOfService />} />
          <Route path="privacy" element={<PrivacyPolicy />} />
          <Route path="acceptable-use" element={<AcceptableUse />} />
          <Route path="risk-disclosures" element={<RiskDisclosures />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
