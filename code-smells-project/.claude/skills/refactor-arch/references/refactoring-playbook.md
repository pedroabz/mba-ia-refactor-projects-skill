# Refactoring Playbook — index

Most confirmed findings map to a transformation below; each transformation has a worked
before/after in its family file under `playbook/`. Load only the families that appear in
the audit.

Read `architecture-guidelines.md` first — it defines the target this playbook moves toward.

**These 24 are examples, not an enumeration**, for the same reason the catalogue is not one:
a finding the catalogue did not anticipate will not have a transformation waiting for it
either. For an uncatalogued finding (`SEC-X`, `DAT-X`, …), take the closest transformation in
the relevant family file as a model — the shape of a fix transfers even when the specifics do
not — and keep its before/after discipline: state what the code does now, what it should do
instead, and how you verified the change. The ordering rules and the baseline replay below
apply unchanged, and they matter more for an improvised fix than for a rehearsed one.

## Transformation index

| ID | Transformation | Fixes | Code example |
|---|---|---|---|
| T-01 | Extract configuration and secrets | SEC-01, SEC-06, LAY-06 | `playbook/security.md` |
| T-02 | Parameterize queries | SEC-03 | `playbook/security.md` |
| T-03 | Replace broken password storage | SEC-04 | `playbook/security.md` |
| T-04 | Remove sensitive fields from serialization | SEC-02 | `playbook/security.md` |
| T-05 | Add an access-control guard | SEC-05 | `playbook/security.md` |
| T-06 | Split a god file into MVC layers | LAY-01, LAY-05 | `playbook/layering.md` |
| T-07 | Extract a controller from a route | LAY-02 | `playbook/layering.md` |
| T-08 | Move domain rules to their owner | LAY-03 | `playbook/layering.md` |
| T-09 | Inject dependencies, remove global state | LAY-04 | `playbook/layering.md` |
| T-10 | Wrap a multi-write operation in a transaction | DAT-01, DAT-02 | `playbook/data-access.md` |
| T-11 | Make deletes preserve integrity | DAT-03 | `playbook/data-access.md` |
| T-12 | Collapse an N+1 into one query | DAT-04 | `playbook/data-access.md` |
| T-13 | Bound a result set | DAT-05, DAT-06 | `playbook/data-access.md` |
| T-14 | Centralize error handling | API-02 | `playbook/api-contract.md` |
| T-15 | Validate at the boundary | API-03 | `playbook/api-contract.md` |
| T-16 | Add the middleware chain | API-04 | `playbook/api-contract.md` |
| T-17 | Normalize the response contract | API-05 | `playbook/api-contract.md` |
| T-18 | Replace hand-rolled async coordination | API-01 | `playbook/api-contract.md` |
| T-19 | Collapse duplicated rules to one owner | QUA-01 | `playbook/code-quality.md` |
| T-20 | Name the constants | QUA-03 | `playbook/code-quality.md` |
| T-21 | Delete dead code | QUA-02 | `playbook/code-quality.md` |
| T-22 | Rename for intent | QUA-04 | `playbook/code-quality.md` |
| T-23 | Replace ad-hoc printing with logging | QUA-05 | `playbook/code-quality.md` |
| T-24 | Modernize a deprecated API | DEP-01 | `playbook/code-quality.md` |
| T-25 | Make a simulated decision fail closed | SEC-07 | `playbook/security.md` |

## What counts as closed

A finding is closed when the consequence named in its own **Impact** line can no longer
happen. Not when a transformation ran, not when the code moved, not when the structure
improved — when the stated harm is gone. This is the single most important check in the
phase, because a finding can be processed and still be live.

**Every CRITICAL and HIGH finding must be closed in this phase.** For those two severities,
"applied the structural part" is not a result and the Deferred section is not available: a
report that classifies something as a forged authorization or an injection point, and then
ships it, has described the vulnerability rather than fixed it — and documented it well
enough for someone else to use. Deferral belongs to MEDIUM and LOW, and to decisions that are
genuinely the operator's (see "Changes that are the operator's call" below).

