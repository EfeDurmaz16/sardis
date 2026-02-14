#!/usr/bin/env bash
set -euo pipefail

chain_mode="$(printf "%s" "${SARDIS_CHAIN_MODE:-simulated}" | tr '[:upper:]' '[:lower:]')"
mpc_name="$(printf "%s" "${SARDIS_MPC__NAME:-simulated}" | tr '[:upper:]' '[:lower:]')"
require_non_custodial="$(printf "%s" "${SARDIS_NON_CUSTODIAL_REQUIRED:-false}" | tr '[:upper:]' '[:lower:]')"
has_eoa_key="false"
if [[ -n "${SARDIS_EOA_PRIVATE_KEY:-}" ]]; then
  has_eoa_key="true"
fi

if [[ "$chain_mode" != "live" ]]; then
  echo "[custody][pass] chain mode is '$chain_mode' (simulation/sandbox posture)"
  exit 0
fi

if [[ "$mpc_name" == "simulated" ]]; then
  echo "[custody][fail] SARDIS_CHAIN_MODE=live cannot run with SARDIS_MPC__NAME=simulated"
  exit 1
fi

if [[ "$require_non_custodial" == "true" ]]; then
  if [[ "$mpc_name" != "turnkey" && "$mpc_name" != "fireblocks" ]]; then
    echo "[custody][fail] non-custodial required but mpc provider is '$mpc_name' (expected turnkey|fireblocks)"
    exit 1
  fi
  if [[ "$has_eoa_key" == "true" ]]; then
    echo "[custody][warn] SARDIS_EOA_PRIVATE_KEY is set; ensure local signer routes are disabled in deploy runtime"
  fi
  echo "[custody][pass] non-custodial live posture detected (mpc=$mpc_name)"
  exit 0
fi

if [[ "$mpc_name" == "local" ]]; then
  echo "[custody][warn] live mode is using local signer (custodial path)"
  exit 0
fi

echo "[custody][pass] live mode signer posture is '$mpc_name'"
