/**
 * Sardis payment piece for Activepieces.
 *
 * Enables workflow automations with policy-controlled payments.
 */

import { createPiece, PieceAuth } from '@activepieces/pieces-framework';
import { createAction, Property } from '@activepieces/pieces-framework';

const sardisAuth = PieceAuth.SecretText({
  displayName: 'API Key',
  description: 'Your Sardis API key (starts with sk_)',
  required: true,
});

const sendPayment = createAction({
  name: 'send_payment',
  displayName: 'Send Payment',
  description: 'Execute a policy-controlled payment from a Sardis wallet',
  auth: sardisAuth,
  props: {
    walletId: Property.ShortText({
      displayName: 'Wallet ID',
      description: 'The Sardis wallet ID',
      required: true,
    }),
    amount: Property.Number({
      displayName: 'Amount',
      description: 'Payment amount in USD',
      required: true,
    }),
    merchant: Property.ShortText({
      displayName: 'Merchant',
      description: 'Recipient address or merchant identifier',
      required: true,
    }),
    purpose: Property.ShortText({
      displayName: 'Purpose',
      description: 'Reason for payment',
      required: false,
    }),
    token: Property.StaticDropdown({
      displayName: 'Token',
      description: 'Stablecoin to use',
      required: false,
      defaultValue: 'USDC',
      options: {
        options: [
          { label: 'USDC', value: 'USDC' },
          { label: 'USDT', value: 'USDT' },
          { label: 'PYUSD', value: 'PYUSD' },
          { label: 'EURC', value: 'EURC' },
        ],
      },
    }),
    chain: Property.StaticDropdown({
      displayName: 'Chain',
      description: 'Blockchain network',
      required: false,
      defaultValue: 'base',
      options: {
        options: [
          { label: 'Base', value: 'base' },
          { label: 'Ethereum', value: 'ethereum' },
          { label: 'Polygon', value: 'polygon' },
          { label: 'Arbitrum', value: 'arbitrum' },
          { label: 'Optimism', value: 'optimism' },
        ],
      },
    }),
  },
  async run(context) {
    const { auth, propsValue } = context;
    const baseUrl = 'https://api.sardis.sh';

    const response = await fetch(
      `${baseUrl}/api/v2/wallets/${propsValue.walletId}/transfer`,
      {
        method: 'POST',
        headers: {
          'X-API-Key': auth as string,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          destination: propsValue.merchant,
          amount: propsValue.amount!.toString(),
          token: propsValue.token || 'USDC',
          chain: propsValue.chain || 'base',
          memo: propsValue.purpose,
        }),
      },
    );

    return await response.json();
  },
});

const checkBalance = createAction({
  name: 'check_balance',
  displayName: 'Check Balance',
  description: 'Check wallet balance and spending limits',
  auth: sardisAuth,
  props: {
    walletId: Property.ShortText({
      displayName: 'Wallet ID',
      description: 'The Sardis wallet ID',
      required: true,
    }),
    token: Property.StaticDropdown({
      displayName: 'Token',
      required: false,
      defaultValue: 'USDC',
      options: {
        options: [
          { label: 'USDC', value: 'USDC' },
          { label: 'USDT', value: 'USDT' },
        ],
      },
    }),
  },
  async run(context) {
    const { auth, propsValue } = context;
    const baseUrl = 'https://api.sardis.sh';
    const token = propsValue.token || 'USDC';

    const response = await fetch(
      `${baseUrl}/api/v2/wallets/${propsValue.walletId}/balance?chain=base&token=${token}`,
      {
        headers: { 'X-API-Key': auth as string },
      },
    );

    return await response.json();
  },
});

export const sardis = createPiece({
  displayName: 'Sardis',
  description: 'Policy-controlled payments for AI agents',
  auth: sardisAuth,
  minimumSupportedRelease: '0.20.0',
  logoUrl: 'https://sardis.sh/logo.png',
  authors: ['sardis-pay'],
  actions: [sendPayment, checkBalance],
  triggers: [],
});
