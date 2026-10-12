/**
 * Fixed-window rate limiting, scoped per route.
 *
 * The endpoint that accepts card numbers had no throttle, and it answers differently for an
 * approved and a declined card — an unmetered oracle for testing stolen card numbers in
 * bulk. Login needs the same protection against credential stuffing, and the destructive
 * admin route against repeated attempts.
 *
 * In-process and therefore per-instance: behind more than one replica the effective limit is
 * multiplied by the replica count. A shared store (Redis) is the production answer; this is
 * a deliberate floor, not a complete solution.
 */
const { RateLimitedError } = require('../domain/errors');

function createRateLimiter({ windowMs, max, name, logger }) {
    /** @type {Map<string, {count:number, resetAt:number}>} */
    const hits = new Map();

    function sweep(now) {
        for (const [key, entry] of hits) {
            if (entry.resetAt <= now) hits.delete(key);
        }
    }

    return function rateLimit(req, res, next) {
        const now = Date.now();
        if (hits.size > 10_000) sweep(now);        // bounded: never grows without limit

        const key = req.ip || 'unknown';
        const entry = hits.get(key);

        if (!entry || entry.resetAt <= now) {
            hits.set(key, { count: 1, resetAt: now + windowMs });
            return next();
        }

        entry.count += 1;
        if (entry.count > max) {
            const retryAfterSeconds = Math.max(1, Math.ceil((entry.resetAt - now) / 1000));
            logger.warn('rate limit exceeded', { limiter: name, path: req.originalUrl, retryAfterSeconds });
            return next(new RateLimitedError(retryAfterSeconds));
        }
        return next();
    };
}

module.exports = { createRateLimiter };