Three traps produce a finding that looks closed and is not:

- **A fix closes its own finding and no other.** Each transformation does one job, completely.
  Moving a rule to its proper layer fixes the layering finding — fully, that work is done. It
  does not touch whether the rule is correct, because changing behaviour is not what it does.
  So the defect that remains is a *different* finding, and it is still open.

  Where this goes wrong is one step earlier, in the audit: if the two defects were written up
  as a single finding, closing one retires both on paper. Before you start a location, check
  that every independent defect there has its own id. If the audit merged them, split it now
  and carry both forward — "One defect, one finding" in `anti-patterns.md` has the test.
- **A guard on one environment is not a fix.** Refusing to run in production, or behind a
  flag that is off in CI, leaves the defect reachable everywhere else — including every
  developer machine and usually staging. Read the configuration **defaults**: a driver, mode
  or adapter selected whenever a variable is unset is on by default, and a default is what
  ships.
- **Documenting a defect is not fixing it.** A thorough comment explaining why something is
  dangerous is valuable and changes no behaviour. A `## Known limitations` entry in the
  README is the right place for a real residual gap, and the wrong place for a CRITICAL or
  HIGH finding.

When the real fix is genuinely outside reach — no provider to integrate with, no credentials,
no sandbox — the finding is still closed, by **failing closed**: the capability that cannot
be verified is denied rather than granted. A placeholder that refuses is an honest gap; a
placeholder that grants is the original vulnerability with better formatting. T-25 is the
general shape of that move.

### Changes that are the operator's call

Some recommendations should *not* be applied unilaterally, and the distinction is about who
bears the consequence rather than about difficulty:

- Raising a validation threshold that would reject credentials or data the system currently
  accepts.
- Renaming a public request or response field, which breaks existing clients.
- Removing an endpoint that something outside the repository may depend on.

Report these as *recommended, not applied*, with the reason and the exact change proposed.
That is a decision deferred to a human, which is legitimate at any severity. It is not the
same as leaving a vulnerability in place because fixing it was hard — and the test that
separates them is simple: if applying the fix only ever removes a capability that should not
have existed, nobody needs to approve it.

## Capture the contract before changing anything

"All endpoints respond correctly" is only checkable against a record of how they responded
before. Without a baseline it is an assertion, and an assertion is exactly what the
validation step is supposed to replace.

1. Enumerate the endpoints from the route registrations found while profiling. Where the project
   ships request examples (an `.http` file, a collection, a README), use those too — they
   carry realistic payloads.
2. Start the application as the project documents it.
3. Call every endpoint, including the error paths that are cheap to trigger (missing
   resource, invalid body). Record method, path, status code and response body.
4. Save it as `.refactor-arch/baseline.json` (or equivalent) in the project directory.

Two things to watch. An in-memory database loses state on restart, so the whole baseline
must be captured in one run of the server. And write endpoints change the data the later
reads return — either order the calls so reads come first, or record the data state
alongside the responses.

## Order of work

Sequence matters more than speed here. The goal is an application that boots after every
step, because a refactor that only compiles at the end gives you nothing to bisect when it
breaks.

1. **Config first** (T-01). It has no dependencies, it unblocks removing secrets from every
   other file, and it is the cheapest possible proof that the structure is changing.
2. **Create the structure, move code without rewriting it.** Pure relocation: routes out,
   then controllers, then models. Fix imports, boot the app, confirm it still answers. Do not
   combine a move with a logic change — when something breaks you want to know which of the
   two did it.
3. **Then layering fixes** (T-06 to T-09). Rules move to their owners now that the owners exist.
4. **Then correctness and security** (T-02 to T-05, T-10 to T-13, T-18). These change
   behaviour, which is why they come after the structure is stable and verifiable.
5. **Then cross-cutting** (T-14 to T-17). Error handling and validation centralize naturally
   once controllers exist.
6. **Quality last** (T-19 to T-24). Cheap, low risk, and genuinely easier once the code sits
   in its final location.

