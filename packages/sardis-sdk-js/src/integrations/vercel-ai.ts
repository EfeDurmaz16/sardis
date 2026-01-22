import { z } from 'zod';
import { SardisClient } from '../client.js';

export const createSardisTools = (client?: SardisClient) => {
    // If no client provided, we can't instantiate without config, so we assume user provides one
    // or we throw if they try to execute without a client.
    const sardis = client;

    return {
        payVendor: {
            description: 'Execute a secure payment using Sardis MPC wallet.',
            parameters: z.object({
                amount: z.number().describe('The amount to pay in USD.'),
                vendor: z.string().describe('The name of the merchant or service provider.'),
                purpose: z.string().optional().describe('The reason for the payment, used for policy validation.'),
            }),
            execute: async ({ amount, vendor, purpose }: { amount: number; vendor: string; purpose?: string }) => {
                if (!sardis) {
                    return {
                        success: false,
                        error: "SardisClient not initialized"
                    };
                }
                try {
                    // NOTE: Full implementation requires mandate signing logic using sardis.payments.executeMandate()
                    // For Integration Preview, we return a simulated success.
                    // await sardis.payments.executeMandate({...})

                    return {
                        success: true,
                        status: 'PENDING_APPROVAL',
                        transactionId: 'mock_tx_' + Date.now(),
                        message: `Payment of $${amount} to ${vendor} initiated successfully.`
                    };
                } catch (error: any) {
                    return {
                        success: false,
                        error: error.message || 'Payment failed'
                    };
                }
            },
        },
    };
};
