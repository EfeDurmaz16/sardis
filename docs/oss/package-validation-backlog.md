# Package Validation Backlog

This backlog tracks public packages that are documented and intentionally kept
in the repo, but still do not have a strong package-owned validation command
that a new contributor can run with the default repo toolchain.

Use this alongside:

```bash
pnpm repo:package-validation
pnpm run check:contributor
```

## Fallback-Only Packages

These packages currently fall back to `pnpm run check:contributor` in
`pnpm repo:package-validation`. That means the repository can still be checked,
but the package itself does not yet prove its own behavior.

| Package | Current status | Required next step | Promotion or archive rule |
| --- | --- | --- | --- |
| `packages/sardis-agentkit/` | `experimental` | Add a minimal import or adapter smoke test under package-owned tests. | Promote only after current AgentKit API compatibility is verified; archive if the upstream integration shape is stale. |
| `packages/sardis-coinbase/` | `experimental` | Add sandbox-safe adapter smoke coverage or a documented provider-not-configured test. | Promote only after current Coinbase/AgentKit/x402 APIs are rechecked; archive if it duplicates a better-supported package. |
| `packages/sardis-connect/` | `experimental` | Clarify overlap with `packages/sardis-connect-js/` and add a package-owned smoke test. | Promote only after the Python/JS boundary is explicit; archive one side if the split is not useful. |
| `packages/sardis-openclaw/` | `experimental` | Add static validation for `SKILL.md`, `clawhub.json`, and API action examples. | Promote only if OpenClaw remains a relevant integration surface; archive if ecosystem use is unclear. |

## External-Tool Validation

These packages have a more specific validation command, but it depends on a
tool that is not part of the default contributor loop.

| Package | External tool | Validation | Required next step |
| --- | --- | --- | --- |
| `packages/sardis-e2b/` | E2B CLI | `(cd packages/sardis-e2b && e2b template build --name sardis-agent)` | Add a static template smoke test that does not require E2B auth. |
| `packages/sardis-zkp/` | Nargo | `(cd packages/sardis-zkp && nargo check)` | Document Nargo install/version and add fixtures before using these circuits in runtime decisions. |

## Maintenance Rule

Do not move a package from `experimental` to `supported` in `docs/packages.md`
while it is listed here. Remove a package from this backlog only when it has a
package-owned validation command or when it is archived from the public repo.
