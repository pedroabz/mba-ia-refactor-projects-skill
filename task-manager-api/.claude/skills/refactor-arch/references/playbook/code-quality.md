# Playbook — code quality transformations

T-19 to T-24. Apply last: cheap, low risk, and genuinely easier once the code sits in its
final location. T-19 is the exception — it often carries the highest practical value in the
whole refactor.

---

## T-19 — Collapse duplicated rules to one owner

Fixes QUA-01. Where an abandoned abstraction already exists, this is deletion, not writing.

**Before** — the overdue rule reimplemented in six places while the model method that
implements it is never called:

```python
# models/task.py — defined, never used
def is_overdue(self):
    if self.due_date:
        if self.due_date < datetime.utcnow():
            if self.status != 'done' and self.status != 'cancelled':
                return True
    return False

# routes/task_routes.py, twice; routes/user_routes.py; routes/report_routes.py, twice
if t.due_date:
    if t.due_date < datetime.utcnow():
        if t.status != 'done' and t.status != 'cancelled':
            task_data['overdue'] = True
        else:
            task_data['overdue'] = False
    else:
        task_data['overdue'] = False
else:
    task_data['overdue'] = False
```

**After** — one owner, called everywhere:

```python
# models/task.py
TERMINAL_STATUSES = frozenset({"done", "cancelled"})

@property
def is_overdue(self) -> bool:
    """Single owner of the overdue rule: every caller goes through here,
    so changing the definition is a one-line change."""
    if self.due_date is None or self.status in TERMINAL_STATUSES:
        return False
    return self.due_date < datetime.now(timezone.utc)

def to_dict(self):
    return {..., "overdue": self.is_overdue}
```

```python
# every call site
task_data["overdue"] = t.is_overdue
```

**Steps**

1. Choose the owner: the entity for an entity rule, a service for a cross-entity rule.
2. Where an unused implementation already exists, fix it and call it rather than writing a
   third version.
3. Replace every copy with a call. Grep for the pattern, not just the obvious sites — the
   count is usually higher than expected.
4. Where copies disagree, decide which behaviour is correct and say so in the report: this
   changes behaviour at the sites that were wrong, and that is the point.
5. Delete the duplicates. Leaving one behind guarantees it drifts again.
6. Replay the baseline — if a drifted copy was feeding a response, the output legitimately
   changes, and the report must declare it.

---

## T-20 — Name the constants

Fixes QUA-03.

**Before**

```python
if faturamento > 10000:   desconto = faturamento * 0.1
elif faturamento > 5000:  desconto = faturamento * 0.05
if len(nome) < 2 or len(nome) > 200: ...
```

**After**

```python
# domain constants live next to the rule that uses them
DISCOUNT_TIERS = (
    (Decimal("10000"), Decimal("0.10")),
    (Decimal("5000"),  Decimal("0.05")),
    (Decimal("1000"),  Decimal("0.02")),
)
NOME_MIN_LENGTH, NOME_MAX_LENGTH = 2, 200
```

**Steps**

1. Name the value where its meaning lives — domain thresholds with the rule, deployment
   values in config (T-01).
2. Collapse repeated literals for one concept into a single constant; a version string or
   path duplicated across modules is the common case.
3. Leave conventional `0`, `1`, `-1` alone. Renaming them adds noise, not meaning.
4. Where the constant is a policy that varies by environment, it belongs in config, not here.

---

## T-21 — Delete dead code

Fixes QUA-02.

**Before**

```python
import json, os, sys, time          # none used
from utils.helpers import format_date, calculate_percentage   # neither called
```

**After**

```python
from datetime import datetime, timezone    # what the module actually uses
```

**Steps**

1. Remove unused imports, functions, constants and parameters. Verify with a grep for each
   name before deleting — dynamic references and framework-by-convention hooks exist.
2. Drop declared dependencies nothing imports; note in the report what each was presumably
   for, since an unused validation library is the fix for T-15 and an unused dotenv library is
   the fix for T-01.
