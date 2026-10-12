/**
 * Domain vocabulary with one owner.
 *
 * These values used to be inline literals: 'PAID' appeared in the seed, in the approval
 * rule and in the revenue filter, so adding a status meant finding every copy — and
 * missing the one in the revenue filter would have silently produced wrong accounting.
 */

const PaymentStatus = Object.freeze({
    PAID: 'PAID',
    DENIED: 'DENIED',
});

/** Only these statuses count toward revenue. The report asks this, it does not decide it. */
const REVENUE_STATUSES = Object.freeze([PaymentStatus.PAID]);

const Role = Object.freeze({
    STUDENT: 'student',
    ADMIN: 'admin',
});

/** Shown in the report where a student's account has been removed and anonymized. */
const REMOVED_STUDENT_LABEL = 'Conta removida';

module.exports = { PaymentStatus, REVENUE_STATUSES, Role, REMOVED_STUDENT_LABEL };
