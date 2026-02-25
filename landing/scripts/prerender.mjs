/**
 * Sardis Landing Page Pre-renderer
 *
 * Generates static HTML snapshots of all routes for AI crawlers and search engines.
 * AI crawlers cannot execute JavaScript, so they see an empty page with a React SPA.
 * This script uses Puppeteer to visit each route and save fully-rendered HTML.
 *
 * Usage:
 *   node scripts/prerender.mjs
 *
 * Runs automatically after `vite build` via the "build" npm script.
 */

import puppeteer from 'puppeteer';
import { preview as vitePreview } from 'vite';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { createServer as createNetServer } from 'net';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const DIST = path.join(ROOT, 'dist');

// All routes to pre-render, extracted from src/main.jsx
const ROUTES = [
  // Top-level pages
  '/',
  '/enterprise',
  '/playground',
  '/demo',

  // Docs - main
  '/docs',
  '/docs/overview',
  '/docs/quickstart',
  '/docs/authentication',

  // Docs - Protocols
  '/docs/protocols',
  '/docs/ap2',
  '/docs/ucp',
  '/docs/a2a',
  '/docs/tap',
  '/docs/acp',

  // Docs - Core Features
  '/docs/wallets',
  '/docs/payments',
  '/docs/holds',
  '/docs/policies',
  '/docs/time-based-policies',
  '/docs/merchant-categories',

  // Docs - SDKs & Tools
  '/docs/sdk-python',
  '/docs/sdk-typescript',
  '/docs/mcp-server',
  '/docs/sdk',
  '/docs/api-reference',

  // Docs - Resources
  '/docs/blockchain-infrastructure',
  '/docs/architecture',
  '/docs/whitepaper',
  '/docs/security',
  '/docs/deployment',
  '/docs/faq',
  '/docs/blog',
  '/docs/changelog',
  '/docs/roadmap',

  // Docs - Legal
  '/docs/terms',
  '/docs/privacy',
  '/docs/acceptable-use',
  '/docs/risk-disclosures',

  // Blog posts
  '/docs/blog/introducing-sardis',
  '/docs/blog/financial-hallucination-prevention',
  '/docs/blog/mcp-integration',
  '/docs/blog/mpc-wallets',
  '/docs/blog/sdk-v0-2-0',
  '/docs/blog/policy-engine-deep-dive',
  '/docs/blog/sardis-v0-5-protocols',
  '/docs/blog/understanding-ap2',
  '/docs/blog/mcp-46-tools',
  '/docs/blog/mcp-36-tools',
  '/docs/blog/why-sardis',
  '/docs/blog/fiat-rails',
  '/docs/blog/sardis-v0-7-production-hardening',
  '/docs/blog/sardis-v0-8-1-protocol-conformance',
  '/docs/blog/sardis-v0-8-2-release-readiness',
  '/docs/blog/sardis-v0-8-3-demo-ops-cloud-deploy',
  '/docs/blog/sardis-v0-8-4-packages-live',
  '/docs/blog/sardis-v0-8-7-launch-hardening',
  '/docs/blog/sardis-ai-agent-payments',
];

const CONCURRENCY = 5;
const PRERENDER_COMMENT = '<!-- prerendered-for-crawlers -->';

/**
 * Injects a comment into the <head> to indicate this page was pre-rendered.
 */
function injectPrerenderNote(html) {
  return html.replace('<head>', `<head>\n  ${PRERENDER_COMMENT}`);
}

/**
 * Derives the output file path for a given route.
 * / -> dist/index.html
 * /playground -> dist/playground/index.html
 * /docs/faq -> dist/docs/faq/index.html
 */
