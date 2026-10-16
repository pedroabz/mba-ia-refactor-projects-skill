# Security — detection depth

Confirmation steps for the `SEC` family. Read before writing any `SEC` finding.

Security findings carry the most weight in a report and are the easiest to get wrong in
both directions: a missed injection is a real vulnerability, an invented one destroys trust
in the other findings. Confirm by reading the code path, not by matching a keyword.

---

## SEC-01 — Hardcoded secrets and credentials · CRITICAL

Violates: config belongs in the environment (12-factor III).

**Confirm by** locating the literal and establishing that it ships with the code. Check
whether the file is version-controlled and whether the value looks live — a vendor prefix
(`sk_live_`, `pk_live_`, `AKIA`), a realistic password, a full DSN with credentials.

**Trace the blast radius.** A secret in code is often also exposed somewhere else: grep the
same identifier across the project and check whether it reaches a response, a log, or a
client-side bundle. Report those as one finding with every location, since the fix is the same.

**Raise** when the credential is for a production system or an external paid service.
**Lower to MEDIUM** when the value is plainly a local development placeholder and the
project has no production path at all — rare, and state the reasoning.

**Not this:** a framework's documented development default; a sample `.env.example`; a test
fixture credential for a disposable container. Also note that credentials which are
*declared but unused* are still findings — a committed production password does not become
safe by being dead code — but say so, since it changes the fix.

**Fix** → T-01.

---

## SEC-02 — Sensitive data exposed through response or log · CRITICAL

Violates: least privilege; OWASP A09.

**Confirm by** following the value to its exit point. Two vectors, both worth checking
whenever the other appears:

- *Response* — a serializer, DTO or response dict that includes a password, hash, token,
  secret, full card number or another user's personal data. Check every caller of a
  serializer: one `to_dict()` that includes a password field leaks it from every endpoint
  that returns it, which is usually more endpoints than the author intended.
- *Log* — a print or logger call interpolating a credential, a card number, a full request
  body, or an entire user record. Logs are frequently shipped to third parties, so this is
  exposure even when the console looks local.

**Raise** when the endpoint is unauthenticated, or when the data belongs to users other than
the caller.

**Not this:** logging an identifier, a non-sensitive field, or a redacted/truncated value.
An error message that names a field without its value.

**Fix** → T-04.

---

## SEC-03 — Injection through string-assembled query or command · CRITICAL

Violates: OWASP A03 — the bug is confusing data with code.

**Confirm by** establishing that an untrusted value becomes part of the *statement text*,
not part of a bound parameter. Work backwards from the query to the value's origin: request
body, query string, path parameter, header, or a stored value that was itself unvalidated.

Query assembly built from `+`, `%`, `.format()`, f-strings or template literals is the
signal. The same applies beyond SQL: `eval`, `exec`, dynamic imports, shell commands, and
constructed file paths (path traversal).

**Report once per pattern, not once per call site.** A model where every function
concatenates is one finding listing all the lines; that is also how the fix is applied.

**Mention the correctness angle too** where it applies: concatenated string literals break
on legitimate input containing a quote. It makes the finding harder to dismiss as theoretical.

**Also look for the auth-bypass case specifically.** A login query that concatenates both
email and password is not just injection, it is an authentication bypass — the highest-impact
instance of this pattern, and worth calling out as such rather than folding into a list.

**Not this:** ORM expressions (`Model.col == value`, `filter_by(id=x)`,
`Model.col.like(f'%{q}%')`) — the f-string builds the search *pattern*, the driver still binds
it. Parameterized calls with placeholders (`execute(sql, (a, b))`, `?`, `$1`, `:name`).
A query assembled from values that cannot originate outside the code.

**Fix** → T-02.

---

## SEC-04 — Broken or absent password storage · CRITICAL

Violates: OWASP A02.

**Confirm by** reading the write path and the verify path. Both matter: storage may be
hashed while comparison is wrong, or a hash function may exist and be bypassed by a seed.

Findings in increasing severity: stored as received; hashed with a fast general-purpose
digest (MD5, SHA-1, SHA-256) directly; no per-user salt; hand-rolled construction; verified
with a plain equality comparison. A hand-rolled function deserves a line of analysis — say
what it actually produces, because "weak" understates a function that collapses the whole
password space into a handful of outputs.

**Check consistency.** Seeds and fixtures that write passwords directly, bypassing the
hashing function, are part of this finding — the stored data is what matters, not the
intended path.

**Check whether verification happens at all.** If nothing ever compares a password, say so:
the field is write-only and there is no authentication, which is a different and larger
problem than weak hashing.

**Not this:** a modern password KDF (bcrypt, scrypt, argon2, PBKDF2 with a sane cost).
SHA-256 used for a non-password purpose such as a checksum or cache key.

**Fix** → T-03.

---

