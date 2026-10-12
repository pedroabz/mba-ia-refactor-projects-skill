# Data access — detection depth

Confirmation steps for the `DAT` family. Read before writing any `DAT` finding.

Transaction and integrity findings need the control flow traced, not just the queries read —
the bug is usually in what happens between the writes, or on the path that skips them.

---

## DAT-01 — Multi-write operation without an atomic boundary · CRITICAL

Violates: ACID — a business operation commits once or not at all.

**Confirm by** identifying one business operation that issues several writes, then checking
whether anything wraps them. Look for an explicit transaction (`BEGIN`, `with
session.begin()`, `db.transaction()`, a unit-of-work object) around the whole sequence.

**Know your driver's default before reporting.** Some drivers open an implicit transaction
for data-modifying statements, so a single commit at the end of several writes is already
atomic. Others autocommit each statement, in which case the same code is broken. Check which
applies to the pinned driver, and do not report a transaction finding that the driver already
handles — this is the most common false positive in the family.

**The real finding is usually the early return.** Validation interleaved with writes, where a
failed check returns between two of them, leaves the operation half-applied regardless of the
driver's defaults. Trace every exit point between the first and last write.

**Name the resulting state.** "Enrollment recorded with no payment row" is actionable;
"possible inconsistency" is not.

**Not this:** several independent operations that are genuinely independent. A single write.
Writes already inside an explicit transaction or an atomic framework helper.

**Fix** → T-10.

---

## DAT-02 — Failure leaves partial state · HIGH

Violates: fail fast; no partial commit.

**Confirm by** reading the error branches of a multi-write flow. The finding is a path that
returns or responds without rolling back.

**The long-lived-connection variant is worth the extra reading**, because it turns a local
bug into a cross-request one: when a module-level connection is shared, an abandoned
transaction stays open on it, and the next successful commit from any other request commits
the orphaned writes too. Confirm it by checking that the connection is global (LAY-04) and
that the error path has no rollback. Report the mechanism, not just "missing rollback" —
it is the difference between a reviewer believing it and not.

**Check the handler as well as the data layer.** A rollback in neither is this finding; a
rollback in the controller only is acceptable if it covers every path.

**Not this:** a framework that rolls back automatically at the end of a failed request. A
single-statement operation.

**Fix** → T-10.

---

## DAT-03 — Orphaned records on delete · HIGH

Violates: referential integrity.

**Confirm by** finding a delete of a parent row, then checking three places for cleanup:
an `ON DELETE` clause in the schema, a cascade declared on the ORM relationship, and manual
deletion of children in the same operation. None of the three is the finding.

**Check whether foreign keys exist at all.** A schema that declares `user_id` as a plain
integer with no constraint has no integrity to cascade — report the missing constraint
together with the delete, since the fix needs both. Note also that some databases require
foreign-key enforcement to be switched on per connection; a declared constraint that is never
enforced is the same finding.

**Name the rows left behind**, with the tables. If the code acknowledges the problem in a
comment or a response message, quote it — self-documented bugs are unusually clear evidence.

**Not this:** a soft delete that intentionally keeps children. A cascade that exists in the
schema even if not in the ORM. An intentional orphan kept for audit, if something says so.

**Fix** → T-11.

---

## DAT-04 — N+1 queries · MEDIUM

Violates: bounded work per request. Named in the challenge's MEDIUM definition.

**Confirm by** finding a query executed inside a loop over the results of a previous query.
Three shapes, all equally valid findings:

- Explicit: a `get`/`count`/`all` call inside a `for` or `forEach` over rows.
- Implicit: a lazy-loaded ORM relation accessed per row — no visible query, same cost.
- Nested: a loop inside a loop, each level adding queries. Worth reporting with the
  multiplication spelled out, because the cost is not obvious from reading it.

**Quantify it.** "1 + N queries, N = number of courses, plus 2 per enrollment" is concrete
and tells the reader whether it matters. Do that rather than asserting a performance problem.

**Not this:** a fixed number of queries that happens to be written near a loop. A loop over
an already-loaded collection with no query inside. Eager loading via `join`, `Include` or
`selectinload`.

**Fix** → T-12.

---

## DAT-05 — Unbounded result set · MEDIUM

Violates: bounded work per request.

**Confirm by** finding a fetch-all over a collection that grows with usage, with no limit,
offset or cursor. List, search and report endpoints are the usual sites.

**Distinguish growth classes.** A table of statuses or categories is bounded by design and
not a finding. A table of users, orders or tasks is not. Say which, so the reader can judge.

**Counting in application code** is a related variant: loading every row to count or
aggregate in a loop, where the database would do it in one statement. Report it here when the
cost is the volume rather than the query count.

**Not this:** a bounded lookup table. An export endpoint that is deliberately full-dump, if
documented. An aggregate performed by the database.

**Fix** → T-13.

---

## DAT-06 — Over-fetching · LOW

Violates: least work; loose coupling to the schema.

**Confirm by** comparing the columns selected against the columns used. `SELECT *` where two
fields are read is the clearest case; a serializer emitting every column by default is the
same problem one layer up.

**Give both reasons.** It wastes transfer, and it couples the caller to the full schema, so a
column added or renamed later changes responses that never asked for it. The second reason is
the one that survives the "it is a small table" objection.

**This overlaps SEC-02 when the extra columns are sensitive.** If `SELECT *` is what pulls a
password column into a response, the finding is SEC-02 at CRITICAL, with the over-fetching as
the mechanism — not two separate findings at LOW and CRITICAL.

**Not this:** a full-entity load where most fields are genuinely used. An ORM fetching an
entity it will persist back.

**Fix** → T-13.
