# Gap report — `SKILL.md` vs `instructions.md`

Step 3 of [PLAN.md](../PLAN.md). Compares the current draft at
`code-smells-project/.claude/skills/refactor-arch/SKILL.md` (152 lines) against the
requirements in [instructions.md](../instructions.md) and against the 16 reference files
delivered in step 1.

**No edits have been made.** Each gap below is a proposal to approve or reject individually.
`SKILL.md` stays Pedro's document: the goal is that every change is deliberate and
attributable, not that the file ends up looking like something Claude would have written. The
"smallest diff" line on each item exists so the cheapest option is always visible — several
gaps close by adding one line rather than by reorganizing a section.

Line references are to the current draft.

## Summary

| # | Gap | Severity | Size of fix |
|---|---|---|---|
| G1 | Report filename hardcoded to `audit-project-1.md` | **Blocking** | 1 line |
| G2 | Reference files named in prose, never located | **Blocking** | ~6 lines added, 14 deleted |
| G3 | `description` omits MVC, the 3-phase flow, and scope | Important | 3 lines |
| G4 | Phase 3 validation is a goal with no procedure | Important | 4 lines |
| G5 | "Zero anti-patterns remaining" printed unconditionally | Important | 5 lines |
| G6 | Knowledge inlined in `SKILL.md` now duplicated in references | Important | up to 90 lines deleted |
| G7 | No instruction to adapt to an already-layered project | Important | 1 line |
| G8 | Confirmation gate does not forbid modification before approval | Minor | 1 line |
| G9 | Truncated sentence | Minor | delete 1 line |
| G10 | Repetition flagged by the author's own TODO | Minor | delete 2 sentences |
| G11 | Phase 2 asks the report to restate Phase 1 content | Minor | wording |

Severity means distance from `instructions.md`, not code quality. **Blocking** = the skill
cannot satisfy a stated requirement or breaks when copied to projects 2 and 3.

---

## G1 — Report filename hardcoded · Blocking

**Required.** Reports go to `reports/audit-project-1.md`, `-2.md`, `-3.md` (instructions.md
lines 201, 217, 236, 333-336), and the same skill folder is copied into all three projects
(lines 208, 224).

**Current.** Line 43: *"The output of this phase will be a report called audit-project-1.md."*

**Why it blocks.** The filename is fixed and the location is unstated. Copied into
`ecommerce-api-legacy/` and `task-manager-api/` as instructions.md requires, every run writes
`audit-project-1.md` — so projects 2 and 3 overwrite project 1's report, and the deliverable
ends up with one file where three are required. This is the single clearest way the current
draft fails the brief.

**Proposed fix.** Delegate the path to the reference file, which already implements the
derivation rule agreed in PLAN.md decision 2 (scan `../reports/`, take the highest `N`,
write `N+1`).

```diff
-The output of this phase will be a report called audit-project-1.md. 
+Write the report to the path derived in `references/report-template.md`
+("Report file"), so the skill stays correct when copied into another project.
```

**Smallest diff.** The one line above.

---

## G2 — Reference files named in prose, never located · Blocking

**Required.** instructions.md lines 159-169 require reference files covering five knowledge
areas, and the skill must use them. Step 1 delivered 16 files.

**Current.** The phases refer to them by English name only — line 16 *"Using the Project
Analysis reference file"*, line 41 *"Using the Anti-Pattern Catalog as a reference"*, line 110
*"by using the reference files for Architecture Guidelines and Refactoring Playbook"*. No path
appears anywhere. Lines 139-152 are a `// TODOS` block listing the files still to be written.

**Why it blocks.** A name is not a location. With no path, the skill has nothing to read, and
the 16 files are dead weight — which also means the five mandatory knowledge areas are
unreachable in practice even though they exist on disk. The stale TODO block compounds it by
implying the files do not exist yet.

**Proposed fix.** One explicit read instruction per phase, plus deletion of the TODO block.
The `deep/` and `playbook/` families are deliberately *not* listed here — the two index files
point at their own families, which is what keeps `SKILL.md` stable when a family is added.

```diff
 PHASE 1 - Project Analysis:
-Using the Project Analysis reference file, your goal in this phase is to identify
+Read `references/project-analysis.md` before starting. Your goal in this phase is to identify
```

