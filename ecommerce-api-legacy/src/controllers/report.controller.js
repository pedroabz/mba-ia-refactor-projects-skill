/**
 * Financial report: pagination in, one response out.
 *
 * The body stays the bare array the endpoint has always returned, so existing clients keep
 * working; pagination is exposed through headers instead of wrapping the payload in a new
 * envelope. The ordering is now deterministic (by course id, then enrollment id) — the
 * original returned the same data in a different order on each call.
 */
function createReportController({ reportService }) {
    async function financial(req, res, next) {
        try {
            const { items, paging } = await reportService.financialReport({
                limit: req.validated.limit,
                offset: req.validated.offset,
            });

            res.set({
                'X-Total-Count': String(paging.totalCourses),
                'X-Page-Limit': String(paging.limit),
                'X-Page-Offset': String(paging.offset),
            });
            res.status(200).json(items);
        } catch (err) {
            next(err);
        }
    }

    return { financial };
}

module.exports = { createReportController };
