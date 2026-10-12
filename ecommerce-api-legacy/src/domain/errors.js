/**
 * Error types carrying an HTTP status and a client-safe code.
 *
 * Controllers and services throw these instead of writing a response, so there is exactly
 * one place that turns a failure into a reply (middlewares/errorHandler.js). The `code` is
 * the stable identifier a client branches on; `message` is for humans and may change.
 */
class AppError extends Error {
    constructor(message, { status = 500, code = 'internal_error', details = null, expose = true } = {}) {
        super(message);
        this.name = this.constructor.name;
        this.status = status;
        this.code = code;
        this.details = details;
        this.expose = expose;        // false ⇒ the handler sends a generic message instead
    }
}

class ValidationError extends AppError {
    constructor(details, message = 'Requisição inválida') {
        super(message, { status: 400, code: 'validation_error', details });
    }
}

class UnauthorizedError extends AppError {
    constructor(message = 'Autenticação necessária') {
        super(message, { status: 401, code: 'unauthorized' });
    }
}

class ForbiddenError extends AppError {
    constructor(message = 'Acesso negado') {
        super(message, { status: 403, code: 'forbidden' });
    }
}

class NotFoundError extends AppError {
    constructor(code, message) {
        super(message, { status: 404, code });
    }
}

class ConflictError extends AppError {
    constructor(code, message) {
        super(message, { status: 409, code });
    }
}

/** 402: the request was well-formed and the provider refused it. Not a client error. */
class PaymentDeclinedError extends AppError {
    constructor(message = 'Pagamento recusado', details = null) {
        super(message, { status: 402, code: 'payment_declined', details });
    }
}

class RateLimitedError extends AppError {
    constructor(retryAfterSeconds) {
        super('Muitas requisições', {
            status: 429,
            code: 'rate_limited',
            details: { retryAfterSeconds },
        });
        this.retryAfterSeconds = retryAfterSeconds;
    }
}

module.exports = {
    AppError,
    ValidationError,
    UnauthorizedError,
    ForbiddenError,
    NotFoundError,
    ConflictError,
    PaymentDeclinedError,
    RateLimitedError,
};
