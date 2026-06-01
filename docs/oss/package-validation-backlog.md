# Package Validation Backlog

`pnpm run check:contributor` fails if a tracked public package has no
package-owned, credential-free validation command and instead falls back to the
repo-wide contributor gate. This file tracks packages that need a non-default
external tool (and therefore cannot yet have a fully self-contained gate entry).

## Current backlog

_Empty._

After the May 2026 consolidation to three published packages, each has a
credential-free validation command:

| Package | Validation command |
| --- | --- |
| `sardis` (PyPI) | `uv run pytest packages/sardis/tests/ -q` |
| `sardis` (npm) | `pnpm --filter sardis typecheck && pnpm --filter sardis test` |
| `@sardis/mcp-server` (npm) | `pnpm --filter @sardis/mcp-server build && pnpm --filter @sardis/mcp-server test` |

If you add a package that requires a tool not available in the credential-free
gate (e.g. a live provider sandbox), list it here with the reason and the
intended path to a self-contained command, so the fallback is intentional and
visible rather than silent.
