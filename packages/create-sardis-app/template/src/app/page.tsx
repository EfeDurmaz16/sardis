'use client';
import { useChat } from 'ai/react';

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit } = useChat();
  return (
    <main style={{ maxWidth: 720, margin: '40px auto', padding: '0 16px' }}>
      <h1 style={{ marginBottom: 12 }}>Sardis Agent</h1>
      <p style={{ color: '#666', marginBottom: 24 }}>
        Try: <i>"Pay $5 to merchant_test for testing"</i> or <i>"What's my USDC balance?"</i>
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginBottom: 24 }}>
        {messages.map((m) => (
          <div key={m.id} style={{ padding: 12, borderRadius: 8, background: m.role === 'user' ? '#eef' : '#fafafa' }}>
            <b>{m.role}:</b> {m.content}
          </div>
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Ask the agent..."
          style={{ width: '100%', padding: 12, border: '1px solid #ccc', borderRadius: 8 }}
        />
      </form>
    </main>
  );
}
