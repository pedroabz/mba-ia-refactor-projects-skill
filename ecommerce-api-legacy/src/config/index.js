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

/**
 * A development-only secret: never required, and never a committed literal.
 *
 * `secret()` cannot be used for these because configuration is built before anything decides
 * whether seeding will run, so a required-in-production secret would stop a production boot
 * over a fixture that production refuses to create anyway. An absent value becomes a random
 * one for this process, which the seeder logs so a developer can still sign in.
 */
function devSecret(name) {
    const value = process.env[name];
    if (value) return value;
    if (isProduction) return null;
    return crypto.randomBytes(18).toString('base64url');
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
        // The rate limiter keys on `req.ip`, so this decides whether it works. Off means the
        // socket's peer address, which is right when the process is exposed directly and
        // wrong behind a load balancer: there every caller presents the proxy's address and
        // shares one bucket, so one client's burst locks out everybody else. Default off
        // because trusting the header when nothing upstream strips it lets a caller choose
        // its own identity — set it only when a proxy you control sets X-Forwarded-For.
        trustProxy: bool('TRUST_PROXY', false),
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
        // 'stub' contacts no provider, so it cannot authorize anything: it declines. See
        // services/payment.gateway.js. Production refuses to use it at all.
        driver: str('PAYMENT_DRIVER', isProduction ? 'gateway' : 'stub'),
        gatewayKey: process.env.PAYMENT_GATEWAY_KEY || null,
        // Lets the stub approve, for developing the post-payment flow without a provider.
        // Named for what it does, off unless set, and honoured only in development — the
        // previous behaviour was the reverse: approval was the default in every environment
        // that was not literally 'production'.
        stubApprove: NODE_ENV === 'development' && bool('PAYMENT_STUB_APPROVE', false),
    }),

    mail: Object.freeze({
        sender: str('MAIL_SENDER', 'no-reply@example.invalid'),
    }),

    seed: Object.freeze({
        // Fixture data for local development only; refused in production (see infra/schema.js).
        enabled: bool('SEED_ENABLED', !isProduction),
        // No literal defaults: these used to be 'dev-student-password' and
        // 'dev-admin-password' in this file, so every environment whose NODE_ENV was not
        // exactly 'production' — staging, qa, an unset value — came up with an administrator
        // whose password was readable in the repository. Unset now means a random password
        // per process, which the seeder logs.
        studentPassword: devSecret('SEED_STUDENT_PASSWORD'),
        adminPassword: devSecret('SEED_ADMIN_PASSWORD'),
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
