/**
 * Authentication and role authorization, enforced at the route layer.
 *
 * The application previously had no concept of a caller: all three endpoints were anonymous,
 * including a report of platform-wide revenue with student names and an irreversible user
 * deletion by path id. Enforcing here rather than inside each handler means a new route is
 * unprotected only if someone writes it that way on purpose.
 */
const { UnauthorizedError, ForbiddenError } = require('../domain/errors');

function bearerToken(req) {
    const header = req.get('authorization');
    if (!header) return null;
    const [scheme, value] = header.split(' ');
    if (!value || scheme.toLowerCase() !== 'bearer') return null;
    return value.trim();
}

/**
 * @param {...string} roles  allowed roles; empty means "any authenticated caller"
 */
function createRequireAuth({ authService }) {
    return function requireAuth(...roles) {
        return (req, res, next) => {
            const token = bearerToken(req);
            if (!token) return next(new UnauthorizedError());

            const payload = authService.verifyToken(token);
            if (!payload) {
                return next(new UnauthorizedError('Token inválido ou expirado'));
            }
            if (roles.length > 0 && !roles.includes(payload.role)) {
                return next(new ForbiddenError());
            }

            req.currentUser = { id: payload.sub, role: payload.role };
            next();
        };
    };
}

module.exports = { createRequireAuth };
