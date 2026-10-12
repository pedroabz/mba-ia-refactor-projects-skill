# Code quality — detection depth

Confirmation steps for the `QUA` family. Read before writing any `QUA` finding.

These are mostly LOW, and the challenge's own definition puts readability, naming and magic
numbers there. Two cautions in opposite directions: do not inflate them to pad a report, and
do not dismiss them — a report with no LOW findings reads as a shallow sweep, and QUA-01 in
particular is frequently the finding with the highest practical cost in the whole audit.

---

## QUA-01 — Rule duplicated, single source of truth violated · MEDIUM

Violates: DRY, applied to rules rather than to characters.

**Confirm by** finding the same validation, calculation or predicate implemented in more than
one place, then checking whether the copies agree. Two levels:

- **Duplicated and consistent** — the rule is correct everywhere but has N owners. Changing
  it means finding all N. Report with every location.
- **Duplicated and drifted** — the copies disagree. This is a live bug, not a maintenance
  risk: name the divergence and what it lets through. A create path that validates a field
  and an update path that does not, where both write the same column, is the classic case.

**Look for the abandoned abstraction specifically.** A model method, helper or constant that
implements the rule and is never called anywhere, while the logic sits copy-pasted across
handlers, is the strongest form of this finding — the right answer is already written and
ignored. Confirm by grepping each exported name for call sites; zero means dead.

**Count the copies and list them all.** "Six reimplementations of one rule across three
files, while the model method that implements it is never called" is specific enough that
nobody argues. Report it once with the full list, not six times.

**Raise toward HIGH** when the duplicated rule is a domain rule and the copies have drifted,
since the system now behaves inconsistently depending on which endpoint is used.

**Not this:** two similar-looking expressions encoding genuinely different rules. Boilerplate
the framework requires. A deliberate denormalization with a comment explaining it.

**Fix** → T-19.

---

## QUA-02 — Dead code and unused declarations · LOW

Violates: lack of surprise — code that exists implies it runs.

**Confirm by** grepping for call sites or references. Shapes:

- Imported names never referenced in the file.
- Functions, methods or constants defined and never called anywhere in the project.
- Declared dependencies never imported — worth noting what they were for, since a declared
  but unused validation library is evidence for API-03 and an unused dotenv library is
  evidence for LAY-06.
- Columns or fields written and never read, or declared and never written. A soft-delete flag
  that exists while deletes are physical is a good example, and belongs with DAT-03.
- Parameters accepted and ignored.

**Group by file and report once.** A project-wide pattern of unused imports is one finding
listing the files, not one per import.

**Entire dead modules deserve separate emphasis.** A whole helpers module where every
function and constant is unreferenced is not the same finding as a stray import — it means
the logic lives duplicated elsewhere, which is QUA-01 and the more important of the two.
Report both, with the duplication as the primary.

**Not this:** a public API exported for external consumers. Code referenced only by tests, or
dynamically by name. A framework hook invoked by convention rather than by call.

**Fix** → T-21.

---

## QUA-03 — Magic numbers and inline literals · LOW

Violates: intent should be nameable. Named in the challenge's LOW definition.

**Confirm by** finding a literal whose meaning is not derivable from its context: a
threshold, rate, limit, timeout or boundary appearing bare in an expression. The test is
whether a reader can say what the number means without tracing the surrounding logic.

**Repeated literals are the stronger case.** The same string or number for one concept in
several places is a magic number *and* a single-source-of-truth problem — they will diverge.
A version string or file path duplicated across two modules is the common instance.

**Enum-like lists written inline** at each use site belong here too, and usually overlap
QUA-01: the list of valid statuses repeated in five places is both.

**Not this:** `0`, `1`, `-1` in their conventional roles. An index or increment. A number
immediately adjacent to a name that explains it. A value whose meaning the function name
already states.

**Fix** → T-20.

---

## QUA-04 — Uninformative naming · LOW

Violates: readability. Named in the challenge's LOW definition.

**Confirm by** reading the name and asking what it tells a reader who has not read the body.
Findings:

- Single-letter or abbreviated names for non-trivial values, especially in a public API
  contract where the caller has to guess.
- Sequentially numbered names (`cursor2`, `cursor3`, `data2`) — these are a reliable sign the
  block grew past the point where it should have been extracted, which is the more useful
  observation.
- Names shadowing language builtins.
- A name stating the mechanism rather than the intent.
- A function whose name lists two responsibilities joined by "and", which is also a design
  finding.

**Say what the reader has to do because of it.** "Three cursors must be traced to know which
query feeds which part of the response" is a cost; "poor naming" is a judgement.

**Deep nesting and long conditional chains belong here**, reported as the illegibility finding
in their own right. Where a bug hides in that nesting, the bug is a separate higher-severity
finding (often API-01) — both are real, and collapsing them into one loses whichever is
reported second.

**Not this:** conventional short names in tight scopes (`i`, `k`, `v`, a lambda parameter).
Domain abbreviations the project uses consistently. Framework-mandated names.

**Fix** → T-22 for naming; T-07 or T-06 where the real answer is extraction.

---

## QUA-05 — Ad-hoc logging · LOW

Violates: observability as a first-class concern.

**Confirm by** checking how the application reports what it does: direct printing to stdout
with no level, no timestamp and no structure, or no logging at all on paths that matter.

**Note what it prevents**, which is more concrete than style: no way to raise or lower
verbosity per environment, no way to filter by severity, nothing machine-parseable, and in
many runtimes the output is lost entirely in production.

**A function that both logs and does something else** is a design finding as much as a
logging one — the name usually admits it. Report the conflated responsibility.

**Where a log line prints a secret or personal data, that is SEC-02 at CRITICAL**, not this.
Keep them apart.

**Not this:** deliberate console output in a CLI tool, where stdout *is* the interface. A
startup banner. Printing in a seed or migration script.

**Fix** → T-23.
