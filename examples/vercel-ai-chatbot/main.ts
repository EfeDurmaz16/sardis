/**
 * Vercel AI SDK Chatbot with Sardis
 *
 * A Next.js-compatible chatbot with payment capabilities.
 *
 * Setup:
 *   npm install @sardis/ai-sdk ai @ai-sdk/openai
 */
import { generateText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { createSardisTools } from '@sardis/ai-sdk';

async function main() {
  const tools = createSardisTools({
    apiKey: process.env.SARDIS_API_KEY!,
    walletId: 'wallet_abc123',
    agentId: 'vercel-chatbot',
  });

  const { text, toolResults } = await generateText({
    model: openai('gpt-4o'),
    tools,
    prompt: 'Check my wallet balance and pay $25 USDC to 0x742d... for hosting',
  });

  console.log('Response:', text);
  console.log('Tool results:', toolResults);
}

main().catch(console.error);
