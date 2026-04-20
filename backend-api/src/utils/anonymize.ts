/**
 * Anonymisation utilities — no raw PII ever stored.
 *
 * session_hash:  HMAC-SHA256(deviceSessionToken, HASH_PEPPER)
 * location_enc:  encrypt() from encryption.ts — raw coords never stored in DB
 */
import { createHmac } from 'crypto';
import { encrypt } from './encryption';

function getPepper(): string {
  const pepper = process.env.HASH_PEPPER;
  if (!pepper || pepper.length < 32) {
    throw new Error('HASH_PEPPER must be at least a 32-char string');
  }
  return pepper;
}

/**
 * Produces a stable, pseudonymous hash from a device session token.
 * Same token + same pepper → same hash. Cannot be reversed.
 */
export function hashSession(sessionToken: string): string {
  return createHmac('sha256', getPepper())
    .update(sessionToken)
    .digest('hex');
}

/**
 * Encrypts a GPS coordinate string (e.g. "24.7136,46.6753") for DB storage.
 * Only the service-role backend can decrypt.
 */
export function encryptLocation(latLon: string): string {
  return encrypt(latLon);
}

/**
 * Round GPS coordinates to ~100m precision before encryption.
 * Prevents fingerprinting from highly precise coordinates.
 */
export function coarsenLocation(lat: number, lon: number): string {
  const precision = 3; // ~111m per 0.001°
  return `${lat.toFixed(precision)},${lon.toFixed(precision)}`;
}
