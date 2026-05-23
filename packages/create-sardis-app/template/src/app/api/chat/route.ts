import { openai } from '@ai-sdk/openai';
import { streamText } from 'ai';
import { sardis } from '@/lib/sardis';

export const runtime = 'nodejs';

export async function POST(req: Request) {
  const { messages } = await req.json();

  const result = await streamText({
    model: openai('gpt-4o-mini'),
    tools: sardis.tools,
    system: sardis.systemPrompt,
    messages,
  });

  return result.toDataStreamResponse();
}
