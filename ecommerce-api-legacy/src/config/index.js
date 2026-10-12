/**
 * Environment-driven configuration. The only module that reads `process.env`.
 *
 * Two rules this file exists to enforce:
 *   - A secret is never a literal here and never has a known fallback value. In production
 *     a missing secret stops the boot; outside production it is replaced by a value
 *     generated at random for that process, so there is nothing committed to leak and
 *     nothing predictable to guess.
 *   - Everything that varies by environment lives here, so no application module has to be
 *     edited to change a port, a database path or a log level.
 */
const crypto = require('node:crypto');
const { loadEnvFile } = require('./env');

loadEnvFile();

const NODE_ENV = process.env.NODE_ENV || 'development';
const isProduction = NODE_ENV === 'production';

/** A secret: required in production, ephemeral elsewhere. Never defaulted to a fixed value. */
function secret(name, { purpose }) {
    const value = process.env[name];
    if (value) return value;
    if (isProduction) {
        throw new Error(
            `Missing required environment variable ${name} (${purpose}). ` +
            'Production refuses to start without it; see .env.example.'
        );
    }
    return crypto.randomBytes(32).toString('hex');
}

/** A non-secret setting: a development-safe default is fine. */
function str(name, fallback) {
    const value = process.env[name];
    return value === undefined || value === '' ? fallback : value;
}

function int(name, fallback) {
    const raw = process.env[name];
    if (raw === undefined || raw === '') return fallback;
    const parsed = Number.parseInt(raw, 10);
    if (!Number.isInteger(parsed)) {
        throw new Error(`Environment variable ${name} must be an integer, got "${raw}"`);
    }
    return parsed;
}

function bool(name, fallback) {
    const raw = process.env[name];
    if (raw === undefined || raw === '') return fallback;
    return ['1', 'true', 'yes', 'on'].includes(raw.toLowerCase());
}

const config = Object.freeze({
    env: NODE_ENV,
    isProduction,

    http: Object.freeze({
        // 3100 e não 3000: a porta 3000 é disputada por quase todo servidor de
        // desenvolvimento e por containers que a publicam, e o conflito custa mais
        // que a convenção. `PORT` sobrescreve.
        port: int('PORT', 3100),
        host: str('HOST', '127.0.0.1'),
        bodyLimit: str('HTTP_BODY_LIMIT', '100kb'),
    }),

    database: Object.freeze({
        // ':memory:' keeps the original behaviour: the schema and seeds are rebuilt on every
        // boot and nothing survives a restart. Point DATABASE_FILE at a path to persist.
        file: str('DATABASE_FILE', ':memory:'),
    }),

    log: Object.freeze({
        level: str('LOG_LEVEL', isProduction ? 'info' : 'debug'),
    }),

    auth: Object.freeze({
        tokenSecret: secret('AUTH_TOKEN_SECRET', { purpose: 'signs session tokens' }),
        tokenTtlSeconds: int('AUTH_TOKEN_TTL_SECONDS', 3600),
    }),

    payment: Object.freeze({
        // 'stub' approves by card prefix without contacting anyone — it is the legacy rule,
        // isolated behind a port so it can be replaced. Production refuses to use it.
        driver: str('PAYMENT_DRIVER', isProduction ? 'gateway' : 'stub'),
        gatewayKey: process.env.PAYMENT_GATEWAY_KEY || null,
    }),

    mail: Object.freeze({
        sender: str('MAIL_SENDER', 'no-reply@example.invalid'),
    }),

    seed: Object.freeze({
        // Fixture data for local development only; refused in production (see infra/schema.js).
        enabled: bool('SEED_ENABLED', !isProduction),
        studentPassword: str('SEED_STUDENT_PASSWORD', 'dev-student-password'),
        adminPassword: str('SEED_ADMIN_PASSWORD', 'dev-admin-password'),
    }),

    report: Object.freeze({
        defaultPageSize: int('REPORT_DEFAULT_PAGE_SIZE', 50),
        maxPageSize: int('REPORT_MAX_PAGE_SIZE', 200),
        maxStudentsPerCourse: int('REPORT_MAX_STUDENTS_PER_COURSE', 200),
    }),

    rateLimit: Object.freeze({
        windowMs: int('RATE_LIMIT_WINDOW_MS', 60_000),
        checkoutMax: int('RATE_LIMIT_CHECKOUT_MAX', 10),
        loginMax: int('RATE_LIMIT_LOGIN_MAX', 5),
        adminMax: int('RATE_LIMIT_ADMIN_MAX', 30),
    }),
});

module.exports = { config };
