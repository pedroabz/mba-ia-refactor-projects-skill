# Manual test plan — ecommerce-api-legacy

Script for validating the refactored application by hand, with no automated suite.
Every case names the audit finding (`../../reports/audit-project-2.md`) it verifies, so a
failure tells you immediately which fix regressed.

**How to use:** run the suites in order. S4 onwards depend on state created by earlier
suites — the *Precondition* column says when. Record outcomes in the table at the end.

All expected values below were observed against the refactored application, not inferred.

---

## 0. Preparation

### Terminal 1 — server

```bash
cd ecommerce-api-legacy
npm install

npm start          # :memory: database, so every restart returns to the seed below
```

Expected on boot — exactly three JSON log lines, then nothing until a request arrives:

```json
{"ts":"…","level":"warn","msg":"using the stub payment gateway","env":"development"}
{"ts":"…","level":"info","msg":"seeded development fixtures","users":2,"courses":2,"enrollments":1}
{"ts":"…","level":"info","msg":"listening","host":"127.0.0.1","port":3100,"env":"development","database":":memory:","paymentDriver":"stub"}
```

**No stack trace.** The default port is **3100**, not 3000: port 3000 is contested by
almost every development server and by containers that publish it. If 3100 is taken too,
run `PORT=<n> npm start` and set `BASE` below to match — nothing else changes.

### Terminal 2 — client

```bash
BASE=http://127.0.0.1:3100
JSON='Content-Type: application/json'

# body + status on one line
req() { curl -s -w '\n[%{http_code}]\n' "$@"; }
# headers only
hdr() { curl -s -D - -o /dev/null "$@"; }
tok() { python3 -c 'import sys,json;print(json.load(sys.stdin)["token"])'; }

ADMIN=$(curl -s -X POST $BASE/api/auth/login -H "$JSON" \
  -d '{"email":"admin@fullcycle.com.br","password":"dev-admin-password"}' | tok)
STUDENT=$(curl -s -X POST $BASE/api/auth/login -H "$JSON" \
  -d '{"email":"leonan@fullcycle.com.br","password":"dev-student-password"}' | tok)

AH="Authorization: Bearer $ADMIN"
SH="Authorization: Bearer $STUDENT"

echo "admin: ${#ADMIN} chars | student: ${#STUDENT} chars"   # both > 80
```

Passwords come from `.env.example` defaults. If you created a `.env` with different
`SEED_*` values, use those.

> **Restarting the server invalidates both tokens.** Outside production, `AUTH_TOKEN_SECRET`
> is generated at random for each process rather than defaulting to a known value, so tokens
> signed by the previous process no longer verify. Any case below that restarts the server
> (S1.*, S10, S11) needs the login block re-run afterwards — a `401 Token inválido ou
> expirado` right after a restart is this, not a failure.

### Initial state (seed)

| Table | Contents |
|---|---|
| `users` | 1 = Leonan (`leonan@fullcycle.com.br`, role `student`), 2 = Admin (`admin@fullcycle.com.br`, role `admin`). Both `pass_hash` are scrypt, `deleted_at` null |
| `courses` | 1 = Clean Architecture (997.0, active), 2 = Docker (497.0, active) |
| `enrollments` | 1 = (user 1, course 1) |
| `payments` | 1 = (enrollment 1, 997.0, `PAID`) |
| `audit_logs` | empty |

Autoincrement ids in this script assume that state. **Restart the server to reset it.**

---

## S1 — Boot and configuration (SEC-01, LAY-06)

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S1.1 | — | `NODE_ENV=production npm start` | Does not start. One line: `configuration error: Missing required environment variable AUTH_TOKEN_SECRET (signs session tokens). Production refuses to start without it; see .env.example.` Exit code 1, **no stack trace** |
| S1.2 | — | `NODE_ENV=production AUTH_TOKEN_SECRET=$(openssl rand -hex 32) npm start` | Does not start. `PAYMENT_DRIVER=stub refuses to run in production: it approves cards without contacting a provider.` The stub cannot reach production even when everything else is configured |
| S1.3 | — | `PORT=abc npm start` | Does not start. `configuration error: Environment variable PORT must be an integer, got "abc"` |
| S1.4 | — | `PORT=3200 npm start` | Starts on 3200 (`"port":3200` in the `listening` line), not on the 3100 default. Proves no port literal survives in application code |
| S1.5 | — | `grep -rniE "pk_live\|senha_super\|admin_master" src/` | No results. The committed gateway key and database password are gone from source |
| S1.6 | — | `grep -rln "process\.env" src/` | Exactly two files, both under `src/config/`. No other module reads the environment |
| S1.7 | — | `test -f .env && echo present` then `git check-ignore -v .env` | If you created one, it is ignored by `.gitignore`. `.env.example` is committed and contains no values |

