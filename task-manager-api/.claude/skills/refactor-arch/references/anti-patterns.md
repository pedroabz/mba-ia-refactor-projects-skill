# Anti-Pattern Catalog — triage index

The index: 29 anti-patterns, each with the fundamental it violates and a detection signal
concrete enough to act on. Meant to be read in full at the start of the audit.

**These 29 are examples, not an enumeration.** They exist to show what a well-formed finding
looks like and which fundamentals to measure against — not to bound what counts as a finding.
See "When nothing matches" below, which is the normal case on any codebase you have not seen
before, not an edge case.

Depth lives in `deep/`, one file per family, loaded only when that family actually shows up:

| Prefix | Family | Deep file |
|---|---|---|
| `SEC` | Secrets, injection, access control, crypto, data exposure | `deep/security.md` |
| `LAY` | Layer boundaries, responsibility placement, coupling | `deep/layering.md` |
| `DAT` | Transactions, integrity, query efficiency | `deep/data-access.md` |
| `API` | Request lifecycle, validation, errors, response contract | `deep/api-contract.md` |
| `QUA` | Duplication, dead code, naming, literals | `deep/code-quality.md` |
| `DEP` | Deprecated and removed APIs | `deep/deprecated-apis.md` |

## How to use this

1. Read the index below alongside the project profile.
2. Sweep the source for the detection signals. Signals are written as *what to look for*,
   never as a verdict — finding the signal starts an investigation, it does not close one.
3. For every candidate, open the matching `deep/` file before writing the finding. It holds
   the confirmation steps, the severity adjustment rules, and the false-positive guards.
4. Record file path and exact line numbers for each confirmed finding. A finding without a
   location cannot be acted on and will not survive review.
5. Drop anything you could not confirm by reading the code. An unverified finding costs more
   credibility than a missed one.

## When nothing matches

A catalogue of 29 entries cannot enumerate the ways code goes wrong. Novel stacks bring
novel failures, and every real codebase contains at least one problem written by someone who
had not read this file. The index is a prompt for investigation, not a checklist to tick, and
a finding that matches no row is a normal result.

So the entries are examples to reason **from**, not a filter to reason **through**. When you
find something real that no row anticipates:

1. **Name the fundamental it violates** — from the table above, or from outside it if the
   violation is of some other well-established principle. This is the part that makes the
   finding legible to a reviewer and distinguishes it from a matter of taste.
2. **Classify it on the severity scale** by what it actually causes, using the same
   reachability and blast-radius adjustments as everything else.
3. **Borrow the confirmation discipline of the nearest family.** The `deep/` files teach how
   to confirm a class of problem and which false positives to expect; that method transfers
   even when the specific entry does not.
4. **Report it with the same schema** — location, description, impact, recommendation. Label
   it with the nearest family prefix and `-X` (`DAT-X`, `SEC-X`) so a reader can see it is
   uncatalogued rather than mistyped.
5. **Derive the fix** from the closest transformation in the playbook, and follow the same
   ordering rules when applying it.

Two failure modes to avoid, in opposite directions:

- **Do not force a poor fit onto an existing id.** A problem filed as DAT-04 because it was
  vaguely query-shaped inherits the wrong severity, the wrong confirmation steps and the wrong
  transformation. An honest `DAT-X` is worth more than a confident mislabel.
- **Do not lower the evidence bar for uncatalogued findings.** "This feels wrong" is not a
  finding. Same requirement as every other row: a location, a mechanism, and a consequence
  you can point at in the code.

If a particular novel finding turns out to recur across projects, it belongs in the index as
a proper entry — one row here and a section in the relevant `deep/` file. That is how the
catalogue is meant to grow.

## One defect, one finding

The most expensive mistake in an audit is not missing a problem — it is reporting two
problems as one. The merged finding gets a single severity, a single recommendation and a
single line in the summary, so when the fix closes the half the finding was named after, the
other half disappears from the accounting. Nobody dropped it; it was never being tracked.

