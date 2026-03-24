export default function IntegrationVercelAISdk() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Vercel AI SDK Integration</h1>
        <p className="text-xl text-muted-foreground">
          Add payment capabilities to your AI chatbot with the Vercel AI SDK and Sardis.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`npm install @sardis/ai-sdk ai @ai-sdk/openai`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The <code>@sardis/ai-sdk</code> package provides Sardis tools as Vercel AI SDK compatible tool definitions,
          ready to use with <code>useChat</code>, <code>streamText</code>, and <code>generateText</code>.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Provider Setup
        </h2>

        <p className="text-muted-foreground mb-4">
          Initialize the Sardis tool provider with your API key:
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { sardisTools } from "@sardis/ai-sdk";

const tools = sardisTools({
  apiKey: process.env.SARDIS_API_KEY,
  agentId: "agent_abc123",
});

// tools.pay        — Execute a payment
// tools.getBalance — Check wallet balance
// tools.getPolicy  — View active spending policy
// tools.listTx     — List recent transactions`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Server-Side: streamText
        </h2>

        <p className="text-muted-foreground mb-4">
          Use <code>streamText</code> in a Next.js API route to stream AI responses with payment tool calls:
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// app/api/chat/route.ts
import { streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import { sardisTools } from "@sardis/ai-sdk";

export async function POST(req: Request) {
  const { messages } = await req.json();

  const tools = sardisTools({
    apiKey: process.env.SARDIS_API_KEY!,
    agentId: "agent_procurement",
  });

  const result = streamText({
    model: openai("gpt-4o"),
    messages,
    tools: {
      ...tools,
    },
    maxSteps: 5,
  });

  return result.toDataStreamResponse();
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Client-Side: useChat
        </h2>

        <p className="text-muted-foreground mb-4">
          On the frontend, use <code>useChat</code> to connect to the streaming endpoint:
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`"use client";
import { useChat } from "ai/react";

export default function PaymentChat() {
  const { messages, input, handleInputChange, handleSubmit } = useChat();

  return (
    <div>
      {messages.map((m) => (
        <div key={m.id}>
          <strong>{m.role}:</strong> {m.content}
          {m.toolInvocations?.map((tool) => (
            <pre key={tool.toolCallId}>
              {JSON.stringify(tool.result, null, 2)}
            </pre>
          ))}
        </div>
      ))}
      <form onSubmit={handleSubmit}>
        <input value={input} onChange={handleInputChange} />
        <button type="submit">Send</button>
      </form>
    </div>
  );
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Tools
        </h2>

        <div className="not-prose mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono font-medium text-muted-foreground">Tool</th>
                  <th className="text-left py-3 px-4 font-mono font-medium text-muted-foreground">Description</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                {[
                  ['pay', 'Execute a payment to a recipient'],
                  ['getBalance', 'Check wallet USDC balance'],
                  ['getPolicy', 'View the active spending policy'],
                  ['listTx', 'List recent transactions with status'],
                  ['holdCreate', 'Create a payment hold (escrow)'],
                  ['holdRelease', 'Release a held payment'],
                  ['mandateCreate', 'Create a spending mandate'],
                ].map(([tool, desc]) => (
                  <tr key={tool} className="border-b border-border/50">
                    <td className="py-3 px-4 font-mono text-foreground">{tool}</td>
                    <td className="py-3 px-4">{desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Next Steps
        </h2>

        <ul>
          <li>Read the <a href="/docs/policies" className="text-[var(--sardis-orange)] hover:underline">Spending Policies</a> guide to define natural language rules</li>
          <li>Set up <a href="/docs/wallets" className="text-[var(--sardis-orange)] hover:underline">Agent Wallets</a> with MPC signing</li>
          <li>Explore the <a href="/docs/mcp-server" className="text-[var(--sardis-orange)] hover:underline">MCP Server</a> for Claude Desktop integration</li>
        </ul>
      </section>
    </article>
  );
}
