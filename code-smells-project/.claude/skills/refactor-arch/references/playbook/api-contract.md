# Playbook — API contract transformations

T-14 to T-18. Apply after the structure is stable: these all assume a controller layer exists.

**The key names and message text in these examples are placeholders.** They read `error`,
`details`, `invalid request` because this file is written in English. In a project whose
contract uses `erro`, `dados` and `sucesso`, those are the names to keep — see "Never
translate the application" in `refactoring-playbook.md`. Every transformation here is about
*where* the response is produced and whether its shape is consistent; none of them is about
renaming fields or rewriting messages. Renaming a response key breaks every client, and the
baseline replay will correctly report it as a regression.

---

## T-14 — Centralize error handling

Fixes API-02. Doing this first makes T-15 to T-18 much smaller, because handlers stop needing
their own try/except.

**Before** — the same block repeated in every handler, leaking internals:

```python
def listar_produtos():
    try:
        ...
    except Exception as e:
        print("ERRO: " + str(e))
        return jsonify({"erro": str(e)}), 500      # driver message to the client
```

**After** — handlers raise, one place answers:

```python
# middlewares/error_handler.py
class AppError(Exception):
    status = 500
    message = "internal error"

class NotFound(AppError):      status, message = 404, "resource not found"
class ValidationError(AppError): status, message = 400, "invalid request"
class Forbidden(AppError):     status, message = 403, "forbidden"

def register_error_handlers(app, logger):
    @app.errorhandler(AppError)
    def handle_app_error(err):
        logger.warning("handled error", extra={"type": type(err).__name__})
        return jsonify({"error": err.message, "details": err.details}), err.status

    @app.errorhandler(Exception)
    def handle_unexpected(err):
        logger.exception("unhandled error")        # full detail server-side
        return jsonify({"error": "internal error"}), 500   # nothing leaked client-side
```

```python
# controllers/produto_controller.py
def buscar(produto_id):
    produto = produto_model.by_id(produto_id)
    if produto is None:
        raise NotFound()                            # no try/except needed
    return jsonify(produto.to_dict()), 200
```

Express: `app.use((err, req, res, next) => {...})` registered **after** the routes, with
handlers calling `next(err)`.

**Steps**

1. Define an error type hierarchy carrying a status and a client-safe message.
2. Register one handler for known errors and one catch-all for the rest.
3. Log the detail server-side; return a generic message for unexpected errors.
4. Delete the per-handler try/except blocks and raise instead.
5. Replace bare `except:` / empty `catch` with either a targeted catch or a re-raise. Never
   inspect nothing — an ignored error argument is how a `TypeError` became a hung request.
6. Keep the status codes the baseline recorded, so this stays a structural change.

---

## T-15 — Validate at the boundary

Fixes API-03.

**Before** — presence checks only, duplicated between create and update, drifted:

```python
if not dados:                    return jsonify({"erro": "Dados inválidos"}), 400
if "nome" not in dados:          return jsonify({"erro": "Nome é obrigatório"}), 400
if preco < 0:                    return jsonify({"erro": "Preço negativo"}), 400
# create checks categoria against a list; update forgot to
```

**After** — one schema, declared once, used by both paths:

```python
# views/schemas.py
from marshmallow import Schema, fields, validate

CATEGORIAS = ("informatica", "moveis", "vestuario", "geral", "eletronicos", "livros")

class ProdutoSchema(Schema):
    nome      = fields.Str(required=True, validate=validate.Length(min=2, max=200))
    descricao = fields.Str(load_default="")
    preco     = fields.Decimal(required=True, validate=validate.Range(min=0))
    estoque   = fields.Int(required=True, validate=validate.Range(min=0))
    categoria = fields.Str(load_default="geral", validate=validate.OneOf(CATEGORIAS))

class ProdutoPatchSchema(ProdutoSchema):
    class Meta: partial = True        # same rules, nothing required — no second copy
```

```python
# controllers/produto_controller.py
def criar():
    try:
        data = ProdutoSchema().load(request.get_json() or {})
    except MarshmallowError as err:
        raise ValidationError(details=err.messages)
    produto = produto_model.create(**data)
    return jsonify(produto.to_dict()), 201
```

**Steps**

1. Declare a schema per resource: types, ranges, lengths, formats, allowed values.
2. Derive the partial/update variant from the same schema rather than writing it again — this
   is what prevents the drift where one path validates and the other does not.
3. Use `is None` for presence, not truthiness, so a legitimate `0` or `""` is accepted.
4. Return 400 with field-level detail; let the error handler format it.
5. Never silently default a security-relevant field — a missing password is an error, not a
   reason to assign a known one.
6. If the project already declares a validation library it never imported, use that one.