One piece of code often holds several independent defects. A long, tangled function can be
*both* unreadable *and* wrong. A route that runs arbitrary SQL is *both* unauthenticated
*and* arbitrary-execution-by-design. A query that selects every column *both* over-fetches
*and* leaks a password into the response.

**The test for whether it is one finding or two: would fixing one of them fix the other?**

- *No* → two findings. Two ids, two severities, two recommendations, even when they point at
  the same line. Say in each that the other exists, so a reader sees both, and never let one
  absorb the other.
- *Yes* → one finding, with one consequence as the mechanism and the other as the effect.

Two common pairs, with the right outcome for each:

| Code | Defects | Verdict |
|---|---|---|
| Deeply nested handler with a broken completion counter | unreadable (LOW/MEDIUM) · request hangs (HIGH) | **Two.** Making it readable does not fix the hang; fixing the hang does not make it readable |
| Rule deciding payment from a card prefix, inline in a route | rule in the wrong layer (HIGH) · the rule is a forged approval (CRITICAL) | **Two.** Moving it to a service fixes the layer completely and leaves the forgery running |

Severity follows each defect on its own. Resist both directions of collapsing: do not raise a
readability finding to CRITICAL because a bug lives nearby, and do not let a structural
finding swallow a security one because they share an address.

**This is not about reporting the same defect twice.** One defect appearing at twenty call
sites is one finding listing twenty locations — see the reporting rules in
`report-template.md`. The distinction is defects, not lines.

## Severity scale

This is the canonical scale for the whole skill. `report-template.md` formats it; this file
defines it.

- **CRITICAL** — severe architectural or security flaws that prevent correct functioning,
  expose sensitive data (hardcoded credentials, SQL injection), or completely violate
  separation of concerns (a God Class holding database access, business logic and routing in
  one file).
- **HIGH** — major violations of MVC or SOLID that significantly hinder maintainability and
  testability: business logic embedded in controllers, tight coupling without dependency
  injection, widespread mutable global state.
- **MEDIUM** — coding standards, code duplication, or moderate performance bottlenecks:
  N+1 queries, improper middleware usage, missing validation on routes.
- **LOW** — readability, poor naming, magic numbers scattered through the code.

Two adjustment rules, applied after the base severity:

- **Reachability raises it.** The same flaw is worse on an unauthenticated route handling
  untrusted input than in a seed script that runs once at setup.
- **Blast radius raises it.** A pattern repeated across every module is worse than one
  instance, and should be reported once with the full line list rather than twenty times.

Do not inflate. A report where everything is CRITICAL carries no information, and a
reviewer who finds one inflated severity discounts the rest.

## Index

### Security — `deep/security.md`

| ID | Anti-pattern | Severity | Violates | Detection signal |
|---|---|---|---|---|
| SEC-01 | Hardcoded secrets and credentials | CRITICAL | Config in the environment | String literal assigned to a name containing `key`, `secret`, `token`, `password`, `passwd`, `pwd`, `credential`, `dsn`; connection strings with embedded credentials; any `sk_`/`pk_`/`AKIA` prefix |
| SEC-02 | Sensitive data exposed through response or log | CRITICAL | Least privilege; OWASP A09 | A serializer or response dict including a password, hash, token, card number or secret; `print`/`console.log`/logger call interpolating a credential, card, or full request body |
| SEC-03 | Injection through string-assembled query or command | CRITICAL | OWASP A03 — data/code confusion | Query built with `+`, `%`, `.format()`, f-string or template literal where any fragment derives from a request; also `eval`, `exec`, shell invocation with interpolated input |
| SEC-04 | Broken or absent password storage | CRITICAL | OWASP A02 | Password persisted as received; MD5/SHA-1/SHA-256 used directly on a password; hand-rolled hashing; no per-user salt; comparison with `==` |
| SEC-05 | Missing access control on sensitive or destructive operation | CRITICAL | OWASP A01 — deny by default | A route that deletes, resets, mass-reads personal data or executes arbitrary input with no auth check in the handler and no guard middleware; a route named `admin` with no role check; a token that is never verified anywhere |
| SEC-06 | Insecure runtime configuration | HIGH | OWASP A05 | Debug mode enabled in the shipped entry point; permissive CORS applied globally; bind to all interfaces combined with debug; stack traces returned to clients |
| SEC-07 | Security-critical decision simulated, and defaulting to permit | CRITICAL | Fail closed; deny by default | A payment approval, authentication, entitlement, quota, signature or fraud check decided by local inspection instead of by the authority that owns it: a card prefix or length, a hardcoded user list, a `TODO`, a flag named `fake`/`mock`/`stub`/`dev`, a function that returns `true` unconditionally. The finding is the **permissive default**, not the stub's existence |