```diff
 Phase 2 - Audit Report:
-Using the Anti-Pattern Catalog as a reference, your goal is to create an audit report
+Read `references/anti-patterns.md` in full, then `references/report-template.md`
+for the output format. Open the matching `references/deep/<family>.md` before writing
+any finding. Your goal is to create an audit report
```

```diff
-You will do that by using the reference files for Architecture Guidelines and Refactoring Playbook.
+Read `references/architecture-guidelines.md` for the target, then
+`references/refactoring-playbook.md` for the transformation index; load the
+`references/playbook/<family>.md` files for the families the audit actually found.
```

```diff
-// TODOS: Add reference files for the skills with:
-1 - Project Analysis: Heuristics for detecting programming languages, frameworks, databases, and mapping the architecture.
-...
-5 - Refactoring Playbook: Concrete transformation patterns for each anti-pattern (including code examples).
```

**Smallest diff.** The three read instructions are the functional minimum; deleting the TODO
block is cosmetic but it is 14 lines of stale scaffolding in a file that is read on every
invocation.

---

## G3 — `description` omits MVC, the flow, and the scope boundary · Important

**Required.** Nothing in instructions.md specifies the description, and the skill is invoked
explicitly as `/refactor-arch` (line 189), so triggering is not at risk. But the description
is the only text always in context, and step 1 introduced a scope boundary that currently
lives in `project-analysis.md` — read *after* the skill has already started.

**Current.** Lines 3-4: *"Analyze the architecture of a codebase and provide recommendations
for refactoring… Identify code smells, architectural issues, and suggest best practices for
restructuring the code."*

**Why it matters.** Three things are wrong with it. It says the skill *recommends* when the
skill actually *performs* the refactor — under-promising what Phase 3 does. It omits MVC,
which is the entire target. And it does not state the scope boundary, so the skill cannot
decline a single-page frontend or a library before doing work it should not do.

**Proposed fix.**

```diff
-description: >
-  Analyze the architecture of a codebase and provide recommendations for refactoring to improve maintainability, scalability, and performance. Identify code smells, architectural issues, and suggest best practices for restructuring the code.
+description: >
+  Audit and refactor a server-side codebase to the MVC pattern in three confirmed phases:
+  profile the stack, produce a severity-classified architecture audit report, then
+  restructure into Models, Views/Routes and Controllers and verify the application still
+  works. Technology-agnostic. Use when asked to audit architecture, find anti-patterns or
+  code smells, or refactor a project to MVC. Targets APIs, fullstack apps and workers; for
+  a single-page frontend, CLI or library, report the analysis and stop.
```

**Smallest diff.** Append the scope sentence to the existing description and leave the rest.
That closes the real risk — doing damage to an out-of-scope project — without rewriting
Pedro's wording.

---

## G4 — Phase 3 validation is a goal with no procedure · Important

**Required.** instructions.md line 178: Phase 3 must validate the result (app boots +
endpoints responding); lines 197-200 and 270-271 repeat it; the acceptance table (line 424)
makes a working application mandatory in 3/3 projects.

**Current.** Lines 112-113: *"In the end of the phase you will need to be able to boot the app
without errors, tests all endpoints and make sure the respond."*

**Why it matters.** It states the outcome and no method: nothing says how to discover the
endpoints, nothing captures how they behaved before the refactor, nothing says what to do when
validation fails. Without a pre-refactor baseline, "endpoints still respond" can only be
asserted — which is how a silent contract change reaches the deliverable. This is the gap most
likely to cost the 3/3 criterion, especially on project 2, where the async rewrite can change
response ordering without anything looking broken.

**Proposed fix.**

```diff
+Before modifying any file, capture the endpoint contract as described in
+`references/refactoring-playbook.md` ("Capture the contract before changing anything").
+Apply transformations in the order given there, booting the app between groups.
+After the last change, replay the baseline and compare. If validation fails, follow
+"When validation fails" in the same file rather than continuing.
```

**Smallest diff.** The first two lines (capture, then replay) are the functional core.

---

## G5 — "Zero anti-patterns remaining" printed unconditionally · Important

**Current.** Line 136, inside the Phase 3 output template the skill is told to print:
`✓ Zero anti-patterns remaining`.

