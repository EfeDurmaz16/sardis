/**
 * Vercel AI SDK + Sardis
 * ======================
 *
 * Give a Vercel AI SDK model Sardis payment tools via the first-party
 * `sardis/ai-sdk` provider. Every payment the model makes is policy-checked.
 *
 * Concept: `createSardis({ apiKey, walletId })` returns `{ tools, systemPrompt }`
 * you pass straight into `generateText` / `streamText` — no hand-rolled tools.
 *
 * Prerequisites:
 *   npm install sardis ai @ai-sdk/openai
 *
 * Run:
 *   export OPENAI_API_KEY=sk-...
 *   export SARDIS_API_KEY=sk_live_...
 *   export SARDIS_WALLET_ID=wallet_...
 *   npx tsx examples/vercel_ai_payment.ts
 */

import { openai } from "@ai-sdk/openai";
import { generateText } from "ai";
import { createSardis } from "sardis/ai-sdk";

async function main() {
  const apiKey = process.env.SARDIS_API_KEY;
  const walletId = process.env.SARDIS_WALLET_ID;
  if (!apiKey || !walletId) {
    throw new Error("Set SARDIS_API_KEY and SARDIS_WALLET_ID and retry.");
  }

  const sardis = createSardis({ apiKey, walletId });

  const { text, toolResults } = await generateText({
    model: openai("gpt-4o"),
    system: sardis.systemPrompt,
    tools: sardis.tools,
    prompt: "Pay $5 of OpenAI API credits to openai.com.",
  });

  console.log("Agent response:", text);
  console.log("Tool results:", JSON.stringify(toolResults, null, 2));
}

main().catch(console.error);
