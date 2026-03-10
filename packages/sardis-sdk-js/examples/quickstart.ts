/**
 * Sardis TypeScript SDK — Quickstart Example
 *
 * Demonstrates: create agent → set spending policy → make payment → check balance.
 *
 * Run: npx ts-node examples/quickstart.ts
 */
import { SardisClient } from '@sardis/sdk';

async function main() {
  const apiKey = process.env.SARDIS_API_KEY;
  if (!apiKey) {
    console.log('Set SARDIS_API_KEY environment variable first.');
    console.log('Get your key at: https://dashboard.sardis.sh/api-keys');
    return;
  }

  const client = new SardisClient({ apiKey });

  // 1. Create an AI agent
  const agent = await client.agents.create({ name: 'My First Agent' });
  console.log(`Agent created: ${agent.agent_id}`);

  // 2. Create a wallet
  const wallet = await client.wallets.create({
    agent_id: agent.agent_id,
    chain: 'base',
  });
  console.log(`Wallet created: ${wallet.wallet_id} (${wallet.address})`);

  // 3. Set spending policy
  const policy = await client.policies.parse({
    text: 'Max $100 per transaction, $500 per day, no gambling',
  });
  await client.policies.apply({
    wallet_id: wallet.wallet_id,
    policy,
  });
  console.log(`Policy applied: ${policy.summary}`);

  // 4. Make a payment
  const payment = await client.payments.send({
    wallet_id: wallet.wallet_id,
    to: 'merchant_demo',
    amount: '25.00',
    purpose: 'API usage - OpenAI',
  });
  console.log(`Payment: ${payment.status} (tx: ${payment.tx_id})`);

  // 5. Check balance
  const balance = await client.wallets.getBalance(wallet.wallet_id);
  console.log(`Balance: ${balance.balance} ${balance.currency}`);
}

main().catch(console.error);
