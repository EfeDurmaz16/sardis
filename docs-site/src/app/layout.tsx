import './global.css';
import { RootProvider } from 'fumadocs-ui/provider';
import { GeistSans } from 'geist/font/sans';
import { GeistMono } from 'geist/font/mono';
import type { Metadata } from 'next';
import type { ReactNode } from 'react';

export const metadata: Metadata = {
  title: {
    template: '%s | Sardis Docs',
    default: 'Sardis Docs',
  },
  description: 'Documentation for Sardis — the Payment OS for the Agent Economy.',
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon.ico', sizes: '32x32' },
    ],
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html
      lang="en"
      className={`${GeistSans.variable} ${GeistMono.variable}`}
      suppressHydrationWarning
    >
      <body>
        <RootProvider>{children}</RootProvider>
      </body>
    </html>
  );
}
