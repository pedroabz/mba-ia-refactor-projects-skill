/**
 * The entry surface: every address the application answers, in one readable place.
 *
 * Each route declares its path, its guards, its validation and the controller it delegates
 * to — and nothing else. No route body contains a rule or a query. Previously the routes
 * were registered from inside the class that owned the database connection, so the API
 * surface could only be discovered by reading the persistence code.
 */
const express = require('express');

const { validate } = require('../middlewares/validate');
const {
    checkoutSchema, loginSchema, userIdParamSchema, reportQuerySchema,
} = require('./schemas');
const { Role } = require('../domain/constants');

function createRoutes({
    checkoutController, reportController, userController, authController,
    requireAuth, limiters, logger,
}) {
    const router = express.Router();

    router.post(
        '/auth/login',
        limiters.login,
        validate({ body: loginSchema }, { logger }),
        authController.login,
    );

    router.post(
        '/checkout',
        limiters.checkout,
        validate({ body: checkoutSchema }, { logger }),
        checkoutController.create,
    );

    router.get(
        '/admin/financial-report',
        requireAuth(Role.ADMIN),
        limiters.admin,
        validate({ query: reportQuerySchema }, { logger }),
        reportController.financial,
    );

    router.delete(
        '/users/:id',
        requireAuth(Role.ADMIN),
        limiters.admin,
        validate({ params: userIdParamSchema }, { logger }),
        userController.remove,
    );

    return router;
}

module.exports = { createRoutes };
