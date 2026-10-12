/**
 * One structured log line per request, with the status and duration.
 *
 * Replaces having no request logging at all, which meant abuse of the unthrottled payment
 * endpoint would have left no trace. Logs the method, path and status — never the body,
 * which on this API carries card numbers and passwords.
 */
function createRequestLogger({ logger }) {
    return function requestLogger(req, res, next) {
        const startedAt = process.hrtime.bigint();
        // Captured now: Express rewrites req.url while routing into a mounted router, so
        // reading req.path once the response has finished can yield a router-relative path.
        const path = req.originalUrl.split('?')[0];

        res.on('finish', () => {
            const durationMs = Number(process.hrtime.bigint() - startedAt) / 1e6;
            const level = res.statusCode >= 500 ? 'error' : 'info';
            logger[level]('request', {
                method: req.method,
                path,
                status: res.statusCode,
                durationMs: Math.round(durationMs),
                userId: req.currentUser ? req.currentUser.id : null,
            });
        });

        next();
    };
}

module.exports = { createRequestLogger };
