/**
 * The financial report use case: two queries and a pure grouping function.
 *
 * The original handler coordinated `1 + C + 2E` concurrent queries with two hand-rolled
 * counters and decided when to respond by decrementing them. Any ignored `err` — and all
 * three inner callbacks ignored theirs — either left a counter that never reached zero (the
 * request hung until the client gave up) or threw inside a driver callback and terminated
 * the process. It also assembled the response in callback-completion order, so two
 * identical calls returned the courses in different orders.
 *
 * `groupByCourse` is exported because it is where the reporting rules live and it needs no
 * database to exercise.
 */
const { REMOVED_STUDENT_LABEL } = require('../domain/constants');

/**
 * Shapes rows into the report payload. Pure: same input, same output, no I/O.
 *
 * Preserved from the original on purpose:
 *   - one entry per enrollment, not per distinct student, so a student enrolled twice
 *     appears twice;
 *   - an enrollment with no payment row counts as `paid: 0`;
 *   - a course with no enrollments keeps an empty `students` list.
 */
function groupByCourse(courses, enrollmentRows, revenueByCourse) {
    const studentsByCourse = new Map(courses.map((course) => [course.id, []]));

    for (const row of enrollmentRows) {
        const students = studentsByCourse.get(row.courseId);
        if (!students) continue;              // a course outside the requested page
        students.push({
            student: row.studentName ?? (row.studentDeletedAt ? REMOVED_STUDENT_LABEL : null),
            paid: row.amount ?? 0,
        });
    }

    return courses.map((course) => ({
        course: course.title,
        revenue: revenueByCourse.get(course.id) ?? 0,
        students: studentsByCourse.get(course.id),
    }));
}

function createReportService({ courseModel, reportModel, config, logger }) {
    const { defaultPageSize, maxPageSize, maxStudentsPerCourse } = config.report;

    /** Clamps server-side: a client-supplied page size is a request, not an authorization. */
    function resolvePaging({ limit, offset }) {
        return {
            limit: Math.min(Math.max(limit ?? defaultPageSize, 1), maxPageSize),
            offset: Math.max(offset ?? 0, 0),
        };
    }

    async function financialReport({ limit, offset } = {}) {
        const paging = resolvePaging({ limit, offset });

        const [courses, totalCourses] = await Promise.all([
            courseModel.listPage(paging),
            courseModel.count(),
        ]);
        const courseIds = courses.map((course) => course.id);

        const [revenueByCourse, enrollmentRows, enrollmentCounts] = await Promise.all([
            reportModel.revenueByCourse(courseIds),
            reportModel.enrollmentRows(courseIds, { limitPerCourse: maxStudentsPerCourse }),
            reportModel.countEnrollmentsByCourse(courseIds),
        ]);

        // A cap that silently drops rows reads as "this is everything". Say so instead.
        for (const [courseId, count] of enrollmentCounts) {
            if (count > maxStudentsPerCourse) {
                logger.warn('report student list truncated', {
                    courseId,
                    enrollments: count,
                    included: maxStudentsPerCourse,
                });
            }
        }

        return {
            items: groupByCourse(courses, enrollmentRows, revenueByCourse),
            paging: { ...paging, totalCourses },
        };
    }

    return { financialReport, groupByCourse };
}

module.exports = { createReportService, groupByCourse };
