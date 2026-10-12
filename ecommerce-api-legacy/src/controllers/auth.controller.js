/**
 * Login.
 *
 * New in this refactor. The application stored a password for every user and never compared
 * one anywhere: the column was write-only and no endpoint could tell callers apart, which is
 * why nothing could be protected. This is what gives the guard middleware something to
 * verify.
 *
 * A failure is always the same 401, so the response cannot be used to distinguish a
 * registered email from an unregistered one.
 */
const { UnauthorizedError } = require('../domain/errors');

function createAuthController({ authService }) {
    async function login(req, res, next) {
        try {
            const session = await authService.login(req.validated);
            if (!session) {
                throw new UnauthorizedError('Credenciais inválidas');
            }
            res.status(200).json(session);
        } catch (err) {
            next(err);
        }
    }

    return { login };
}

module.exports = { createAuthController };
