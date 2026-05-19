# 10 Frontend UX Code Audit

## Findings

### High: Authenticated frontend API access is inconsistent

- Evidence: dashboard uses `/api/sardis` same-origin proxy; landing reads stored token/cookies and calls `NEXT_PUBLIC_API_URL`.
- Impact: Landing can break with HttpOnly sessions and risks normalizing browser-readable auth tokens.
- Recommended action: Make dashboard proxy approach the standard for authenticated browser calls.
- Action type: Migration.
- Estimated risk: Medium.
- Validation method: manual auth smoke and typecheck.

### High: Dashboard has overlapping request layers

- Evidence: `apps/dashboard/hooks/use-sardis.ts`, `apps/dashboard/lib/sardis-api.ts`, `apps/dashboard/utils/dashboard-client.ts`, and direct `/api/sardis` fetches all exist.
- Impact: error handling, auth failure behavior, cache settings, list normalization, and UX states can differ by page.
- Recommended action: consolidate to one dashboard API client plus one React hook wrapper; disallow raw dashboard fetches outside that client.
- Action type: Architecture refactor.
- Estimated risk: Medium.
- Validation method: focused smoke on agents, wallets, mandates, and approvals.

### High: Canvas public exports are stale

- Evidence: canvas sitemap points to `/pages/...` URLs while current Astro output/nav uses root slugs; `llms-full.txt` hashes differ across root, `public`, and `canvases`.
- Impact: crawlers and LLM readers get stale or broken public content.
- Recommended action: generate sitemap and LLM exports from one canvas registry.
- Action type: Generated export repair.
- Estimated risk: Low.
- Validation method: sitemap/source comparison and hash equality check.

### Medium: Dashboard mixes product constants and client transport

- Evidence: `apps/dashboard/lib/sardis-api.ts` defines API transport, response parsing, domain records, onboarding steps, and spending policy templates.
- Impact: Changes to policy defaults or transport require touching one large file.
- Recommended action: Split into `transport`, `types`, `onboarding`, and `policy-templates` modules or move types to SDK.
- Action type: Refactor.
- Estimated risk: Low.
- Validation method: `pnpm --filter @sardis/app-dashboard typecheck`.

### Medium: Static canvases may be stale build output

- Evidence: `canvases/*/index.html` duplicates app/canvas-site output and public narrative pages.
- Impact: Public claims and docs drift.
- Recommended action: Decide whether `canvases` is source or generated artifact; if generated, move to build output or publish artifact.
- Action type: Documentation/deletion.
- Estimated risk: Low.
- Validation method: link and sitemap audit.
