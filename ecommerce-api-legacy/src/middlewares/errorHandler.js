/**
 * The one place a failure becomes a response.
 *
 * Previously there was none: five database callbacks declared `err` and never read it, so a
 * failed insert still answered `200 {"msg":"Sucesso"}` and a failed delete still answered
 * "Usuário deletado". Errors that did surface hit Express's default handler, which — with
 * NODE_ENV unset — returns a stack trace to the caller.
 *
 * Known errors answer with their own status and a stable `code`. Anything else is logged in
 * full server-side and answered generically, so a driver message naming tables and columns
 * never reaches a client.
 */
const { AppError } = require('../domain/errors');

/**
 * Errors raised by the body parser before any handler runs. They carry a safe status and a
 * `type`, but their messages describe internals, so the status is honoured and the message
 * is replaced by a stable code of our own.
 */
const BODY_PARSER_CODES = {
    'entity.parse.failed': { code: 'malformed_json', message: 'Corpo da requisição não é JSON válido' },
    'entity.too.large': { code: 'payload_too_large', message: 'Corpo da requisição excede o limite' },
    'parameters.too.many': { code: 'payload_too_large', message: 'Corpo da requisição excede o limite' },
    'encoding.unsupported': { code: 'unsupported_encoding', message: 'Codificação não suportada' },
    'request.aborted': { code: 'request_aborted', message: 'Requisição interrompida' },
    'request.size.invalid': { code: 'invalid_content_length', message: 'Content-Length inconsistente' },
};

/**
 * Maps a non-AppError to a client-safe {status, code, message}, or null when it is a
 * genuine server fault that must be answered generically.
 *
 * `http-errors` marks a 4xx as `expose: true`, which is the general signal that the status
 * was chosen for a client rather than being an internal failure.
 */
function clientSafeFailure(err) {
    const known = BODY_PARSER_CODES[err.type];
    if (known) return { status: err.status || err.statusCode || 400, ...known };

    const status = err.status || err.statusCode;
    if (err.expose === true && Number.isInteger(status) && status >= 400 && status < 500) {
        return { status, code: 'bad_request', message: 'Requisição inválida' };
    }
    return null;
}

function notFoundHandler(req, res) {
    res.status(404).json({
        error: {
            code: 'route_not_found',
            message: `Rota não encontrada: ${req.method} ${req.path}`,
        },
    });
}

function createErrorHandler({ logger }) {
    // Express identifies an error handler by its four parameters; `next` must stay declared.
    return function errorHandler(err, req, res, next) {    // eslint-disable-line no-unused-vars
        if (res.headersSent) {
            logger.error('error raised after the response was sent', {
                path: req.originalUrl,
                cause: err.message,
            });
            return res.end();
        }

        if (err instanceof AppError) {
            logger.warn('request failed', {
                path: req.originalUrl,
                method: req.method,
                status: err.status,
                code: err.code,
            });
            if (err.retryAfterSeconds) res.set('Retry-After', String(err.retryAfterSeconds));
            return res.status(err.status).json({
                error: {
                    code: err.code,
                    message: err.expose ? err.message : 'Erro interno',
                    ...(err.details ? { details: err.details } : {}),
                },
            });
        }

        // A client error raised before any handler ran — a malformed or oversized body.
        // Logged as a warning, since nothing on the server is broken.
        const safe = clientSafeFailure(err);
        if (safe) {
            logger.warn('request rejected at the body parser', {
                path: req.originalUrl,
                method: req.method,
                status: safe.status,
                code: safe.code,
                type: err.type || null,
            });
            return res.status(safe.status).json({
                error: { code: safe.code, message: safe.message },
            });
        }

        // Unexpected: the detail is for the operator, never for the caller.
        logger.error('unhandled error', {
            path: req.originalUrl,
            method: req.method,
            name: err.name,
            cause: err.message,
            stack: err.stack,
        });
        return res.status(500).json({
            error: { code: 'internal_error', message: 'Erro interno' },
        });
    };
}

module.exports = { createErrorHandler, notFoundHandler };
