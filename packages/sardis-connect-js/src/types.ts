/** Pricing model for an endpoint. */
export enum PricingModel {
  PerCall = "per_call",
  PerUnit = "per_unit",
  Subscription = "subscription",
}

/** A priced API endpoint. */
export interface PricedEndpoint {
  path: string;
  method?: string;
  price: string;
  currency?: string;
  description?: string;
  pricingModel?: PricingModel;
  unitName?: string;
  category?: string;
  rateLimit?: number;
  requiresAuth?: boolean;
}

/** Result of a payment verification. */
export interface PaymentResult {
  verified: boolean;
  sessionId: string;
  amount: string;
  currency: string;
  payerId?: string;
  error?: string;
}

/** Machine-readable service manifest for agent discovery. */
export interface ServiceManifest {
  version: string;
  name: string;
  description: string;
  baseUrl: string;
  merchantId?: string;
  accepts: string[];
  endpoints: PricedEndpoint[];
}

/** Payment session created for agent. */
export interface PaySession {
  sessionId: string;
  clientSecret: string;
  checkoutUrl: string;
  amount: string;
  currency: string;
  status: string;
}