> Restore the normal server (`npm start`) before continuing.

---

## S2 — Authentication (SEC-04)

The legacy application stored a password for every user and compared one nowhere: the
column was write-only. These cases exist because that path is new.

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S2.1 | server up | `req -X POST $BASE/api/auth/login -H "$JSON" -d '{"email":"admin@fullcycle.com.br","password":"dev-admin-password"}'` | 200, `{"token":"…","expiresInSeconds":3600,"role":"admin"}` |
| S2.2 | — | same for `leonan@fullcycle.com.br` / `dev-student-password` | 200, `"role":"student"` |
| S2.3 | — | wrong password for a real account | 401 `{"error":{"code":"unauthorized","message":"Credenciais inválidas"}}` |
| S2.4 | — | `{"email":"ninguem@teste.com","password":"dev-admin-password"}` | 401, **byte-identical body to S2.3**. An unknown email must not be distinguishable from a wrong password |
| S2.5 | — | `{"email":"admin@fullcycle.com.br"}` (no password) | 400 `validation_error`, `details.password = "é obrigatório"` |
| S2.6 | — | `{"email":"nao-e-email","password":"x"}` | 400, `details.email = "deve ser um e-mail válido"` |
| S2.7 | — | Compare the `token` from two consecutive logins of the same account | Different strings (the payload carries a fresh `exp`). Neither is a stored value |
| S2.8 | — | `T=$(…login…); req $BASE/api/admin/financial-report -H "Authorization: Bearer ${T%?}x"` (last char altered) | 401 `{"code":"unauthorized","message":"Token inválido ou expirado"}`. The HMAC rejects a tampered token |

---

## S3 — Authorization (SEC-05)

All three original routes were anonymous, including an irreversible delete.

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S3.1 | server up | `req $BASE/api/admin/financial-report` | 401 `{"code":"unauthorized","message":"Autenticação necessária"}` |
| S3.2 | — | `req -X DELETE $BASE/api/users/1` | 401, same shape. Nothing is deleted |
| S3.3 | S0 tokens | `req $BASE/api/admin/financial-report -H "$SH"` | 403 `{"code":"forbidden","message":"Acesso negado"}`. A valid token with the wrong role is a different answer from no token |
| S3.4 | — | `req -X DELETE $BASE/api/users/1 -H "$SH"` | 403. Nothing is deleted |
| S3.5 | — | `req $BASE/api/admin/financial-report -H "$AH"` | 200 with the report |
| S3.6 | — | `req $BASE/api/admin/financial-report -H "Authorization: $ADMIN"` (no `Bearer`) | 401. The scheme is required |
| S3.7 | — | `req $BASE/api/admin/financial-report -H "Authorization: Bearer not.a.token"` | 401 `Token inválido ou expirado` |
| S3.8 | — | `grep -n "requireAuth" src/routes/index.js` | The guard appears on the report and the delete, declared at the route — not inside a controller, so no path reaches a controller unguarded |

---

