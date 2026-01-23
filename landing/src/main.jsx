import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import DocsLayout from './docs/DocsLayout.jsx'
import DocsOverview from './docs/pages/Overview.jsx'
import DocsSDK from './docs/pages/SDK.jsx'
import DocsWhitepaper from './docs/pages/Whitepaper.jsx'
import DocsSecurity from './docs/pages/Security.jsx'
import DocsArchitecture from './docs/pages/Architecture.jsx'
import DocsQuickstart from './docs/pages/Quickstart.jsx'
import DocsDeployment from './docs/pages/Deployment.jsx'
import DocsFAQ from './docs/pages/FAQ.jsx'
import DocsBlog from './docs/pages/Blog.jsx'
import DocsChangelog from './docs/pages/Changelog.jsx'
// Blog posts
import IntroducingSardis from './docs/pages/blog/IntroducingSardis.jsx'
import FinancialHallucination from './docs/pages/blog/FinancialHallucination.jsx'
import MCPIntegration from './docs/pages/blog/MCPIntegration.jsx'
import MPCWallets from './docs/pages/blog/MPCWallets.jsx'
import SDKRelease from './docs/pages/blog/SDKRelease.jsx'
import PolicyEngineDeepDive from './docs/pages/blog/PolicyEngineDeepDive.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/docs" element={<DocsLayout />}>
          <Route index element={<DocsOverview />} />
          <Route path="overview" element={<DocsOverview />} />
          <Route path="quickstart" element={<DocsQuickstart />} />
          <Route path="sdk" element={<DocsSDK />} />
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
          <Route path="changelog" element={<DocsChangelog />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
