/**
 * A small set of response headers, set without adding a dependency.
 *
 * This is not a replacement for `helmet` — it covers the headers that matter for a JSON API
 * with no browser-rendered content, and it removes the `X-Powered-By` advertisement Express
 * sends by default. A browser-facing deployment should use helmet and an explicit CORS
 * policy driven by config; no CORS middleware is registered here because the API has no
 * declared browser origin, and a wildcard would be worse than its absence.
 */
function securityHeaders(req, res, next) {
    res.removeHeader('X-Powered-By');
    res.set({
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'Referrer-Policy': 'no-referrer',
        'Cache-Control': 'no-store',
    });
    next();
}

module.exports = { securityHeaders };
