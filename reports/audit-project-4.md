================================
ARCHITECTURE AUDIT REPORT
================================
Project: ecommerce-api-legacy
Stack:   JavaScript + Express 4.22.1 + SQLite (sqlite3 5.1.7, no ORM)
Files:   30 analyzed | ~1,902 lines of code

## Project Profile
Language:      JavaScript (Node.js 24.10.0 local; no `engines` field in `package.json`)
Framework:     Express 4.22.1 (pinned `^4.18.2`)
Dependencies:  express, sqlite3; node:crypto, node:fs, node:path
Domain:        Course enrollment with paid checkout (users, courses, enrollments, payments)
Architecture:  Layered — config/domain/infra/models/services/controllers/routes/middlewares,
               composition root in `src/app.js`; express imported only by `app.js` and
               `routes/`, sqlite3 only by `infra/database.js`, no SQL outside `models/`
               and `infra/`
DB tables:     users, courses, enrollments, payments, audit_logs

## Scope note
This is a second audit of this project. The first one (`audit-project-2.md`) examined the
original three-file version; that refactor has already been applied, so the findings below
are against the layered codebase, not against `AppManager.js`. Most of what the first audit
raised is genuinely gone: there is a transaction boundary, foreign keys are declared and
enforced, passwords use `scrypt` with a per-user salt and a constant-time comparison, the
report runs in a fixed number of queries, errors are centralized, and the admin routes are
behind role-checked authentication.

What follows is what survived, plus what the first audit did not separate out.

## Summary
CRITICAL: 1 | HIGH: 1 | MEDIUM: 1 | LOW: 2

## Findings

### [CRITICAL] Payment approval is decided by the card's first digit, and that path is the default
ID: SEC-07
File: src/services/payment.gateway.js:20, :31-44, :48-58 · src/config/index.js:86
Description: `createStubPaymentGateway` decides authorization with
             `String(cardNumber).startsWith(APPROVED_CARD_PREFIX)` where the prefix is
             `'4'` (`payment.gateway.js:20,32`). Nothing contacts a provider, validates the
             card, checks funds or captures anything — the decision is an inspection of one
             character. `config/index.js:86` selects this driver whenever `PAYMENT_DRIVER`
             is unset and `NODE_ENV` is not exactly `'production'`, so it is the active path
             in every environment that is not explicitly production, including staging and
             every developer machine. The guard at `payment.gateway.js:50-55` throws when
             `isProduction`, which covers production and nothing else.

             Confirmed live on the current code, server started with no environment
             variables set: an anonymous `POST /api/checkout` with
             `cardNumber: "4999999999999"` returned `201
             {"enrollmentId":2,"courseId":2,"amount":497,"status":"PAID"}` — a paid
             enrollment in a 497.00 course, with a `payments` row recorded as `PAID`. The
             same request with `"5000000000000"` returned `402 payment_declined`, which
             confirms the first digit is the whole policy.
Impact: Anyone who can reach the port enrolls in any course for free, unauthenticated and
        rate-limited only to 10 attempts per minute. The system records the enrollment and a
        `PAID` payment row, so the revenue in `GET /api/admin/financial-report` counts money
        that was never charged — the financial report is wrong in a way no reader can detect
        from the output. Discovering the rule requires one request with a card starting
        with 4.
Recommendation: T-25 — invert the default so the placeholder cannot grant. Have `authorize`
                return `approved: false` with a reason naming the real cause (no adapter
                configured), remove `cardNumber` from the decision entirely so there is no
                rule left to discover, and gate any approving path behind a variable named
                for what it does (`PAYMENT_STUB_APPROVE`), defaulted off and rejected outside
                development. Keep the existing production refusal as a second layer. The
                success path then returns `402` where it previously returned `201`, which is
                the fix rather than a regression: a request that used to buy a course for
                free is refused. Declare it as an intentional contract change.

### [HIGH] Seeded admin account uses a password committed to the repository, and seeding is on by default outside production
ID: SEC-01
File: src/config/index.js:96-99 · src/infra/schema.js:67-95
Description: `config/index.js:98` defines `adminPassword: str('SEED_ADMIN_PASSWORD',
             'dev-admin-password')` — a literal in a version-controlled file — and
             `schema.js:92-95` uses it to create `admin@fullcycle.com.br` with
             `Role.ADMIN`. Seeding is enabled by `config/index.js:96`,
             `enabled: bool('SEED_ENABLED', !isProduction)`, so it runs in any environment
             whose `NODE_ENV` is not the exact string `'production'`. `schema.js:72-74`
             refuses to seed when `isProduction`, and `:76-80` skips when the `users` table
             is non-empty.

             Confirmed live: `POST /api/auth/login` with
             `{"email":"admin@fullcycle.com.br","password":"dev-admin-password"}` returned
             `200` with an admin token on a server started with no environment variables.
