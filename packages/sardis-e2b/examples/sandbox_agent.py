"""Example: Running a Sardis-enabled agent in an E2B sandbox."""
from sardis import SardisClient

# Works in simulation mode inside the sandbox
client = SardisClient()
wallet = client.wallets.create(name="sandbox-agent", policy="Max $50/day")

# Agent can make payments
tx = wallet.pay(to="openai.com", amount="10.00", purpose="API credits")
print(f"Payment: {tx.status.value} - {tx.tx_id}")
print(f"Balance remaining: {wallet.balance}")
