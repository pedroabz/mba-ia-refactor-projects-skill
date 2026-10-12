/**
 * The checkout use case: the sequence of steps, and the transaction boundary around them.
 *
 * Three defects in the original flow are fixed by the ordering alone:
 *   - The four writes (user, enrollment, payment, audit log) had no transaction, so a
 *     failure between them left committed partial state — an enrollment with no payment
 *     meant course access with no charge on record.
 *   - Payment was "processed" before any write, so a database failure produced a charge
 *     with no counterpart.
 *   - A declined payment returned 400 *after* the user row had been committed, leaving an
 *     account behind for a purchase that never happened.
 *
 * Everything that can fail now happens before the first write, and the writes commit once.
 */
const { NotFoundError, PaymentDeclinedError } = require('../domain/errors');
const { PaymentStatus, Role } = require('../domain/constants');

function createCheckoutService({
    db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel,
    paymentGateway, authService, logger,
}) {
    /**
     * @returns {Promise<{enrollmentId:number, courseId:number, amount:number, status:string}>}
     */
    async function purchase({ name, email, password, courseId, cardNumber }) {
        // ---- everything that can fail, before anything is written -------------------
        const course = await courseModel.findActiveById(courseId);
        if (!course) {
            throw new NotFoundError('course_not_found', 'Curso não encontrado');
        }

        const existingUser = await userModel.findActiveByEmail(email);

        const authorization = await paymentGateway.authorize({
            cardNumber,
            amount: course.price,
            reference: `course:${course.id}`,
        });
        if (!authorization.approved) {
            // Nothing has been written, so there is nothing to roll back or clean up.
            logger.info('checkout declined', {
                courseId: course.id,
                reason: authorization.declineReason,
            });
            throw new PaymentDeclinedError();
        }

        // Hashing is deliberately outside the transaction: a password KDF is slow by design
        // and holding a write transaction open across it would serialize every checkout.
        const passwordHash = existingUser ? null : await authService.hashPassword(password);

        // ---- one unit of work ------------------------------------------------------
        const result = await db.transaction(async () => {
            const userId = existingUser
                ? existingUser.id
                : await userModel.create({ name, email, passwordHash, role: Role.STUDENT });

            const enrollmentId = await enrollmentModel.create({ userId, courseId: course.id });

            await paymentModel.create({
                enrollmentId,
                amount: course.price,
                status: PaymentStatus.PAID,
            });

            await auditLogModel.record(`Checkout curso ${course.id} por ${userId}`);

            return {
                enrollmentId,
                courseId: course.id,
                amount: course.price,
                status: PaymentStatus.PAID,
                userId,
                userCreated: !existingUser,
            };
        });

        logger.info('checkout completed', {
            enrollmentId: result.enrollmentId,
            courseId: result.courseId,
            userId: result.userId,
            userCreated: result.userCreated,
        });

        return {
            enrollmentId: result.enrollmentId,
            courseId: result.courseId,
            amount: result.amount,
            status: result.status,
        };
    }

    return { purchase };
}

module.exports = { createCheckoutService };
