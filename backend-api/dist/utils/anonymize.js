"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.hashSession = hashSession;
exports.encryptLocation = encryptLocation;
exports.coarsenLocation = coarsenLocation;
/**
 * Anonymisation utilities — no raw PII ever stored.
 *
 * session_hash:  HMAC-SHA256(deviceSessionToken, HASH_PEPPER)
 * location_enc:  encrypt() from encryption.ts — raw coords never stored in DB
 */
const crypto_1 = require("crypto");
const encryption_1 = require("./encryption");
function getPepper() {
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
function hashSession(sessionToken) {
    return (0, crypto_1.createHmac)('sha256', getPepper())
        .update(sessionToken)
        .digest('hex');
}
/**
 * Encrypts a GPS coordinate string (e.g. "24.7136,46.6753") for DB storage.
 * Only the service-role backend can decrypt.
 */
function encryptLocation(latLon) {
    return (0, encryption_1.encrypt)(latLon);
}
/**
 * Round GPS coordinates to ~100m precision before encryption.
 * Prevents fingerprinting from highly precise coordinates.
 */
function coarsenLocation(lat, lon) {
    const precision = 3; // ~111m per 0.001°
    return `${lat.toFixed(precision)},${lon.toFixed(precision)}`;
}
//# sourceMappingURL=anonymize.js.map