## S4 — Checkout, successful paths (LAY-02, API-05, QUA-04)

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S4.1 | fresh server | `req -X POST $BASE/api/checkout -H "$JSON" -d '{"name":"Guilherme","email":"gui@fullcycle.com.br","password":"senhaforte","courseId":2,"cardNumber":"4111222233334444"}'` | **201**, `{"enrollmentId":2,"courseId":2,"amount":497,"status":"PAID"}` |
| S4.2 | S4.1 | `hdr -X POST …` (same body, new email) | `Location: /api/enrollments/<id>` present |
| S4.3 | after S4.1 | `req -X POST $BASE/api/checkout -H "$JSON" -d '{"usr":"Leonan","eml":"leonan@fullcycle.com.br","pwd":"senhaforte","c_id":1,"card":"4222333344445555"}'` | 201, `{"enrollmentId":3,"courseId":1,"amount":997,"status":"PAID"}`. The deprecated abbreviated field names still work |
| S4.4 | S4.3 | Terminal 1 log | A `warn` line: `"msg":"request used deprecated field names","fields":["usr","eml","pwd","c_id","card"]` |
| S4.5 | S4.3 | Terminal 1 log | `"msg":"checkout completed"` with `enrollmentId`, `courseId`, `userId`, `userCreated:false` — an existing email reuses the account rather than duplicating it |
| S4.6 | — | `req -X POST $BASE/api/checkout -H "$JSON" -d '{"name":"X","email":"x@t.com","password":"senhaforte","courseId":999,"cardNumber":"4111222233334444"}'` | 404 `{"code":"course_not_found","message":"Curso não encontrado"}` |
| S4.7 | — | Card starting with 5: `…"cardNumber":"5111222233334444"` with a valid password | **402** `{"code":"payment_declined","message":"Pagamento recusado"}`. A provider refusal is not a client error (the legacy answer was 400) |

---

## S5 — Checkout, rejected input (API-03, SEC-04)

Every case here returns `400` with `{"error":{"code":"validation_error","message":"Requisição inválida","details":{…}}}`. The table gives the `details` entry to expect.

| ID | Precondition | Action | Expected `details` |
|---|---|---|---|
| S5.1 | server up | `-d '{}'` | All five fields: `name`, `email`, `password`, `courseId`, `cardNumber` → `"é obrigatório"` |
| S5.2 | — | omit `cardNumber` only | `cardNumber: "é obrigatório"` and nothing else |
| S5.3 | — | `"password"` absent | `password: "é obrigatório"` — **never** a 201. The legacy code substituted `"123456"` and created the account |
| S5.4 | — | `"password":"123"` | `password: "deve ter no mínimo 8 caracteres"` |
| S5.5 | — | `"email":"nao-e-um-email"` | `email: "deve ser um e-mail válido"` |
| S5.6 | — | `"courseId":"dois"` | `courseId: "deve ser um número inteiro"` |
| S5.7 | — | `"courseId":0` | `courseId: "deve ser no mínimo 1"` |
| S5.8 | — | `"cardNumber":"4111-2222-3333-4444"` | `cardNumber: "deve conter apenas dígitos"` |
| S5.9 | — | `"cardNumber":"411"` | `cardNumber: "deve ter no mínimo 13 caracteres"` |
| S5.10 | — | `"name":""` | `name: "deve ter no mínimo 1 caracteres"` — presence is tested against `undefined`, so an empty string reaches the length rule rather than being reported as missing |

> After any S5 case, check Terminal 1: there must be **no** `"msg":"checkout completed"` line, and the report in S7 must not grow.

---

## S6 — The process-killing crash path (API-03)

The headline regression test. In the legacy application a single anonymous POST with
`card` as a JSON **number** reached `cc.startsWith(…)` inside a sqlite3 callback; the
TypeError escaped Express as an uncaught exception and terminated the server.

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S6.1 | server up | `req -X POST $BASE/api/checkout -H "$JSON" -d '{"usr":"Tipo Errado","eml":"t@teste.com","pwd":"senhaforte","c_id":1,"card":4111222233334444}'` (note: no quotes around the card) | 400, `details.cardNumber = "deve ser uma string"` |
| S6.2 | S6.1 | `req $BASE/api/admin/financial-report -H "$AH"` | 200. **The server is still running** — this is the whole point |
| S6.3 | S6.1 | Terminal 1 log | A `warn` line for the rejected request. **No** `uncaught exception`, no stack trace, no exit |
| S6.4 | S6.1 | Repeat S6.1 twenty times in a loop, then S6.2 | Still 200. Note that rate limiting (S10) will start answering 429 after 10 in a minute, which is also a pass — the process must stay up either way |

---

