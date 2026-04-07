Subject: [demo] Sardis — MPP payment governance for AI agents

---

Hi Ben,

Following up — we have a live MPP demo running on Tempo mainnet.

Sardis is a payment governance layer for AI agents. Non-custodial MPC wallets (Turnkey-signed), programmable spending policies (rate limits, vendor allowlists, amount caps), and a full audit trail. Agents spend autonomously; businesses stay in control.

The demo shows the full 402 flow: agent hits a paid endpoint, gets a WWW-Authenticate challenge, pays $0.001 pathUSD on Tempo mainnet (chain_id 4217), resends with the credential, Sardis runs 3 policy checks, and returns data with a Payment-Receipt header.

Live endpoint: https://api.sardis.sh/api/v2/demo/paid-data
Endpoint metadata: https://api.sardis.sh/api/v2/demo/info

Test it:
  npx mppx account create
  npx mppx fund --chain tempo-testnet
  npx mppx GET https://api.sardis.sh/api/v2/demo/paid-data

Loom walkthrough: [PLACEHOLDER — will record after final testing]

Next up: we want to add Mppx.stripe() for fiat SPT payments alongside Tempo crypto, so agents can pay with either rail through the same 402 flow.

Happy to jump on a call if useful.

Efe Baran Durmaz
Founder, Sardis Labs
sardis.sh
