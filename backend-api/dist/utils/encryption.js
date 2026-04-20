"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.encrypt = encrypt;
exports.decrypt = decrypt;
/**
 * AES-256-GCM encryption utilities.
 * Used for crowd_source.longitude_enc and camera stream URLs.
 *
 * Format: base64(iv):base64(authTag):base64(ciphertext)
 */
const crypto_1 = require("crypto");
const ALGORITHM = 'aes-256-gcm';
const IV_LEN = 12; // 96-bit IV — recommended for GCM
const TAG_LEN = 16; // 128-bit auth tag
function getKey() {
    const hex = process.env.ENCRYPTION_KEY;
    if (!hex || hex.length !== 64) {
        throw new Error('ENCRYPTION_KEY must be a 64-char hex string (32 bytes)');
    }
    return Buffer.from(hex, 'hex');
}
/**
 * Encrypts plaintext. Returns "iv:tag:ciphertext" (all base64).
 */
function encrypt(plaintext) {
    const key = getKey();
    const iv = (0, crypto_1.randomBytes)(IV_LEN);
    const cipher = (0, crypto_1.createCipheriv)(ALGORITHM, key, iv);
    const encrypted = Buffer.concat([
        cipher.update(plaintext, 'utf8'),
        cipher.final(),
    ]);
    const tag = cipher.getAuthTag();
    return [
        iv.toString('base64'),
        tag.toString('base64'),
        encrypted.toString('base64'),
    ].join(':');
}
/**
 * Decrypts a value produced by encrypt().
 */
function decrypt(ciphertext) {
    const key = getKey();
    const [ivB64, tagB64, dataB64] = ciphertext.split(':');
    if (!ivB64 || !tagB64 || !dataB64) {
        throw new Error('Invalid ciphertext format. Expected iv:tag:data (base64).');
    }
    const iv = Buffer.from(ivB64, 'base64');
    const tag = Buffer.from(tagB64, 'base64');
    const data = Buffer.from(dataB64, 'base64');
    const decipher = (0, crypto_1.createDecipheriv)(ALGORITHM, key, iv);
    decipher.setAuthTag(tag);
    return Buffer.concat([decipher.update(data), decipher.final()]).toString('utf8');
}
//# sourceMappingURL=encryption.js.map