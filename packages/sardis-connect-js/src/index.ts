/**
 * Sardis Connect — Make any API agent-ready in 3 lines.
 *
 * Express/Node.js:
 *   import { sardisConnect } from '@sardis/connect';
 *   const sardis = sardisConnect({ apiKey: 'mch_live_xxx' });
 *   app.use(sardis.middleware());
 *
 * Next.js API Routes:
 *   export { GET, POST } from '@sardis/connect/next';
 */

export { sardisConnect, type SardisConnectOptions } from "./middleware";
export {
  type PricedEndpoint,
  type PaymentResult,
  type ServiceManifest,
  PricingModel,
} from "./types";
