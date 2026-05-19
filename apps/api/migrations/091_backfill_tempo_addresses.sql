-- Migration 091: Backfill Tempo chain addresses for all existing wallets
--
-- Tempo is an EVM-compatible chain so it shares the same address as other
-- EVM chains (same private key -> same address).  For wallets that already
-- have a "base" (or any EVM) address but no "tempo" key, this copies the
-- address into the "tempo" slot.

UPDATE wallets
SET    addresses = addresses || jsonb_build_object('tempo', addresses ->> 'base')
WHERE  addresses IS NOT NULL
  AND  addresses ? 'base'
  AND  NOT (addresses ? 'tempo');

-- Fallback: wallets that have "ethereum" but not "base" or "tempo"
UPDATE wallets
SET    addresses = addresses || jsonb_build_object('tempo', addresses ->> 'ethereum')
WHERE  addresses IS NOT NULL
  AND  addresses ? 'ethereum'
  AND  NOT (addresses ? 'tempo');

-- Fallback: wallets that have "base_sepolia" but not "base"/"ethereum"/"tempo"
UPDATE wallets
SET    addresses = addresses || jsonb_build_object('tempo', addresses ->> 'base_sepolia')
WHERE  addresses IS NOT NULL
  AND  addresses ? 'base_sepolia'
  AND  NOT (addresses ? 'tempo');
