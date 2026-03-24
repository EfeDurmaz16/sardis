'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { useChat } from '@ai-sdk/react';

interface AISearchContextType {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

const AISearchContext = createContext<AISearchContextType>({
  isOpen: false,
  open: () => {},
  close: () => {},
  toggle: () => {},
});

export function AISearch({ children }: { children: ReactNode }) {
  const [isOpen, setIsOpen] = useState(false);

  const open = useCallback(() => setIsOpen(true), []);
  const close = useCallback(() => setIsOpen(false), []);
  const toggle = useCallback(() => setIsOpen((prev) => !prev), []);

  return (
    <AISearchContext.Provider value={{ isOpen, open, close, toggle }}>
      {children}
    </AISearchContext.Provider>
  );
}

export function useAISearch() {
  return useContext(AISearchContext);
}

export function AISearchTrigger({
  children,
  className,
  position = 'float',
}: {
  children?: ReactNode;
  className?: string;
  position?: 'float' | 'inline';
}) {
  const { toggle } = useAISearch();

  return (
    <button
      onClick={toggle}
      className={className}
      style={
        position === 'float'
          ? { position: 'fixed', bottom: 24, right: 24, zIndex: 50 }
          : undefined
      }
    >
      {children ?? 'Ask AI'}
    </button>
  );
}

export function AISearchPanel() {
  const { isOpen, close } = useAISearch();
  const { messages, input, handleInputChange, handleSubmit, isLoading } =
    useChat({
      api: '/api/chat',
    });

  if (!isOpen) return null;

  return (
    <div
      style={{
        position: 'fixed',
        bottom: 80,
        right: 24,
        width: 400,
        maxHeight: 500,
        zIndex: 50,
        display: 'flex',
        flexDirection: 'column',
        border: '1px solid var(--fd-border)',
        borderRadius: 12,
        background: 'var(--fd-background)',
        boxShadow: '0 8px 32px rgba(0,0,0,0.3)',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: '12px 16px',
          borderBottom: '1px solid var(--fd-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <span style={{ fontWeight: 600, fontSize: 14 }}>Ask Sardis AI</span>
        <button onClick={close} style={{ fontSize: 18, lineHeight: 1 }}>
          x
        </button>
      </div>

      {/* Messages */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {messages.length === 0 && (
          <p
            style={{
              color: 'var(--fd-muted-foreground)',
              fontSize: 13,
              textAlign: 'center',
              padding: '20px 0',
            }}
          >
            Ask anything about Sardis — wallets, payments, policies, SDKs...
          </p>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              padding: '8px 12px',
              borderRadius: 8,
              fontSize: 13,
              lineHeight: 1.5,
              background:
                m.role === 'user' ? 'var(--fd-muted)' : 'transparent',
              border:
                m.role === 'assistant'
                  ? '1px solid var(--fd-border)'
                  : 'none',
            }}
          >
            {m.content}
          </div>
        ))}
      </div>

      {/* Input */}
      <form
        onSubmit={handleSubmit}
        style={{
          borderTop: '1px solid var(--fd-border)',
          padding: 12,
          display: 'flex',
          gap: 8,
        }}
      >
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="How do I create a wallet?"
          style={{
            flex: 1,
            padding: '8px 12px',
            borderRadius: 8,
            border: '1px solid var(--fd-border)',
            background: 'var(--fd-muted)',
            color: 'var(--fd-foreground)',
            fontSize: 13,
            outline: 'none',
          }}
        />
        <button
          type="submit"
          disabled={isLoading}
          style={{
            padding: '8px 16px',
            borderRadius: 8,
            background: 'var(--fd-primary)',
            color: 'var(--fd-primary-foreground)',
            fontSize: 13,
            fontWeight: 500,
            border: 'none',
            cursor: isLoading ? 'wait' : 'pointer',
            opacity: isLoading ? 0.7 : 1,
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
}
