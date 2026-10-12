#!/usr/bin/env python3
"""Capture and compare the HTTP contract of a running application.

Used to prove that a refactor preserved behaviour instead of asserting it. Run
`capture` against the application before refactoring, run it again afterwards, then
`compare` the two baselines.

    python3 tools/contract_check.py capture <spec.json> <base-url> <out.json>
    python3 tools/contract_check.py compare <before.json> <after.json> [declared.json]

Volatile values (timestamps, durations) are normalized so that two runs of an
unchanged application compare equal. Everything else is compared verbatim: any
difference is either a regression or an intentional contract change that has to be
declared. Passing a declarations file makes that separation explicit: it maps step id to
the reason the contract changed, and the comparison fails only on differences that were
not written down — or on declarations for steps that turned out not to change.

A spec may also list step ids under "unordered" when the application's list order is
genuinely nondeterministic before the refactor — proven by capturing the unchanged app
twice and seeing the order differ. Those steps are compared as multisets, so the
comparison still checks every element and only ignores position. Use it only with that
proof: silencing a real ordering regression is exactly the failure this tool exists to
prevent. The step ids travel in the baseline, so old baselines without the key keep
comparing verbatim.

Standard library only, so it runs against any project without adding dependencies.
"""
import json
import re
import sys
import urllib.error
import urllib.request

TIMEOUT = 15

# Values that legitimately differ between two runs of the same code.
VOLATILE_VALUE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}"      # 2026-10-11 14:03:22[.123][+00:00]
    r"|^\d{4}-\d{2}-\d{2}$"                          # bare date
)
VOLATILE_KEY = {"timestamp", "generated_at", "criado_em", "created_at", "updated_at",
                "ts", "duration", "duration_ms", "elapsed", "uptime", "days_overdue"}


def normalize(value, key=None):
    """Replace volatile leaves with a marker, recursively, preserving structure."""
    if isinstance(value, dict):
        return {k: normalize(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if key in VOLATILE_KEY and value is not None:
        return "<VOLATILE>"
    if isinstance(value, str) and VOLATILE_VALUE.match(value):
        return "<VOLATILE>"
    return value


def canonical(value):
    """Sort every list, recursively, so two orderings of the same elements compare equal.

    Only applied to steps the spec declares "unordered". Every element is still
    compared — a missing, extra or changed element fails exactly as before.
    """
    if isinstance(value, dict):
        return {k: canonical(v) for k, v in value.items()}
    if isinstance(value, list):
        return sorted((canonical(v) for v in value),
                      key=lambda item: json.dumps(item, sort_keys=True, ensure_ascii=False))
    return value


def obtain_tokens(base_url, auth):
    """Log in as each declared identity, so role-based access can be exercised.

    `auth` is either a single login spec or a mapping of identity name to login spec. A
    step selects one with `"auth": true` (the single/"default" identity) or
    `"auth": "<name>"`. Returns {name: (header_name, header_value)}.
    """
    identities = {"default": auth} if "path" in auth else auth
    tokens = {}
    for name, spec in identities.items():
        header = obtain_token(base_url, spec)
        if header:
            tokens[name] = header
            print(f"  authenticated as {name} via {spec['path']}")
    return tokens


def obtain_token(base_url, auth):
    """Log in and extract a token, so protected routes can be exercised.

    Returns (header_name, header_value) or None if the login did not yield a token —
    in which case the caller continues unauthenticated and the protected steps record
    whatever the guard returns, which is itself a useful observation.
    """
    probe = {"id": "_auth", "method": auth.get("method", "POST"),
             "path": auth["path"], "body": auth.get("body")}
    result = call(base_url, probe)
    node = result.get("body")
    for key in auth.get("token_path", ["token"]):
        node = node.get(key) if isinstance(node, dict) else None
    if not isinstance(node, str) or not node:
        print(f"  warning: login at {auth['path']} returned no token "
              f"(status {result.get('status')}) — running unauthenticated")
        return None
    return auth.get("header", "Authorization"), auth.get("format", "Bearer {token}").format(token=node)


def call(base_url, step, tokens=None):
    """Execute one step and return the recorded observation."""
    url = base_url.rstrip("/") + step["path"]
    body = step.get("body")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}

    wanted = step.get("auth")
    if wanted:
        identity = "default" if wanted is True else wanted
        header = (tokens or {}).get(identity)
        if header:
            headers[header[0]] = header[1]
        else:
            print(f"  warning: step {step['id']} wants identity '{identity}', "
                  "which has no token — sending unauthenticated")
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=step.get("method", "GET"))

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            status, raw, ctype = resp.status, resp.read(), resp.headers.get_content_type()
    except urllib.error.HTTPError as err:
        status, raw, ctype = err.code, err.read(), err.headers.get_content_type()
    except Exception as err:                      # connection refused, timeout, reset
        return {"id": step["id"], "method": step.get("method", "GET"),
                "path": step["path"], "error": f"{type(err).__name__}: {err}"}

    text = raw.decode("utf-8", errors="replace")
    try:
        payload = normalize(json.loads(text))
    except json.JSONDecodeError:
        payload = text.strip()                    # plain-text responses are part of the contract

    return {"id": step["id"], "method": step.get("method", "GET"), "path": step["path"],
            "status": status, "content_type": ctype, "body": payload}