## S7 — Financial report (DAT-04, DAT-05, API-01, LAY-03)

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S7.1 | fresh server | `req $BASE/api/admin/financial-report -H "$AH"` | 200, exactly:<br>`[{"course":"Clean Architecture","revenue":997,"students":[{"student":"Leonan","paid":997}]},{"course":"Docker","revenue":0,"students":[]}]`<br>A course with no enrollments keeps `revenue: 0` and an empty list |
| S7.2 | S7.1 | Call it 5 times in a row and compare bodies | **Byte-identical every time**, including order. The legacy version returned the courses in callback-completion order and disagreed with itself between calls |
| S7.3 | after S4.1 + S4.3 | repeat S7.1 | `Clean Architecture` revenue 1994 with two `Leonan` entries (one per enrollment, not deduplicated); `Docker` revenue 497 with `Guilherme` |
| S7.4 | — | `hdr $BASE/api/admin/financial-report -H "$AH"` | `X-Total-Count: 2`, `X-Page-Limit: 50`, `X-Page-Offset: 0`. The body stays a bare array — pagination did not wrap it in an envelope |
| S7.5 | — | `req "$BASE/api/admin/financial-report?limit=1" -H "$AH"` | One course only (`Clean Architecture`), `X-Page-Limit: 1`, `X-Total-Count: 2` |
| S7.6 | — | `req "$BASE/api/admin/financial-report?limit=99999" -H "$AH"` | 200, and `X-Page-Limit: 200` — the server clamps to `REPORT_MAX_PAGE_SIZE`; a client-supplied limit is a request, not an authorization |
| S7.7 | — | `req "$BASE/api/admin/financial-report?offset=50" -H "$AH"` | 200, `[]` |
| S7.8 | — | `req "$BASE/api/admin/financial-report?limit=abc" -H "$AH"` | 400, `details.limit = "deve ser um número inteiro"` |
| S7.9 | — | `req "$BASE/api/admin/financial-report?limit=0" -H "$AH"` | 400, `details.limit = "deve ser no mínimo 1"`. The bounds are deliberately asymmetric: a `limit` below 1 is meaningless and is rejected at the boundary, while a `limit` above the maximum is a legitimate "give me everything" that the server clamps (S7.6) |
| S7.10 | — | `grep -cE "SELECT\|INSERT\|UPDATE\|DELETE" src/controllers/report.controller.js src/services/report.service.js` | 0 in both. All SQL lives in `models/`; the service only groups rows |

For the query-count claim (5 statements regardless of volume) see S12.8 — it is not
observable over HTTP.

---

## S8 — User removal and referential integrity (DAT-03, API-05)

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S8.1 | after S7.3 | `req -X DELETE $BASE/api/users/1 -H "$AH"` | **204**, empty body. The legacy answer was 200 with the sentence `"Usuário deletado, mas as matrículas e pagamentos ficaram sujos no banco."` |
| S8.2 | S8.1 | `req $BASE/api/admin/financial-report -H "$AH"` | `Clean Architecture` revenue still **1994**, students now `"Conta removida"` ×2. The accounting figure survives the removal; the legacy version showed `"Unknown"` because the row had vanished |
| S8.3 | S8.1 | `req -X DELETE $BASE/api/users/1 -H "$AH"` (again) | **404** `{"code":"user_not_found","message":"Usuário não encontrado"}`. Removing an already-removed account is not a success |
| S8.4 | S8.1 | `req -X DELETE $BASE/api/users/9999 -H "$AH"` | 404, same shape. The legacy version answered 200 `"Usuário deletado"` for an id that never existed |
| S8.5 | S8.1 | `req -X POST $BASE/api/auth/login -H "$JSON" -d '{"email":"leonan@fullcycle.com.br","password":"dev-student-password"}'` | 401. Anonymization clears the email and the hash, so the account can no longer authenticate |
| S8.6 | S8.1 | Terminal 1 log | `"msg":"user account removed"` with `userId` and `removedBy` — who did it is recorded |
| S8.7 | — | `req -X DELETE $BASE/api/users/abc -H "$AH"` | 400, `details.id = "deve ser um número inteiro"`. The path parameter is validated before reaching the database |
| S8.8 | — | `req -X DELETE $BASE/api/users/-1 -H "$AH"` | 400, `id` rejected |

The database-level guarantee (a hard `DELETE` is refused by a foreign key) is S12.6.

---

