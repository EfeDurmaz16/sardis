/**
 * @sardis/reference — how Sardis decides if an agent may spend.
 *
 * Pure, deterministic, money-free TS mirror of the Sardis authority-decision
 * and protocol-verification logic. No network, no provider clients, no DB, no
 * key custody, no `fetch`. It never executes a payment — the private backend
 * owns execution; this package owns the decision contract so the ecosystem can
 * audit it offline.
 *
 * Barrels are populated by the type/policy/verify modules in later commits.
 */
export {};
