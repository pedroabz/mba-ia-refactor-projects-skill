# Playbook — data access transformations

T-10 to T-13.

---

## T-10 — Wrap a multi-write operation in a transaction

Fixes DAT-01, DAT-02. Confirm the driver's default behaviour first (see
`deep/data-access.md`) so the fix addresses a real gap.

**Before** — three writes, no boundary, no rollback, and an early return between them:

```javascript
this.db.run("INSERT INTO enrollments (user_id, course_id) VALUES (?, ?)", [userId, cid], function(err) {
    if (err) return res.status(500).send("Erro Matrícula");
    const enrId = this.lastID;
    self.db.run("INSERT INTO payments (enrollment_id, amount, status) VALUES (?, ?, ?)", [...], function(err) {
        if (err) return res.status(500).send("Erro Pagamento");   // enrollment already committed
        self.db.run("INSERT INTO audit_logs (action, created_at) VALUES (?, datetime('now'))", [...]);
    });
});
```

**After** — one unit of work, committed once, rolled back on any failure:

```javascript
// services/checkout.service.js
async function purchase({ userId, courseId, amount, status }) {
    const tx = await db.begin();
    try {
        const enrollment = await tx.enrollments.create({ userId, courseId });
        await tx.payments.create({ enrollmentId: enrollment.id, amount, status });
        await tx.auditLogs.create({ action: `checkout ${courseId} by ${userId}` });
        await tx.commit();
        return enrollment;
    } catch (err) {
        await tx.rollback();
        throw err;                      // the error handler owns the response (T-14)
    }
}
```

Python with an ORM session:

```python
def criar_pedido(usuario_id, itens):
    try:
        with db.session.begin():                 # commits on exit, rolls back on raise
            pedido = Pedido(usuario_id=usuario_id, status="pendente")
            db.session.add(pedido)
            for item in itens:
                produto = reservar_estoque(item)   # raises if insufficient
                db.session.add(ItemPedido(pedido=pedido, produto=produto, ...))
        return pedido
    except EstoqueInsuficiente:
        raise                                     # nothing was written
```

**Steps**

1. Identify the business operation's full extent — first write to last.
2. Move all validation that can fail **before** the first write. An early return between
   writes is the bug, and ordering removes it entirely.
3. Open a transaction, perform the writes, commit once.
4. Roll back on every error path, including the ones that currently return a response.
5. Raise rather than respond from inside the transaction; let the error handler answer.
6. Where a shared long-lived connection exists, fix that too (T-09) — an abandoned
   transaction on a shared connection gets committed by the next unrelated request.

---

## T-11 — Make deletes preserve integrity

Fixes DAT-03.

**Before** — children left pointing at a deleted parent, acknowledged in the response:

```javascript
app.delete('/api/users/:id', (req, res) => {
    this.db.run("DELETE FROM users WHERE id = ?", [req.params.id], (err) => {
        res.send("Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco.");
    });
});
```

**After** — the schema enforces the relationship and the operation is atomic:

```sql
CREATE TABLE enrollments (
    id        INTEGER PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE RESTRICT
);
```

```javascript
// controllers/user.controller.js
async function remove(req, res, next) {
    const deleted = await userService.remove(req.params.id);   // cascade inside one transaction
    if (!deleted) return res.status(404).json({ error: 'user not found' });
    return res.status(204).send();
}
```

**Steps**

1. Decide the policy per relationship: cascade (children are meaningless alone), restrict
   (deletion must be refused), or set-null (the link is optional).
2. Declare it in the schema with foreign keys. Where the database requires enforcement to be
   enabled per connection, enable it in the connection factory — a declared constraint that is
   never enforced is not a fix.
3. Where the schema cannot change, delete children explicitly inside one transaction (T-10).
4. Consider soft delete instead when history matters; then make reads filter it, and note that
   an existing unused `active`/`deleted` column is evidence this was the original intent.
5. Return 404 for a missing resource and 204 for a successful delete — not 200 with a message
   describing the bug.

---

## T-12 — Collapse an N+1 into one query

Fixes DAT-04.

**Before** — 1 + N + 2·M queries to build a report:

```javascript
this.db.all("SELECT * FROM courses", [], (err, courses) => {
    courses.forEach(c => {
        this.db.all("SELECT * FROM enrollments WHERE course_id = ?", [c.id], (err, enrollments) => {
            enrollments.forEach(enr => {
                this.db.get("SELECT name, email FROM users WHERE id = ?", [enr.user_id], ...);
                this.db.get("SELECT amount, status FROM payments WHERE enrollment_id = ?", [enr.id], ...);
            });
        });
    });
});
```

**After** — one query, grouped in memory:

```javascript
const rows = await db.all(`
    SELECT c.id AS course_id, c.title, u.name AS student,
           p.amount, p.status
      FROM courses c
      LEFT JOIN enrollments e ON e.course_id = c.id
      LEFT JOIN users       u ON u.id = e.user_id
      LEFT JOIN payments    p ON p.enrollment_id = e.id
     ORDER BY c.id
`);
const report = groupByCourse(rows);          // pure function, trivially testable
```

With an ORM, eager-load instead of hand-writing the join:

```python
tasks = (db.session.query(Task)
         .options(selectinload(Task.user), selectinload(Task.category))
         .all())                              # 3 queries total, not 1 + 2N
```

And prefer an aggregate over counting in Python:

```python
counts = dict(db.session.query(Task.status, func.count()).group_by(Task.status).all())
```

**Steps**

1. Join or eager-load the relations the response needs.
2. Group and shape in application code with a pure function — easy to test, and it keeps the
   query readable.
3. Push counting and summing into the database rather than iterating rows.
4. Select only the columns used (T-13), since the join widens rows.
5. Verify against the baseline: the response must stay identical, including ordering. Add an
   explicit `ORDER BY` — relying on insertion order is how a "pure" refactor changes output.

---

## T-13 — Bound a result set

Fixes DAT-05, DAT-06.

**Before**

```python
cursor.execute("SELECT * FROM produtos")      # every column, every row, forever
rows = cursor.fetchall()
```

**After**

```python
# models/produto_model.py
DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE = 20, 100

def listar(limit=DEFAULT_PAGE_SIZE, offset=0):
    limit = min(max(limit, 1), MAX_PAGE_SIZE)          # clamp: callers don't set policy
    cur = conn.execute(
        "SELECT id, nome, preco, estoque, categoria FROM produtos "
        "ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    )
    return cur.fetchall()
```

```python
# controllers/produto_controller.py
def listar():
    limit = request.args.get("limit", DEFAULT_PAGE_SIZE, type=int)
    offset = request.args.get("offset", 0, type=int)
    items = produto_model.listar(limit, offset)
    total = produto_model.contar()
    return jsonify({"items": [...], "total": total, "limit": limit, "offset": offset}), 200
```

**Steps**

1. Add limit and offset (or a cursor) with a default and a hard maximum. Clamp server-side;
   a client-supplied limit is a request, not an authorization.
2. Always pair pagination with a deterministic `ORDER BY`, or pages overlap and skip rows.
3. Replace `SELECT *` with the columns actually used — this is also what stops a future column
   from leaking into responses.
4. Pagination changes the response shape, which the baseline will flag. Either keep the bare
   array and add headers, or declare the envelope as an intentional change in the report.
   Decide deliberately; do not let the shape change silently.
5. Leave genuinely bounded lookups (statuses, categories) unpaginated — note why, so the next
   reader does not "fix" it.
