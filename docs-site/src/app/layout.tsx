import './global.css';
import { RootProvider } from 'fumadocs-ui/provider';
import { AISearch, AISearchPanel, AISearchTrigger } from '@/components/ai/search';
import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: {
    template: '%s | Sardis Docs',
    default: 'Sardis Docs',
  },
  description: 'Documentation for Sardis — the Payment OS for the Agent Economy.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <RootProvider>
          <AISearch>
            {children}
            <AISearchPanel />
            <AISearchTrigger
              position="float"
              className="rounded-2xl border border-fd-border bg-fd-background px-4 py-2 text-sm text-fd-muted-foreground shadow-lg transition-colors hover:bg-fd-muted"
            >
              Ask AI
            </AISearchTrigger>
          </AISearch>
        </RootProvider>
      </body>
    </html>
  );
}
