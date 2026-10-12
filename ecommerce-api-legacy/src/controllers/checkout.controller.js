/**
 * Checkout: reads the validated request, calls the use case, chooses the status code.
 *
 * No SQL, no payment rule, no password handling — those belong to the models and services
 * this delegates to. Failures are thrown, not answered, so the error handler owns every
 * error response.
 */
function createCheckoutController({ checkoutService }) {
    async function create(req, res, next) {
        try {
            const enrollment = await checkoutService.purchase(req.validated);
            res.status(201)
                .location(`/api/enrollments/${enrollment.enrollmentId}`)
                .json(enrollment);
        } catch (err) {
            next(err);
        }
    }

    return { create };
}

module.exports = { createCheckoutController };
