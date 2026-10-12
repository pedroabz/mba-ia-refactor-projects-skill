/**
 * Request schemas: what the boundary accepts, declared once per endpoint.
 *
 * The original checkout read five fields and applied a single truthiness check, which let
 * through anything of any type. `card` arriving as a JSON number rather than a string made
 * the handler call `cc.startsWith` on a number inside a sqlite3 callback, and the resulting
 * TypeError escaped Express as an uncaught exception — one malformed anonymous POST
 * terminated the server.
 *
 * Hand-written rather than pulled from a library: the project declares no validation
 * dependency, and what is needed here is types, lengths, ranges and one format.
 */
const { ValidationError } = require('../domain/errors');

const EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
const DIGITS_ONLY = /^\d+$/;

const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_MAX_LENGTH = 200;
const CARD_MIN_LENGTH = 13;
const CARD_MAX_LENGTH = 19;

/**
 * Checkout.
 *
 * `aliases` keeps the abbreviated field names the endpoint shipped with (`usr`, `eml`,
 * `pwd`, `c_id`, `card`) working while giving callers readable names. Breaking the request
 * contract outright would break every existing client for a readability fix; accepting both
 * fixes it for new callers and lets the old ones be retired deliberately.
 */
const checkoutSchema = {
    name: { type: 'string', required: true, minLength: 1, maxLength: 120, aliases: ['usr'] },
    email: { type: 'string', required: true, maxLength: 180, pattern: EMAIL, aliases: ['eml'], patternMessage: 'deve ser um e-mail válido' },
    // Required, never defaulted: the original substituted "123456" when absent, creating
    // accounts with a publicly known password.
    password: { type: 'string', required: true, minLength: PASSWORD_MIN_LENGTH, maxLength: PASSWORD_MAX_LENGTH, aliases: ['pwd'], secret: true },
    courseId: { type: 'integer', required: true, min: 1, aliases: ['c_id'] },
    cardNumber: {
        type: 'string', required: true, minLength: CARD_MIN_LENGTH, maxLength: CARD_MAX_LENGTH,
        pattern: DIGITS_ONLY, aliases: ['card'], secret: true,
        patternMessage: 'deve conter apenas dígitos',
    },
};

const loginSchema = {
    email: { type: 'string', required: true, maxLength: 180, pattern: EMAIL, patternMessage: 'deve ser um e-mail válido' },
    password: { type: 'string', required: true, maxLength: PASSWORD_MAX_LENGTH, secret: true },
};

/** Path parameters arrive as strings; an id must still be a positive integer. */
const userIdParamSchema = {
    id: { type: 'integer', required: true, min: 1, coerce: true },
};

/** Query parameters for a paginated read. Absent means "use the server default". */
const reportQuerySchema = {
    limit: { type: 'integer', required: false, min: 1, coerce: true },
    offset: { type: 'integer', required: false, min: 0, coerce: true },
};

function readField(source, field, rule) {
    for (const key of [field, ...(rule.aliases || [])]) {
        if (source[key] !== undefined && source[key] !== null) {
            return { value: source[key], usedKey: key };
        }
    }
    return { value: undefined, usedKey: null };
}

function checkString(value, rule) {
    if (typeof value !== 'string') return 'deve ser uma string';
    if (rule.minLength !== undefined && value.length < rule.minLength) {
        return `deve ter no mínimo ${rule.minLength} caracteres`;
    }
    if (rule.maxLength !== undefined && value.length > rule.maxLength) {
        return `deve ter no máximo ${rule.maxLength} caracteres`;
    }
    if (rule.pattern && !rule.pattern.test(value)) {
        return rule.patternMessage || 'está em formato inválido';
    }
    return null;
}

function checkInteger(value, rule) {
    let candidate = value;
    if (rule.coerce && typeof value === 'string') {
        if (!DIGITS_ONLY.test(value.trim())) return 'deve ser um número inteiro';
        candidate = Number.parseInt(value, 10);
    }
    if (typeof candidate !== 'number' || !Number.isInteger(candidate)) {
        return 'deve ser um número inteiro';
    }
    if (rule.min !== undefined && candidate < rule.min) return `deve ser no mínimo ${rule.min}`;
    if (rule.max !== undefined && candidate > rule.max) return `deve ser no máximo ${rule.max}`;
    return null;
}

/**
 * Applies a schema and returns the cleaned values, or throws ValidationError with one
 * message per offending field. Presence is tested against `undefined`, not truthiness, so a
 * legitimate `0` or empty string is not mistaken for a missing field.
 */
function apply(schema, source) {
    const cleaned = {};
    const details = {};
    const deprecatedKeys = [];

    for (const [field, rule] of Object.entries(schema)) {
        const { value, usedKey } = readField(source, field, rule);

        if (value === undefined) {
            if (rule.required) details[field] = 'é obrigatório';
            continue;
        }
        if (usedKey !== field) deprecatedKeys.push(usedKey);

        const problem = rule.type === 'integer' ? checkInteger(value, rule) : checkString(value, rule);
        if (problem) {
            details[field] = problem;
            continue;
        }
        cleaned[field] = rule.type === 'integer' && typeof value === 'string'
            ? Number.parseInt(value, 10)
            : value;
    }

    if (Object.keys(details).length > 0) throw new ValidationError(details);
    return { value: cleaned, deprecatedKeys };
}

module.exports = {
    checkoutSchema,
    loginSchema,
    userIdParamSchema,
    reportQuerySchema,
    apply,
    PASSWORD_MIN_LENGTH,
};
