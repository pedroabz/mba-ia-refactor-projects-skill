/**
 * Users: persistence and the invariants that hold regardless of who is asking.
 *
 * Receives the connection; never creates one. Knows nothing about HTTP, and never returns
 * a response-shaped object — `pass_hash` leaves this module only through `findCredentials`,
 * which exists so the auth service can verify a password and nothing else.
 */
class UserModel {
    constructor(db) {
        this.db = db;
    }

    /** Public columns only: a password hash has no business in a lookup result. */
    findActiveByEmail(email) {
        return this.db.get(
            'SELECT id, name, email, role FROM users WHERE email = ? AND deleted_at IS NULL',
            [email],
        );
    }

    findActiveById(id) {
        return this.db.get(
            'SELECT id, name, email, role FROM users WHERE id = ? AND deleted_at IS NULL',
            [id],
        );
    }

    /** The one query that reads the hash. Called only by the auth service. */
    findCredentialsByEmail(email) {
        return this.db.get(
            'SELECT id, email, pass_hash, role FROM users WHERE email = ? AND deleted_at IS NULL',
            [email],
        );
    }

    async create({ name, email, passwordHash, role }) {
        const { lastID } = await this.db.run(
            'INSERT INTO users (name, email, pass_hash, role) VALUES (?, ?, ?, ?)',
            [name, email, passwordHash, role],
        );
        return lastID;
    }

    /**
     * Removal is anonymization, not deletion: the personal data goes, the row stays so the
     * enrollments and payments that reference it keep a valid parent. Deleting the row
     * instead is what left the financial records orphaned and unattributable, with revenue
     * still counted against students who no longer existed.
     *
     * Returns the number of rows affected: 0 means "no such active user", which the
     * controller turns into a 404 rather than reporting a success that did not happen.
     */
    async anonymize(id) {
        const { changes } = await this.db.run(
            `UPDATE users
                SET name = NULL, email = NULL, pass_hash = NULL, deleted_at = datetime('now')
              WHERE id = ? AND deleted_at IS NULL`,
            [id],
        );
        return changes;
    }
}

module.exports = { UserModel };
