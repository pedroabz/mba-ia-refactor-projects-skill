/**
 * Composition root: the only place that knows how the application is assembled.
 *
 * It loads configuration, creates the connection, builds the models, services, controllers
 * and middleware, wires them together, registers the chain in order and starts listening.
 * It defines no route handler, runs no query and creates no schema — `AppManager` used to do
 * all three while also owning the Express instance it had been handed.
 *
 * `buildApp` returns the configured app without listening, so the application can be
 * constructed for a test or a script without binding a port.
 */
const express = require('express');

const { createLogger } = require('./infra/logger');
const { createDatabase } = require('./infra/database');
const { createSchema, seed } = require('./infra/schema');

const { UserModel } = require('./models/user.model');
const { CourseModel } = require('./models/course.model');
const { EnrollmentModel } = require('./models/enrollment.model');
const { PaymentModel } = require('./models/payment.model');
const { AuditLogModel } = require('./models/auditLog.model');
const { ReportModel } = require('./models/report.model');

const { createAuthService } = require('./services/auth.service');
const { createPaymentGateway } = require('./services/payment.gateway');
const { createCheckoutService } = require('./services/checkout.service');
const { createReportService } = require('./services/report.service');

const { createCheckoutController } = require('./controllers/checkout.controller');
const { createReportController } = require('./controllers/report.controller');
const { createUserController } = require('./controllers/user.controller');
const { createAuthController } = require('./controllers/auth.controller');

const { createRoutes } = require('./routes');
const { createErrorHandler, notFoundHandler } = require('./middlewares/errorHandler');
const { createRequireAuth } = require('./middlewares/requireAuth');
const { createRateLimiter } = require('./middlewares/rateLimit');
const { createRequestLogger } = require('./middlewares/requestLogger');
const { securityHeaders } = require('./middlewares/securityHeaders');

/**
 * Loaded here rather than at module scope so that a misconfiguration — a secret missing in
 * production, a non-numeric port — reports one clear line instead of a stack trace from
 * inside a require.
 */
function loadConfig() {
    try {
        return require('./config').config;
    } catch (err) {
        process.stderr.write(`configuration error: ${err.message}\n`);
        process.exit(1);
    }
    return undefined;        // unreachable; keeps the return type honest
}

async function buildApp() {
    const config = loadConfig();
    const logger = createLogger({ level: config.log.level });

    // ---- infrastructure --------------------------------------------------------
    const db = createDatabase({ file: config.database.file, logger });
    await db.initialize();
    await createSchema(db);

    // ---- models ----------------------------------------------------------------
    const userModel = new UserModel(db);
    const courseModel = new CourseModel(db);
    const enrollmentModel = new EnrollmentModel(db);
    const paymentModel = new PaymentModel(db);
    const auditLogModel = new AuditLogModel(db);
    const reportModel = new ReportModel(db);

    // ---- services --------------------------------------------------------------
    const authService = createAuthService({ userModel, config, logger });
    const paymentGateway = createPaymentGateway({ config, logger });
    const checkoutService = createCheckoutService({
        db, userModel, courseModel, enrollmentModel, paymentModel, auditLogModel,
        paymentGateway, authService, logger,
    });
    const reportService = createReportService({ courseModel, reportModel, config, logger });

    await seed(db, { config, authService, logger });

    // ---- controllers -----------------------------------------------------------
    const checkoutController = createCheckoutController({ checkoutService });
    const reportController = createReportController({ reportService });
    const userController = createUserController({ userModel, logger });
    const authController = createAuthController({ authService });

    // ---- middleware ------------------------------------------------------------
    const requireAuth = createRequireAuth({ authService });
    const limiters = {
        checkout: createRateLimiter({
            windowMs: config.rateLimit.windowMs,
            max: config.rateLimit.checkoutMax,
            name: 'checkout',
            logger,
        }),
        login: createRateLimiter({
            windowMs: config.rateLimit.windowMs,
            max: config.rateLimit.loginMax,
            name: 'login',
            logger,
        }),
        admin: createRateLimiter({
            windowMs: config.rateLimit.windowMs,
            max: config.rateLimit.adminMax,
            name: 'admin',
            logger,
        }),
    };

    // ---- the chain, in order ---------------------------------------------------
    const app = express();
    app.disable('x-powered-by');
    app.set('trust proxy', false);          // req.ip must not be spoofable by a header

    app.use(securityHeaders);
    app.use(express.json({ limit: config.http.bodyLimit }));
    app.use(createRequestLogger({ logger }));

    app.use('/api', createRoutes({
        checkoutController, reportController, userController, authController,
        requireAuth, limiters, logger,
    }));

    app.use(notFoundHandler);
    app.use(createErrorHandler({ logger }));    // last, or it never runs

    return { app, db, logger, config };
}

async function start() {
    const { app, db, logger, config } = await buildApp();

    const server = app.listen(config.http.port, config.http.host, () => {
        logger.info('listening', {
            host: config.http.host,
            port: config.http.port,
            env: config.env,
            database: config.database.file,
            paymentDriver: config.payment.driver,
        });
    });

    // A rejection or a throw inside an async callback used to terminate the process with a
    // stack trace and no log line. Report it, then exit deliberately.
    process.on('unhandledRejection', (reason) => {
        logger.error('unhandled rejection', {
            cause: reason instanceof Error ? reason.message : String(reason),
            stack: reason instanceof Error ? reason.stack : null,
        });
    });
    process.on('uncaughtException', (err) => {
        logger.error('uncaught exception — shutting down', { cause: err.message, stack: err.stack });
        server.close(() => process.exit(1));
    });

    for (const signal of ['SIGINT', 'SIGTERM']) {
        process.on(signal, () => {
            logger.info('shutting down', { signal });
            server.close(async () => {
                await db.close().catch(() => undefined);
                process.exit(0);
            });
        });
    }

    return server;
}

if (require.main === module) {
    start().catch((err) => {
        process.stderr.write(`failed to start: ${err.stack || err.message}\n`);
        process.exit(1);
    });
}

module.exports = { buildApp, start };
