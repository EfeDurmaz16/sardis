# Five-Track Hardening Plan (Atomic Execution)

Date: 2026-02-25
Owner: Sardis Platform

## Scope

Bu plan aşağıdaki 5 hattı sıralı ve atomik commitlerle ilerletir:
1. Multi-instance güvenlik tamamlama
2. Reference executor servisi
3. Otomatik risk response
4. Provider-agnostic funding/routing
5. Compliance evidence paketi

## Track 1: Multi-instance Güvenlik

T1-A:
- `secret_ref` payload’larını process-memory yerine cache/redis tabanlı one-time store’a taşı.
- Amaç: multi-instance + restart sonrası tutarlılık.

T1-B:
- secret consume için distributed lock + replay-safe consume-once semantiği.

T1-C:
- prod fail-closed kontrolleri:
  - persistent job store zorunlu
  - redis/cache erişimi yoksa PAN lane kapalı

## Track 2: Reference Executor Servisi

T2-A:
- signed-dispatch doğrulayan worker endpoint contract’ı.
- dispatch token + signature verify + idempotent acceptance.

T2-B:
- callback client:
  - `/secure/jobs/{job_id}/complete` çağrısı
  - retry + timeout + idempotent completion key.

T2-C:
- execution runner interface:
  - tokenized flow
  - pan-entry flow (secret_ref consume)
  - structured failure reason mapping.

## Track 3: Otomatik Risk Response

T3-A:
- risk trigger taxonomy:
  - policy deny
  - attestation replay
  - merchant anomaly
  - excessive decline burst.

T3-B:
- response orchestrator:
  - freeze card
  - rotate card
  - create alert
  - append immutable audit event.

T3-C:
- severity-based cooldown + auto-unfreeze policy (ops onayı ile).

## Track 4: Provider-Agnostic Funding/Routing

T4-A:
- ortak funding adapter interface (fiat/stablecoin).

T4-B:
- fallback persistence:
  - provider attempt history
  - deterministic retry order.

T4-C:
- capability matrix endpoint:
  - provider-by-provider funding/issuing readiness.

## Track 5: Compliance Evidence Paketi

T5-A:
- secure checkout + approval + policy + attestation birleşik evidence export endpoint’i.
  - Durum: ✅ Tamamlandı (`GET /api/v2/checkout/secure/jobs/{job_id}/evidence`)

T5-B:
- digest + hash-chain integrity summary.
  - Durum: ✅ Tamamlandı (`integrity.digest_sha256`, `integrity.hash_chain_tail`)

T5-C:
- audit bundle metadata:
  - generated_at
  - scope window
  - entry counts
  - verifier hints.
  - Durum: ✅ Tamamlandı (`generated_at`, `scope_window`, `event_count`, `verifier_hints`)

## Delivery Rules

- Her atomik adım ayrı commit.
- Her adımda test çalıştır ve sonucu commit mesajında izlenebilir bırak.
- PAN/CVV hiçbir log/payload/export içine alınmaz.
