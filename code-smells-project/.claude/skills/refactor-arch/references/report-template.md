# Report Template — output formats

The formats below are what the operator reads to decide whether to approve the next step,
so they are fixed: a reviewer should be able to compare two runs of two different projects
line by line.

Severity definitions are not repeated here — they live in `anti-patterns.md`, which is their
single home. Use that scale.

## Project analysis output

Printed to the console. Every line is a fact gathered while profiling the project; state
`none` rather than dropping a line.

```
================================
PHASE 1: PROJECT ANALYSIS
================================
Language:      <language + version if pinned>
Framework:     <framework + version from the manifest>
Dependencies:  <direct dependencies, comma separated>
Domain:        <what the application does, in the codebase's own vocabulary>
Architecture:  <one sentence: current state, measured not guessed>
Source files:  <N> files analyzed
DB tables:     <table names, or "none">
================================
```

Every later judgement inherits this profile, so it is worth a reviewer's five seconds here
rather than five minutes into a report built on the wrong stack.

## Audit report output

Written to the report file **and** printed. Numbering of the report file is derived at
runtime — see "Report file" below.

```
================================
ARCHITECTURE AUDIT REPORT
================================
Project: <directory name>
Stack:   <language + framework + persistence>
Files:   <N> analyzed | ~<M> lines of code

## Project Profile
Language:      <language + version if pinned>
Framework:     <framework + version from the manifest>
Dependencies:  <direct dependencies, comma separated>
Domain:        <what the application does, in the codebase's own vocabulary>
Architecture:  <one sentence: state before refactoring, measured not guessed>
DB tables:     <table names, or "none">

## Summary
CRITICAL: <n> | HIGH: <n> | MEDIUM: <n> | LOW: <n>

## Findings

### [<SEVERITY>] <finding title>
ID: <catalog id, e.g. SEC-03>
File: <path>:<line or line range>
Description: <what the code does, specifically. Name the construct, not a category.>
Impact: <what breaks or is exposed as a result. Consequence, not restatement.>
Recommendation: <the transformation to apply, by name where the playbook has one.>

<... one block per finding, ordered CRITICAL → HIGH → MEDIUM → LOW ...>

## Notes
<observations that are not code findings: absent tests, no migrations, no deprecated
API found. Optional — omit the section when there is nothing to say.>

================================
Total: <n> findings
================================
```

### Rules the format depends on

- **Carry the profile, don't re-derive it.** `## Project Profile` repeats what the analysis
  already established, so the report stands on its own: a reader who only has this file can
  judge whether the findings make sense for that stack without going back to the console
  output. The three-line header above it stays because it is what the challenge's own example
  shows; the profile block is the detail behind it.
- **Order by severity**, CRITICAL first. Within a severity, order by file path so repeated
  reads of the same report are stable.
- **Exact locations.** `path:42` for a single line, `path:42-68` for a range. A finding whose
  location is a whole file is only acceptable when the finding genuinely is the whole file
  (a god file, for instance) — and then the full range is still given.
- **One finding per distinct problem.** A pattern repeated across many sites is one finding
  with every location listed, not one per site. Twenty copies of the same issue reported
  separately buries the other nineteen findings.
- **Describe, then conclude.** Description says what the code does; Impact says what follows
  from it. If the Impact line only rephrases the Description, the finding is not understood
  well enough to report.
- **Minimum five findings** per the acceptance criteria, including at least one CRITICAL or
  HIGH. If a genuine audit finds fewer, say so plainly rather than padding with LOW entries —
  but on a legacy codebase this is unlikely, and coming up short usually means the sweep was
  shallow rather than the code clean.
- **Deprecated APIs** get a finding when present and a line under Notes when absent. Both
  are results; silence is not.

## Report file

The report goes to the repository's `reports/` directory, which sits next to the project
directory the skill is running in (`../reports/` from the project root).

Deriving the name, so that nothing project-specific is baked into the skill:

1. If `reports/` does not exist, create it.
2. Find existing `audit-project-<N>.md` files and take the highest `N`.
3. Write to `audit-project-<N+1>.md`. With no existing reports, that is
   `audit-project-1.md`.

Re-running a project that already has a report is handled outside the skill — the operator
deletes the stale file first, so the increment lands back on that project's number.

## Confirmation gate

After the report is written, stop. Nothing in the working tree may be modified until the
operator approves the refactor — this is the last point at which a human can inspect the
plan before files change, which is why the challenge requires the gate here.

Ask in a form that makes the consequence explicit and the default safe:

```
Phase 2 complete. <n> findings written to reports/audit-project-<N>.md.
Phase 3 will modify files in this project.
Proceed with refactoring? [y/n]
```

Treat anything other than an explicit yes as no.