Boot the app after each group. Replay the baseline at least after step 2 and at the end.

## Never translate the application

The transformations below are written with English examples because this file is in English.
That is a property of the documentation, not an instruction about the code. Whatever language
the project speaks, it keeps speaking it:

- **Messages and copy** — error text, validation messages, notification bodies. A refactor
  moves a message to a different layer; it does not rewrite the message.
- **Response and request keys** — `dados`, `sucesso`, `erro`, `usr`, `c_id`. These are the
  contract every client depends on. Centralizing error handling does not mean renaming `erro`
  to `error`.
- **Enum and status values** — `pendente`, `aprovado`, `cancelado`. These are persisted, so
  renaming them silently invalidates every existing row.
- **Identifiers** — functions, modules, tables, columns, routes. New files you create may use
  the project's conventions, but existing names are not translated on the way past.
- **Comments and logs** inside the project.

A translated message is a behaviour change, and a translated key or status value is a
breaking change. Both will show up in the baseline replay as regressions, which is the right
outcome: they are regressions. If a project genuinely needs localizing, that is a separate
task with its own approval.

## Deliberate behaviour changes

Some fixes must change observable behaviour — that is the point of them. A secret removed
from a health endpoint changes that endpoint's response. Password storage switched to a
real hash invalidates existing stored passwords. An unauthenticated admin route gaining a
guard starts returning 401.

These are not baseline regressions, but they must be declared rather than discovered. For
each one, record what changed and why in the completion summary, and keep the shape of the
response intact where the fix does not require breaking it. Everything else is expected to
match the baseline exactly.

Where a fix would change a contract the challenge requires to keep working, prefer the
version that preserves the endpoint: add the guard but keep the route, strip the sensitive
field but keep the payload shape.

## Validation and the completion report

Replay the baseline against the refactored application and compare. Then report honestly, in
English, following the language rule in `report-template.md` — identifiers, paths and
anything in backticks stay in the source's own words.

```
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
<the actual tree>

## Transformations Applied
<T-id — what changed, file(s) touched>

## Findings
<one line per finding from the audit:>
<  <ID> <SEVERITY> — closed | recommended, not applied | deferred — <how the Impact can no
   longer happen, or who has to decide>

## Validation
  <✓|✗> Application boots without errors
  <✓|✗> Endpoints replayed: <n>/<n> match the baseline
  <✓|✗> Every CRITICAL and HIGH finding closed: <n>/<n>
  <list any intentional contract change, with its reason>
================================
```

Three rules about this output.

Report what was actually verified — a checkmark next to "endpoints respond correctly" that
nobody replayed is worse than no checkmark, because it converts an unknown into a false
claim. And never print a fixed string like "zero anti-patterns remaining".

**Account for every finding by id, including the closed ones.** The per-finding list is what
makes a partial fix visible: a finding whose structural half was applied and whose behaviour
is unchanged has to appear as something other than closed, and writing that line is usually
the moment the gap becomes obvious. A summary that reports only totals and transformations
hides exactly this case.

**A CRITICAL or HIGH that is not closed fails the phase.** Say so plainly at the top of the
summary rather than leaving it to be inferred from a list — and go back and close it. The
only exception is a change that is genuinely the operator's call, which is reported as
*recommended, not applied* with the decision stated.

## When validation fails

A failed boot or a diverging endpoint is information, not a dead end:

1. Stop. Do not pile another transformation on top of a broken state.
2. Identify the last group applied — this is why the order above keeps the app bootable.
3. Fix forward if the cause is obvious (a missed import, a renamed symbol). Otherwise revert
   that group and report it as deferred.
4. Re-run the baseline before continuing.

Reporting a deferred transformation with the reason is a better outcome than a broken
application with a full checklist. That trade applies to MEDIUM and LOW work: if a CRITICAL
or HIGH fix will not go in cleanly, the answer is a different approach to the same finding —
narrower, or failing closed — not a note explaining why the vulnerability is still there.