## S9 — HTTP boundary (API-02, API-04, API-05)

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S9.1 | server up | `req $BASE/api/nope` | 404 `{"error":{"code":"route_not_found","message":"Rota não encontrada: GET /api/nope"}}` — JSON, not Express's default HTML error page |
| S9.2 | — | `req $BASE/` | 404 with the same envelope |
| S9.3 | — | `req -X POST $BASE/api/checkout -H "$JSON" -d '{"name":'` (truncated JSON) | **400** `{"code":"malformed_json","message":"Corpo da requisição não é JSON válido"}` |
| S9.4 | — | `python3 -c "import json;print(json.dumps({'name':'x'*150000}))" > /tmp/big.json` then `req -X POST $BASE/api/checkout -H "$JSON" --data-binary @/tmp/big.json` | **413** `{"code":"payload_too_large",…}`. The body limit is 100 kB |
| S9.5 | — | `req -X POST $BASE/api/checkout -H "$JSON" -H 'Content-Encoding: nope' -d '{"a":1}'` | **415** `{"code":"unsupported_encoding",…}` |
| S9.6 | S9.3–S9.5 | Terminal 1 log | Each logged at `warn` as `request rejected at the body parser` — a client error is not a server fault. **No** `unhandled error`, no stack trace in any response body |
| S9.7 | — | `hdr $BASE/api/nope` | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, and **no** `X-Powered-By` |
| S9.8 | — | `req -X POST $BASE/api/checkout -H 'Content-Type: text/plain' -d 'hello'` | 400 `validation_error` with all five fields missing — a non-JSON content type yields an empty body, not a crash |
| S9.9 | — | Every response observed in S1–S8 | `Content-Type: application/json` on all of them, success and failure alike. The legacy API returned `text/html` on every error path |
| S9.10 | — | `req -X GET $BASE/api/checkout` | 404 — the route exists only for POST |

---

## S10 — Rate limiting (API-04)

Limits are per minute and per IP: checkout 10, login 5, admin 30. In-process, so they
reset when the server restarts.

| ID | Precondition | Action | Expected |
|---|---|---|---|
| S10.1 | fresh server | 13 checkouts in a loop with distinct emails and a valid card:<br>`for i in $(seq 1 13); do curl -s -o /dev/null -w "%{http_code} " -X POST $BASE/api/checkout -H "$JSON" -d "{\"name\":\"B$i\",\"email\":\"b$i@t.com\",\"password\":\"senhaforte\",\"courseId\":1,\"cardNumber\":\"4111222233334444\"}"; done` | `201` ×10 then `429` ×3 |
| S10.2 | S10.1 | `hdr -X POST $BASE/api/checkout …` on the 429 | `Retry-After: 60` present |
| S10.3 | S10.1 | body of the 429 | `{"error":{"code":"rate_limited","message":"Muitas requisições","details":{"retryAfterSeconds":<n>}}}` |
| S10.4 | S10.1 | Terminal 1 log | `"msg":"rate limit exceeded","limiter":"checkout"` |
| S10.5 | **restarted server, no login yet** | 7 failed logins in a row | `401` ×5 then `429` ×2, limiter `login`. This is the credential-stuffing guard. The limiter counts *all* login attempts, successful ones included — run this before the Preparation logins, or the first 429 arrives two attempts earlier |

> The checkout limiter is what makes the stub gateway's approve/decline difference
> unusable as a free card-testing oracle. Restart the server before S11 — and remember
> that a restart invalidates `$ADMIN` and `$STUDENT` (see Preparation), so re-run the
> login block afterwards.

---

## S11 — Transaction rollback (DAT-01, DAT-02) — intrusive

Verifies the highest-severity data-integrity finding. **Requires a temporary code
change**; revert it at the end. The HTTP surface cannot show this.

1. Note the state: `req $BASE/api/admin/financial-report -H "$AH"`.
2. In `src/models/auditLog.model.js`, at the top of `record`, insert:
   ```javascript
   throw new Error('simulated audit-log failure');
   ```
   This is the **last** write inside the checkout transaction — the user, the enrollment
   and the payment have all been written by the time it runs.
3. Restart the server and attempt a checkout with a new email:
   ```bash
   req -X POST $BASE/api/checkout -H "$JSON" \
     -d '{"name":"Rollback","email":"rollback@teste.com","password":"senhaforte","courseId":1,"cardNumber":"4111222233334444"}'
   ```
