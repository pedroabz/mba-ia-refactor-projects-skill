# Project Analysis — detection heuristics

How to build a factual profile of an unfamiliar codebase: archetype, language, framework,
dependencies, persistence, domain, current architecture, and size. Everything downstream
inherits this profile, so a wrong stack here invalidates the audit that follows.

Read evidence from files, not from assumptions. Every line of the summary should be
traceable to something you actually opened.

## 1. Archetype

Classify this first, because it decides whether the rest of the skill applies at all. The
layer rules, the anti-pattern families and the endpoint-replay validation all assume a
server-side application; applied to something else they produce confident nonsense.

| Archetype | Signals | Consequence |
|---|---|---|
| Server-side API | HTTP route registrations, JSON responses, no view templates | Everything applies as written |
| Fullstack, server-rendered | Route handlers plus view templates (Jinja, ERB, Blade, EJS, Razor) | Applies, and "View" means the template layer literally |
| Worker / consumer | Subscribes to a queue, schedule or stream; no listener | Layering applies; handlers take messages instead of requests; no endpoints to replay |
| Single-page frontend | Build tooling, component tree, router without a server, an API client | MVC as defined here does not map — components, state and API access are the layers |
| CLI / batch | Entry point parses arguments and exits; no listener | Layering applies; the `API` family mostly does not; validation means argument parsing |
| Library / package | No entry point, a published public surface, consumers outside the repo | No routes, no composition root, no runtime to boot |

**Scope boundary.** This skill targets server-side applications: APIs, fullstack apps and
workers. For a single-page frontend, a CLI or a library, report the profile and stop,
stating that the MVC target does not apply rather than restructuring anyway. Declining is a
correct outcome; reorganizing a component tree into `models/views/controllers` is not.

In a repository containing both a frontend and a backend, scope to the server-side part and
say so explicitly in the summary, so nobody reads the report as covering the whole repo.

## 2. Language

Start from the dependency manifest, because it is declarative and cheap to read. Fall back
to file extensions only when no manifest exists.

| Manifest found | Language | Where the version lives |
|---|---|---|
| `requirements.txt`, `pyproject.toml`, `Pipfile`, `setup.py` | Python | `python_requires`, `.python-version`, CI config |
| `package.json` | JavaScript / TypeScript | `engines.node`; TypeScript if `tsconfig.json` present |
| `pom.xml`, `build.gradle` | Java / Kotlin | `maven.compiler.source`, `sourceCompatibility` |
| `go.mod` | Go | `go` directive |
| `Gemfile` | Ruby | `.ruby-version` |
| `composer.json` | PHP | `require.php` |
| `*.csproj`, `*.sln` | C# | `TargetFramework` |
| `Cargo.toml` | Rust | `rust-version` |

If several manifests exist, the one next to the entry point describes the application; the
others are tooling or sub-packages. Say so rather than reporting a hybrid stack.

## 3. Framework and version

The manifest names the framework; the code confirms how it is used. Report the version the
project pins, not the latest release.

The procedure is the content of this section, and it is the same for every ecosystem:
manifest first, confirm in code, record the pinned version. The table below is a handful of
examples of that procedure, not a list to match against — apply the same steps to whatever
stack you find, including ones not listed here.

| Signal in code | Framework |
|---|---|
| `Flask(__name__)`, `@app.route`, `Blueprint` | Flask |
| `FastAPI()`, `APIRouter` | FastAPI |
| `django.urls`, `settings.py`, `manage.py` | Django |
| `express()`, `app.use`, `Router()` | Express |
| `@nestjs/common`, `@Controller()` | NestJS |
| `@SpringBootApplication`, `@RestController` | Spring Boot |
| `Microsoft.AspNetCore`, `[ApiController]`, `Program.cs` | ASP.NET Core |
| `Rails::Application`, `config/routes.rb` | Ruby on Rails |
| `Illuminate\\`, `artisan`, `routes/web.php` | Laravel |
| `next` dependency, `app/` or `pages/` directory | Next.js |

The pinned version matters beyond reporting: it decides whether an API is deprecated,
current, or not yet available. Never flag a deprecation without checking that the pinned
version supports the replacement you intend to recommend.

## 4. Persistence

Four independent signals, in decreasing reliability:

1. **Driver or ORM import** — `sqlite3`, `psycopg2`, `pymysql`, `sqlalchemy`,
   `flask_sqlalchemy`, `mongoose`, `pg`, `mysql2`, `prisma`, `sequelize`, `typeorm`,
   `EntityFramework`, `ActiveRecord`, `Eloquent`.
2. **Schema definition** — ORM model classes (`db.Model`, `@Entity`, `Schema({...})`) or
   raw `CREATE TABLE` executed at startup. Both give you the table list directly.
3. **Connection string / DSN** — `sqlite:///`, `postgresql://`, `mongodb://`. Often also
   the first hardcoded-secret finding of the audit.
4. **Migration directory** — `migrations/`, `alembic/`, `prisma/migrations`, `db/migrate`.
   Absence is itself worth noting: schema created at boot means no migration path.

Table names come from the schema, whichever form it takes. If the schema is created inline
at startup, record that — it is an audit finding, not just a profile fact.

## 5. Domain

The domain is the **business the software serves, not the software itself**. "REST API",
"web service", "microservice", "CRUD backend" and "Flask application" are implementation
shapes — nearly every project in scope is one of those, so naming it conveys nothing. The
domain is what someone would be doing if the software did not exist: selling goods,
enrolling students, tracking work, scheduling appointments, moving money.

**Output shape — one line.** Business first, key entities in parentheses, in the code's own
words:

```
Domain:  <business domain> (<three or four key entities>)
```

