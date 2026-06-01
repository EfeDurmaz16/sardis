/**
 * TAP (Trusted Agent Protocol) — structural verification, mirror of
 * `protocol/tap.py` (`parse_signature_input`, `validate_tap_headers`).
 *
 * Cryptographic signature verification and nonce-replay are caller-injected
 * (a `verifySignature` fn and a `nonceCache` set) so the verifier stays pure.
 */
import {
  TAP_ALLOWED_TAGS,
  TAP_ALLOWED_MESSAGE_ALGS,
  TAP_MAX_TIME_WINDOW_SECONDS,
  TAP_SUPPORTED_VERSIONS,
  type TapSignatureInput,
  type TapVerificationResult,
} from '../types/tap.js';

const SIG_INPUT_RE = /^\s*(?<label>[A-Za-z][A-Za-z0-9_-]*)=\((?<components>[^)]*)\)\s*;(?<params>.+)$/;
const SIG_RE = /^\s*(?<label>[A-Za-z][A-Za-z0-9_-]*)=:(?<sig>[A-Za-z0-9+/=_-]+):\s*$/;
const COMPONENT_RE = /"([^"]+)"/g;
const PARAM_RE = /^\s*(?<key>[A-Za-z0-9_-]+)\s*=\s*(?<value>.+?)\s*$/;

/** Parse a TAP Signature-Input header. Throws on malformed input. */
export function parseSignatureInput(headerValue: string): TapSignatureInput {
  const m = SIG_INPUT_RE.exec(headerValue || '');
  if (!m || !m.groups) {
    throw new Error('invalid_signature_input_format');
  }
  const label = m.groups.label!;
  const componentsRaw = m.groups.components!;
  const paramsRaw = m.groups.params!;

  const components: string[] = [];
  for (const cm of componentsRaw.matchAll(COMPONENT_RE)) {
    components.push(cm[1]!);
  }
  if (components.length === 0) {
    throw new Error('signature_input_missing_components');
  }

  const params: Record<string, string> = {};
  for (let chunk of paramsRaw.split(';')) {
    chunk = chunk.trim();
    if (!chunk) continue;
    const pm = PARAM_RE.exec(chunk);
    if (!pm || !pm.groups) {
      throw new Error('invalid_signature_input_param');
    }
    const key = pm.groups.key!.toLowerCase();
    let value = pm.groups.value!.trim();
    if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) {
      value = value.slice(1, -1);
    }
    params[key] = value;
  }

  for (const req of ['created', 'expires', 'keyid', 'alg', 'nonce', 'tag']) {
    if (!(req in params)) {
      throw new Error(`signature_input_missing_${req}`);
    }
  }

  const created = Number(params.created);
  const expires = Number(params.expires);
  if (!Number.isInteger(created) || !Number.isInteger(expires)) {
    throw new Error('invalid_signature_input_timestamps');
  }

  return {
    label,
    components,
    created,
    expires,
    keyid: params.keyid!,
    alg: params.alg!,
    nonce: params.nonce!,
    tag: params.tag!,
  };
}

/** Parse a TAP Signature header. Throws on malformed input. */
export function parseSignatureHeader(headerValue: string): { label: string; sig: string } {
  const m = SIG_RE.exec(headerValue || '');
  if (!m || !m.groups) {
    throw new Error('invalid_signature_header_format');
  }
  return { label: m.groups.label!, sig: m.groups.sig! };
}

export interface VerifyTapOptions {
  now?: number; // epoch seconds
  maxTimeWindowSeconds?: number;
  allowedTags?: readonly string[];
  allowedAlgs?: readonly string[];
  tapVersion?: string;
  /** Caller-supplied nonce cache. Required unless requireReplayCheck=false. */
  nonceCache?: Set<string>;
  requireReplayCheck?: boolean;
}

function validateTapVersion(version: string | undefined): { ok: boolean; reason?: string } {
  if (!version) return { ok: true };
  if ((TAP_SUPPORTED_VERSIONS as readonly string[]).includes(version)) return { ok: true };
  const major = version.includes('.') ? version.split('.')[0]! : version;
  const supportedMajors = new Set(TAP_SUPPORTED_VERSIONS.map((v) => v.split('.')[0]!));
  if (!supportedMajors.has(major)) {
    return { ok: false, reason: `tap_version_unsupported:${version}` };
  }
  return { ok: true };
}

/**
 * Validate TAP message-signature headers. Mirrors `validate_tap_headers`
 * (structural + semantic). Replay protection is fail-closed: a missing
 * `nonceCache` rejects with `tap_nonce_cache_required` unless `requireReplayCheck`
 * is explicitly false.
 */
export function verifyTapRequest(
  signatureInputHeader: string,
  signatureHeader: string,
  opts: VerifyTapOptions = {},
): TapVerificationResult {
  const allowedTags = opts.allowedTags ?? TAP_ALLOWED_TAGS;
  const allowedAlgs = opts.allowedAlgs ?? TAP_ALLOWED_MESSAGE_ALGS;
  const maxWindow = opts.maxTimeWindowSeconds ?? TAP_MAX_TIME_WINDOW_SECONDS;
  const requireReplay = opts.requireReplayCheck ?? true;

  const ver = validateTapVersion(opts.tapVersion);
  if (!ver.ok) {
    return { accepted: false, reason: ver.reason };
  }

  let si: TapSignatureInput;
  try {
    si = parseSignatureInput(signatureInputHeader);
  } catch (e) {
    return { accepted: false, reason: `tap_signature_input_invalid:${(e as Error).message}` };
  }

  let sig: { label: string; sig: string };
  try {
    sig = parseSignatureHeader(signatureHeader);
  } catch (e) {
    return { accepted: false, reason: `tap_signature_invalid:${(e as Error).message}` };
  }

  if (sig.label !== si.label) {
    return { accepted: false, reason: 'tap_signature_label_mismatch' };
  }

  const required = new Set(['@authority', '@path']);
  if (![...required].every((c) => si.components.includes(c))) {
    return { accepted: false, reason: 'tap_required_components_missing' };
  }

  if (!new Set(allowedTags).has(si.tag)) {
    return { accepted: false, reason: 'tap_tag_invalid' };
  }
  const algLower = si.alg.toLowerCase();
  if (!new Set(allowedAlgs.map((a) => a.toLowerCase())).has(algLower)) {
    return { accepted: false, reason: 'tap_alg_invalid' };
  }

  const now = opts.now ?? Math.floor(Date.now() / 1000);
  if (si.created >= now) {
    return { accepted: false, reason: 'tap_created_not_in_past' };
  }
  if (si.expires <= now) {
    return { accepted: false, reason: 'tap_expired' };
  }
  if (si.expires - si.created > maxWindow) {
    return { accepted: false, reason: 'tap_window_too_large' };
  }

  if (!opts.nonceCache) {
    if (requireReplay) {
      return { accepted: false, reason: 'tap_nonce_cache_required' };
    }
  } else {
    if (opts.nonceCache.has(si.nonce)) {
      return { accepted: false, reason: 'tap_nonce_replayed' };
    }
    opts.nonceCache.add(si.nonce);
  }

  return { accepted: true, signatureInput: si, signatureB64: sig.sig };
}
