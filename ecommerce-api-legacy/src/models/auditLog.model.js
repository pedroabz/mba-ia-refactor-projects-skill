/**
 * Audit trail for operations that move money.
 *
 * Written inside the checkout transaction on purpose: a payment that cannot be recorded in
 * the trail should not commit. Previously the insert's error was discarded and checkout
 * answered "Sucesso" regardless, so the trail could silently miss entries.
 *
 * No read path exists yet — nothing in the application queries these rows. That is a known
 * gap recorded in the refactor report, not an oversight: the write is kept because an audit
 * trail is a requirement of the domain, and exposing it needs a use case of its own.
 */
class AuditLogModel {
    constructor(db) {
        this.db = db;
    }

    async record(action) {
        const { lastID } = await this.db.run(
            'INSERT INTO audit_logs (action) VALUES (?)',
            [action],
        );
        return lastID;
    }
}

module.exports = { AuditLogModel };