3. Where an entire module is dead, check first whether its logic is duplicated elsewhere. If
   so, T-19 comes first: adopt the abstraction, then delete the copies. Deleting the unused
   module and keeping six copies is the wrong direction.
4. Remove columns and flags that are written and never read — or start using them, if the
   feature they imply is the actual intent (an unused `active` flag beside a physical delete).
5. Do this after the structural work; moving code reveals more dead code than reading it does.

---

## T-22 — Rename for intent

Fixes QUA-04.

**Before**

```javascript
let u = req.body.usr, e = req.body.eml, p = req.body.pwd, cid = req.body.c_id, cc = req.body.card;
```

```python
cursor2 = db.cursor(); cursor3 = db.cursor()
def buscar_produto(id): ...        # shadows the builtin
```

**After**

```javascript
const { name, email, password, courseId, cardNumber } = req.validated;
```

```python
cursor_itens = conn.cursor(); cursor_produto = conn.cursor()
def buscar_produto(produto_id): ...
```

**Steps**

1. Name by intent, not mechanism. `cursor_itens` beats `cursor2`.
2. Avoid shadowing builtins; prefer the qualified domain name (`produto_id` over `id`).
3. Expand abbreviations in the public API contract — a caller should not have to guess that
   `eml` is an email. This changes the request contract, so declare it in the report.
4. Sequentially numbered names usually mean the block should be extracted. Prefer the
   extraction (T-07, T-12) over a better name for the same tangle.
5. Keep renames mechanical and separate from logic changes, so the baseline diff stays readable.

---

## T-23 — Replace ad-hoc printing with logging

Fixes QUA-05.

**Before**

```python
print("Produto criado com ID: " + str(id))
print("ERRO ao criar produto: " + str(e))
```

**After**

```python
# config/logging.py
import logging, sys

def configure_logging(level: str):
    logging.basicConfig(
        level=level, stream=sys.stdout,
        format='{"ts":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","msg":"%(message)s"}',
    )
```

```python
logger = logging.getLogger(__name__)

logger.info("produto criado", extra={"produto_id": produto.id})
logger.exception("falha ao criar produto")      # stack trace, server-side only
```

**Steps**

1. Configure logging once in the composition root; level comes from config.
2. Replace prints with the appropriate level: `debug`, `info`, `warning`, `error`,
   `exception`.
3. Log identifiers and structured fields, never secrets, credentials or full request bodies.
4. Split functions that both log and do something else — the conflation is usually visible in
   the name.
5. Leave deliberate CLI output alone: in a command-line tool, stdout is the interface.

---

## T-24 — Modernize a deprecated API

Fixes DEP-01. Confirm status against the pinned version first (`deep/deprecated-apis.md`).

**Before**

```python
created_at = db.Column(db.DateTime, default=datetime.utcnow)     # deprecated in 3.12
...
if self.due_date < datetime.utcnow():
```

**After**

```python
from datetime import datetime, timezone

def utcnow() -> datetime:
    """Single source for the current time: one place to change, and tests can patch it."""
    return datetime.now(timezone.utc)

created_at = db.Column(db.DateTime(timezone=True), default=utcnow)
...
if self.due_date < utcnow():
```

**Steps**

1. Verify the replacement exists in the pinned version before using it.
2. Replace every call site in one pass; a half-migrated API is harder to reason about than
   either state.
3. Prefer a single wrapper where the call appears many times — it makes the next migration a
   one-line change, and it makes time patchable in tests.
4. Watch for semantic differences, not just naming. `utcnow()` returns a naive datetime and
   `now(timezone.utc)` returns an aware one; mixing the two raises on comparison. If stored
   values are naive, either migrate the column to timezone-aware or keep the comparison
   consistent — this is the one step in this transformation that can break the application.
5. Replay the baseline: timestamp representation in responses may gain an offset suffix.