**Why it matters.** It is a fixed string in an output format, so the skill prints it whether or
not it is true — and it will rarely be true, since LOW findings are routinely and legitimately
deferred. A validation summary that claims something unverified is worse than one that omits
it, because it converts an unknown into a false claim in the artifact a reviewer reads. It also
contradicts `report-template.md` and `refactoring-playbook.md`, which both require stating what
was fixed versus deferred.

**Proposed fix.** Replace the fixed validation block with the completion format from the
playbook, which reports transformations applied, replay results, intentional contract changes,
and deferred findings.

```diff
 ## Validation
-  ✓ Application boots without errors
-  ✓ All endpoints respond correctly
-  ✓ Zero anti-patterns remaining
+  <✓|✗> Application boots without errors
+  <✓|✗> Endpoints replayed: <n>/<n> match the baseline
+  <any intentional contract change, with its reason>
+
+## Deferred
+<findings not fixed, and why>
```

**Smallest diff.** Delete line 136. The claim disappears and nothing replaces it, which is
already an improvement.

---

## G6 — Knowledge inlined in `SKILL.md`, now duplicated in references · Important

**Required.** instructions.md lines 159-169 split the work deliberately: `SKILL.md` is the
procedure, the reference files hold the knowledge. The closing tip at line 442 says it
outright — *"O SKILL.md é um prompt — ele instrui o agente sobre o que fazer, enquanto os
arquivos de referência fornecem o conhecimento de domínio."*

**Current.** Roughly 90 of 152 lines are knowledge that now also exists in the references:

