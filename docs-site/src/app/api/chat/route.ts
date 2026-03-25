// @ts-nocheck — ai@6 tool() types cause infinite depth with zod@3
import { openai } from '@ai-sdk/openai';
import { streamText, tool } from 'ai';
import { z } from 'zod';
import { source } from '@/lib/source';

export const maxDuration = 30;

export async function POST(req: Request) {
  const { messages } = await req.json();

  const pages = source.getPages().map((page) => ({
    title: String(page.data.title ?? ''),
    description: String(page.data.description ?? ''),
    url: page.url,
  }));

  const result = streamText({
    model: openai(process.env.AI_MODEL ?? 'gpt-4o-mini'),
    system: `You are a helpful assistant for Sardis documentation. Sardis is the Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely through non-custodial MPC wallets with natural language spending policies.

Answer questions about Sardis based on the documentation. Be concise and accurate. If you don't know the answer, say so.

Available documentation pages:
${pages.map((p) => `- ${p.title}: ${p.description} (${p.url})`).join('\n')}`,
    messages,
    tools: {
      searchDocs: tool({
        description: 'Search Sardis documentation pages',
        inputSchema: z.object({
          query: z.string().describe('The search query'),
        }),
        execute: async ({ query }) => {
          const results = pages.filter(
            (p) =>
              p.title.toLowerCase().includes(query.toLowerCase()) ||
              p.description.toLowerCase().includes(query.toLowerCase()),
          );
          return results.slice(0, 5);
        },
      }),
    },
  });

  return result.toDataStreamResponse();
}
