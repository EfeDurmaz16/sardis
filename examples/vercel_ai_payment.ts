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
  // Create a wallet with a natural language spending policy
  const wallet = await sardis.wallets.create({
    name: "vercel-ai-agent",
    chain: "base",
    token: "USDC",
    policy: `
      Max $100 per transaction.
      Daily limit $500.
      Only allow SaaS, developer tools, and API services.
    `,
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
          const result = await sardis.payments.send({
            walletId: wallet.id,
            to,
            amount,
            token,
            memo: purpose,
          });
          return {
            status: result.status,
            txHash: result.txHash,
            amount: result.amount,
            policyResult: result.policyResult,
          };
        },
      }),
      sardisBalance: tool({
        description: "Check the wallet balance and remaining limits",
        parameters: z.object({}),
        execute: async () => {
          const info = await sardis.wallets.get(wallet.id);
          return {
            balance: info.balance,
            spentToday: info.spentDaily,
            dailyLimit: info.dailyLimit,
            remaining: info.dailyRemaining,
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
