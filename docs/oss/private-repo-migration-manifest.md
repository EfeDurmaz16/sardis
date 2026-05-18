# Private Repository Migration Manifest

This file records tracked public-repo paths that should move to a private company or product repository instead of remaining in Sardis OSS.

The public repository should not contain private commercial planning, hiring, investor, partnership-development, customer-specific, or GTM workflow material. When the private repository is created, recover these files from git history or a local private archive, then remove them from public history if needed.

## Removed From Public Tracking

The following categories are private by default:

- `docs/cdp/` - commercial/customer-development drafts
- `docs/hiring/` - internal hiring materials
- `docs/partnerships/` - partner-development and LOI drafts
- `docs/sales/` - sales prospecting and outreach strategy
- `docs/yc/` - accelerator application drafts
- `scripts/gtm/` - GTM automation and lead workflow scripts

## Follow-Up

After this branch lands:

1. Create `sardis-product` or `sardis-company-private`.
2. Export these paths from the last pre-removal commit if they are needed.
3. Keep the public repo clean by enforcing the boundary in review.
4. If any removed material was already pushed to a public remote and is truly sensitive, perform a history rewrite with maintainer approval.
