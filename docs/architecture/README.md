# Architecture docs

**New here? Start with the top-level [`ARCHITECTURE.md`](../../ARCHITECTURE.md).**
It is the canonical, newcomer-facing map of the current repository: the single
authority path (`PaymentOrchestrator`), the typed provider-port layer, the route
domains, the three published packages, and where to make your first change.

The other files in this directory are **internal design notes** — deeper dives
on specific subsystems, written for maintainers working on that subsystem. They
are not a guided tour of the repo and some predate the May 2026 package
consolidation, so treat the top-level `ARCHITECTURE.md` and the live code as the
source of truth where they disagree.

| Note | Subsystem |
| --- | --- |
| [`production-critical-spine.md`](production-critical-spine.md) | The end-to-end money path that must stay correct |
| [`facility-gate-v1.md`](facility-gate-v1.md) | Facility gate design |
| [`attenuated-delegation.md`](attenuated-delegation.md) | Delegated authority / attenuation |
| [`propagating-revocation.md`](propagating-revocation.md) | Revocation propagation |
| `connect-packages.md`, `openai-packages.md`, `sdk-packages.md` | Historical package-boundary notes (referenced by `scripts/package_layout_check.py`; pre-consolidation naming) |
