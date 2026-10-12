/**
 * Users: removal.
 *
 * Removal anonymizes rather than deleting the row, because the enrollments and payments that
 * reference a user are financial records. Deleting the row is what used to leave them
 * parentless — revenue still counted, with no way left to tell who had paid.
 *
 * The status now reports what happened: 204 when an account was removed, 404 when there was
 * no active account with that id. The original answered 200 and the text "Usuário deletado"
 * in both cases, and also when the delete had failed outright, because its `err` was ignored.
 */
const { NotFoundError } = require('../domain/errors');

function createUserController({ userModel, logger }) {
    async function remove(req, res, next) {
        try {
            const { id } = req.validated;
            const changed = await userModel.anonymize(id);

            if (changed === 0) {
                throw new NotFoundError('user_not_found', 'Usuário não encontrado');
            }

            logger.info('user account removed', {
                userId: id,
                removedBy: req.currentUser.id,
            });
            res.status(204).send();
        } catch (err) {
            next(err);
        }
    }

    return { remove };
}

module.exports = { createUserController };
