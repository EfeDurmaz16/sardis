# Acquirer / Sponsor Bank / QSA Ownership Notu

Tarih: 2026-02-25
Durum: Stripe, Lithic, Rain, Bridge outreach gönderildi; cevap bekleniyor.

## 1. Biz mi Acquirer / Sponsor Bank bulacağız?

Kısa cevap: çoğu durumda hayır.

- Stripe Issuing, Lithic, Rain, Bridge gibi issuer sağlayıcılarında sponsor bank/BIN programı genelde sağlayıcı tarafında gelir.
- Biz doğrudan bir kart kabul acquirer'ı kurmuyoruz; issuing programını entegre ediyoruz.
- Buna rağmen platform/service-provider olarak compliance sorumluluğumuz devam eder.

## 2. Sorumluluk kime ait?

Sağlayıcı tarafı (tipik):
- sponsor bank / BIN setup
- kart network program operasyonu
- issuer tarafı bazı kontrol ve raporlamalar

Bizim taraf:
- KYB/KYC/KYT süreçlerinin uygulanması
- policy enforcement + approval + audit trail
- incident response + access control + data minimization
- PAN lane açılıyorsa PCI kapsamı için ek kontroller

## 3. QSA nedir?

QSA (Qualified Security Assessor), PCI DSS denetim/yorumlama konusunda yetkili bağımsız denetçidir.

QSA ile yapılacak işler:
- scope belirleme (hangi sistemler PCI kapsamına giriyor)
- gap analizi
- remediation plan
- gerekliyse ROC/AOC süreci desteği

## 4. Şu anki Sardis için doğru yaklaşım

1. Default: tokenized/embedded checkout.
2. PAN lane: prod'da default kapalı.
3. PAN lane açılacaksa:
- merchant allowlist
- approval zorunluluğu
- executor attestation + replay protection
- persistent DB + append-only audit
- PCI/QSA readiness onayı

## 5. Partnerlerden yazılı istenecek 3 net cevap

1. Sponsor bank/BIN ownership ve sözleşmesel sınır kimde?
2. Bu mimaride bizim beklenen PCI deliverable'ımız ne? (SAQ/AOC/ROC path)
3. PAN hiç bizde değilse sorumluluk matrisi nasıl ayrılıyor?

## 6. Aksiyon Planı (bekleme sürecinde)

- Partner cevapları gelene kadar prod'da `tokenized/embedded-only` kal.
- PAN lane yalnızca break-glass, allowlist ve onayla aç.
- Gelen cevapları bu dosyaya ekleyip final responsibility matrix çıkar.
