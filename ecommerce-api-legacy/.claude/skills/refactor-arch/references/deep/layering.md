# Layering — detection depth

Confirmation steps for the `LAY` family. Read before writing any `LAY` finding.

These are the findings the challenge is actually about: MVC violations and the SOLID
principles behind them. They are also the ones most easily reported as vibes. The discipline
that keeps them concrete: name the responsibility, name the file that currently holds it, and
name the layer that should. If you cannot do all three, the finding is not ready.

`architecture-guidelines.md` defines the layer boundaries these findings are measured against.

---

## LAY-01 — God class / god file · CRITICAL

Violates: single responsibility; separation of concerns.

**Confirm by** listing the distinct responsibilities in the file. Two or more of the
following is the finding: schema definition or DDL, queries, business rules, routing,
serialization, external integration, configuration.

Size is a hint, never the finding. A 400-line module that only contains queries is cohesive;
a 140-line class holding DDL, routing, payment rules and persistence is a god class. Report
the responsibility mix, with line ranges for each, so the recommendation follows directly
from the evidence.

**Count the domains too.** One file covering four unrelated entities raises the severity
independently of responsibility mixing, because every change to any entity touches the same
file.

**Not this:** a long file of related pure functions. A framework-conventional module that
looks big because it declares many routes but delegates each one. A generated file.

**Fix** → T-06.

---

## LAY-02 — Business logic in the controller or route · HIGH

Violates: MVC boundaries. Named explicitly in the challenge's HIGH definition.

**Confirm by** identifying a rule in the handler that would need to hold anywhere else in the
system: pricing, discounts, eligibility, state transitions, scoring, tax, limits. Arithmetic
on domain values and conditional chains on domain state are the usual shapes.

**Side effects count.** Mail, SMS, push, webhooks or queue publishing fired inline in a
handler is this finding: the rule "when X happens, notify Y" belongs to the use case, and
the mechanism belongs behind a service.

**Distinguish from legitimate controller work.** Reading the request, validating input
shape, choosing a status code, sequencing calls and shaping the response are a controller's
job. The test is whether another caller — a scheduled job, a CLI command, a second endpoint
— would have to copy the rule to behave consistently.

**A hardcoded rule standing in for an integration** deserves naming: payment approval decided
by inspecting the first digit of a card number is both this finding and a correctness problem.
Say both.

**Not this:** a thin handler delegating to a model or service. Input validation. HTTP concerns.

**Fix** → T-07.

---

## LAY-03 — Business logic or side effects in the model · HIGH

Violates: single responsibility.

**Confirm by** finding, inside a model or data-access module, something that is not about an
entity's own shape, persistence or invariants: cross-entity aggregation, policy decisions,
reporting calculations, discount tiers, or response-shaped dictionaries assembled for a caller.

**This is the mirror of LAY-02 and is missed more often**, because code in a file called
`models.py` looks like it is where it belongs. The question is not which file holds it but
whether an entity owns the rule. A discount scale applied to total revenue is not a property
of any entity; it is a use case.

**Serialization in the data layer** is the common variant: a query function that returns
hand-built dictionaries shaped for the HTTP response couples persistence to the API contract,
and duplicates once a second endpoint needs a different shape.

**I/O beyond persistence** — a model sending mail or calling an external API — is the same
finding with a sharper edge, since it makes the model impossible to test without the network.

**Not this:** validation intrinsic to the entity (a price cannot be negative). A computed
property derived only from the entity's own fields. An ORM relationship declaration.

**Fix** → T-08.

---

## LAY-04 — Global mutable state / dependency built in place · HIGH

Violates: dependency inversion; low coupling. Named in the challenge's HIGH definition.

**Confirm by** finding module-level mutable state or a dependency constructed where it is
used, then checking what that makes impossible.

Shapes to look for:

- A module-level connection, client, cache or counter mutated at runtime.
- A class or module that constructs its own connection instead of receiving one.
- A thread-safety check disabled to make a shared object work across requests — the flag is
  an admission that the object is shared without synchronization.
- A cache that is written and never invalidated or bounded, which is also a slow memory leak.
- A mutable value exported from a module, where importers receive a copy and mutations never
  propagate. Report it as a bug as well as a design problem: the state does not work.

**State the consequence concretely.** "Untestable" is the real cost — no test can substitute
a fake, so every test needs the real database. That is more persuasive than citing DIP.

**Not this:** an immutable module-level constant or configuration object. A framework
extension object designed to be module-level and initialized with the app. A connection pool
obtained through the framework's request lifecycle.

**Fix** → T-09.

---

## LAY-05 — Layer bypass · HIGH

Violates: dependency direction.

**Confirm by** following imports against the intended direction. The violations worth
reporting:

- The entry point or composition root importing a driver and executing queries, or defining
  handlers that do. A file whose job is to assemble the app holding a `DELETE` statement is
  the clearest possible evidence that layers are decorative.
- A route handler importing the database driver or ORM session directly.
- A model importing the framework's request/response objects, or reading request state.
- Data-access code importing serialization or HTTP concerns.

**Report direction, not just location.** Name the importing module, the imported module, and
which arrow in the architecture it reverses.

**Not this:** config imported by any layer that needs values. A shared types or constants
module imported everywhere. Framework imports in the layer that legitimately owns them.

**Fix** → T-06 for extraction; T-09 where the cause is a globally reachable dependency.

---

## LAY-06 — Configuration embedded in code, no config module · MEDIUM

Violates: config belongs in the environment.

**Confirm by** checking for a configuration module and for environment reads, then listing
what is hardcoded in application files: ports, hosts, database paths, debug flags, timeouts,
feature flags, business thresholds that are deployment choices rather than domain rules.

**Say what the coupling costs.** The concrete version — changing the debug flag requires
editing the file that also wires every route — lands better than "configuration should be
externalized".

**A declared but unused configuration dependency is evidence**, not a separate finding: a
project that depends on a dotenv library and never imports it shows the intent existed and
was abandoned. Fold it into this finding.

**Secrets among the hardcoded values are SEC-01**, not this. Keep them separate: one is a
vulnerability, this is a maintainability finding. Reporting them together lets a reader
dismiss both at one severity.

**Not this:** a constant that is genuinely a domain invariant. A default in a config module
that reads the environment first.

**Fix** → T-01.
