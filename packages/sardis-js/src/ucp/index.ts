/**
 * `sardis/ucp` — Universal Commerce Protocol client + session builders.
 *
 * Thin façade over the `ucp` resource. Re-exports the UCP resource class
 * so consumers can construct it standalone if they have a custom Engine.
 */

export { UCPResource } from '../resources/ucp.js';
