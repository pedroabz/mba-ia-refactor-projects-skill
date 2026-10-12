# Playbook — security transformations

T-01 to T-05. Examples are illustrative shapes, not templates to paste: match the project's
language, style and framework idioms.

---

## T-01 — Extract configuration and secrets

Fixes SEC-01, SEC-06, LAY-06. Do this first: it has no dependencies and unblocks the rest.

**Before**

```python
app = Flask(__name__)
app.config["SECRET_KEY"] = "minha-chave-super-secreta-123"
app.config["DEBUG"] = True
...
app.run(host="0.0.0.0", port=5000, debug=True)
```

**After**

```python
# config/settings.py
import os

class Settings:
    SECRET_KEY = os.environ["SECRET_KEY"]          # required: fail fast if absent
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    HOST = os.getenv("HOST", "127.0.0.1")
    PORT = int(os.getenv("PORT", "5000"))
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///local.db")

settings = Settings()
```

```python
# app.py (composition root)
from config.settings import settings

app.config["SECRET_KEY"] = settings.SECRET_KEY
app.config["DEBUG"] = settings.DEBUG
app.run(host=settings.HOST, port=settings.PORT, debug=settings.DEBUG)
```

Node equivalent: a `config/index.js` exporting a frozen object read from `process.env`, with
the same required-vs-defaulted split.

**Steps**

1. Create the config module; read from the environment.
2. Secrets are **required** — no default. A missing secret should stop the boot, not fall back
   to a known value, because a default secret in production is the original bug again.
3. Non-secret settings get development-safe defaults (`DEBUG` off, `HOST` loopback).
4. Replace every literal with a config read.
5. Write `.env.example` with the variable names and no values, and ensure `.env` is ignored.
6. Rotate anything that was committed — say so in the report; the old value is in git history
   and the extraction does not undo that.

---

## T-02 — Parameterize queries

Fixes SEC-03. Apply to every call site in one pass: a partially parameterized model is still
injectable and harder to audit than either extreme.

**Before**

```python
cursor.execute("SELECT * FROM produtos WHERE id = " + str(id))

cursor.execute(
    "SELECT * FROM usuarios WHERE email = '" + email + "' AND senha = '" + senha + "'"
)
```

**After**

```python
cursor.execute("SELECT id, nome, preco FROM produtos WHERE id = ?", (id,))

cursor.execute("SELECT id, nome, email FROM usuarios WHERE email = ?", (email,))
# password verified in application code against a stored hash — see T-03
```

Dynamic filters stay parameterized by building the clause list, never the values:

```python
clauses, params = ["1=1"], []
if termo:
    clauses.append("(nome LIKE ? OR descricao LIKE ?)")
    params += [f"%{termo}%", f"%{termo}%"]        # the pattern is data, not SQL
if categoria:
    clauses.append("categoria = ?")
    params.append(categoria)

cursor.execute(f"SELECT * FROM produtos WHERE {' AND '.join(clauses)}", params)
```

The f-string here interpolates only clause fragments the code itself authored. Every
caller-supplied value travels in `params`.

**Steps**

1. Replace concatenation with placeholders; pass values as parameters.
2. Never parameterize identifiers (table or column names) — those must come from an allowlist
   the code owns, since placeholders cannot bind them.
3. Where an endpoint exists to execute caller-supplied SQL, the fix is removal, not
   parameterization. Replace it with specific endpoints for the operations it was used for,
   and note the removal in the report as an intentional contract change.

---

## T-03 — Replace broken password storage

Fixes SEC-04. This changes behaviour by design: existing stored passwords stop validating.

**Before**

```python
def set_password(self, pwd):
    self.password = hashlib.md5(pwd.encode()).hexdigest()

def check_password(self, pwd):
    return self.password == hashlib.md5(pwd.encode()).hexdigest()
```

**After**

```python
from werkzeug.security import generate_password_hash, check_password_hash

def set_password(self, pwd):
    self.password_hash = generate_password_hash(pwd)   # salted, tunable cost

def check_password(self, pwd):
    return check_password_hash(self.password_hash, pwd)
```

Node: `bcrypt.hash(pwd, 12)` and `bcrypt.compare(pwd, hash)`. Prefer a KDF the framework
already ships over adding a dependency.

**Steps**

1. Use a password KDF — bcrypt, scrypt, argon2, or PBKDF2 with a real cost. Not a bare digest.
2. Rename the column to `password_hash` so the field no longer claims to be a password.
3. Fix every write path, including seeds and fixtures that bypassed the hashing function.
4. Compare with the library's verify function, never with `==`.
5. Enforce a sane minimum length at the boundary (T-15).
6. Report that stored credentials are invalidated and seeded users must be re-seeded.

---

## T-04 — Remove sensitive fields from serialization

Fixes SEC-02. Fix the serializer, not each endpoint — the leak is centralized, so the fix can
be too.

**Before**

```python
def to_dict(self):
    return {
        "id": self.id, "name": self.name, "email": self.email,
        "password": self.password,            # leaks from every endpoint that serializes
        "role": self.role,
    }
```

**After**

```python
def to_dict(self):
    """Public representation. Never include credentials: every endpoint
    that returns a user goes through here."""
    return {
        "id": self.id, "name": self.name, "email": self.email,
        "role": self.role, "active": self.active,
    }
```

Logs follow the same rule — log identifiers, never values:

```python
logger.info("checkout processed", extra={"user_id": user.id, "order_id": order.id})
# not: the card number, the gateway key, or the request body
```

**Steps**

1. Remove credential, token and secret fields from every serializer.
2. Audit each serializer's callers to confirm nothing depended on the removed field.
3. Strip secrets from diagnostic endpoints — a health check reports liveness, not configuration.
4. Replace logged secrets with identifiers; where a value must be traceable, log a prefix or
   a hash.
5. Keep the response shape otherwise identical, so the baseline replay stays meaningful.

---

## T-05 — Add an access-control guard

Fixes SEC-05. Enforce in one place; a per-handler check is the thing that gets forgotten.

**Before**

```python
@app.route("/admin/reset-db", methods=["POST"])
def reset_database():
    db = get_db()                      # no authentication, no authorization
    ...
```

**After**

```python
# middlewares/auth.py
from functools import wraps
from flask import request, jsonify, g

def require_role(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = authenticate(request)          # verify the token, don't trust it
            if user is None:
                return jsonify({"error": "unauthorized"}), 401
            if roles and user.role not in roles:
                return jsonify({"error": "forbidden"}), 403
            g.current_user = user
            return fn(*args, **kwargs)
        return wrapper
    return decorator
```

```python
# views/routes.py
@admin_bp.route("/admin/reset-db", methods=["POST"])
@require_role("admin")
def reset_database():
    return admin_controller.reset_database()
```

Express equivalent: `router.post('/admin/reset', requireRole('admin'), controller.reset)`.

**Steps**

1. Decide the model: who may call what. Deny by default.
2. Implement authentication that actually verifies — a token that is issued and never checked
   provides nothing. If the project issues a placeholder token, replace it with a signed token
   or state plainly in the report that authentication is unimplemented.
3. Apply the guard at the route layer so the controller cannot be reached unguarded.
4. Add ownership checks where a caller may only touch their own resources; role alone is not
   enough for per-resource access.
5. Report the intentional contract change: guarded endpoints now return 401/403 where they
   previously returned 200.
