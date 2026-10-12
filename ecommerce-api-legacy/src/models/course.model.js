/** Courses: persistence only. Columns are named explicitly so a new column cannot leak. */
class CourseModel {
    constructor(db) {
        this.db = db;
    }

    findActiveById(id) {
        return this.db.get(
            'SELECT id, title, price FROM courses WHERE id = ? AND active = 1',
            [id],
        );
    }

    /**
     * One page of courses, ordered deterministically. Pagination is clamped by the caller
     * (the controller owns the policy); this method just refuses to fetch the whole table
     * by default the way `SELECT * FROM courses` did.
     */
    listPage({ limit, offset }) {
        return this.db.all(
            'SELECT id, title FROM courses ORDER BY id LIMIT ? OFFSET ?',
            [limit, offset],
        );
    }

    async count() {
        const { count } = await this.db.get('SELECT COUNT(*) AS count FROM courses');
        return count;
    }
}

module.exports = { CourseModel };
