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
          <Route path="changelog" element={<DocsChangelog />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
