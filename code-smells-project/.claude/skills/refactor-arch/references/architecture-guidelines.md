# Architecture Guidelines — the target

What "refactored to MVC" means, defined so that the same target applies whether the
starting point is a single file or a partially layered project.

MVC here is about **where responsibility lives**, and the directory structure is how that
placement is made visible and enforceable. Both matter: the validation checklist asks for an
MVC directory structure *and* for controllers that concentrate application flow. A project
with the right folders and the rules still in the wrong place has not arrived.

## The layers

Each layer is defined by what it owns and, more usefully, by what it must not do. The
"never" lines are the ones that catch regressions.

### Config

Owns every value that varies by environment: connection strings, secrets, ports, hosts,
debug flags, external service credentials, thresholds that are deployment choices.

Reads from the environment with safe defaults for local development. Never contains a real
secret as a literal. Never imported by a model or a controller for anything other than
values it legitimately needs — config is not a global bag for passing state around.

### Models

Own the domain: entity shape, persistence, and the invariants that are true of an entity
regardless of who is asking. Validation that is intrinsic to the entity belongs here (a
price cannot be negative), as does the data access for that entity.

Never import the framework's request or response objects. Never format HTTP responses.
Never trigger side effects outside persistence — no email, no SMS, no push, no HTTP calls.
Never hold cross-entity workflow: a model knows its own rules, not the sequence of steps a
use case follows.

### Views / Routes — the entry surface

Own the boundary where work enters the application: the address it arrives at, the transport
it arrives on, and the binding of that input to a controller. The transport differs by
archetype, the rule does not:

| Archetype | The entry surface is | "View" means |
|---|---|---|
| Server-side API | HTTP route registrations | the serialized representation returned |
| Fullstack, server-rendered | route handlers plus templates | the template layer, literally |
| Worker / consumer | queue subscriptions, schedule or stream handlers | the published message or the acknowledgement |

Never contain business rules. Never touch the database or import a driver. Never implement
validation beyond what the transport itself provides — the entry surface declares the
contract and delegates. A route handler, like a message handler, should read as one line of
delegation plus the wiring around it.

For a worker this is the layer most often missing entirely: a consumer that subscribes and
then performs the whole job inline is the same violation as a route handler that does, and
it is fixed the same way.

### Controllers

Own application flow for a use case: read the request, validate input, call models and
services in the right order, choose the status code, shape the response. This is where a
multi-step operation is sequenced and where transaction boundaries are opened.

Never contain SQL or ORM queries directly — that is the model's job. Never contain domain
rules that other use cases would need; those move down into models or services. A
controller is allowed to be procedural; it is not allowed to be the only place a rule exists.

### Supporting layers

An MVC project may legitimately contain more than three directories, and keeping existing
ones is preferable to relocating working code for the sake of a shorter tree:

- **Services** — logic that spans several models, or integration with something external
  (payments, mail, notifications). A service is the right home for a rule that does not
  belong to any single entity. Keep an existing `services/` directory and populate it rather
  than dissolving it into controllers.
- **Middlewares** — cross-cutting concerns applied to many routes: error handling, auth,
  rate limiting, request size limits, logging, CORS.
- **Utils / helpers** — pure functions with no domain knowledge. The risk here is a helpers
  module that duplicates rules living elsewhere; if a helper encodes a domain rule, it belongs
  in a model or service instead.
- **Repositories / DAOs** — a separate data-access layer under the models. Optional. Worth
  introducing when queries are complex enough that mixing them into model classes obscures
  the domain; unnecessary overhead when an ORM already provides the abstraction.

### Composition root

One place — the entry point — builds the application: loads config, creates the
dependencies, injects them, registers middleware, registers routes, and starts the server.

Never defines a route handler. Never runs a query. Never creates schema. An entry point that
holds two admin endpoints and a `DELETE` statement is the first thing to fix, because
it is the clearest possible statement that layers are not being respected.

## Dependency direction

Dependencies point inward, toward the domain:

```
entry surface → controllers → services → models → (persistence)
      ↑               ↑            ↑         ↑
      └───────────────┴────────────┴─────────┴──  config, middlewares

entry surface = routes (API) · routes + templates (fullstack) · handlers (worker)
```

An import that goes the other way is a boundary violation regardless of how convenient it
is. The practical test: a model should be importable and testable without starting a web
server or connecting to a broker, and without the framework installed at all in principle.

## Reference layouts

The shape adapts to the stack's conventions. These are starting points, not quotas — a
project with two entities does not need twelve files.

**Python / Flask**

```
src/
├── config/settings.py            environment-driven configuration
├── models/<entity>_model.py      one module per entity
├── views/routes.py               blueprints: path → controller
├── controllers/<entity>_controller.py
├── services/<concern>_service.py when logic spans entities or calls outward
├── middlewares/error_handler.py  centralized error handling
└── app.py                        composition root
```

**Node / Express**

```
src/
├── config/index.js
├── models/<entity>.model.js
├── routes/<entity>.routes.js
├── controllers/<entity>.controller.js
├── services/<concern>.service.js
├── middlewares/errorHandler.js
└── app.js / server.js            composition root
```

**Worker / consumer**

```
src/
├── config/index.*
├── handlers/<topic>.handler.*     subscription → controller, one per topic or job
├── controllers/<usecase>.*        flow for one job, including the transaction boundary
├── models/, services/            unchanged — these layers do not care how work arrived
├── middlewares/                   retry, dead-letter, idempotency, logging
└── worker.*                       composition root: subscribe, inject, start consuming
```

A project that already uses the framework's idiomatic layout (Flask blueprints in
`routes/`, Django apps, NestJS modules) keeps it. Renaming `routes/` to `views/` to match
the example above buys nothing and risks breaking imports; what matters is that the layer
exists, owns only its own concern, and that controllers exist as a distinct layer.

## Adapting to the starting point

The target is the same for every project. What changes is the distance to it, and therefore
which transformations apply:

- **Monolith, no layers.** The work is decomposition: split by responsibility first, then by
  entity. Expect every layer to be created from scratch.
- **One god class.** Extract routes out first so the application still boots, then controllers,
  then models. Moving in that order keeps the app runnable between steps, which matters
  because a refactor you cannot test halfway through is a refactor you cannot debug.
- **Partially layered.** The directories exist; the violations are placement and duplication.
  The work is adding the missing layer (usually controllers), moving rules out of routes and
  models into their proper homes, and deleting duplicate implementations in favour of the one
  that stays. Keep the layers that already work.

In all three cases the same question decides whether the refactor is done: for each rule in the
system, is there exactly one place that owns it, and is that place the layer whose job it is?

## Non-negotiables

These come straight from the validation checklist, and each is verifiable by reading the
result rather than by asserting it:

- Directory structure reflects MVC layers.
- Configuration extracted to a config module, with no secret left as a literal.
- Models abstract the data.
- Views/Routes separated from the logic they delegate to.
- Controllers concentrate application flow.
- Error handling centralized rather than repeated per handler.
- A clear entry point that only composes.
- The application starts without errors.
- Every input the application handled before is still handled, with the same contract —
  endpoints for an API or fullstack app, message and schedule handlers for a worker.

The last two are the ones that fail silently. `refactoring-playbook.md` covers how to verify
them instead of assuming them.