def capture(spec_path, base_url, out_path):
    spec = json.loads(open(spec_path).read())

    tokens = obtain_tokens(base_url, spec["auth"]) if "auth" in spec else {}

    observations = [call(base_url, step, tokens) for step in spec["steps"]]

    baseline = {"project": spec["project"], "base_url": base_url,
                "authenticated": sorted(tokens),
                "unordered": spec.get("unordered", []),
                "step_count": len(observations), "observations": observations}
    with open(out_path, "w") as fh:
        json.dump(baseline, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    errors = [o for o in observations if "error" in o]
    print(f"captured {len(observations)} steps -> {out_path}")
    if errors:
        print(f"  {len(errors)} step(s) could not be reached:")
        for o in errors:
            print(f"    {o['id']:<28} {o['method']:<6} {o['path']}  {o['error']}")
        return 1
    by_status = {}
    for o in observations:
        by_status[o["status"]] = by_status.get(o["status"], 0) + 1
    print("  statuses: " + ", ".join(f"{k}×{v}" for k, v in sorted(by_status.items())))
    return 0


def compare(before_path, after_path, declared_path=None):
    before = json.loads(open(before_path).read())
    after = json.loads(open(after_path).read())
    declared = json.loads(open(declared_path).read())["changes"] if declared_path else {}

    after_by_id = {o["id"]: o for o in after["observations"]}
    unordered = set(before.get("unordered", []))
    matched, diffs = 0, []

    for want in before["observations"]:
        got = after_by_id.get(want["id"])
        if got is None:
            diffs.append((want["id"], "step missing from the replay", None, None))
            continue
        if want.get("status") != got.get("status"):
            diffs.append((want["id"], "status", want.get("status", want.get("error")),
                          got.get("status", got.get("error"))))
            continue
        shape = canonical if want["id"] in unordered else (lambda v: v)
        if shape(want.get("body")) != shape(got.get("body")):
            diffs.append((want["id"], "body", want.get("body"), got.get("body")))
            continue
        matched += 1

    total = len(before["observations"])
    print(f"{matched}/{total} steps match the baseline")
    if unordered:
        print(f"  ({len(unordered)} step(s) compared as multisets: {', '.join(sorted(unordered))})")

    if not declared:
        if diffs:
            print(f"\n{len(diffs)} difference(s) — each is a regression or a declared change:\n")
            for step_id, what, want, got in diffs:
                print(f"  {step_id}  [{what}]")
                if what != "step missing from the replay":
                    print(f"    before: {json.dumps(want, ensure_ascii=False)[:300]}")
                    print(f"    after:  {json.dumps(got, ensure_ascii=False)[:300]}")
        return 0 if not diffs else 1

    # With a declarations file, a difference is only acceptable if it was written down in
    # advance. Undeclared differences are the failures; unused declarations are suspicious
    # too, because they claim a change the replay did not actually produce.
    accounted, undeclared = [], []
    for step_id, what, want, got in diffs:
        (accounted if step_id in declared else undeclared).append((step_id, what, want, got))

    print(f"  {len(accounted)} declared change(s), {len(undeclared)} undeclared")

    if accounted:
        print("\ndeclared changes:\n")
        for step_id, what, want, got in accounted:
            print(f"  {step_id}  [{what}]  {declared[step_id]}")
            print(f"    before: {json.dumps(want, ensure_ascii=False)[:200]}")
            print(f"    after:  {json.dumps(got, ensure_ascii=False)[:200]}")

    if undeclared:
        print(f"\n{len(undeclared)} UNDECLARED difference(s) — these are regressions:\n")
        for step_id, what, want, got in undeclared:
            print(f"  {step_id}  [{what}]")
            print(f"    before: {json.dumps(want, ensure_ascii=False)[:300]}")
            print(f"    after:  {json.dumps(got, ensure_ascii=False)[:300]}")

    changed_ids = {d[0] for d in diffs}
    stale = sorted(set(declared) - changed_ids)
    if stale:
        print(f"\n{len(stale)} declaration(s) for step(s) that did not change: {', '.join(stale)}")
        print("  Either the change was reverted or the declaration is wrong.")

    return 0 if not undeclared and not stale else 1


USAGE = __doc__.split("    python3")[1] if False else (
    "usage:\n"
    "  contract_check.py capture <spec.json> <base-url> <out.json>\n"
    "  contract_check.py compare <before.json> <after.json> [declared.json]"
)

if __name__ == "__main__":
    args = sys.argv[1:]
    if args[:1] == ["capture"] and len(args) == 4:
        sys.exit(capture(args[1], args[2], args[3]))
    if args[:1] == ["compare"] and len(args) in (3, 4):
        sys.exit(compare(args[1], args[2], args[3] if len(args) == 4 else None))
    print(USAGE)
    sys.exit(2)