| | |
|---|---|
| Good | `E-commerce (produtos, usuarios, pedidos, itens_pedido)` |
| Good | `Course enrollment with paid checkout (users, courses, enrollments, payments)` |
| Good | `Task management with per-user reporting (tasks, users, categories)` |
| Bad | `REST API of an online store serving product catalogue and order placement` |
| Bad | `Flask CRUD application over four tables` |

The first bad example leads with the transport and spends its words describing the
software. The second names a framework and a table count, which the other lines of the
summary already report.

### Reaching that line

Everything below is **working material, not output.** You read all of it; you print one
line. Gather evidence in descending order of authority:

1. **Declared intent.** README, manifest description, repository name, OpenAPI title, API
   docs, request examples. Read these first — they are the cheapest and most direct
   statement of purpose available, and skipping them to infer from schema is doing hard work
   to reach a worse answer.
2. **The operations that are not CRUD.** Generic create/read/update/delete tells you what
   the system stores. The endpoints that are *not* generic tell you what it is for:
   checkout, login, approve, reconcile, publish, enroll, export. These carry the purpose.
3. **Relationships, not just entity names.** The nouns list the pieces; the foreign keys
   show the flow. A chain from actor to transaction to line-items with a monetary column is
   a purchase pipeline. An actor linked to work items through a classification table is
   assignment and tracking. The same three nouns can appear in both.
4. **Integrations and side effects.** A payment SDK means money moves. An SMTP or push
   client means the system notifies people. A scheduler means time-driven behaviour. A
   storage client means documents. These reveal purpose that the schema hides.
5. **The vocabulary of the code itself**, including its natural language.

### Condensing the evidence into the line

- **Say what the business is, then anchor it.** The business phrase should survive on its
  own — "e-commerce", "course enrollment with paid checkout", "task management with
  reporting" — and the parenthesised entities anchor it to this specific codebase so a
  reader can tell you looked rather than guessed.
- **Keep the codebase's own words, including its language.** Translating `pedidos` to
  "orders" makes every later finding harder to locate in the source.
- **Prefer the specific business phrase over the broad category** where the evidence
  supports it. "Course enrollment with paid checkout" is better than "e-learning" because it
  is checkable. But do not pad it into a sentence describing the software's behaviour — that
  is what produced the first bad example above.

**When the evidence is thin, say so in the same one line.** `Unclear — CRUD only over
(items, users); no stated purpose` is a legitimate result. Inventing a plausible category is
how a profile becomes wrong in a way nobody catches, because it reads as confident.

### Keep findings out of the profile

The profile answers *what is this?*. The audit answers *what is wrong with it?*. Those are
separate phases with separate outputs, and mixing them costs twice: the summary stops being
reviewable at a glance, and the finding escapes the catalogue's confirmation steps and
false-positive guards on its way into the report.

So the domain line carries no problems, no severities, no line numbers, no route inventory
and no notes about what is unenforced or insecure. Noticing while reading the schema that
passwords are stored as received is valuable — carry it forward into the audit, where it gets
confirmed and classified properly. Not into this line.

Knowing the domain does change how findings are weighed later: money moving through the
system raises the weight of transaction-integrity findings, personal data raises exposure
findings, a public read-only catalogue lowers access-control findings. That is a reason to
establish the domain carefully. It is not a reason to write severity reasoning into the
summary — do that weighing during the audit, against the catalogue.

Two specific temptations, both of which belong to the audit:

- **The actors.** Note who the system distinguishes if a roles table or role column makes it
  visible, and keep it to the names. Whether the distinction is actually enforced anywhere is
  an access-control finding, not a profile fact.
- **The interesting operations.** The non-CRUD endpoints are how you *identified* the domain;
  they are not the domain. An inventory of routes with commentary belongs nowhere in the
  summary — the file count and the architecture line already describe the surface.

**Guard against pattern-matching on a familiar schema.** Tables named `users` and `orders`
appear in subscription billing, ticketing, logistics, marketplaces and internal tooling —
all with different risk profiles and different severity calibration. Read the operations
before naming the domain.

## 6. Current architecture

Measure before judging. The facts to collect:

- **Entry point** — the file that creates the app and starts the server.
- **File and line counts** — per source file, excluding dependencies (`node_modules/`,
  `venv/`, `.venv/`, `vendor/`, `dist/`, `build/`) and lock files. A single 300-line file
  holding routes, queries and rules is a different problem from thirty 40-line files.
- **Layer presence** — does a directory or module exist for each of: config, routes/views,
  controllers/handlers, models/entities, data access, services, middleware? Record present,
  absent, or present-but-bypassed. The third case is the interesting one.
- **Dependency direction** — which modules import which. A model importing a route, or an
  entry point importing a database driver, is a boundary violation and becomes a finding.
- **Dead layers** — a module that exists and is never imported, or imported and never
  called. Grep each exported name across the project; zero call sites means the abstraction
  was written and abandoned, and the logic now lives duplicated elsewhere.

Then classify honestly, in one sentence, using what you measured:

- *Monolithic, no separation* — everything in one or a few files, no layer directories.
- *Partially layered* — some layer directories exist, but boundaries leak or layers are
  bypassed.
- *Layered* — directories match responsibilities and the dependency direction holds.

"Partially layered" is the most common and the easiest to get wrong in both directions.
Directories named `models/` and `services/` prove intent, not compliance; check whether the
code in them does what the name claims before crediting the project with a layer.

## 7. What the profile must report

Language, framework + version, dependencies, domain, current architecture, source file
count, and database tables if any. `report-template.md` holds the exact output format.

Two habits keep the profile honest:

- **Count, don't estimate.** File and line counts are cheap to obtain and the checklist
  verifies them against reality.
- **Say "none" out loud.** No database, no tests, no migrations, no middleware — stating
  the absence is information. Leaving the line out reads as "not checked".
