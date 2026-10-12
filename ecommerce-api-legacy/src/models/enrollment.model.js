/** Enrollments: persistence only. Created inside the checkout transaction. */
class EnrollmentModel {
    constructor(db) {
        this.db = db;
    }

    async create({ userId, courseId }) {
        const { lastID } = await this.db.run(
            'INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)',
            [userId, courseId],
        );
        return lastID;
    }

    countByUser(userId) {
        return this.db.get(
            'SELECT COUNT(*) AS count FROM enrollments WHERE user_id = ?',
            [userId],
        );
    }
}

module.exports = { EnrollmentModel };
