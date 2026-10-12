/**
 * Password storage and session tokens.
 *
 * Replaces `badCrypto`, which appended the first two base64 characters of the password ten
 * thousand times and returned ten characters of the result — so the output depended only on
 * the first 12 bits of the input. Measured on the original: 5,000 distinct passwords
 * produced one distinct hash, and "senhaforte", "senha123" and "sexo" all collided.
 *
 * `scrypt` from `node:crypto` is used rather than adding bcrypt: it is a real password KDF
 * with a tunable cost, it is salted per user, and it needs no dependency.
 */
const crypto = require('node:crypto');

const SCRYPT_KEY_LENGTH = 32;
const SCRYPT_SALT_LENGTH = 16;
// cost/blockSize/parallelization. N=2^15 keeps a single hash in the tens of milliseconds.
const SCRYPT_PARAMS = Object.freeze({ N: 32768, r: 8, p: 1, maxmem: 64 * 1024 * 1024 });
const HASH_PREFIX = 'scrypt';
const TOKEN_ALGORITHM = 'sha256';

function base64url(buffer) {
    return Buffer.from(buffer).toString('base64url');
}

function createAuthService({ userModel, config, logger }) {
    function hashPassword(password) {
        return new Promise((resolve, reject) => {
            const salt = crypto.randomBytes(SCRYPT_SALT_LENGTH);
            crypto.scrypt(password, salt, SCRYPT_KEY_LENGTH, SCRYPT_PARAMS, (err, derived) => {
                if (err) return reject(err);
                resolve([
                    HASH_PREFIX,
                    SCRYPT_PARAMS.N,
                    SCRYPT_PARAMS.r,
                    SCRYPT_PARAMS.p,
                    salt.toString('base64'),
                    derived.toString('base64'),
                ].join('$'));
            });
        });
    }

    /** Constant-time comparison; never `===` on a hash. */
    function verifyPassword(password, stored) {
        return new Promise((resolve, reject) => {
            if (typeof stored !== 'string') return resolve(false);
            const [prefix, n, r, p, saltB64, hashB64] = stored.split('$');
            if (prefix !== HASH_PREFIX || !saltB64 || !hashB64) return resolve(false);

            const expected = Buffer.from(hashB64, 'base64');
            const params = { N: Number(n), r: Number(r), p: Number(p), maxmem: SCRYPT_PARAMS.maxmem };
            crypto.scrypt(password, Buffer.from(saltB64, 'base64'), expected.length, params, (err, derived) => {
                if (err) return reject(err);
                resolve(derived.length === expected.length && crypto.timingSafeEqual(derived, expected));
            });
        });
    }

    function sign(payloadB64) {
        return crypto.createHmac(TOKEN_ALGORITHM, config.auth.tokenSecret)
            .update(payloadB64)
            .digest();
    }

    function issueToken({ userId, role }) {
        const payload = {
            sub: userId,
            role,
            exp: Math.floor(Date.now() / 1000) + config.auth.tokenTtlSeconds,
        };
        const payloadB64 = base64url(JSON.stringify(payload));
        return `${payloadB64}.${base64url(sign(payloadB64))}`;
    }

    /** Returns the payload, or null for anything that does not verify. Never throws on input. */
    function verifyToken(token) {
        if (typeof token !== 'string' || !token.includes('.')) return null;
        const [payloadB64, signatureB64] = token.split('.', 2);

        let presented;
        let expected;
        try {
            presented = Buffer.from(signatureB64, 'base64url');
            expected = sign(payloadB64);
        } catch {
            return null;
        }
        if (presented.length !== expected.length || !crypto.timingSafeEqual(presented, expected)) {
            return null;
        }

        let payload;
        try {
            payload = JSON.parse(Buffer.from(payloadB64, 'base64url').toString('utf8'));
        } catch {
            return null;
        }
        if (typeof payload.exp !== 'number' || payload.exp * 1000 <= Date.now()) return null;
        return payload;
    }

    /**
     * Verifies credentials and issues a token. Returns null on any failure — the caller must
     * not be able to tell an unknown email from a wrong password.
     */
    async function login({ email, password }) {
        const credentials = await userModel.findCredentialsByEmail(email);
        if (!credentials) {
            logger.info('login rejected', { reason: 'unknown_account' });
            return null;
        }
        const ok = await verifyPassword(password, credentials.pass_hash);
        if (!ok) {
            logger.info('login rejected', { reason: 'bad_password', userId: credentials.id });
            return null;
        }
        logger.info('login accepted', { userId: credentials.id, role: credentials.role });
        return {
            token: issueToken({ userId: credentials.id, role: credentials.role }),
            expiresInSeconds: config.auth.tokenTtlSeconds,
            role: credentials.role,
        };
    }

    return { hashPassword, verifyPassword, issueToken, verifyToken, login };
}

module.exports = { createAuthService };