## SEC-05 — Missing access control on sensitive or destructive operation · CRITICAL

Violates: OWASP A01 — deny by default.

**Confirm by** reading the handler for an authorization check and the application for guard
middleware. Absence in both is the finding. Then classify what is reachable: deleting or
resetting data, reading personal data in bulk, executing caller-supplied input, moving money,
changing roles.

**Check the whole chain, not the route name.** A route under `/admin` with no role check is
a finding; so is a non-admin route that happens to expose everything. Conversely, a token
that is issued but never verified anywhere means every route is unprotected — report that as
one systemic finding rather than per route.

**An endpoint that executes caller-supplied SQL or code** has two independent defects and
gets two findings. One is the missing access control (this entry): anyone can call it. The
other is that it executes whatever it is given (SEC-03): arbitrary execution by design, whose
recommendation is removal rather than escaping. Adding authentication leaves a logged-in user
with arbitrary execution; removing the endpoint closes both, but they are still two findings,
because an audit that reports only one of them hides half the exposure.

**Raise** when the operation is destructive, irreversible, or exposes data belonging to
other users.

**Not this:** a route intentionally public (health check, landing page, public catalogue) —
though a health check leaking configuration is SEC-02. A missing check in a layer where
another layer already enforces it, if you can see that enforcement.

**Fix** → T-05.

---

## SEC-06 — Insecure runtime configuration · HIGH

Violates: OWASP A05.

**Confirm by** reading the entry point and the framework configuration for what ships
enabled: debug mode, an interactive debugger, permissive CORS applied globally, binding to
all interfaces, stack traces returned to clients, directory listing, verbose error pages.

**Debug mode deserves specific treatment.** In frameworks whose debug mode includes an
interactive console, enabling it on a listening interface is remote code execution, not a
tidiness issue. Say which it is rather than reporting "debug enabled" flatly.

**Raise to CRITICAL** when an interactive debugger is reachable on a non-local interface.

**Not this:** a debug flag read from the environment and defaulting to off. A permissive CORS
policy on a genuinely public read-only API, if that is a deliberate documented choice.

**Fix** → T-01 for the configuration itself; T-16 for the middleware that should constrain it.

---

## SEC-07 — Security-critical decision simulated, and defaulting to permit · CRITICAL

Violates: fail closed; deny by default.

**Confirm by** finding a decision that grants something of value — money captured, access
granted, identity accepted, quota allowed, signature trusted — and checking **who actually
decides**. The finding is a decision made by local inspection when the authority that owns it
is never consulted.

Shapes this takes:

- A payment approved by looking at the card number (prefix, length, a checksum) with no
  provider call, no funds check and no capture.
- Authentication that accepts a hardcoded list, any non-empty credential, or a token it never
  verifies.
- An entitlement, plan or quota check that returns `true` unconditionally.
- A signature or webhook verification that parses the payload and skips the signature.
- A function named `fake`, `mock`, `stub`, `dummy`, `dev` or `test` wired into the live path.
- A `TODO`/`FIXME` sitting where the real check belongs.

**The finding is the permissive default, not the stub.** A project with no provider to call
legitimately needs a placeholder; what makes it CRITICAL is that the placeholder *grants*.
Establish three things and report them explicitly, because they are what the fix has to
change:

1. **Which way does it fail?** A stub that denies is a known gap. A stub that approves is a
   bypass — anyone who learns the rule gets the thing for free.
2. **Is it reachable by default?** Read the configuration defaults, not just the code. A
   driver that defaults to the stub whenever an environment variable is unset is on in every
   deployment that forgot to set it, which includes every developer machine and usually
   staging.
3. **What does a production guard actually cover?** Refusing to boot when
   `NODE_ENV=production` is worth having and is not sufficient: it protects one environment
   and leaves the default permissive everywhere else. Say so rather than counting it as the
   fix.

**Severity does not drop because it is "only a stub".** Judge by what the permissive path
grants. Free goods, free access, accepted identity or bypassed billing is CRITICAL. Where the
decision grants something minor and non-transferable, HIGH is defensible — state the
reasoning.

**Almost always this sits on top of a layering finding, and the two are separate.** The same
expression is usually both business logic in the wrong layer (LAY-02) and a forged decision
(this entry). Report both, at their own severities. Extracting the rule into a service closes
LAY-02 completely — that work is finished and correct — and leaves the forged decision exactly
as it was, because relocating code is not supposed to change behaviour. If only LAY-02 gets
written up, the extraction retires the whole location on paper and the bypass survives the
refactor. "One defect, one finding" in `anti-patterns.md` has the test for splitting them.

**Not this:** a test double in a test suite. A feature flag that gates a non-security
behaviour. A deliberately open endpoint that grants nothing. A stub that already fails closed
and is documented — that is a known gap, worth a line under Notes, not a CRITICAL finding.

**Fix** → T-25.
