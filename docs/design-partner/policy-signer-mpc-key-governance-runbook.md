# Policy Signer + MPC Key Governance Runbook

Date: 2026-02-26  
Owner: Sardis Security + Platform

## Scope

Bu runbook iki kritik alanı kapsar:
1. `policySigner` rotasyonu (ERC-4337 smart account seviyesi)
2. MPC provider credential lifecycle (Turnkey / Fireblocks)

## 1) Policy Signer Rotation (On-chain)

Contract capability:
- `SardisSmartAccount.setPolicySigner(address)` owner-only çağrıdır.

Operational flow:
1. Yeni signer üret (HSM/MPC kontrollü).
2. Canlıya almadan önce staging’de dry-run ile `setPolicySigner` çağrısını doğrula.
3. Mainnet değişikliği için change ticket + 4-eyes approval zorunlu.
4. Değişiklik sonrası:
   - yeni signer ile test UserOperation sign
   - eski signer reject davranışı doğrula
5. Audit evidence:
   - tx hash
   - wallet/smart account id
   - requester + approver
   - timestamp

Cadence:
- Planlı rotation: 90 gün
- Acil rotation: compromise şüphesi olduğunda derhal

## 2) MPC Credential Lifecycle (Turnkey / Fireblocks)

Requirements:
1. Prod’da plaintext key materyali kod/depo/log içinde tutulmaz.
2. Credential’lar yalnızca secret manager üzerinden inject edilir.
3. Revocation + reissue prosedürü tanımlı olmalıdır.
4. Her credential değişimi incident/change kaydına bağlanır.

Minimum evidence:
- hangi credential değişti (`TURNKEY_*` veya `FIREBLOCKS_*`)
- change id / ticket
- rollout zamanı
- health-check sonucu

## 3) Drill Checklist (Quarterly)

1. Non-prod ortamda signer rotate et.
2. En az bir ödeme akışını yeni signer ile başarıyla tamamla.
3. Eski signer ile denemede beklenen fail behavior’u doğrula.
4. Sonuçları evidence paketine ekle.

## 4) Release Gate

`bash scripts/release/key_governance_check.sh` aşağıdakileri doğrular:
- runbook varlığı
- policy signer rotation surface varlığı
- Turnkey/Fireblocks config surface varlığı
- key rotation unit testleri
