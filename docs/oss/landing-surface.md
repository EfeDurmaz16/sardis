# Public Landing Surface Policy

The public landing app is part of the OSS repository because it explains the
protocol, SDKs, reference API, docs, and developer adoption path. It must not
make the private hosted product look like a required contributor surface.

## Public-First Surfaces

These surfaces are indexed by crawlers, language models, docs readers, and
contributors. They must point to public docs, the public API reference, or the
GitHub repository:

- `apps/landing/app/sitemap.ts`
- `apps/landing/app/llms.txt/route.ts`
- `apps/landing/app/llms-full.txt/route.ts`
- public docs pages under `docs/`
- environment examples such as `.env.example`

Do not list `https://app.sardis.sh`, dashboard signup, dashboard API keys,
hosted checkout, or hosted billing as canonical OSS surfaces in these files.
Those belong to the private hosted product.

## Commercial CTA Surfaces

Interactive marketing pages may link to the hosted product when the link is a
deliberate commercial conversion path rather than contributor onboarding.
Examples include:

- hero or pricing CTAs such as "Get started" or "Start building"
- comparison-page bottom CTAs
- pricing-card billing CTAs

These links should be treated as product handoff links. They must not be copied
into contributor docs, SDK examples, CLI demos, generated LLM metadata, sitemap
entries, or environment templates.

## Contributor CTA Defaults

When a page or artifact is meant for contributors, prefer:

- `https://sardis.sh/docs`
- `https://docs.sardis.sh`
- `https://github.com/EfeDurmaz16/sardis`
- local commands such as `pnpm run check:contributor`

If a future public UI package needs a hosted demo, document the demo as an OSS
demo endpoint, not as the closed hosted product.

## Validation

Run this before changing landing, docs, SDK onboarding, or environment examples:

```bash
python3 scripts/oss_surface_check.py
pnpm --dir apps/landing typecheck
pnpm run check:contributor
```
