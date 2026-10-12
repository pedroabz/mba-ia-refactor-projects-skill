"""Compare a replay against the baseline, call by call.

Reports three outcomes per record:
  match       - same status, same normalized body
  status-diff - the status code changed
  body-diff   - same status, different normalized body

Usage: python .refactor-arch/compare.py baseline.json replay.json [--quiet]
"""
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def diff_keys(a, b, prefix=""):
    """Shallow-ish structural diff, enough to name what changed."""
    out = []
    if type(a) is not type(b):
        return [f"{prefix or '<root>'}: {type(a).__name__} -> {type(b).__name__}"]
    if isinstance(a, dict):
        for key in sorted(set(a) | set(b)):
            path = f"{prefix}.{key}" if prefix else key
            if key not in a:
                out.append(f"+{path} = {json.dumps(b[key], ensure_ascii=False)[:70]}")
            elif key not in b:
                out.append(f"-{path} = {json.dumps(a[key], ensure_ascii=False)[:70]}")
            else:
                out.extend(diff_keys(a[key], b[key], path))
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append(f"{prefix}: list len {len(a)} -> {len(b)}")
        else:
            for i, (x, y) in enumerate(zip(a, b)):
                out.extend(diff_keys(x, y, f"{prefix}[{i}]"))
    elif a != b:
        out.append(f"{prefix}: {json.dumps(a, ensure_ascii=False)[:60]} -> "
                   f"{json.dumps(b, ensure_ascii=False)[:60]}")
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    base, repl = load(sys.argv[1]), load(sys.argv[2])
    quiet = "--quiet" in sys.argv[3:]

    by_label = {r["label"]: r for r in repl["records"]}
    match = status_diff = body_diff = missing = 0
    details = []

    for rec in base["records"]:
        label = rec["label"]
        other = by_label.get(label)
        if other is None:
            missing += 1
            details.append(("MISSING", label, ["not present in replay"]))
            continue
        if rec["status"] != other["status"]:
            status_diff += 1
            details.append(("STATUS", label,
                            [f"{rec['method']} {rec['path']}: "
                             f"{rec['status']} -> {other['status']}"]))
            continue
        d = diff_keys(rec.get("normalized"), other.get("normalized"))
        if d:
            body_diff += 1
            details.append(("BODY", label,
                            [f"{rec['method']} {rec['path']} ({rec['status']})"] + d[:12]))
        else:
            match += 1

    total = len(base["records"])
    print(f"baseline calls : {total}")
    print(f"matched        : {match}")
    print(f"status changed : {status_diff}")
    print(f"body changed   : {body_diff}")
    print(f"missing        : {missing}")
    print()
    if not quiet:
        for kind, label, lines in details:
            print(f"[{kind}] {label}")
            for line in lines:
                print(f"    {line}")
    sys.exit(0 if match == total else 1)


if __name__ == "__main__":
    main()