4. Expected:
   - **500** with body `{"error":{"code":"internal_error","message":"Erro interno"}}` — no
     stack trace, no table name, no driver message;
   - Terminal 1 shows `"msg":"unhandled error"` with the cause, server-side only;
   - `req $BASE/api/admin/financial-report -H "$AH"` → **unchanged**: no new enrollment
     and no new revenue;
   - `req -X POST $BASE/api/auth/login -H "$JSON" -d '{"email":"rollback@teste.com","password":"senhaforte"}'`
     → **401**: the user row was rolled back too, so the account does not exist.
5. Now the part that distinguishes a transaction from merely ordering the writes: issue a
   **successful** checkout with a different email and card, then re-check the report. Only
   that one enrollment appears. The abandoned transaction was not left open on the shared
   connection for the next request to commit.
6. Remove the `throw`, restart, and confirm the same checkout now answers 201.

Also verify the declined-payment path leaves nothing behind, which needs no code change:

7. Restart. `req -X POST $BASE/api/checkout -H "$JSON" -d '{"name":"Recusado","email":"recusado@teste.com","password":"senhaforte","courseId":1,"cardNumber":"5111222233334444"}'`
   → 402. Then try to log in as `recusado@teste.com` → **401**. The legacy code committed
   the user row before deciding the payment, so a declined checkout left an account behind
   carrying the default password.

---

## S12 — Direct database and code checks (LAY-01, LAY-04, LAY-05, LAY-06, QUA-02, QUA-03, QUA-05, SEC-01, SEC-02, DEP-01)

Run from `ecommerce-api-legacy/`. These check structure and invariants, not responses.

| ID | Action | Expected |
|---|---|---|
| S12.1 | `ls src/AppManager.js src/utils.js` | Both absent. The god class and the global-state module are gone |
| S12.2 | `grep -rln "require('express')" src/ \| grep -v "routes/index.js\|app.js"` | No output. Express is imported only by the route layer and the composition root |
| S12.3 | `grep -rln "require('sqlite3')" src/ \| grep -v infra/` | No output. The driver is confined to `infra/` |
| S12.4 | `grep -rlniE "select \|insert into\|update .* set\|delete from" src/controllers src/routes` | No output. No SQL above the model layer |
| S12.5 | `grep -rln "req\.\|res\." src/models src/services` | No output. Models and services never touch request or response objects |
| S12.6 | `grep -n "REFERENCES\|ON DELETE" src/infra/schema.js` and `grep -n "foreign_keys" src/infra/database.js` | Foreign keys declared `ON DELETE RESTRICT` on `enrollments` and `payments`, and `PRAGMA foreign_keys = ON` executed per connection. A declared constraint that is never enforced is not a fix |
| S12.7 | `grep -rnE "badCrypto\(\|globalCache\|totalRevenue\|logAndCache" src/` | No output. The dead global cache, the unused revenue accumulator, the log-and-cache function and the broken hash are gone. (A plain `grep badCrypto src/` still matches one line — a comment in `auth.service.js` recording what it replaced. The form above excludes prose and matches only a definition or a call.) |
| S12.8 | Query count — run the internal check:<br>`node -e "…"` against `services/report.service.js` with 20 courses and 100 enrollments, counting calls to `db.all/get/run` | **5 statements**, the same as with 2 courses. The legacy structure issued `1 + C + 2E` — 221 for that data. (A ready-made script lives outside the repo; the quick version is to wrap the three `db` methods with a counter before calling `financialReport`.) |
| S12.9 | `grep -rn "console\.log" src/` | Only the one occurrence inside a comment in `infra/logger.js`. All output goes through the structured logger |
| S12.10 | Terminal 1 log, after any checkout | Lines contain `"card":"****4444"` and **never** the full number, and never `pk_live_…`. Grep the whole log: `grep -cE "pk_live\|[0-9]{13,}" <logfile>` → 0 |
| S12.11 | `grep -rn "'PAID'" src/` | Two lines, both in `domain/constants.js` (the definition and a comment). No bare status literal survives anywhere else — the schema's `CHECK`, the checkout service and the revenue filter all reference `PaymentStatus.PAID`, so adding a status is a one-file change. Confirm with `grep -rn "PAID" src/ \| grep -v domain/constants.js`: every hit is either `PaymentStatus.PAID` or the comment in `payment.gateway.js` quoting the original line |
| S12.12 | `grep -rniE "new Buffer\(\|url\.parse\(\|createCipher\(\|fs\.exists\(\|util\.is" src/` | No output. No deprecated Node API in use — matching the audit's verified "none found" for DEP-01 |