function routeToOutputPath(route) {
  if (route === '/') {
    return path.join(DIST, 'index.html');
  }
  // Strip leading slash, use as directory, write index.html inside
  const segments = route.replace(/^\//, '');
  return path.join(DIST, segments, 'index.html');
}

/**
 * Find a free port starting from the given number.
 */
async function findFreePort(start = 4173, max = 65535) {
  for (let port = start; port <= max; port += 1) {
    try {
      // eslint-disable-next-line no-await-in-loop
      const found = await new Promise((resolve, reject) => {
        const server = createNetServer();
        server.once('error', reject);
        server.listen(port, () => {
          const addr = server.address();
          const freePort = typeof addr === 'object' && addr ? addr.port : port;
          server.close(() => resolve(freePort));
        });
      });
      return found;
    } catch (error) {
      if (error && error.code === 'EADDRINUSE') {
        continue;
      }
      throw error;
    }
  }
  throw new Error(`No free port found in range ${start}-${max}`);
}

/**
 * Process a single route: visit with Puppeteer, grab HTML, save to dist/.
 */
async function processRoute(browser, baseUrl, route) {
  const url = `${baseUrl}${route}`;
  const outputPath = routeToOutputPath(route);

  let page;
  try {
    page = await browser.newPage();

    // Suppress console noise from the page
    page.on('console', () => {});
    page.on('pageerror', () => {});

    await page.goto(url, {
      waitUntil: 'networkidle0',
      timeout: 30000,
    });

    // Give React a moment to finish any deferred rendering
    await new Promise((resolve) => setTimeout(resolve, 500));

    const html = await page.content();
    const finalHtml = injectPrerenderNote(html);

    // Ensure output directory exists (idempotent)
    const outputDir = path.dirname(outputPath);
    fs.mkdirSync(outputDir, { recursive: true });

    fs.writeFileSync(outputPath, finalHtml, 'utf8');
    console.log(`  [OK] ${route} -> ${path.relative(ROOT, outputPath)}`);
  } catch (err) {
    console.error(`  [FAIL] ${route}: ${err.message}`);
  } finally {
    if (page) {
      await page.close().catch(() => {});
    }
  }
}

/**
 * Run routes in batches of CONCURRENCY size.
 */
async function processInParallel(browser, baseUrl, routes) {
  let index = 0;
  const total = routes.length;

  while (index < total) {
    const batch = routes.slice(index, index + CONCURRENCY);
    index += CONCURRENCY;

    const batchEnd = Math.min(index, total);
    console.log(`Processing routes ${batchEnd - batch.length + 1}-${batchEnd} of ${total}...`);

    await Promise.all(batch.map((route) => processRoute(browser, baseUrl, route)));
  }
}

async function main() {
  console.log('Sardis Pre-renderer starting...');
  console.log(`Dist directory: ${DIST}`);

  if (!fs.existsSync(DIST)) {
    console.error(`ERROR: dist/ directory not found at ${DIST}`);
    console.error('Run `vite build` first before pre-rendering.');
    process.exit(1);
  }

  const port = await findFreePort(4173);
  console.log(`Starting Vite preview server on port ${port}...`);

  // Start Vite's preview server serving the built dist/
  const previewServer = await vitePreview({
    root: ROOT,
    preview: {
      port,
      strictPort: true,
      host: '127.0.0.1',
      // Serve SPA fallback so all routes return index.html
      open: false,
    },
  });

  if (typeof previewServer.listen === 'function') {
    await previewServer.listen();
  }
  const resolvedLocalUrl = previewServer.resolvedUrls?.local?.[0];
  const baseUrl = (resolvedLocalUrl || `http://127.0.0.1:${port}`).replace(/\/$/, '');
  console.log(`Preview server running at ${baseUrl}\n`);

  let browser;
  let exitCode = 0;

  try {
    console.log('Launching Puppeteer...');
    browser = await puppeteer.launch({
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
      ],
    });

    console.log(`Pre-rendering ${ROUTES.length} routes (${CONCURRENCY} concurrent)...\n`);
    await processInParallel(browser, baseUrl, ROUTES);

    console.log('\nPre-rendering complete.');
  } catch (err) {
    console.error('Fatal error during pre-rendering:', err);
    exitCode = 1;
  } finally {
    if (browser) {
      await browser.close().catch(() => {});
    }
    if (typeof previewServer.close === 'function') {
      await previewServer.close().catch(() => {});
    } else if (previewServer.httpServer?.close) {
      await new Promise((resolve) => previewServer.httpServer.close(resolve));
    }
  }

  process.exit(exitCode);
}

main();