### Layering — `deep/layering.md`

| ID | Anti-pattern | Severity | Violates | Detection signal |
|---|---|---|---|---|
| LAY-01 | God class / god file | CRITICAL | SRP; separation of concerns | One file or class holding two or more of: schema/DDL, queries, business rules, routing, serialization — especially across several domain entities. Size alone is a hint, mixed responsibilities are the finding |
| LAY-02 | Business logic in the controller or route | HIGH | MVC boundaries | Handler body containing pricing, scoring, state-machine or eligibility rules; arithmetic on domain values; conditional chains on domain state; side effects such as email/SMS/push fired inline |
| LAY-03 | Business logic or side effects in the model | HIGH | SRP | Model or data-access function computing discounts, aggregates or policy decisions; a model performing I/O beyond persistence; persistence code assembling response DTOs |
| LAY-04 | Global mutable state / dependency built in place | HIGH | DIP; low coupling | Module-level mutable variable (connection, cache, counter) mutated at runtime; a class constructing its own connection or client instead of receiving it; thread-safety flags set to bypass checks; a cache that is never invalidated |
| LAY-05 | Layer bypass | HIGH | Dependency direction | Entry point or route importing a driver and running queries directly; model importing a route or framework request object; serialization logic in the data layer |
| LAY-06 | Configuration embedded in code, no config module | MEDIUM | Config in the environment | Ports, hosts, paths, feature flags, timeouts, thresholds as literals inside application files; no config module and no environment reads; `.env` tooling declared as a dependency but never used |

### Data access — `deep/data-access.md`

| ID | Anti-pattern | Severity | Violates | Detection signal |
|---|---|---|---|---|
| DAT-01 | Multi-write operation without an atomic boundary | CRITICAL | ACID — atomic unit of work | One business operation issuing several writes across tables with no explicit transaction wrapping them; writes interleaved with validation that can return early between them |
| DAT-02 | Failure leaves partial state | HIGH | Fail fast, no partial commit | Error path that returns without rollback; long-lived shared connection where an abandoned transaction can be committed by an unrelated later request; no rollback in the error branch of a multi-write flow |
| DAT-03 | Orphaned records on delete | HIGH | Referential integrity | Delete of a parent with no cascade, no `ON DELETE` clause, and no manual cleanup of children; schema declaring relationships without foreign keys; integrity enforcement left to a comment |
| DAT-04 | N+1 queries | MEDIUM | Bounded work per request | A query inside a loop over the result of a previous query; lazy-loaded relation accessed per row; per-row `count`/`get` to enrich a list |
| DAT-05 | Unbounded result set | MEDIUM | Bounded work per request | Fetch-all with no limit, offset or cursor on a collection that grows with usage; search endpoint without pagination |
| DAT-06 | Over-fetching | LOW | Least work, loose coupling to schema | `SELECT *` or full-entity load where a few columns are used; serializer emitting every column by default |

### API contract — `deep/api-contract.md`

