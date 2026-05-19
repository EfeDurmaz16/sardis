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
| _None_ | - | Keep new tracked packages out of fallback-only validation. | Add package-owned tests, a build command, or archive the package before exposing it as a contribution path. |

## External-Tool Validation

These packages have a more specific validation command, but it depends on a
tool that is not part of the default contributor loop.

| Package | External tool | Validation | Required next step |
| --- | --- | --- | --- |
| `packages/sardis-zkp/` | Nargo | `(cd packages/sardis-zkp && nargo check)` | Document Nargo install/version and add fixtures before using these circuits in runtime decisions. |

## Maintenance Rule

Do not move a package from `experimental` to `supported` in `docs/packages.md`
while it is listed here. Remove a package from this backlog only when it has a
package-owned validation command or when it is archived from the public repo.