Impact: Any deployment that is not labelled exactly `production` — `staging`, `qa`, `test`,
        or an unset `NODE_ENV` — comes up with an administrator whose password is readable in
        this repository. That token opens `GET /api/admin/financial-report` (every student's
        name and the platform's revenue) and `DELETE /api/users/:id`. Nothing logs a warning
        at boot that a known-password administrator exists.
Recommendation: T-01 — treat the seed passwords as secrets rather than settings: read them
                with the `secret()` helper so an absent value is generated at random per
                process instead of falling back to a literal, and remove the literals from
                `config/index.js`. Gate seeding on an explicit `SEED_ENABLED=true` rather
                than on "not production", so an environment opts in instead of inheriting it.
                Log a warning naming the seeded accounts whenever seeding runs.

                Considered and rejected as a reason to drop this finding: the README
                documents these as development fixtures, and a documented fixture credential
                for a disposable database is normally not a finding. It counts here because
                the literal is committed, the account is an administrator, and the gate
                admits every environment except one.

### [MEDIUM] `trust proxy` is hardcoded, which silently mis-keys the rate limiter behind a proxy
ID: LAY-06
File: src/app.js:117 · src/middlewares/rateLimit.js:29
Description: `app.js:117` sets `app.set('trust proxy', false)` as a literal, with no
             environment variable to change it — it is the only such setting not routed
             through `config/`. The rate limiter keys its buckets on `req.ip`
             (`rateLimit.js:29`). With `trust proxy` false, `req.ip` is the socket's peer
             address, which is correct when the process is exposed directly and is the
             proxy's address when it is not.
Impact: Deployed behind a load balancer, ingress or CDN — the normal case — every client
        presents the same `req.ip`, so all callers share one bucket. The login limiter of 5
        requests per minute is then consumed globally: a single client's six attempts lock
        out every other user, turning a protection into a denial of service. In the same
        configuration a distributed attacker is not limited per-origin at all. Changing it
        requires editing the composition root, which is the coupling `config/` exists to
        remove.
Recommendation: T-01 — read it from configuration (`TRUST_PROXY`, default `false` so direct
                exposure stays safe), and pass the resolved value through `config.http`.
                Where the limiter must work behind a proxy, document that `TRUST_PROXY` has
                to be set, since the failure is silent either way.

### [LOW] `config.payment.gatewayKey` is read from the environment and never used
ID: QUA-02
File: src/config/index.js:87
Description: `gatewayKey: process.env.PAYMENT_GATEWAY_KEY || null` is defined and referenced
             nowhere else in `src/` — the stub gateway does not use it and no real adapter
             exists yet.
Impact: A configuration value that appears to be wired up and is not. An operator who sets
        `PAYMENT_GATEWAY_KEY` gets no error and no effect, and may reasonably conclude a real
        gateway is configured when the stub is still deciding. That is a mild version of the
        confusion SEC-07 describes.
Recommendation: T-21 — remove it, and reintroduce it in the adapter that actually calls a
                provider. If it is kept deliberately as a placeholder, say so in
                `.env.example` and note that it is unused until an adapter exists.

### [LOW] `audit_logs` is written on every checkout and never read
ID: QUA-02
File: src/infra/schema.js:47-51 · src/models/auditLog.model.js · src/services/checkout.service.js:66
Description: The `audit_logs` table is created, and `checkout.service.js:66` records a row
             inside the checkout transaction. No query anywhere in `src/` reads the table,
             and no route exposes it.
Impact: An audit trail that cannot be consulted does not serve the purpose an audit trail
        exists for: the rows accumulate, the write cost is paid on every checkout inside the
        transaction, and the information is unreachable without opening the database by hand.
Recommendation: Either expose it — an admin-only, paginated read endpoint — or drop the table
                and the write (T-21). The decision is a product one; what should not persist
                is the current state, where the write implies a capability that does not
                exist. This is a half-implemented feature rather than an architectural
                defect, so it is reported at LOW.

## Notes

**No deprecated APIs found.** Checked against Node.js 24.10.0, Express 4.22.1 and
sqlite3 5.1.7: no `new Buffer()` (the code uses `Buffer.from`), no `url.parse`, no
`crypto.createCipher`, no callback-form `fs.exists`, no `util.is*` helpers, no `domain`
module. `body-parser` is not a separate dependency — `express.json()` is used. Express 4
while 5 is released is a dependency-currency observation, not a deprecated API.

**In-process rate limiting** is per-instance by construction (`rateLimit.js:9-12`), so with
several replicas the effective limit multiplies by the replica count. This is documented in
the code and in the README as a deliberate floor, so it is recorded here rather than as a
finding; the `trust proxy` interaction above is the part that is not documented and is a
finding.

**No migrations.** The schema is created at boot by `createSchema` (`infra/schema.js:58-60`),
which is appropriate for a `:memory:` default and becomes a problem the moment
`DATABASE_FILE` points at a real path: there is no versioned path from one schema to the
next.

**No automated tests** in the project. Recorded as an observation rather than a finding,
since there is no code location to point at and no transformation that produces one. Worth
noting that `groupByCourse` (`services/report.service.js:25`) and the `scrypt` helpers were
written to be exercisable without a database, so the surface is ready for a suite.

**Not reported, having been checked.** `cardNumber` is validated as 13–19 digits
(`routes/schemas.js:38-42`) and is never logged — `requestLogger` does not log bodies, and
the stub masks to the last four. Password hashing uses `scrypt` with a per-user salt and
`timingSafeEqual`. `login` returns the same failure for an unknown account and a wrong
password. Foreign keys are declared `ON DELETE RESTRICT` and enforcement is verified at boot
(`infra/database.js:70-76`). Deletion anonymizes rather than removing the row, so financial
records keep a valid parent. The report's queries are bounded and its revenue is aggregated
in SQL, independent of the student cap.

================================
Total: 5 findings
================================
