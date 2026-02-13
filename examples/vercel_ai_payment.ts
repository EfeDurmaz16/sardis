/**
 * Vercel AI SDK + Sardis TypeScript Example
 * ==========================================
 *
 * This example shows how to use the Vercel AI SDK with Sardis
 * to build a streaming agent that can execute payments.
 *
 * Prerequisites:
 *   npm install ai @ai-sdk/openai @sardis/sdk zod
 *
 * Run:
 *   npx tsx examples/vercel_ai_payment.ts
 */

import { generateText, tool } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";
import { SardisClient } from "@sardis/sdk";

const sardis = new SardisClient({ apiKey: process.env.SARDIS_API_KEY ?? "sim_demo" });

async function main() {
  const agent = await sardis.agents.create({
    name: "vercel-ai-agent",
    description: "Vercel AI SDK procurement example agent",
  });

  // Create a wallet for the agent
  const wallet = await sardis.wallets.create({
    agent_id: agent.agent_id,
    currency: "USDC",
    limit_per_tx: "100.00",
    limit_total: "500.00",
  });

  const { text, toolResults } = await generateText({
    model: openai("gpt-4o"),
    system:
      "You are a procurement agent with a Sardis wallet. " +
      "You can make payments for software and API credits. " +
      "Always explain what you are purchasing before paying.",
    prompt: "Purchase $25 of OpenAI API credits for our research team.",
    tools: {
      sardisPay: tool({
        description:
          "Execute a payment through Sardis with policy enforcement",
        parameters: z.object({
          to: z.string().describe("Recipient address or merchant ID"),
          amount: z.string().describe("Amount in USD (e.g. '25.00')"),
          token: z.enum(["USDC", "USDT", "EURC"]),
          purpose: z.string().describe("Reason for the payment"),
        }),
        execute: async ({ to, amount, token, purpose }) => {
          const result = await sardis.wallets.transfer(wallet.wallet_id, {
            destination: to,
            amount,
            token,
            chain: "base_sepolia",
            domain: "vercel-ai.local",
            memo: purpose,
          });
          return {
            status: result.status,
            txHash: result.tx_hash,
            amount: result.amount,
            chain: result.chain,
          };
        },
      }),
      sardisBalance: tool({
        description: "Check the wallet balance and remaining limits",
        parameters: z.object({}),
        execute: async () => {
          const info = await sardis.wallets.getBalance(wallet.wallet_id, "base_sepolia", "USDC");
          return {
            balance: info.balance,
            chain: info.chain,
            token: info.token,
            walletId: info.wallet_id,
          };
        },
      }),
    },
    maxSteps: 5,
  });

  console.log("Agent response:", text);
  console.log("Tool results:", JSON.stringify(toolResults, null, 2));
}

main().catch(console.error);
