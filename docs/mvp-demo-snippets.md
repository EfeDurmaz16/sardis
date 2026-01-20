# Sardis MVP Demo Snippets (Base Sepolia)

## Prereqs
- Run API: `uvicorn sardis_api.main:create_app --factory --reload`
- Env (example):
  - `SARDIS_CHAIN_MODE=live`
  - `SARDIS_CHAINS__0__NAME=base_sepolia`
  - `SARDIS_CHAINS__0__RPC_URL=https://sepolia.base.org`
  - `SARDIS_EOA_PRIVATE_KEY=<funded testnet key>`
  - `SARDIS_EOA_ADDRESS=<same address>`
- Fund EOA with Base Sepolia ETH + USDC (testnet faucet).

## Python (requests + pynacl)
```python
import base64, os, time, uuid, requests
from nacl import signing

BASE_URL = os.getenv("SARDIS_API_BASE_URL", "http://localhost:8000/api/v2/mvp")

def issue():
    r = requests.post(f"{BASE_URL}/tap/issue", json={"domain": "example.com"})
    r.raise_for_status()
    return r.json()

def sign_mandate(identity, secret_hex, destination):
    mandate_id = f"mandate_{uuid.uuid4().hex[:12]}"
    nonce = str(int(time.time() * 1000))
    expires = int(time.time()) + 300
    amount_minor = 5_000_000  # 5 USDC (6 decimals)
    audit_hash = f"audit::{mandate_id}"
    canonical = "|".join([mandate_id, identity["agent_id"], str(amount_minor), "USDC", "base_sepolia", destination, audit_hash]).encode()
    payload = b"|".join([identity["domain"].encode(), nonce.encode(), b"checkout", canonical])
    sig = signing.SigningKey(bytes.fromhex(secret_hex)).sign(payload).signature
    proof_val = base64.b64encode(sig).decode()
    return {
        "mandate_id": mandate_id,
        "mandate_type": "payment",
        "issuer": identity["agent_id"],
        "subject": identity["agent_id"],
        "expires_at": expires,
        "nonce": nonce,
        "domain": identity["domain"],
        "purpose": "checkout",
        "chain": "base_sepolia",
        "token": "USDC",
        "amount_minor": amount_minor,
        "destination": destination,
        "audit_hash": audit_hash,
        "proof": {
            "type": "DataIntegrityProof",
            "verification_method": identity["verification_method"],
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "proof_purpose": "assertionMethod",
            "proof_value": proof_val,
        },
    }

identity = issue()
secret = identity["private_key"]
mandate = sign_mandate(identity, secret, os.getenv("DESTINATION_ADDRESS", identity["agent_id"][:42]))
print(requests.post(f"{BASE_URL}/mandates/validate", json={"mandate": mandate}).json())
print(requests.post(f"{BASE_URL}/payments/execute", json={"mandate": mandate}).json())
```

## Node (fetch + tweetnacl)
```javascript
import fetch from "node-fetch";
import nacl from "tweetnacl";

const BASE_URL = process.env.SARDIS_API_BASE_URL || "http://localhost:8000/api/v2/mvp";

async function issue() {
  const res = await fetch(`${BASE_URL}/tap/issue`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ domain: "example.com" }),
  });
  return res.json();
}

function signMandate(identity, secretHex, destination) {
  const mandateId = `mandate_${Math.random().toString(16).slice(2, 14)}`;
  const nonce = Date.now().toString();
  const expires = Math.floor(Date.now() / 1000) + 300;
  const amountMinor = 5_000_000; // 5 USDC
  const auditHash = `audit::${mandateId}`;
  const canonical = [
    mandateId,
    identity.agent_id,
    amountMinor.toString(),
    "USDC",
    "base_sepolia",
    destination,
    auditHash,
  ].join("|");
  const payload = Buffer.from(
    `${identity.domain}|${nonce}|checkout|${canonical}`,
    "utf8"
  );
  const secret = Buffer.from(secretHex, "hex");
  const signature = nacl.sign.detached(payload, secret);
  const proofValue = Buffer.from(signature).toString("base64");
  return {
    mandate_id: mandateId,
    mandate_type: "payment",
    issuer: identity.agent_id,
    subject: identity.agent_id,
    expires_at: expires,
    nonce,
    domain: identity.domain,
    purpose: "checkout",
    chain: "base_sepolia",
    token: "USDC",
    amount_minor: amountMinor,
    destination,
    audit_hash: auditHash,
    proof: {
      type: "DataIntegrityProof",
      verification_method: identity.verification_method,
      created: new Date().toISOString(),
      proof_purpose: "assertionMethod",
      proof_value: proofValue,
    },
  };
}

(async () => {
  const identity = await issue();
  const secret = identity.private_key;
  const destination = process.env.DESTINATION_ADDRESS || identity.agent_id.slice(0, 42);
  const mandate = signMandate(identity, secret, destination);
  console.log(await (await fetch(`${BASE_URL}/mandates/validate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mandate }) })).json());
  console.log(await (await fetch(`${BASE_URL}/payments/execute`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ mandate }) })).json());
})();
```



