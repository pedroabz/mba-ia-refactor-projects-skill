# Report Template — output formats

The formats below are what the operator reads to decide whether to approve the next step,
so they are fixed: a reviewer should be able to compare two runs of two different projects
line by line.

## Language

**Write the reports in English** — field labels, finding titles, descriptions, impacts and
recommendations. This holds regardless of the language the codebase is written in, and it is
the strongest pull to resist: a project whose identifiers and comments are in another
language invites matching it, which produces reports that cannot be compared across projects
and that mix two languages inside one finding. Translation to another language, if wanted, is
a separate pass over the finished report.

**This rule governs the reports and nothing else.** It is about the documents this skill
writes — the analysis summary, the audit report, the completion report. It says nothing about
the language of the application being audited, and it is never a reason to change a single
string in the code. The application's own words are its behaviour:

- **User-facing messages** — error text, validation messages, response bodies, notification
  copy. `{"erro": "Produto não encontrado"}` stays exactly that.
- **Response and request keys** — `dados`, `sucesso`, `erro`, `usr`, `eml`. These are the API
  contract; renaming them breaks every client.
- **Enum and status values** — `pendente`, `aprovado`, `cancelado`. These are stored in the
  database, so changing them invalidates existing rows.
- **Log messages, comments and documentation** inside the project.

Translating any of those is a breaking change dressed as a refactor. If a project's messages
genuinely should be localized, that is its own task with its own approval — not something to
fold into an architecture refactor.

**Identifiers are not prose and are never translated.** File paths, table and column names,
function names, route paths, configuration keys and anything inside backticks or a code
fence stay exactly as they appear in the source. Translating `pedidos` to "orders" or
`criar_produto` to "create_product" makes the finding impossible to locate in the code, which
defeats the purpose of recording a location at all.

So in a Portuguese codebase, a finding reads:

```
### [CRITICAL] Hardcoded Credentials Exposed Through Health Endpoint
ID: SEC-01
File: app.py:7, controllers.py:289
Description: `SECRET_KEY` is assigned the literal `'minha-chave-super-secreta-123'` in
             `app.py:7`, and `health_check` returns the same value in its response body
             alongside `debug` and `ambiente` (controllers.py:289).
```

English sentences, Portuguese identifiers and literals, untouched.

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
Domain:        <business domain> (<key entities>)
Architecture:  <one sentence: current state, measured not guessed>
Source files:  <N> files analyzed
DB tables:     <table names, or "none">
================================
```

**One line per field. No field is a paragraph.** Each is a single value or a single
sentence; `Architecture` is the only one that is a sentence at all. This summary exists to
be scanned in a few seconds and approved or rejected, so a field that expands into bullets,
sub-headings or a route inventory has stopped doing its job — and the reviewer can no longer
tell at a glance whether the stack was identified correctly.

**The summary reports facts, not judgements.** No findings, no severities, no line numbers,
no commentary on what is insecure or unenforced. Problems noticed while profiling are
carried into the audit, where they get confirmed and classified. Writing them here both
pre-empts the audit and escapes its false-positive guards.

A filled example, matching the shape the challenge itself specifies:

```
Language:      Python
Framework:     Flask 3.1.1
Dependencies:  flask-cors
Domain:        E-commerce (produtos, usuarios, pedidos, itens_pedido)
Architecture:  Monolithic — 4 files, no layer separation, routes and SQL in the same modules
Source files:  4 files analyzed
DB tables:     produtos, usuarios, pedidos, itens_pedido
```

A trailing noun like "API" or "service" after the business phrase is fine —
`E-commerce API (produtos, pedidos, usuarios)` is exactly what the challenge's own example
shows. What breaks the field is leading with the technical shape, or expanding it into prose
about what the software does. See "Domain" in `project-analysis.md`.

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
