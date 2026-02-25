# PCI Approvals + DB Hardening Checklist

Date: 2026-02-25
Owner: Sardis Compliance + Platform

## 1. Kimlerden Ne Onayı Lazım

1. Acquirer / sponsor bank
- Soru: Bu modelde biz `service provider` mı `merchant facilitator` mı sayılıyoruz?
- Çıktı: PCI validation yolu (SAQ/ROC), yıllık kanıt teslim formatı.

2. Issuer partner (Stripe/Lithic/Rain/Bridge)
- Soru: Embedded/iframe + tokenized path’i prod’da kullanırken PAN exposure sorumluluk sınırı nedir?
- Çıktı: Responsibility matrix (PAN, CVV, auth controls, webhook SLO, breach-notification).

3. QSA (Qualified Security Assessor)
- Soru: Bizim enclave + BYO-executor modelinde scope boundary ve compensating control kabulü.
- Çıktı: Scope memo + remediation list + hedef certification path.

4. Legal counsel (payments/data)
- Soru: DPA, cross-border data transfer, KYB/KYA kayıt saklama süreleri.
- Çıktı: ToS, DPA, incident disclosure clause, data retention policy.

## 2. Hemen Gönderilecek Mail (Acquirer / Sponsor Bank)

Subject: Sardis autonomous card execution architecture - PCI scope confirmation request

Body:
We are launching an autonomous purchasing stack with the following controls:
- tokenized/embedded checkout as default,
- PAN-entry disabled by default in production,
- per-merchant allowlist for break-glass PAN lane,
- isolated executor with one-time secret references and short TTL,
- deterministic policy + approval gate + immutable audit trail.

Please confirm:
1) our PCI role classification for this architecture,
2) required validation artifact type and cadence,
3) any mandatory controls for real-time auth and card data handling.

We can share data-flow diagram and control matrix immediately.

## 3. Hemen Gönderilecek Mail (Stripe/Lithic/Rain/Bridge)

Subject: Request for production architecture confirmation (embedded card + controlled PAN lane)

Body:
We need confirmation for a production deployment where:
- default path is embedded/iframe or tokenized checkout,
- PAN lane is restricted, allowlisted, and approval-gated,
- issuer auth controls are enforced (merchant lock, velocity, spend caps, auto-freeze),
- audit evidence is stored in append-only hash-chain backed store.

Please confirm:
1) supported implementation pattern and constraints,
2) funding model options (Treasury/FBO/stablecoin prefund),
3) compliance boundary and incident handling responsibilities.

## 4. DB Hardening (Acil Uygulanacak)

1. PostgreSQL zorunlu (prod)
- Secure checkout active ise prod’da in-memory store yasak.

2. PAN/CVV DB’ye yazmama
- Sadece redacted metadata + job state + audit events saklanır.

3. Append-only audit
- Checkout eventleri audit store’a append edilir, silme/güncelleme yok.

4. Encryption & keys
- Disk encryption + backup encryption + KMS key rotation.

5. Access control
- Least privilege DB role, app-only write role, read role ayrımı.

6. Network & transport
- Private VPC peering / private IP, TLS zorunlu, public DB endpoint kapalı.

7. Retention
- KYB/KYA/audit için yasal saklama süresi + purge policy (PAN olmayan veri için).

8. Monitoring
- Failed attestation, replay denemesi, policy deny, approval bypass attempt alarm.

## 5. Go/No-Go

Go:
- Acquirer role classification net,
- issuer architecture approval yazılı,
- prod DB hardening checklist tamam,
- PAN lane only by explicit allowlist + approval.

No-Go:
- Role/scope belirsiz,
- issuer auth controls eksik,
- prod’da in-memory veya audit gap varsa.
