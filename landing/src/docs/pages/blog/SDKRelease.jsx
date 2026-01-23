import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function SDKRelease() {
  return (
    <article className="prose prose-invert max-w-none">
      {/* Back link */}
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      {/* Header */}
      <header className="not-prose mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-500">
            RELEASE
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          SDK v0.2.0: LangChain, OpenAI, and LlamaIndex Support
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 2, 2025
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />4 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Our latest SDK release adds native integrations for all major AI
          frameworks. Now you can add Sardis payments to any LangChain agent,
          OpenAI function caller, or LlamaIndex tool in minutes.
        </p>

        <h2>What's New in v0.2.0</h2>

        <h3>LangChain Integration</h3>
        <p>
          The new <code>@sardis/langchain</code> package provides a drop-in
          toolkit for LangChain agents:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`import { SardisToolkit } from '@sardis/langchain';
import { ChatOpenAI } from '@langchain/openai';
import { AgentExecutor, createToolCallingAgent } from 'langchain/agents';

const tools = new SardisToolkit({
  walletId: 'wallet_xxx',
  policy: { maxPerTransaction: 50 }
}).getTools();

const agent = createToolCallingAgent({
  llm: new ChatOpenAI({ model: 'gpt-4' }),
  tools,
  prompt: yourPromptTemplate
});

const executor = new AgentExecutor({ agent, tools });
await executor.invoke({
  input: "Pay $25 for the monthly API subscription"
});`}
          </pre>
        </div>

        <h3>OpenAI Functions</h3>
        <p>
          For those using OpenAI's function calling directly, we now export
          properly typed function schemas:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`import { sardisTools, executeSardisTool } from '@sardis/openai';
import OpenAI from 'openai';

const client = new OpenAI();

const response = await client.chat.completions.create({
  model: 'gpt-4-turbo',
  messages: [{ role: 'user', content: 'Pay $30 for hosting' }],
  tools: sardisTools,
  tool_choice: 'auto'
});

// Handle tool calls
for (const toolCall of response.choices[0].message.tool_calls) {
  const result = await executeSardisTool(toolCall);
  console.log(result);
}`}
          </pre>
        </div>

        <h3>LlamaIndex Tools</h3>
        <p>
          LlamaIndex users can now use Sardis as a query engine tool:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`from sardis.llama_index import SardisPaymentTool

payment_tool = SardisPaymentTool(
    wallet_id="wallet_xxx",
    policy={"max_per_transaction": 50}
)

agent = OpenAIAgent.from_tools(
    [payment_tool],
    system_prompt="You are a helpful assistant that can make payments."
)`}
          </pre>
        </div>

        <h2>Breaking Changes</h2>
        <p>
          Version 0.2.0 includes some breaking changes from 0.1.x:
        </p>

        <div className="not-prose border border-border mb-6">
          <div className="border-b border-border p-4 bg-red-500/5">
            <div className="font-mono text-sm text-red-400 mb-2">REMOVED</div>
            <div className="text-muted-foreground text-sm">
              <code>wallet.sendPayment()</code> - Use{" "}
              <code>wallet.pay()</code> instead
            </div>
          </div>
          <div className="border-b border-border p-4 bg-yellow-500/5">
            <div className="font-mono text-sm text-yellow-400 mb-2">
              CHANGED
            </div>
            <div className="text-muted-foreground text-sm">
              Policy configuration now uses camelCase (
              <code>maxPerTransaction</code>) instead of snake_case (
              <code>max_per_transaction</code>)
            </div>
          </div>
          <div className="p-4 bg-blue-500/5">
            <div className="font-mono text-sm text-blue-400 mb-2">RENAMED</div>
            <div className="text-muted-foreground text-sm">
              <code>SardisClient</code> is now <code>SardisWallet</code> to
              better reflect its purpose
            </div>
          </div>
        </div>

        <h2>Migration Guide</h2>
        <p>
          Migrating from 0.1.x is straightforward. Here's a quick comparison:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <div className="text-red-400 mb-2">// Before (0.1.x)</div>
          <pre className="text-[var(--sardis-canvas)] mb-4">
            {`const client = new SardisClient({
  policy: { max_per_transaction: 50 }
});
await client.sendPayment({ amount: 25, to: 'vendor' });`}
          </pre>
          <div className="text-emerald-400 mb-2">// After (0.2.0)</div>
          <pre className="text-[var(--sardis-canvas)]">
            {`const wallet = new SardisWallet({
  policy: { maxPerTransaction: 50 }
});
await wallet.pay({ amount: 25, vendor: 'vendor' });`}
          </pre>
        </div>

        <h2>New Features</h2>

        <h3>Batch Payments</h3>
        <p>
          Process multiple payments in a single transaction for efficiency:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`await wallet.payBatch([
  { amount: 10, vendor: 'service-a.com' },
  { amount: 15, vendor: 'service-b.com' },
  { amount: 20, vendor: 'service-c.com' }
]);`}
          </pre>
        </div>

        <h3>Transaction Webhooks</h3>
        <p>Get notified when transactions complete or fail:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`wallet.on('transaction:completed', (tx) => {
  console.log(\`Payment of $\${tx.amount} to \${tx.vendor} completed\`);
});

wallet.on('transaction:failed', (tx, error) => {
  console.error(\`Payment failed: \${error.message}\`);
});`}
          </pre>
        </div>

        <h3>Improved TypeScript Types</h3>
        <p>
          Full type safety with discriminated unions for transaction results:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`const result = await wallet.pay({ amount: 25, vendor: 'test.com' });

if (result.status === 'success') {
  // TypeScript knows result.txHash exists here
  console.log(result.txHash);
} else {
  // TypeScript knows result.error exists here
  console.error(result.error.code, result.error.message);
}`}
          </pre>
        </div>

        <h2>Python SDK Updates</h2>
        <p>
          The Python SDK (<code>sardis-sdk</code>) has received matching
          updates:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`from sardis import SardisWallet

wallet = SardisWallet(
    wallet_id="wallet_xxx",
    policy={"max_per_transaction": 50}
)

# Async support
result = await wallet.pay(amount=25, vendor="test.com")

# LangChain integration
from sardis.langchain import SardisToolkit
toolkit = SardisToolkit(wallet=wallet)`}
          </pre>
        </div>

        <h2>What's Next</h2>
        <p>In upcoming releases, we're planning:</p>
        <ul>
          <li>
            <strong>v0.3.0:</strong> Crew AI and AutoGen integrations
          </li>
          <li>
            <strong>v0.4.0:</strong> Virtual card issuance API for fiat payments
          </li>
          <li>
            <strong>v1.0.0:</strong> Production-ready mainnet release
          </li>
        </ul>

        <h2>Getting Started</h2>
        <p>Install the latest SDK:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-emerald-400 mb-2">
            # TypeScript/JavaScript
          </div>
          <div className="text-[var(--sardis-canvas)] mb-4">
            npm install @sardis/sdk@0.2.0
          </div>
          <div className="text-emerald-400 mb-2"># Python</div>
          <div className="text-[var(--sardis-canvas)]">
            pip install sardis-sdk==0.2.0
          </div>
        </div>

        <p>
          Check out our updated documentation for full API reference and
          examples.
        </p>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Engineering Team
          </div>
          <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors">
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </footer>
    </article>
  );
}
