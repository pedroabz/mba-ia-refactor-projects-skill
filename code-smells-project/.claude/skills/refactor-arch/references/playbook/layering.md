# Playbook — layering transformations

T-06 to T-09. These are the transformations the challenge is really about. Read
`architecture-guidelines.md` for the target before applying them.

---

## T-06 — Split a god file into MVC layers

Fixes LAY-01, LAY-05. The largest transformation; do it as pure relocation, then fix logic
separately. Combining a move with a rewrite means a failure gives you two suspects.

**Before** — one class owning schema, routing, rules and persistence:

```javascript
class AppManager {
    constructor() { this.db = new sqlite3.Database(':memory:'); }
    initDb() { this.db.run("CREATE TABLE users (...)"); /* + seeds */ }
    setupRoutes(app) {
        app.post('/api/checkout', (req, res) => {
            // validation, payment rule, 3 inserts, response — all inline
        });
    }
}
```

**After** — one responsibility per module:

```
src/
├── config/index.js
├── models/user.model.js          persistence + entity invariants
├── models/enrollment.model.js
├── services/payment.service.js   external integration
├── controllers/checkout.controller.js   use-case flow
├── routes/checkout.routes.js     path → controller
├── middlewares/errorHandler.js
└── app.js                        composition root only
```

```javascript
// routes/checkout.routes.js — declares the contract, delegates
router.post('/checkout', validateCheckout, checkoutController.create);

// controllers/checkout.controller.js — sequences the use case
async function create(req, res, next) {
    try {
        const result = await checkoutService.purchase(req.validated);
        res.status(201).json(result);
    } catch (err) { next(err); }
}

// app.js — composes and nothing else
app.use(express.json({ limit: '100kb' }));
app.use('/api', checkoutRoutes);
app.use(errorHandler);
```

**Steps**

1. Create the directory structure first, empty.
2. Move the schema and seeds out of the application into a migration or an explicit
   initialization module the entry point calls once.
3. Extract routes: move each handler body into a controller function, leave the route as one
   line of delegation. Boot the app and replay the baseline here — this is the checkpoint that
   catches import mistakes while there are few of them.
4. Extract persistence from the controllers into models, one module per entity.
5. Extract external integrations into services.
6. Reduce the entry point to config, dependency construction, middleware, routes, listen.
7. Boot and replay again before touching any logic.

---

## T-07 — Extract a controller from a route

Fixes LAY-02. The smaller, more common version of T-06.

**Before** — rules and side effects inline in the handler:

```python
def criar_pedido():
    dados = request.get_json()
    ...
    resultado = models.criar_pedido(usuario_id, itens)
    print("ENVIANDO EMAIL: Pedido " + str(resultado["pedido_id"]))
    print("ENVIANDO SMS: Seu pedido foi recebido!")
    return jsonify({"dados": resultado, "sucesso": True}), 201
```

**After** — the route declares, the controller sequences, the service owns the mechanism:

```python
# views/routes.py
pedido_bp.add_url_rule("/pedidos", view_func=pedido_controller.criar, methods=["POST"])

# controllers/pedido_controller.py
def criar():
    payload = validate_pedido(request.get_json())        # T-15
    pedido = pedido_service.criar(payload)               # rules live here
    notification_service.pedido_criado(pedido)           # side effect behind a port
    return jsonify(pedido.to_dict()), 201
```

```python
# services/notification_service.py
class NotificationService:
    def __init__(self, mailer, logger):      # injected, so it can be faked in a test
        self._mailer, self._logger = mailer, logger

    def pedido_criado(self, pedido):
        self._mailer.send(pedido.usuario.email, "Pedido recebido", render(pedido))
        self._logger.info("pedido criado", extra={"pedido_id": pedido.id})
```

**Steps**

1. Move the handler body to a controller function; leave routing behind.
2. Move domain rules down into a model or service — whichever owns them.
3. Put side effects behind a service interface so the controller states *what* happens and the
   service owns *how*.
4. Keep the status code and response shape in the controller; that part is genuinely HTTP.

---

## T-08 — Move domain rules to their owner

Fixes LAY-03. The mirror of T-07, and the one more often missed.

**Before** — a reporting rule inside the data layer:

```python
def relatorio_vendas():
    cursor.execute("SELECT SUM(total) FROM pedidos")
    faturamento = cursor.fetchone()[0] or 0

    desconto = 0                                  # policy, not persistence
    if faturamento > 10000:   desconto = faturamento * 0.1
    elif faturamento > 5000:  desconto = faturamento * 0.05
    elif faturamento > 1000:  desconto = faturamento * 0.02
    return { "faturamento_bruto": faturamento, "desconto_aplicavel": desconto, ... }
```

**After** — persistence returns data, the rule lives once and is named:

```python
# models/pedido_model.py
def faturamento_total() -> Decimal:
    return db.session.scalar(select(func.coalesce(func.sum(Pedido.total), 0)))

# services/pricing.py
DISCOUNT_TIERS = ((10_000, Decimal("0.10")), (5_000, Decimal("0.05")), (1_000, Decimal("0.02")))

def desconto_por_faturamento(faturamento: Decimal) -> Decimal:
    for limite, taxa in DISCOUNT_TIERS:
        if faturamento > limite:
            return faturamento * taxa
    return Decimal(0)

# controllers/relatorio_controller.py
def vendas():
    faturamento = pedido_model.faturamento_total()
    desconto = pricing.desconto_por_faturamento(faturamento)
    return jsonify(build_report(faturamento, desconto)), 200
```

The tiers became a named constant on the way out, which is T-20 for free.

**Steps**

1. Identify the rule and ask which entity owns it. If none does, it belongs in a service.
2. Move the rule; leave the query behind.
3. Remove response-shaped dictionaries from the data layer — models return entities or
   values, controllers shape responses.
4. Make the model function return a value rather than a serialized payload.

---

## T-09 — Inject dependencies, remove global state

Fixes LAY-04. The transformation that makes everything else testable.

**Before** — module-level connection, constructed where used, shared across threads:

```python
db_connection = None

def get_db():
    global db_connection
    if db_connection is None:
        db_connection = sqlite3.connect("loja.db", check_same_thread=False)
    return db_connection
```

**After** — created once by the composition root, handed to whoever needs it:

```python
# infra/database.py
def create_connection(database_url: str):
    conn = sqlite3.connect(database_url)
    conn.row_factory = sqlite3.Row
    return conn

# models/produto_model.py
class ProdutoModel:
    def __init__(self, conn):          # receives the dependency
        self._conn = conn

    def by_id(self, produto_id):
        cur = self._conn.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,))
        return cur.fetchone()

# app.py — the only place that knows how a connection is built
conn = create_connection(settings.DATABASE_URL)
produto_model = ProdutoModel(conn)
produto_controller = ProdutoController(produto_model)
```

Where the framework owns the lifecycle (Flask-SQLAlchemy, request-scoped sessions), use that
instead of hand-rolling: the goal is a dependency the caller does not construct, not DI for
its own sake.

**Steps**

1. Move construction to the composition root.
2. Pass the dependency in through the constructor or function signature.
3. Delete the global and the accessor function.
4. Remove thread-safety overrides — they exist to make a shared mutable object tolerable, and
   the sharing is what is being fixed.
5. Give caches an explicit owner, a bound and an invalidation rule, or delete them.
6. Replace a mutable exported value with a function call, since importers of a mutable
   primitive get a copy and never see updates.
