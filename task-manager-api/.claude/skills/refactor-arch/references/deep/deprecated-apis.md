# Deprecated APIs — detection depth

Confirmation steps for `DEP-01`. Read before writing a deprecation finding, and read it
even when you expect to find nothing — reporting a verified "none" is part of the job.

Deprecation is the one finding that is **relative to a version**. The same call can be
current, deprecated, or removed depending on what the project pins, which means a lookup
table alone will produce wrong findings. The method matters more than the list.

## Method

1. **Get the pinned versions first** — runtime and libraries, from the dependency
   manifest. Without them you cannot classify anything.
2. **Find the call sites**, matching the exact call rather than the concept.
3. **Classify against the pinned version:**
   - *Current* — not a finding. Drop it.
   - *Deprecated* — warned, still functional. MEDIUM.
   - *Removed* — the code is broken on the pinned version. HIGH, and say that it cannot run.
4. **Check the replacement is available** in the pinned version before recommending it.
   Recommending an API that does not exist yet in the project's version is worse than the
   deprecation.
5. **Report every site as one finding**, listing all locations. Deprecations are mechanical and
   repetitive; one entry with twenty lines is readable, twenty entries are not.

Where you cannot establish the status with confidence, say that instead of guessing. A
finding that states "deprecated in 3.12, project pins no Python version — verify before
migrating" is useful and honest.

## Starting-point table

A prompt for where to look, not an authority. Verify each against the project's pinned
version; these change with every release.

**Python**

| Call | Status | Replacement |
|---|---|---|
| `datetime.utcnow()`, `datetime.utcfromtimestamp()` | deprecated 3.12 | `datetime.now(timezone.utc)`, `datetime.fromtimestamp(ts, timezone.utc)` |
| `distutils` | removed 3.12 | `setuptools`, `packaging` |
| `imp` | removed 3.12 | `importlib` |
| `collections.Mapping` and siblings | removed 3.10 | `collections.abc.*` |
| `unittest.assertEquals` and other aliases | deprecated | `assertEqual` etc. |
| `asyncio.get_event_loop()` outside a running loop | deprecated 3.12 | `asyncio.run`, `get_running_loop` |
| `locale.getdefaultlocale()` | deprecated 3.11 | `locale.getlocale()` |

**Flask / SQLAlchemy**

| Call | Status | Replacement |
|---|---|---|
| `@app.before_first_request` | removed in Flask 2.3 | app-factory setup or a guarded `before_request` |
| `flask.json.JSONEncoder` subclassing | removed in Flask 2.3 | custom `app.json` provider |
| `Model.query` / `Query.get()` | legacy in SQLAlchemy 2.0 | `db.session.get()`, `select()` with `session.execute()` |
| `Query.get()` by primary key | legacy | `Session.get()` |

**Node / Express**

| Call | Status | Replacement |
|---|---|---|
| `new Buffer(...)` | deprecated | `Buffer.from()`, `Buffer.alloc()` |
| `url.parse()` | legacy | `new URL()` |
| `crypto.createCipher` / `createDecipher` | deprecated | `createCipheriv` / `createDecipheriv` |
| `fs.exists` | deprecated | `fs.access`, `fs.existsSync` |
| `util.isArray` and `util.is*` | deprecated | `Array.isArray`, `typeof` |
| `body-parser` as a separate dependency | redundant since Express 4.16 | `express.json()`, `express.urlencoded()` |
| `domain` module | deprecated | `AsyncLocalStorage` |

## Adjacent findings that are not deprecations

These are worth reporting, but not as `DEP-01` — calling a supported version "deprecated" is
the kind of inaccuracy that costs a report its credibility:

- **An old major version of a dependency.** Express 4 while 5 is released, or a framework a
  major behind, is a maintenance observation. Report it under the report's Notes section, or
  as LAY-06 if the pin itself is the problem. Not a deprecated API.
- **A callback-style API where a promise API also exists.** Still supported; a modernization
  opportunity. If the callback style is causing a concrete bug, the finding is API-01 and the
  bug is the point.
- **An unpinned or loosely pinned dependency.** A supply-chain and reproducibility concern,
  not a deprecation.
- **A library that is unmaintained but whose API is unchanged.** A dependency risk. Say so in
  the Notes.

## False-positive guards

The modern form of several APIs looks almost identical to the deprecated one, which is where
false positives come from. Match the exact call:

- `Buffer.from(x)` is correct. `new Buffer(x)` is deprecated.
- `datetime.now(timezone.utc)` is correct. `datetime.utcnow()` is deprecated.
- `createCipheriv` is correct. `createCipher` is deprecated.
- `fs.existsSync` is current. `fs.exists` (callback form) is deprecated.
- `express.json()` is current. A separate `body-parser` dependency is merely redundant.

## Reporting none

When the sweep finds nothing, the report gets a line under Notes:

```
No deprecated APIs found. Checked against <runtime> <version> and
<framework> <version>: <what was checked, briefly>.
```

This is a result. Naming what was checked is what makes it one — an unqualified "none found"
is indistinguishable from not having looked. Never invent a deprecation to fill the slot: a
fabricated finding here is easy for a reviewer to disprove, and it puts every other finding
in the report in doubt.

**Fix** → T-24.
