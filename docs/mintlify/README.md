# Mintlify Documentation

Mintlify tabanlı API dokümantasyonu için çalışma rehberi.

## Kurulum
```bash
cd docs/mintlify
npm install -g mintlify   # veya npx mintlify ile global kurulum olmadan
```

## Açık kaynak önizleme
```bash
# OpenAPI şemasını güncelle
python export_openapi.py

# Dokümanı çalıştır
mintlify dev
# veya
npx mintlify dev
```

## Lint / Kontrol
```bash
mintlify lint
# veya
npx mintlify lint
```

## Dağıtım
- Bu repo yeni bir Mintlify projesine bağlanacak.
- Mintlify dashboard üzerinden yeni proje açın ve repo’yu bağlayın.
- Build kaynağı: `docs/mintlify`

## Dizın Yapısı
- `mint.json` — site yapılandırması
- `reference/openapi.mdx` — OpenAPI referansı (./openapi.json)
- `guides/*.mdx` — kullanım kılavuzları (auth, payments, cards, mandates)
- `export_openapi.py` — FastAPI şemasını üretir




