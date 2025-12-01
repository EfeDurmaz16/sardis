# Sardis Mandate Schemas (First Pass)

All mandates are conveyed as W3C Verifiable Credentials using Data Integrity proofs. Each VC must include TAP binding fields: `domain`, `nonce`, `timestamp`, `purpose`, `expires_at`.

## Intent Mandate
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://schemas.sardis.network/ap2/intent.json",
  "type": "object",
  "required": ["@context", "type", "issuer", "credentialSubject", "proof"],
  "properties": {
    "@context": {"const": ["https://www.w3.org/2018/credentials/v1", "https://sardis.network/ap2"]},
    "type": {"const": ["VerifiableCredential", "IntentMandate"]},
    "issuer": {"type": "string", "format": "uri"},
    "issuanceDate": {"type": "string", "format": "date-time"},
    "expirationDate": {"type": "string", "format": "date-time"},
    "credentialSubject": {
      "type": "object",
      "required": ["mandateId", "agentId", "scope", "nonce", "domain", "purpose"],
      "properties": {
        "mandateId": {"type": "string"},
        "agentId": {"type": "string"},
        "scope": {"type": "array", "items": {"type": "string"}},
        "maxAmountMinor": {"type": "integer", "minimum": 0},
        "currency": {"type": "string"},
        "nonce": {"type": "string"},
        "domain": {"type": "string", "format": "uri"},
        "purpose": {"const": "intent"}
      }
    },
    "proof": {"$ref": "https://www.w3.org/2018/credentials/v1#DataIntegrityProof"}
  }
}
```

## Cart Mandate
```json
{
  "$id": "https://schemas.sardis.network/ap2/cart.json",
  "allOf": [{"$ref": "./intent.json"}],
  "properties": {
    "type": {"const": ["VerifiableCredential", "CartMandate"]},
    "credentialSubject": {
      "required": ["cartHash", "lineItems", "merchantDomain", "currency", "nonce", "purpose"],
      "properties": {
        "cartHash": {"type": "string", "description": "Hash of intent + line items"},
        "lineItems": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["sku", "description", "amountMinor"],
            "properties": {
              "sku": {"type": "string"},
              "description": {"type": "string"},
              "amountMinor": {"type": "integer", "minimum": 0},
              "category": {"type": "string"}
            }
          }
        },
        "merchantDomain": {"type": "string", "format": "uri"},
        "currency": {"type": "string"},
        "taxesMinor": {"type": "integer", "minimum": 0},
        "purpose": {"const": "cart"}
      }
    }
  }
}
```

## Payment Mandate
```json
{
  "$id": "https://schemas.sardis.network/ap2/payment.json",
  "allOf": [{"$ref": "./intent.json"}],
  "properties": {
    "type": {"const": ["VerifiableCredential", "PaymentMandate"]},
    "credentialSubject": {
      "required": ["paymentHash", "cartHash", "amountMinor", "token", "chain", "destination", "auditHash", "nonce", "purpose"],
      "properties": {
        "paymentHash": {"type": "string"},
        "cartHash": {"type": "string"},
        "amountMinor": {"type": "integer", "minimum": 0},
        "token": {"enum": ["USDC", "USDT", "PYUSD", "EURC"]},
        "chain": {"enum": ["base", "ethereum", "polygon", "solana", "arbitrum", "optimism"]},
        "destination": {"type": "string"},
        "auditHash": {"type": "string", "description": "Merkle leaf linking Payment -> Ledger"},
        "merchantAccount": {"type": "string"},
        "nonce": {"type": "string"},
        "purpose": {"const": "checkout"}
      }
    }
  }
}
```

### Signature Requirements
- Proofs use Data Integrity with Ed25519Signature2020 (upgradeable to P-256)
- `proofValue` signs canonicalized JSON-LD with TAP domain binding: `hash(@context + credentialSubject + domain + nonce + purpose)`
- Replay defense: `mandateId` + `nonce` stored in Redis w/ `expirationDate`

### Audit Chain
```
Intent.proof.hash --(SHA-256)--> cart.intentHash
Cart.proof.hash   --(SHA-256)--> payment.cartHash
Payment.auditHash --(Merkle)--> ledger.anchor
Ledger.anchor     --(Keccak)--> on-chain receipt anchor
```