| ID | Anti-pattern | Severity | Violates | Detection signal |
|---|---|---|---|---|
| API-01 | Broken request lifecycle | HIGH | Fail fast; one response per request | Hand-rolled coordination of concurrent work (manual counters, flags) deciding when to respond; an error branch that skips the decrement or the send; response sent inside a loop; nesting deep enough that an early return cannot reach the responder |
| API-02 | Errors swallowed or leaked verbatim | MEDIUM | Explicit errors | Bare `except:` / `catch {}` with no rethrow; an error parameter declared and never inspected; raw exception text or stack trace returned to the client; no centralized error handler |
| API-03 | Input not validated at the boundary | MEDIUM | Validate at the edge | Handler reading request fields with no type, range, format or enum check; presence-only checks that reject legitimate zero or empty values; optional credentials silently defaulted |
| API-04 | Missing middleware chain | MEDIUM | Cross-cutting concerns belong in one place | No request-size limit, no rate limit on expensive or payment routes, no auth middleware, no centralized error handler; cross-cutting work copy-pasted into each handler instead |
| API-05 | Inconsistent or uninformative response contract | LOW | Predictable interface | Same endpoint returning plain text on error and structured data on success; envelope present on some responses and absent on others; success status returned for a missing resource or a failed write |

### Code quality — `deep/code-quality.md`

| ID | Anti-pattern | Severity | Violates | Detection signal |
|---|---|---|---|---|
| QUA-01 | Rule duplicated, single source of truth violated | MEDIUM | DRY, applied to rules | The same validation, calculation or predicate implemented in more than one place — especially where one copy has drifted; an existing helper or model method that implements the rule and is never called |
| QUA-02 | Dead code and unused declarations | LOW | Lack of surprise | Imported names never referenced; functions and constants defined and never called anywhere; declared dependencies never imported; columns or fields written and never read |
| QUA-03 | Magic numbers and inline literals | LOW | Intent should be nameable | Bare numeric thresholds, rates, limits in expressions; repeated string literals for the same concept; enum-like lists written inline at each use site |
| QUA-04 | Uninformative naming | LOW | Readability | Single-letter or sequentially numbered names (`cursor2`, `u`, `e`) for non-trivial values; names shadowing builtins; abbreviations in a public API contract; a name that states the mechanism instead of the intent |
| QUA-05 | Ad-hoc logging | LOW | Observability | `print`/`console.log` as the logging mechanism; no level, no timestamp, no structure; a function that both logs and does something else |

### Deprecated APIs — `deep/deprecated-apis.md`

| ID | Anti-pattern | Severity | Violates | Detection signal |
|---|---|---|---|---|
| DEP-01 | Deprecated or removed API in use | MEDIUM | Supported surface area | A call that the pinned runtime or library version marks deprecated, legacy, or removed. Check the version in the manifest first — the same call can be fine, deprecated, or gone depending on it. Raise to HIGH when the API is already removed in the pinned version, since the code is broken rather than dated |

Deprecation is version-relative, so this is the one family where the answer may legitimately
be "none found". Report that explicitly; it is a verified result, not a gap.

## Global false-positive guards

Each `deep/` file carries guards for its own entries. These four cause the most damage
because they turn a well-organized project into a page of false CRITICALs:

- **Parameterization through an ORM is safe.** `Model.col.like(f'%{q}%')`,
  `query.filter(Model.id == user_input)` and `execute(sql, (a, b))` pass values as bound
  parameters. The f-string builds the *pattern*, not the SQL. Injection requires the
  untrusted value to become part of the statement text.
- **An ORM is a data layer.** Declarative model classes are not "missing abstraction".
  Judge where the *rules* live, not whether hand-written SQL is present.
- **A framework default is not a hardcoded secret.** A development placeholder in a sample
  config differs from a live key in a shipped module. Judge by what the value is and whether
  it ships.
- **Modern forms that resemble deprecated ones.** `Buffer.from()` is correct; `new Buffer()`
  is deprecated. `datetime.now(timezone.utc)` is correct; `datetime.utcnow()` is deprecated.
  Match the exact call, not the surrounding concept.

One more, which is about scope rather than correctness: absence of automated tests is a real
weakness but not an anti-pattern in the code — there is no line to point at and no
transformation in the playbook that fixes it. Mention it as an observation in the report's
notes if relevant; keep it out of the findings list.
