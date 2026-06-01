-- Migration: 111_revocation_delegation_target.sql
-- Description: Extend the propagating Revocation to the Attenuated Delegation
--   Graph. Revoking a mandate / agent / delegation must propagate to the ENTIRE
--   delegation subtree (every descendant delegation -> revoked), recorded as
--   PropagationTargets with kind='delegation' in the signed RevocationProof.
--
--   Two changes:
--   1. Allow a revocation to be aimed directly at a single delegation hop
--      (target_kind='delegation') — its whole subtree is then killed.
--   2. (No schema change needed for the target list: revocations.targets is
--      JSONB, so the new PropagationKind 'delegation' is carried verbatim and
--      bound into the proof without a DB enum change.)

ALTER TYPE revocation_target_kind ADD VALUE IF NOT EXISTS 'delegation';

COMMENT ON TYPE revocation_target_kind IS
    'What a revocation is aimed at: agent (all its authority), mandate (one '
    'SpendingMandate + derivations), principal (all granted by a principal), or '
    'delegation (one delegation hop + its entire attenuated subtree).';
