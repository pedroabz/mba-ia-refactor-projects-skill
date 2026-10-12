/**
 * Connection factory. The only module that knows `sqlite3` exists.
 *
 * Three things it provides that the original code lacked:
 *   - A promise interface, so callers use `await` instead of nested callbacks. An error
 *     becomes a rejection that propagates to the error handler rather than an ignored
 *     `err` argument or an exception thrown inside a driver callback (which escapes
 *     Express entirely and terminates the process).
 *   - `transaction()`, so a multi-write operation commits once or not at all.
 *   - Foreign-key enforcement, which SQLite leaves off per connection by default.
 *
 * The connection is created here and handed to whoever needs it; nothing constructs its
 * own. That is what makes the models testable against a different database.
 */
const sqlite3 = require('sqlite3');

function createDatabase({ file, logger }) {
    const db = new sqlite3.Database(file);

    const run = (sql, params = []) => new Promise((resolve, reject) => {
        db.run(sql, params, function callback(err) {
            if (err) return reject(err);
            resolve({ lastID: this.lastID, changes: this.changes });
        });
    });

    const get = (sql, params = []) => new Promise((resolve, reject) => {
        db.get(sql, params, (err, row) => (err ? reject(err) : resolve(row)));
    });

    const all = (sql, params = []) => new Promise((resolve, reject) => {
        db.all(sql, params, (err, rows) => (err ? reject(err) : resolve(rows)));
    });

    const exec = (sql) => new Promise((resolve, reject) => {
        db.exec(sql, (err) => (err ? reject(err) : resolve()));
    });

    const close = () => new Promise((resolve, reject) => {
        db.close((err) => (err ? reject(err) : resolve()));
    });

    // Transactions are serialized with a promise chain because SQLite transactions belong to
    // a connection, not to a request: two overlapping BEGINs on one connection would
    // interleave their statements into each other's unit of work. A second connection is not
    // an option for ':memory:', where it would be a different database altogether.
    let queue = Promise.resolve();

    function transaction(work) {
        const result = queue.then(async () => {
            await run('BEGIN IMMEDIATE');
            try {
                const value = await work();
                await run('COMMIT');
                return value;
            } catch (err) {
                try {
                    await run('ROLLBACK');
                } catch (rollbackErr) {
                    logger.error('rollback failed', { cause: rollbackErr.message });
                }
                throw err;
            }
        });
        // The queue must not reject, or every later transaction inherits the failure.
        queue = result.then(() => undefined, () => undefined);
        return result;
    }

    async function initialize() {
        await run('PRAGMA foreign_keys = ON');
        const [{ foreign_keys: enforced }] = await all('PRAGMA foreign_keys');
        if (!enforced) {
            throw new Error('SQLite refused to enable foreign-key enforcement');
        }
    }

    return { run, get, all, exec, close, transaction, initialize, file };
}

module.exports = { createDatabase };
