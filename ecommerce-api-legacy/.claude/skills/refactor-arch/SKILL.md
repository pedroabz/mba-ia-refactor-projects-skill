---
name: refactor-arch
description: >
  Audit and refactor a server-side codebase to the MVC pattern in three confirmed phases:
  profile the stack, produce a severity-classified architecture audit report, then
  restructure into Models, Views/Routes and Controllers and verify the application still
  works. Technology-agnostic. Use when asked to audit architecture, find anti-patterns or
  code smells, or refactor a project to MVC. Targets APIs, fullstack apps and workers; for
  a single-page frontend, CLI or library, report the analysis and stop.
---

You are a software architect and code refactoring expert. You will identify the language,
framework and project characteristics, write an audit report about them, and then refactor
the code to follow the MVC pattern (Models, Views/Routes, and Controllers layers, including
their respective responsibilities) — independent of the technology the project uses.

The knowledge you need lives in `references/`. Each phase below names the file to read before
acting on that phase: the instructions here are the procedure, the reference files are the
domain knowledge.

This analysis will be done in three phases done sequentially:

PHASE 1 - Project Analysis:
Read `references/project-analysis.md` before starting. Your goal in this phase is to identify
the programming language, framework, and architecture of the codebase. You will also analyze
the project structure, dependencies, and any architectural patterns used. You will provide a
summary of your findings.
It has to contain:
- Language of the app
- Framework used
- Dependencies used
- Domain correctly described
- Number of source files analyzed
- DB tables (if applicable)

This phase reports facts, one line per field, and nothing else. Problems you notice while
reading the code are carried into Phase 2, where the catalog confirms and classifies them —
do not put findings, severities or line numbers in this summary. The domain is the business
the software serves, not the software: `E-commerce (produtos, pedidos, usuarios)`, never a
description of the API.

If the project is not a server-side application — a single-page frontend, a CLI tool or a
library — print the summary, state that the MVC target of this skill does not apply, and
stop. Declining is a correct outcome; restructuring a project this skill was not built for
is not.

When the analysis is done you will print the result and wait for confirmation before moving
to phase 2. Everything after this inherits the profile, so a wrong stack here invalidates the
audit that follows.

Here is an Example.:
================================ PHASE 1: PROJECT ANALYSIS ================================

Language:      C#
Framework:     ASP.NET Core 8.0
Dependencies:  Entity Framework Core, MediatR, FluentValidation
Domain:        Healthcare API (patients, appointments, medical records)
Architecture:  Clean Architecture — separation into API, Application,
               Domain, and Infrastructure layers
Source files:  87 files analyzed
DB tables:     Patients, Doctors, Appointments, MedicalRecords, Prescriptions

================================================================================================

Phase 2 - Audit Report:
Read `references/anti-patterns.md` in full, then `references/report-template.md` for the
output format. Open the matching `references/deep/<family>.md` before writing any finding — it
holds the confirmation steps, the severity adjustments and the false-positive guards for that
family. Your goal is to create an audit report to find the architectural issues in the
codebase. You will identify anti-patterns, code smells, and architectural violations, and
classify them according to their severity (CRITICAL, HIGH, MEDIUM, LOW). You will provide a
summary of your findings and recommendations for refactoring.

The catalog is a set of examples, not a closed list. When you find a real problem that no
entry anticipates, report it following "When nothing matches" in `anti-patterns.md` rather
than forcing it onto an entry that does not fit.

Write the report to the path derived in `references/report-template.md` ("Report file"), so
the skill stays correct when copied into another project. The report has to carry the project
identification from Phase 1 as well as all of the Phase 2 analysis.

It is mandatory that phase 2 analysis includes:
- Each finding includes the exact file path and line numbers.
- Findings are sorted by severity (CRITICAL → LOW).
- At least 5 findings are identified.
- Deprecated API detection is included (if applicable).
- The skill pauses and requests confirmation before proceeding to Phase 3.

When the report is done the user should review it and confirm before moving to Phase 3. Until
that confirmation, do not create, modify or delete any file in the project — the report is the
only output of this phase. Treat anything other than an explicit yes as no.

Phase 3 - Refactoring to MVC Architecture:

Read `references/architecture-guidelines.md` for the target, then
`references/refactoring-playbook.md` for the transformation index; load the
`references/playbook/<family>.md` files for the families the audit actually found.

In this phase, you will refactor the codebase to follow a more maintainable architecture with
the MVC pattern (Models, Views/Routes, and Controllers layers, including their respective
responsibilities). You will apply the recommendations from the audit report and implement best
practices for structuring the code.

Match the work to the starting point using "Adapting to the starting point" in
`architecture-guidelines.md`: the MVC target is the same for every project, but a partially
layered codebase needs different transformations than a monolith — keep the layers that
already work.

Before modifying any file, capture the endpoint contract as described in
`refactoring-playbook.md` ("Capture the contract before changing anything"). Apply the
transformations in the order given there, booting the app between groups. After the last
change, replay the baseline and compare. If validation fails, follow "When validation fails"
in the same file rather than continuing — a deferred transformation with a stated reason is a
better outcome than a broken application.

At the end of the phase you will print the new project structure and a validation summary
reporting what you actually verified, plus anything you deliberately left undone.

It has to print something following the format below:
================================
PHASE 3: REFACTORING COMPLETE
================================
## New Project Structure
src/
├── config/settings.py
├── models/
│   ├── produto_model.py
│   └── usuario_model.py
├── views/
│   └── routes.py
├── controllers/
│   ├── produto_controller.py
│   └── pedido_controller.py
├── middlewares/error_handler.py
└── app.py (composition root)

## Transformations Applied
<T-id — what changed, file(s) touched>

## Validation
  <✓|✗> Application boots without errors
  <✓|✗> Endpoints replayed: <n>/<n> match the baseline
  <any intentional contract change, with its reason>

## Deferred
<findings not fixed, and why>
================================
