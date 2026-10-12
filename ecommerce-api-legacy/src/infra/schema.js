/**
 * Schema and development seeds, applied once at boot by the composition root.
 *
 * This is not a migration system — the project has none, and the database is ':memory:' by
 * default, so the schema is rebuilt on every start. It is separated from the application
 * anyway so that no request path can create tables, and so the DDL is readable in one place.
 *
 * Relationships are declared as real foreign keys with ON DELETE RESTRICT: enrollments and
 * payments are financial records, so the database must refuse to leave them parentless.
 * Removing a user is an anonymization, not a row deletion (see models/user.model.js).
 */
const { PaymentStatus, Role } = require('../domain/constants');

const DDL = `
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY,
    name       TEXT,
    email      TEXT UNIQUE,
    pass_hash  TEXT,
    role       TEXT     NOT NULL DEFAULT '${Role.STUDENT}',
    created_at DATETIME NOT NULL DEFAULT (datetime('now')),
    deleted_at DATETIME
);

CREATE TABLE IF NOT EXISTS courses (
    id     INTEGER PRIMARY KEY,
    title  TEXT    NOT NULL,
    price  REAL    NOT NULL CHECK (price >= 0),
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS enrollments (
    id         INTEGER PRIMARY KEY,
    user_id    INTEGER  NOT NULL REFERENCES users(id)   ON DELETE RESTRICT,
    course_id  INTEGER  NOT NULL REFERENCES courses(id) ON DELETE RESTRICT,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS payments (
    id            INTEGER PRIMARY KEY,
    enrollment_id INTEGER  NOT NULL REFERENCES enrollments(id) ON DELETE RESTRICT,
    amount        REAL     NOT NULL CHECK (amount >= 0),
    status        TEXT     NOT NULL CHECK (status IN ('${PaymentStatus.PAID}', '${PaymentStatus.DENIED}')),
    created_at    DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id         INTEGER PRIMARY KEY,
    action     TEXT     NOT NULL,
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_enrollments_course ON enrollments(course_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_user   ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_payments_enrollment ON payments(enrollment_id);
`;

async function createSchema(db) {
    await db.exec(DDL);
}

/**
 * Development fixtures. Passwords go through the same hashing path as a real registration —
 * the original seed wrote '123' in plaintext, which meant the stored data was weaker than
 * the (already broken) code path suggested.
 */
async function seed(db, { config, authService, logger }) {
    if (!config.seed.enabled) {
        logger.info('seeding disabled');
        return;
    }
    if (config.isProduction) {
        throw new Error('Refusing to seed fixture accounts in production (set SEED_ENABLED=false)');
    }

    const { count } = await db.get('SELECT COUNT(*) AS count FROM users');
    if (count > 0) {
        logger.info('database already seeded, skipping');
        return;
    }

    const [studentHash, adminHash] = await Promise.all([
        authService.hashPassword(config.seed.studentPassword),
        authService.hashPassword(config.seed.adminPassword),
    ]);

    await db.transaction(async () => {
        await db.run(
            'INSERT INTO users (name, email, pass_hash, role) VALUES (?, ?, ?, ?)',
            ['Leonan', 'leonan@fullcycle.com.br', studentHash, Role.STUDENT],
        );
        await db.run(
            'INSERT INTO users (name, email, pass_hash, role) VALUES (?, ?, ?, ?)',
            ['Admin', 'admin@fullcycle.com.br', adminHash, Role.ADMIN],
        );
        await db.run(
            'INSERT INTO courses (title, price, active) VALUES (?, ?, 1), (?, ?, 1)',
            ['Clean Architecture', 997.0, 'Docker', 497.0],
        );
        await db.run('INSERT INTO enrollments (user_id, course_id) VALUES (1, 1)');
        await db.run(
            'INSERT INTO payments (enrollment_id, amount, status) VALUES (1, ?, ?)',
            [997.0, PaymentStatus.PAID],
        );
    });

    logger.info('seeded development fixtures', { users: 2, courses: 2, enrollments: 1 });
}

module.exports = { createSchema, seed };
