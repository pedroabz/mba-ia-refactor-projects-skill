# Plan — `refactor-arch` skill

Working plan for building the skill required by [instructions.md](./instructions.md).
Six steps, executed in order, with a validation gate owned by Pedro between step 1 and
step 3, and again at step 4.

Current state: `code-smells-project/.claude/skills/refactor-arch/SKILL.md` exists as a
first draft (3 phases sketched, inline examples, `// TODO` markers). No reference files
yet. Manual analysis of the 3 projects is done and committed in `README.md`.

**On the role of that manual analysis:** it is a *floor*, not the source. The catalog is
built from language-agnostic fundamentals (below); the manual analysis is then used as a
regression check — every finding documented there must be reachable by some catalog
entry. If the catalog only knew the things already found by hand, it would be a lookup
table for three specific repos instead of a skill.

---

## Hard constraints (from instructions.md)

Non-negotiable, independent of design choices:

- Skill name is `refactor-arch` and the entry file is `SKILL.md`. Neither may be renamed.
- Path follows the Claude Code convention: `<project>/.claude/skills/refactor-arch/`.
- Reference files must be Markdown.
- Five knowledge areas must be covered: project analysis, anti-pattern catalog,
  report template, architecture guidelines, refactoring playbook.
- Anti-pattern catalog: **≥ 8** anti-patterns, severities spread across CRITICAL / HIGH /
  MEDIUM / LOW, and it must include **deprecated-API detection**.
- Refactoring playbook: **≥ 8** transformation patterns, each with before/after code.
- Phase 2 must **pause and ask for confirmation** before any file is modified.
- Phase 3 must validate the result: app boots + endpoints respond.
- The skill must work on all 3 projects (Python/Flask monolith, Node/Express, partially
  organized Python/Flask) — i.e. it must be copyable, with nothing project-specific baked in.

Acceptance criteria to hit in **all three** projects: Phase 1 detects the stack; Phase 2
produces ≥ 5 findings including ≥ 1 CRITICAL or HIGH; Phase 3 leaves a working app.

---

## Step 1 — Create the reference files

**Owner:** Claude. **Deliverable:** 16 Markdown files under
`code-smells-project/.claude/skills/refactor-arch/references/`.

### Grounding: fundamentals first

Every catalog entry names the fundamental it violates, and the fundamentals are stated
in language-neutral terms. This is what makes the skill agnostic *by construction* rather
than by having a branch per framework. The spine:

| Fundamental | Source of the rule |
|---|---|
| Separation of concerns / layer boundaries | MVC — a layer may not reach past its neighbour |
| Single responsibility, dependency inversion | SOLID (SRP and DIP carry most of the weight here) |
| Low coupling, high cohesion | structured design |
| Config in the environment, not the artifact | 12-factor, factor III |
| Least privilege, deny by default | access control |
| Injection is a data/code confusion bug | OWASP A03 — fix is parameterization, not escaping |
| Broken access control, crypto failures, misconfiguration, auth failures, logging failures | OWASP A01 / A02 / A05 / A07 / A09 |
| Atomic unit of work | ACID — a business operation commits once or not at all |
| Single source of truth | DRY, applied to rules rather than to characters |
| Fail fast, explicit errors | no silent swallow, no partial state |
| Validate at the boundary | the edge is where untrusted input stops being untrusted |

Breadth comes from these principles plus the detection patterns a reviewer actually uses;
the three sample repos only decide what gets a worked example. Target ~22 catalog entries
— enough to cover the principle space, short enough that the triage file stays scannable.

### File architecture (progressive disclosure)

Three loading levels, per the skill-authoring guidance: metadata always in context,
`SKILL.md` on invocation, reference files on demand. So the tier-1 files stay short and
the depth sits behind them, loaded only for families that actually came up in the audit.

