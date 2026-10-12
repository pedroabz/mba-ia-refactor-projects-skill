/**
 * Read model for the financial report: the cross-entity queries, and nothing else.
 *
 * It replaces a `1 + C + 2E` query storm (one query per course, then two per enrollment)
 * with a fixed two queries, regardless of how many courses, enrollments or payments exist.
 *
 * Revenue is summed by the database rather than accumulated in a loop, which also makes it
 * independent of how many students the response embeds: capping the student list can never
 * change the reported revenue.
 */
const { REVENUE_STATUSES } = require('../domain/constants');

/**
 * One payment per enrollment, chosen as the lowest id.
 *
 * The original code read payments with a single-row fetch per enrollment, so a second
 * payment row for the same enrollment was ignored. A plain join would instead multiply the
 * enrollment and double-count its revenue, so the selection is pinned explicitly.
 */
const ONE_PAYMENT_PER_ENROLLMENT = `
    p.id = (SELECT MIN(id) FROM payments WHERE enrollment_id = e.id)
`;

const REVENUE_PLACEHOLDERS = REVENUE_STATUSES.map(() => '?').join(', ');

class ReportModel {
    constructor(db) {
        this.db = db;
    }

    /** Revenue per course for the given courses, aggregated in SQL. */
    async revenueByCourse(courseIds) {
        if (courseIds.length === 0) return new Map();
        const placeholders = courseIds.map(() => '?').join(', ');
        const rows = await this.db.all(
            `SELECT e.course_id AS courseId, COALESCE(SUM(p.amount), 0) AS revenue
               FROM enrollments e
               JOIN payments p ON ${ONE_PAYMENT_PER_ENROLLMENT}
              WHERE e.course_id IN (${placeholders})
                AND p.status IN (${REVENUE_PLACEHOLDERS})
              GROUP BY e.course_id`,
            [...courseIds, ...REVENUE_STATUSES],
        );
        return new Map(rows.map((row) => [row.courseId, row.revenue]));
    }

    /**
     * One row per enrollment for the given courses, with the student's name and the amount
     * paid. `studentName` is null for an anonymized account; the caller decides how to label
     * that, because it is a presentation choice, not a persistence one.
     */
    enrollmentRows(courseIds, { limitPerCourse }) {
        if (courseIds.length === 0) return Promise.resolve([]);
        const placeholders = courseIds.map(() => '?').join(', ');
        return this.db.all(
            `SELECT enrollmentId, courseId, studentName, studentDeletedAt, amount, status
               FROM (
                    SELECT e.id         AS enrollmentId,
                           e.course_id  AS courseId,
                           u.name       AS studentName,
                           u.deleted_at AS studentDeletedAt,
                           p.amount     AS amount,
                           p.status     AS status,
                           ROW_NUMBER() OVER (
                               PARTITION BY e.course_id ORDER BY e.id
                           ) AS positionInCourse
                      FROM enrollments e
                      LEFT JOIN users    u ON u.id = e.user_id
                      LEFT JOIN payments p ON ${ONE_PAYMENT_PER_ENROLLMENT}
                     WHERE e.course_id IN (${placeholders})
               )
              WHERE positionInCourse <= ?
              ORDER BY courseId, enrollmentId`,
            [...courseIds, limitPerCourse],
        );
    }

    /** Enrollment totals per course, so a truncated student list can be reported honestly. */
    async countEnrollmentsByCourse(courseIds) {
        if (courseIds.length === 0) return new Map();
        const placeholders = courseIds.map(() => '?').join(', ');
        const rows = await this.db.all(
            `SELECT course_id AS courseId, COUNT(*) AS count
               FROM enrollments
              WHERE course_id IN (${placeholders})
              GROUP BY course_id`,
            courseIds,
        );
        return new Map(rows.map((row) => [row.courseId, row.count]));
    }
}

module.exports = { ReportModel };
