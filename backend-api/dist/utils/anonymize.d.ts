/**
 * Produces a stable, pseudonymous hash from a device session token.
 * Same token + same pepper → same hash. Cannot be reversed.
 */
export declare function hashSession(sessionToken: string): string;
/**
 * Encrypts a GPS coordinate string (e.g. "24.7136,46.6753") for DB storage.
 * Only the service-role backend can decrypt.
 */
export declare function encryptLocation(latLon: string): string;
/**
 * Round GPS coordinates to ~100m precision before encryption.
 * Prevents fingerprinting from highly precise coordinates.
 */
export declare function coarsenLocation(lat: number, lon: number): string;
//# sourceMappingURL=anonymize.d.ts.map