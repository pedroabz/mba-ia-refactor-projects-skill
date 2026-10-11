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

The domain is not decoration in the summary: it calibrates severity for everything that
follows. Money moving through the system raises the weight of transaction findings.
Personal data raises exposure findings. A public read-only catalogue lowers access-control
findings. Without the domain, severity is guesswork.

Gather evidence in descending order of authority:

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

Then state the domain as a **description of what the system does and for whom**, not as a
category label:

- A description is verifiable against the code; a category is a guess that smuggles in
  assumptions. "Course enrollment with checkout and payment recording" can be checked.
  Calling the same project "e-commerce" imports carts, inventory, shipping and catalogues
  that may not exist, and the reader cannot tell which parts you actually saw.
- **Keep the codebase's own words, including its language.** Translating `pedidos` to
  "orders" in the report makes every finding harder to locate in the source.
- Name the actors where they are visible — a roles table or a role column tells you who the
  system distinguishes, which directly informs access-control findings.
- Note the boundaries of what you can see. An API with no frontend in the repo, or a service
  that assumes an upstream caller, should say so.

**When the evidence is thin, say so.** "Purpose not declared; entities are X, Y and Z, with
operations limited to CRUD" is a legitimate result. Inventing a plausible category is how a
profile becomes wrong in a way nobody catches, because it reads as confident.

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