---

## Finding → case matrix

Every finding in `reports/audit-project-2.md` and where it is verified. Two are partially
deferred by design; the matrix says what is checkable about them today.

| Finding | Cases |
|---|---|
| SEC-01 hardcoded secrets | S1.1, S1.2, S1.5, S1.6, S1.7 |
| SEC-02 card and key in logs | S12.10 |
| SEC-04 broken password storage | S2.1–S2.4, S2.7, S5.3, S5.4, S12.7 |
| SEC-05 missing access control | S3.1–S3.8, S8.5 |
| LAY-01 god class | S12.1–S12.5 |
| LAY-02 business logic in the route | S4.7, S11.7 (rule *isolated*, not replaced — see Deferred) |
| LAY-04 global state / dependency in place | S12.7, S12.3, S11.5 |
| LAY-05 inverted dependency direction | S12.2–S12.5 |
| LAY-06 configuration in code | S1.3, S1.4, S1.6, S7.6 |
| DAT-01 no transaction boundary | S11.1–S11.6 |
| DAT-02 partial state on failure | S11.4, S11.7 |
| DAT-03 orphaned records on delete | S8.1–S8.6, S12.6 |
| DAT-04 N+1 queries | S12.8 |
| DAT-05 unbounded result set | S7.4–S7.9 |
| DAT-06 over-fetching | S12.4 (columns are named in `models/`; no `SELECT *` remains) |
| API-01 broken request lifecycle | S7.2, S6.2, S6.4 |
| API-02 errors swallowed or leaked | S9.1–S9.6, S11.4, S8.3, S8.4 |
| API-03 input not validated | S5.1–S5.10, S6.1–S6.4, S7.8, S8.7, S8.8 |
| API-04 missing middleware chain | S10.1–S10.5, S9.4, S9.7 |
| API-05 inconsistent response contract | S4.1, S4.7, S8.1, S8.3, S8.4, S9.1, S9.9 |
| QUA-02 dead code | S12.1, S12.7 |
| QUA-03 magic literals | S12.11 |
| QUA-04 uninformative naming | S4.1 (canonical field names), S4.3, S4.4 (aliases still accepted) |
| QUA-05 ad-hoc logging | S12.9, and the structured lines checked throughout |
| DEP-01 deprecated APIs | S12.12 |

### Not covered here, and why

- **LAY-02, the approval rule itself.** `cardNumber.startsWith('4')` is unchanged; it is
  now behind a port that production refuses to use (S1.2). No test can verify a gateway
  integration that does not exist. Replacing `services/payment.gateway.js` with a real
  adapter is what closes it.
- **The audit trail has no read path.** `audit_logs` is written inside the checkout
  transaction (that is what S11 exercises) but no endpoint returns it, so there is nothing
  to assert over HTTP. Inspect the table directly if you need to see the rows.
- **Rate limiting across replicas.** S10 validates one process. The limits multiply by
  replica count behind a load balancer; that needs a shared store, not a test.

---

## Execution log

| Suite | Cases | Run on | Result | Notes |
|---|---|---|---|---|
| S1 — Boot and configuration | 7 | | | |
| S2 — Authentication | 8 | | | |
| S3 — Authorization | 8 | | | |
| S4 — Checkout, successful paths | 7 | | | |
| S5 — Checkout, rejected input | 10 | | | |
| S6 — Crash path | 4 | | | |
| S7 — Financial report | 10 | | | |
| S8 — User removal | 8 | | | |
| S9 — HTTP boundary | 10 | | | |
| S10 — Rate limiting | 5 | | | |
| S11 — Transaction rollback | 7 steps | | | intrusive — confirm the `throw` was reverted |
| S12 — Database and code checks | 12 | | | |

**89 table cases in 11 suites, plus the 7-step intrusive procedure in S11.**

A failing case should be recorded with the finding id from the matrix above, so it is
immediately clear which fix regressed.
