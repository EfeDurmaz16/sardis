import { createSardis } from 'sardis/ai-sdk';

if (!process.env.SARDIS_API_KEY || !process.env.SARDIS_WALLET_ID) {
  throw new Error('Set SARDIS_API_KEY and SARDIS_WALLET_ID in .env.local');
}

export const sardis = createSardis({
  apiKey: process.env.SARDIS_API_KEY!,
  walletId: process.env.SARDIS_WALLET_ID!,
  onTransaction: async (event) => {
    // Log every tool invocation so you can audit agent behavior in dev.
    // Swap this for your database / observability sink in production.
    // eslint-disable-next-line no-console
    console.log('[sardis]', event.type, event.success ? 'ok' : 'fail', event.input);
  },
});