```
references/
├── project-analysis.md          tier 1 · phase 1 · detection heuristics
├── anti-patterns.md             tier 1 · phase 2 · triage index, ~22 entries
├── report-template.md           tier 1 · phase 2 · output formats + severity scale
├── architecture-guidelines.md   tier 1 · phase 3 · target MVC rules
├── refactoring-playbook.md      tier 1 · phase 3 · transformation index
├── deep/                        tier 2 · detection depth, per family
│   ├── security.md              secrets, injection, authn/z, crypto, data exposure
│   ├── layering.md              god class, logic placement, DI, global state
│   ├── data-access.md           transactions, N+1, orphans, SELECT *, pagination
│   ├── api-contract.md          validation, error handling, status codes, middleware
│   ├── code-quality.md          duplication, dead code, naming, magic numbers, imports
│   └── deprecated-apis.md       per-stack lookup + how to verify + how to report none
└── playbook/                    tier 2 · transformations with before/after code
    ├── security.md
    ├── layering.md
    ├── data-access.md
    ├── api-contract.md
    └── code-quality.md
```

The five tier-1 files map 1:1 onto the five mandatory knowledge areas, so the mapping is
checkable at a glance. `deep/` and `playbook/` use the same family names, so an anti-pattern
id points at both its confirmation steps and its fix without a lookup. Both directories are
extension points: a new family is a new file plus one row in the triage index, with no edit
to `SKILL.md`.

**Size budgets.** The driver here is Pedro's constraint that individual files stay short —
splitting into `deep/` and `playbook/` is the mechanism for that, not a competing goal. A
reference too long to read is a reference that gets skimmed, and anything skimmed may as
well not be there. Tier-1 files 100-200 lines; tier-2 files 80-150. If a file outgrows its
budget it splits along family lines rather than being compressed into something unreadable.
This is also why the playbook is an index: 12 transformations with before/after code in both
Python and JavaScript is a 400-line file, which is exactly the shape being avoided.

**Entry schema for the triage index** — id, severity, the fundamental violated, a
detection signal concrete enough to act on, and a pointer to its `deep/` file. Detection
signals are written as what to look for, not as a verdict: "SQL string assembled with
`+`, `%`, `.format()` or f-string interpolation of a request value" rather than "unsafe
query".

**False-positive guards are mandatory**, inline with the entry they protect. At minimum:
`Model.col.like(f'%{q}%')` through an ORM is parameterized and is *not* injection;
`Buffer.from()` is the correct modern form, not deprecated `new Buffer()`; an ORM is not
"missing data layer"; a framework's own debug default is not a hardcoded secret. Without
these the skill inflates CRITICALs on project 3 and the whole report loses credibility.

**Deprecated APIs** get their own `deep/` file because the checklist requires detection and
only one project has a true hit — `datetime.utcnow()`, deprecated in Python 3.12, in
`task-manager-api`. Projects 1 and 2 have none. So the file must also teach the skill to
verify against the declared dependency version and to report "none found" honestly instead
of manufacturing one. Secondary entries: `new Buffer()`, `@app.before_first_request`
(removed in Flask 2.3), `Query.get()` (legacy in SQLAlchemy 2.0), Express 4 vs 5,
callback-style drivers where a promise API exists.

**Not in scope for step 1:** touching `SKILL.md`. It stays untouched so step 3 can diff the
draft against finished references and against instructions.md.

---

## Step 2 — Validation gate (Pedro)

**Owner:** Pedro. Review the 16 files and confirm they make sense before anything is
wired up. Useful questions to review against:

- Are the detection signals specific enough to act on, rather than vague?
- Does every finding from the manual analysis map to a catalog entry?
- Is the breadth right — principles covered without padding the list to look thorough?
- Are the severities consistent with the scale in instructions.md, not inflated?
- Do the playbook before/after examples reflect the actual shape of these codebases?
- Is anything project-1-specific that would break when the folder is copied?
- Is the tier-1 / `deep/` split in the right place, or is something in the wrong tier?

Output: approved files, or a change list to apply before moving on.

---

## Step 3 — Gap report: `SKILL.md` vs `instructions.md`

