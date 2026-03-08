import {
  IExecuteFunctions,
  INodeExecutionData,
  INodeType,
  INodeTypeDescription,
} from 'n8n-workflow';

export class Sardis implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'Sardis',
    name: 'sardis',
    icon: 'file:sardis.svg',
    group: ['transform'],
    version: 1,
    subtitle: '={{$parameter["operation"]}}',
    description: 'Execute policy-controlled payments via Sardis',
    defaults: {
      name: 'Sardis',
    },
    inputs: ['main'],
    outputs: ['main'],
    credentials: [
      {
        name: 'sardisApi',
        required: true,
      },
    ],
    properties: [
      {
        displayName: 'Operation',
        name: 'operation',
        type: 'options',
        noDataExpression: true,
        options: [
          {
            name: 'Send Payment',
            value: 'sendPayment',
            description: 'Execute a policy-controlled payment',
            action: 'Send a payment',
          },
          {
            name: 'Check Balance',
            value: 'checkBalance',
            description: 'Check wallet balance and limits',
            action: 'Check wallet balance',
          },
          {
            name: 'Check Policy',
            value: 'checkPolicy',
            description: 'Pre-check if a payment would pass policy',
            action: 'Check spending policy',
          },
        ],
        default: 'sendPayment',
      },
      // Send Payment fields
      {
        displayName: 'Wallet ID',
        name: 'walletId',
        type: 'string',
        default: '',
        required: true,
        description: 'The Sardis wallet ID to use',
      },
      {
        displayName: 'Amount',
        name: 'amount',
        type: 'number',
        default: 0,
        required: true,
        displayOptions: {
          show: { operation: ['sendPayment', 'checkPolicy'] },
        },
        description: 'Payment amount in USD',
      },
      {
        displayName: 'Merchant',
        name: 'merchant',
        type: 'string',
        default: '',
        required: true,
        displayOptions: {
          show: { operation: ['sendPayment', 'checkPolicy'] },
        },
        description: 'Merchant or recipient identifier',
      },
      {
        displayName: 'Purpose',
        name: 'purpose',
        type: 'string',
        default: '',
        displayOptions: {
          show: { operation: ['sendPayment'] },
        },
        description: 'Reason for payment',
      },
      {
        displayName: 'Token',
        name: 'token',
        type: 'options',
        options: [
          { name: 'USDC', value: 'USDC' },
          { name: 'USDT', value: 'USDT' },
          { name: 'PYUSD', value: 'PYUSD' },
          { name: 'EURC', value: 'EURC' },
        ],
        default: 'USDC',
        description: 'Stablecoin to use',
      },
      {
        displayName: 'Chain',
        name: 'chain',
        type: 'options',
        options: [
          { name: 'Base', value: 'base' },
          { name: 'Ethereum', value: 'ethereum' },
          { name: 'Polygon', value: 'polygon' },
          { name: 'Arbitrum', value: 'arbitrum' },
          { name: 'Optimism', value: 'optimism' },
        ],
        default: 'base',
        description: 'Blockchain network',
      },
    ],
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];
    const credentials = await this.getCredentials('sardisApi');
    const apiKey = credentials.apiKey as string;
    const baseUrl = (credentials.baseUrl as string) || 'https://api.sardis.sh';

    for (let i = 0; i < items.length; i++) {
      const operation = this.getNodeParameter('operation', i) as string;
      const walletId = this.getNodeParameter('walletId', i) as string;
      const token = this.getNodeParameter('token', i, 'USDC') as string;
      const chain = this.getNodeParameter('chain', i, 'base') as string;

      try {
        if (operation === 'sendPayment') {
          const amount = this.getNodeParameter('amount', i) as number;
          const merchant = this.getNodeParameter('merchant', i) as string;
          const purpose = this.getNodeParameter('purpose', i, '') as string;

          const response = await this.helpers.request({
            method: 'POST',
            url: `${baseUrl}/api/v2/wallets/${walletId}/transfer`,
            headers: { 'X-API-Key': apiKey, 'Content-Type': 'application/json' },
            body: JSON.stringify({
              destination: merchant,
              amount: amount.toString(),
              token,
              chain,
              memo: purpose,
            }),
          });

          const result = typeof response === 'string' ? JSON.parse(response) : response;
          returnData.push({ json: { success: true, ...result } });

        } else if (operation === 'checkBalance') {
          const response = await this.helpers.request({
            method: 'GET',
            url: `${baseUrl}/api/v2/wallets/${walletId}/balance?chain=${chain}&token=${token}`,
            headers: { 'X-API-Key': apiKey },
          });

          const result = typeof response === 'string' ? JSON.parse(response) : response;
          returnData.push({ json: { success: true, ...result } });

        } else if (operation === 'checkPolicy') {
          const amount = this.getNodeParameter('amount', i) as number;
          const merchant = this.getNodeParameter('merchant', i) as string;

          const response = await this.helpers.request({
            method: 'GET',
            url: `${baseUrl}/api/v2/wallets/${walletId}`,
            headers: { 'X-API-Key': apiKey },
          });

          const wallet = typeof response === 'string' ? JSON.parse(response) : response;
          const limitPerTx = parseFloat(wallet.limit_per_tx || '0');
          const allowed = amount <= limitPerTx;

          returnData.push({
            json: {
              allowed,
              amount,
              merchant,
              limitPerTx,
              message: allowed
                ? `$${amount} to ${merchant} would be allowed`
                : `$${amount} exceeds per-tx limit of $${limitPerTx}`,
            },
          });
        }
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : 'Unknown error';
        returnData.push({ json: { success: false, error: msg } });
      }
    }

    return [returnData];
  }
}