---

## T-16 — Add the middleware chain

Fixes API-04, and the configuration half of SEC-06.

**Before**

```javascript
const app = express();
app.use(express.json());       // the entire chain
```

**After**

```javascript
// app.js — composition root
app.use(helmet());                                   // security headers
app.use(cors({ origin: config.allowedOrigins }));    // explicit, not wildcard
app.use(express.json({ limit: '100kb' }));           // bounded body
app.use(requestLogger(logger));

app.use('/api/checkout', rateLimit({ windowMs: 60_000, max: 10 }));  // card testing
app.use('/api/admin', requireRole('admin'));         // guard the whole subtree

app.use('/api', routes);
app.use(notFoundHandler);
app.use(errorHandler);                               // last: errors land here
```

Flask equivalent: `before_request` hooks, a CORS resource map, `MAX_CONTENT_LENGTH` in config,
and a rate-limit extension applied per blueprint.

**Steps**

1. Order matters: security headers → CORS → body parsing (bounded) → logging → auth →
   routes → 404 → error handler. The error handler is registered last or it never runs.
2. Scope rate limits to the endpoints that need them — authentication, payment, search,
   anything destructive.
3. Replace wildcard CORS with an explicit origin list from config.
4. Set a request body limit; the default is usually generous.
5. Move anything copy-pasted into every handler into the chain.

---

## T-17 — Normalize the response contract

Fixes API-05.

**Before** — text on failure, JSON on success, from the same endpoint:

```javascript
if (!u || !e || !cid || !cc) return res.status(400).send("Bad Request");
if (!course)                 return res.status(404).send("Curso não encontrado");
return res.status(200).json({ msg: "Sucesso", enrollment_id: enrId });
```

**After** — one shape, always parseable:

```javascript
// success
res.status(201).json({ id: enrollment.id, courseId, amount });

// failure — produced only by the error handler
res.status(400).json({ error: 'invalid request', details: { card: 'required' } });
```

**Steps**

1. Adopt the convention the project already uses in most of its handlers, and apply it to the
   rest — do not invent a new one. If the majority of responses are `{"dados": …,
   "sucesso": true}` with `{"erro": …}` on failure, that is the convention: the fix is making
   the outliers match, keeping those key names. Record it in the project README.
2. Never return plain text where JSON is the contract.
3. Fix status codes that misreport the outcome: 404 for missing, 201 for created, 204 for
   deleted, 409 for conflict, 400 for client validation failure, 401/403 for auth. Verify the
   current code before changing it — most projects get creation right and a few handlers wrong,
   and rewriting the correct ones adds risk for nothing.
4. Returning success for an operation that did not happen is a bug, not a convention: check
   existence before reporting a successful update or delete.
5. Each change here is visible in the baseline replay. Keep the list and declare it in the
   completion report as intentional.

---

## T-18 — Replace hand-rolled async coordination

Fixes API-01. The riskiest transformation in the playbook — it changes control flow, so replay
the baseline immediately after.

**Before** — manual counters deciding when to respond; one skipped decrement hangs the request:

```javascript
let coursesPending = courses.length;
courses.forEach(c => {
    this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
        let enrPending = enrollments.length;        // throws if err — nothing ever decrements
        enrollments.forEach(enr => {
            this.db.get(..., (err, user) => {
                this.db.get(..., (err, payment) => {
                    if (--enrPending === 0) {
                        report.push(courseData);
                        if (--coursesPending === 0) res.json(report);
                    }
                });
            });
        });
    });
});
```

**After** — the language's own coordination; errors propagate instead of stalling:

```javascript
// controllers/report.controller.js
async function financialReport(req, res, next) {
    try {
        const report = await reportService.financialReport();
        res.json(report);                     // exactly one response
    } catch (err) {
        next(err);                            // T-14 answers
    }
}

// services/report.service.js
async function financialReport() {
    const rows = await db.all(FINANCIAL_REPORT_SQL);   // T-12 removed the N+1 as well
    return groupByCourse(rows);                        // deterministic order
}
```

Where genuinely independent work must run concurrently, use the structured primitive —
`Promise.all` / `asyncio.gather` — never a counter.

**Steps**

1. Promisify or replace the callback API; most drivers ship a promise interface.
2. Rewrite the handler as linear `async`/`await`. The nesting disappears, which is the
   readability finding fixed as a side effect.
3. Delete every manual counter and completion flag.
4. Ensure exactly one response per path, and that errors reach the error handler.
5. Add an explicit ordering to anything the old code ordered by completion timing — otherwise
   the response order changes and the baseline diff will show it.
6. Replay the baseline before moving on. This transformation is where a silent contract change
   is most likely.
