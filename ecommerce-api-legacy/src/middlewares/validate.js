/**
 * Boundary validation, applied at the route so a controller never receives unchecked input.
 *
 * The cleaned values land on `req.validated`; the raw `req.body` is not read downstream.
 */
const { apply } = require('../routes/schemas');

function validate({ body, params, query }, { logger }) {
    return (req, res, next) => {
        try {
            req.validated = {};

            if (body) {
                const { value, deprecatedKeys } = apply(body, req.body || {});
                Object.assign(req.validated, value);
                if (deprecatedKeys.length > 0) {
                    logger.warn('request used deprecated field names', {
                        path: req.originalUrl,
                        fields: deprecatedKeys,
                    });
                }
            }
            if (params) {
                Object.assign(req.validated, apply(params, req.params || {}).value);
            }
            if (query) {
                Object.assign(req.validated, apply(query, req.query || {}).value);
            }

            next();
        } catch (err) {
            next(err);          // ValidationError — the error handler formats it
        }
    };
}

module.exports = { validate };