**Owner:** Claude. **Deliverable:** a written report (`docs/skill-gap-report.md`), listing
each gap as: what instructions.md requires, what the draft currently does, severity of the
gap, proposed fix, and the smallest diff that achieves it. **No edits in this step.**

**Ownership constraint (Pedro):** `SKILL.md` is Pedro's document. The gap report exists so
every change is intentional and known, approved item by item. No wholesale rewrite, no
silent restructuring, no change that is not on the approved list — including changes that
look obviously right. Where a gap can be closed by adding a line rather than reorganizing a
section, the proposal must say so.

Items already visible in the draft and queued for that report (to be confirmed, not acted on):

- `description` in the frontmatter does not mention MVC refactoring or the 3-phase flow,
  and does not say when to invoke — weak triggering.
- The report filename is hardcoded as `audit-project-1.md` (line 43). Biggest portability
  bug: copied to projects 2 and 3 it overwrites project 1's report. Reports also belong at
  the repo-root `reports/`, not inside the project.
- The reference files are named in prose ("Using the Project Analysis reference file") but
  no path is ever given, so there is nothing for the skill to read. They exist only as a
  `// TODO` block at the end (lines 139-152).
- Severity definitions, the Phase 2 example report and the Phase 3 output example are
  inlined; they now live in the references. Keeping both copies means they will drift.
- Phase 3's validation is a goal ("be able to boot the app") with no procedure: no endpoint
  discovery, no failure path, no rollback rule.
- No pre-refactor contract snapshot, so "endpoints still respond" cannot be proven.
- `// TODO: be less repetitive` (line 9) — paragraphs 7, 10 and 11 restate each other.
- Truncated sentence at line 104 ("In this phase, following the conventions on").
- Phase 3 prints "Zero anti-patterns remaining" unconditionally — should report what was
  actually fixed vs deferred.
- Nothing tells the skill to adapt depth to an already-organized project (project 3).

Resolved by Pedro's answers, so no longer gaps: the Phase 1 confirmation pause stays (it is
deliberate), and the report number is derived at runtime rather than hardcoded.

---

## Step 4 — Apply the approved changes

**Owner:** Claude, limited to Pedro's approved subset of step 3. Expected shape:

- Surgical edits to `SKILL.md`, preserving its existing structure, section order and voice.
  Each edit traceable to one approved gap item.
- Wire in the references explicitly: each phase says which file to read before acting, by
  path, and which `deep/` files to pull when a family shows up.
- Replace the inlined knowledge with pointers, so the formats have one home.
- Parameterize the report path.
- Add the Phase 3 validation procedure and its failure path.
- Keep `SKILL.md` lean — it is paid for on every invocation; knowledge belongs in references.

Gate: Pedro re-reads `SKILL.md` end to end before step 5, since this file drives all three runs.

Open for this step: whether a `scripts/` directory is allowed. Endpoint discovery, contract
snapshot and replay are deterministic and identical on every run, which is exactly what a
bundled script is for — and it would make Phase 3's validation reproducible instead of
improvised. instructions.md requires the *reference* files to be Markdown and says nothing
about scripts, so this is a judgement call, not a rule. Needs a yes/no.

---

## Step 5 — Execute and validate

**Owner:** Claude + Pedro. Order: project 1 → fix → project 2 → fix → project 3.
Expect 2-4 iterations; instructions.md says so explicitly.

Per project:

1. **Snapshot the contract first** — start the app, hit every endpoint, save status + body
   to a baseline file. For project 2 the endpoint list is `api.http`; for the Flask projects
   derive it from the route registrations. Without this, "endpoints still respond" is
   unverifiable.
2. Run `claude "/refactor-arch"` in the project directory.
3. Check Phase 1 against the real stack; check Phase 2 against the manual analysis in
   `README.md` (≥ 5 documented findings should appear); confirm both pauses happen.
4. Approve Phase 3, then replay the contract snapshot and diff against the baseline.
5. Save Phase 2's output to `reports/audit-project-N.md`.
6. Fill the validation checklist from instructions.md.

