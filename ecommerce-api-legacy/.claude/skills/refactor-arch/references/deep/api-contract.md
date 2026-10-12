# API contract — detection depth

Confirmation steps for the `API` family. Read before writing any `API` finding.

This family covers the request lifecycle: what the boundary accepts, what happens when
something fails, and what the caller receives. The findings are mostly MEDIUM, which makes
them easy to under-report — but they are also where the challenge's MEDIUM definition points
("improper middleware usage, missing validation in API routes").

---

## API-01 — Broken request lifecycle · HIGH

Violates: fail fast; exactly one response per request.

**Confirm by** tracing every path through the handler to a response. The finding is a path
that sends none, or more than one.

The usual cause is hand-rolled coordination of concurrent work: manual counters or flags
deciding when all the pieces are done and the response can be sent. Check each branch for
whether it decrements the counter and whether it can be reached before the decrement. An
early return, a thrown error, or a value read before an error check will skip it — and the
request then hangs until the client times out, because nothing ever reaches the send.

**Deep nesting is the enabling condition**, not the finding itself. Report the hang or the
double-send as the consequence, and the nesting as the reason it is invisible.

**Report illegibility separately and honestly.** Unreadable nesting is a real finding on its
own terms, independent of whether a bug is present — a reviewer skimming the handler cannot
verify it either way, which is how the bug survived. Keep that as its own LOW/MEDIUM finding
(QUA-04 territory) rather than folding it into this one; the severities and the fixes differ.

**Not this:** a framework's own async handling. Multiple response branches where exactly one
is reachable per path. A deliberate streaming response.

**Fix** → T-18.

---

## API-02 — Errors swallowed or leaked verbatim · MEDIUM

Violates: explicit errors.

Two opposite failures, both from the same missing design:

**Swallowed.** A bare `except:` or `catch {}` with no rethrow; an error parameter declared
and never inspected; a callback that ignores its error argument and proceeds with undefined
data. Confirm by checking what the handler does with the error — if nothing, the caller gets
a success or a generic message and the cause is lost. A bare catch also swallows
cancellation and shutdown signals, which is worth stating where the language works that way.

**Leaked.** Raw exception text, a stack trace, or a driver error message returned to the
client. Confirm by following the error into the response body. This is an information
disclosure finding as well as a contract one — database errors name tables and columns.

**No centralized handler** is the structural version: every handler wrapping itself in
try/except with the same generic message, which is duplication and guarantees drift.

**Not this:** a targeted catch of a specific expected exception, handled deliberately. A
deliberately generic client-facing message with the detail logged server-side.

**Fix** → T-14.

---

## API-03 — Input not validated at the boundary · MEDIUM

Violates: validate at the edge. Named in the challenge's MEDIUM definition.

**Confirm by** listing what the handler reads from the request and what it checks. Gaps to
look for:

- No type check before arithmetic or comparison — a string where a number is expected
  reaches the database or raises an unhandled error.
- Presence-only checks that treat falsy as missing, so a legitimate `0` or empty string is
  rejected. Worth reporting as a correctness bug, not a style note.
- No format check on structured values: email, date, colour, identifier.
- No enum check where only a fixed set is valid.
- No range or length bounds.
- An optional credential or security-relevant field silently defaulted — an account created
  with a known default password is a security finding too.
- A cast with no error handling, so malformed input becomes a 500 rather than a 400.

**Check for the validation that exists elsewhere.** Where a validation helper or schema
library is present in the project but bypassed, that is the stronger finding: the mechanism
exists and is not used. A declared schema-validation dependency that is never imported is
evidence of the same.

**Not this:** validation performed by a framework-level schema, decorator or type coercion.
A path converter that already constrains the type. Trusted internal input, if the trust
boundary is visible.

**Fix** → T-15.

---

## API-04 — Missing middleware chain · MEDIUM

Violates: cross-cutting concerns belong in one place. Named in the challenge's MEDIUM
definition.

**Confirm by** reading the composition root and listing what is registered. Then check for
the absence of what this application actually needs — not a generic checklist:

- Request size limit on any endpoint accepting a body.
- Rate limiting on expensive, destructive, authentication or payment endpoints.
- Authentication/authorization middleware where routes assume a caller identity.
- A centralized error handler.
- Security headers and a restrictive CORS policy where a browser is a client.
- Request logging, if operability matters.

**Tie each absence to the route it exposes.** "No rate limit" is generic; "no rate limit on
the endpoint that accepts card numbers, so card testing is unthrottled" is a finding. The
second also makes the severity self-evident.

**The inverse is the same finding:** cross-cutting work copy-pasted into every handler
instead of registered once. Report it here, since the fix is the same middleware chain.

**Not this:** a framework that applies a given protection by default. A deliberate choice
documented in the project. An internal service behind a gateway that provides these, if that
is visible.

**Fix** → T-16.

---

## API-05 — Inconsistent or uninformative response contract · LOW

Violates: a predictable interface.

**Confirm by** collecting every response from one endpoint, then from its siblings, and
comparing shapes. Findings:

- The same endpoint returning plain text on error and structured data on success, so the
  client cannot parse failures programmatically.
- An envelope or flag present on some responses and absent on others.
- Status codes that misreport the outcome: success for a missing resource, success for a
  failed write, a generic server error for what is a client validation failure, no conflict
  status for a duplicate.
- An error body shape that differs between handlers.

**Verify before claiming a status code is wrong.** Read the actual return, including the
status argument — conventions are often followed in most handlers and broken in a few, and
reporting the whole project as wrong when creation endpoints already return the right code
discredits the finding. Report the specific divergences with their lines.

**Returning success for an operation that did not happen** is the member of this family worth
raising above LOW, since it is a correctness bug: the caller believes a write occurred.

**Not this:** deliberate variation between a collection and a single resource. A documented
contract that is unusual but consistent.

**Fix** → T-17.
