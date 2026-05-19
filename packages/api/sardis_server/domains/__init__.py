"""Bounded domain modules for future independent deployment.

Currently Python modules with clear interfaces. They communicate through
the execution queue. Later they can become independently deployable services.

Domains:
- control_plane: Intent submission + routing
- policy_engine: Policy evaluation
- execution_engine: Chain execution
- ledger_core: Ledger + reconciliation
"""