Then copy `.claude/skills/refactor-arch/` into `ecommerce-api-legacy/` and
`task-manager-api/` and repeat. Any fix made to the skill during a later project propagates
back to all three copies — the three directories must end up identical. Worth re-running
project 1 at the end if the skill changed meaningfully after it.

Note for project 2: the DB is `:memory:` (`AppManager.js:7`), so the baseline must be
captured in a single run — restarting the server resets all data.

**Commits are Pedro's.** Claude does not commit; Pedro reviews the working tree and commits
himself.

---

## Step 6 — Write the README

**Owner:** Claude, reviewed by Pedro. Portuguese. Fill the four mandatory sections.
"Análise Manual" is written; remaining:

- **Construção da Skill** — design decisions (fundamentals-first catalog, tier-1 / `deep/`
  split and why, the 1:1 mapping to the five knowledge areas), which anti-patterns made the
  catalog and why, how agnosticism was achieved (manifest-driven detection, principle-level
  rules, no hardcoded paths), and problems hit with their fixes.
- **Resultados** — findings-per-severity table for the 3 projects, before/after structure,
  filled validation checklist per project, boot logs / endpoint output after refactor, and
  notes on behaviour across stacks.
- **Como Executar** — prerequisites, command per project, how to verify the refactor held.

Also pending before delivery: finish the MEDIUM/LOW sections of the manual analysis so each
project has ≥ 1 CRITICAL-or-HIGH, ≥ 2 MEDIUM and ≥ 2 LOW (`task-manager-api` has an empty
MEDIUM section).

---

## Decisions

1. **Confirmation gates — pause between every phase.** Rationale (Pedro): if Phase 1 got the
   language wrong there is no point auditing. instructions.md only requires the gate before
   Phase 3; the extra one after Phase 1 is additive and allowed. So: Phase 1 → confirm →
   Phase 2 → confirm → Phase 3.
2. **Report numbering — derived at runtime, plain increment.** Scan the output folder and use
   the highest existing `audit-project-N.md` plus 1; create `reports/` and start at 1 if
   empty. Nothing project-specific baked in, so the folder stays copyable.
   Re-runs are handled outside the skill: Pedro deletes the stale report before re-running a
   project, so the increment lands on the number that project already had.
3. **Language — skill in English, deliverable docs in Portuguese.**
4. **MVC is the target for all three projects, project 3 included.** The validation checklist
   is applied "para cada projeto refatorado" (line 243) and requires "estrutura de diretórios
   segue padrão MVC" (line 263), and the note on project 3 states that necessary structural
   changes must be proposed *and executed* (line 239). What adapts per project is the set of
   transformations (line 446) — there is no god file to split in project 3 — not the target.
   Flexibility is in what else an MVC project may contain: existing `services/`, `utils/` and
   middleware layers are kept, since they are compatible with MVC rather than alternatives to
   it. The contract baseline is what keeps the restructure honest.
5. **Commits — Pedro's, always.** Claude leaves changes in the working tree.

---

## Risks

- **Skill drift across the 3 copies** — the most likely way to fail "3/3 projects".
  Mitigation: project 1's copy is the source of truth; re-sync after every change and diff
  the three directories before delivery.
- **Phase 3 breaking project 2** — the callback-based async coordination in
  `AppManager.js:80-129` is fragile; a mechanical refactor can silently change response shape
  or ordering. The contract baseline catches this.
- **Over-reporting on project 3** — a partially organized project invites false CRITICALs.
  The inline false-positive guards are the mitigation.
- **`SKILL.md` ownership** — the failure mode here is Claude "improving" the file beyond the
  approved list. Step 3 produces the list, step 4 applies only that.
- **`SKILL.md` bloat** — everything in it is read on every invocation. Knowledge goes in
  references, loaded on demand.
- **Reference sprawl** — 16 files means navigation has a cost of its own. The mitigation is
  structural: the triage index is the only map the skill needs, every id resolves to its
  family by prefix, and `deep/`+`playbook/` share family names so no file has to be hunted
  for. If a tier-2 file stops earning its place during step 5, fold it back.
