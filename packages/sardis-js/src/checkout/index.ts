/**
 * `sardis/checkout` — "Pay with Sardis" merchant checkout helpers.
 *
 * Re-exports the `checkout` resource. React hooks live behind an optional
 * peer dep on `react` and are *not* imported here — consumers can build
 * their own via the resource directly.
 */

export { CheckoutResource } from '../resources/checkout.js';