| Lines | Content | Now lives in |
|---|---|---|
| 28-39 | Phase 1 example output (C# / ASP.NET) | `report-template.md` |
| 55-102 | Phase 2 example report (C# / healthcare) | `report-template.md` |
| 116-137 | Phase 3 example output | `refactoring-playbook.md` |
| 143-149 | Severity definitions | `anti-patterns.md` |

Line 53 is the author's own note on this: *"Example (move this to the reference file Report
Template:)"*.

**Why it matters.** Two copies of a format will drift, and when they disagree the skill has no
way to know which wins. It is also the cost paid on every invocation: all 152 lines load every
time, while the reference files load only when needed.

**Proposed fix — two options, Pedro's call.**

*Option A, full extraction.* Delete lines 28-39, 55-102, 116-137 and 143-149; each already has
a pointer from G2's read instructions. `SKILL.md` drops to roughly 60 lines of pure procedure.

*Option B, keep one example.* Delete lines 55-102 and 143-149 (the largest block and the
duplicated scale) and keep the short Phase 1 and Phase 3 examples inline. The file lands around
100 lines, and the C#/ASP.NET example stays visible as evidence of technology-agnostic intent —
which is worth something to a reviewer, since neither of the three target projects is C#.

I would take B. The 48-line healthcare report is the real weight and the clearest duplication;
the two small output banners cost little and make the file readable on its own.

Decision: Go with B

**Smallest diff.** Delete lines 55-102 only.

---

## G7 — No instruction to adapt to an already-layered project · Important

**Required.** instructions.md line 446: *"a Fase 3 de um projeto já parcialmente organizado não
vai ter as mesmas transformações de um monolito. Sua skill deve se adaptar ao contexto."* Line
239 adds that for project 3, necessary structural changes must be proposed *and* executed.

**Current.** Nothing. Phase 3 (lines 108-113) describes one refactoring path regardless of
starting point.

**Why it matters.** `task-manager-api` already has `models/`, `routes/` and `services/`. Without
this instruction the skill either re-does work that is already correct or relocates working code
for the sake of the tree shape — and that is the likeliest way to break the app and lose the
3/3 criterion. `architecture-guidelines.md` has the section ("Adapting to the starting point")
that handles all three starting points against the same MVC target; the skill just needs to be
told to use it.

**Proposed fix.**

```diff
+Match the work to the starting point using "Adapting to the starting point" in
+`references/architecture-guidelines.md`: the MVC target is the same for every project,
+but a partially layered codebase needs different transformations than a monolith —
+keep the layers that already work.
```

**Smallest diff.** The one line above.

---

## G8 — Confirmation gate does not forbid modification before approval · Minor

**Required.** instructions.md line 447: *"Pedir confirmação na Fase 2 é obrigatório — o humano
deve revisar o relatório antes de qualquer modificação."* Line 177 repeats it: Phase 2 must
pause before modifying any file.

**Current.** Line 51 lists *"The skill pauses and requests confirmation before proceeding to
Phase 3"* and line 106 says the user should review and confirm. Both describe the pause; neither
states the prohibition.

**Why it matters.** The requirement is not that a question is asked, it is that nothing is
touched before it is answered. As written, a skill that creates a directory or writes a config
file "to prepare" would satisfy the letter and break the intent.

**Proposed fix.**

```diff
-When the report is done the user should review it and confirm before moving to Phase 3.
+When the report is done the user should review it and confirm before moving to Phase 3.
+Until that confirmation, do not create, modify or delete any file in the project —
+the report is the only output of this phase. Treat anything other than an explicit yes as no.
```

---

## G9 — Truncated sentence · Minor

**Current.** Line 104: *"In this phase, following the conventions on"* — the sentence ends
mid-clause.

**Proposed fix.** Delete the line. Whatever it was going to say is covered by the
`report-template.md` pointer from G2.

---

## G10 — Repetition flagged by the author's own TODO · Minor

**Current.** Line 9 is `// TODO: be less repetitive`, and it is correct: line 7 ("You are a
software architect and code refactoring expert… identify code smells, architectural issues, and
suggest best practices"), line 10 ("You will identify the language, framework and project
characteristics, write a report about it and then refactor…") and line 11 ("This Skill is
designed to be agnostic to technology, being able to identify the language, framework, and
architecture…") state the same three things.

**Proposed fix.** Keep line 7 as the role statement and the MVC sentence from line 10; delete
the overlap in lines 10-11 and the TODO marker. Four lines become two.

---

## G11 — Phase 2 asks the report to restate Phase 1 content · Minor

**Current.** Line 44: *"As well as the content from phase 1, it has to contain all the analysis
of phase 2."*

**Why it is awkward.** `report-template.md`'s audit format opens with `Project / Stack / Files`,
which is a condensed profile rather than the full Phase 1 block — matching the example in
instructions.md lines 56-58. So the requirement is *roughly* met but the wording promises more
than the template delivers, and a reviewer comparing the two will notice.

**Proposed fix.** Either reword to "it has to carry the project identification from Phase 1
(project, stack, file count) plus all Phase 2 analysis", or extend `report-template.md` to embed
the full Phase 1 block. The reword is cheaper and matches the challenge's own example; changing
the template is the better choice only if Pedro wants the report to stand alone.

Decision: Extend report-template

---

## Requirements already satisfied

Worth recording so they are not re-litigated:

- **Three sequential phases** — line 13, with all three present and ordered.
- **Phase 1 content** (language, framework, dependencies, domain, file count, DB tables) —
  lines 18-23, matching instructions.md lines 44-48.
- **Phase 2 mandatory properties** — lines 46-51 cover exact file and line numbers, severity
  ordering, the five-finding minimum, deprecated-API detection, and the confirmation pause.
  This list maps cleanly onto the validation checklist at instructions.md lines 254-260.
- **Deprecated-API detection** — required at line 175, present at line 50.
- **Phase 1 → Phase 2 confirmation** — line 25. Not a gap: PLAN.md decision 1 keeps this
  deliberately, and instructions.md requires a gate before Phase 3 without forbidding others.
- **≥ 8 anti-patterns and ≥ 8 transformations** (lines 174, 176) — satisfied by the reference
  files at 29 and 24 respectively, not by `SKILL.md`.
- **Skill name and `SKILL.md` filename** — unchanged, as line 169 requires.

## Approval

All eleven applied in step 4, with Pedro's two open decisions resolved as recorded above
(G6 → Option B, G11 → extend the template).

- [x] G1 — report path (blocking)
- [x] G2 — reference file paths (blocking)
- [x] G3 — description, full version
- [x] G4 — validation procedure
- [x] G5 — removed the unconditional claim, replaced with the completion format
- [x] G7 — adapt to starting point
- [x] G8 — prohibition during the gate
- [x] G9 — truncated line deleted
- [x] G10 — repetition cut
- [x] G6 — Option B: healthcare report and severity scale removed, output banners kept
- [x] G11 — `report-template.md` extended with a `## Project Profile` block

`SKILL.md` went from 152 to 141 lines: roughly 55 lines of duplicated knowledge removed,
roughly 44 lines of procedure and reference pointers added.
