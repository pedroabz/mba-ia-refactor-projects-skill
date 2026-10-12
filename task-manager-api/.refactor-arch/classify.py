"""Classify each baseline/replay divergence as intended or a regression.

The declared intentional changes are listed below, each tied to the finding it
fixes. Anything that does not match one of them is reported as UNEXPLAINED,
which is the only outcome that should fail the validation.

Usage: python .refactor-arch/classify.py baseline.json replay.json
"""
import json
import re
import sys

sys.path.insert(0, ".refactor-arch")
from compare import diff_keys, load  # noqa: E402

# --- declared intentional changes -------------------------------------------
# (label regex, description, matcher over a single diff line)
ADDED_TASK_FIELDS = ("overdue", "user_name", "category_name",
                     "user_id", "category_id", "updated_at", "tags")

INTENTIONAL = [
    (
        "API-05/T-17: canonical task shape adds the fields that were missing "
        "from some task representations",
        lambda line: line.startswith("+") and any(
            line[1:].split(" = ")[0].split(".")[-1] == f for f in ADDED_TASK_FIELDS
        ),
    ),
    (
        "SEC-02/T-04: the stored password hash is no longer serialized",
        lambda line: re.fullmatch(r"-(?:user\.)?password = .*", line) is not None,
    ),
    (
        "API-03/T-15: validation failures carry field-level `details`",
        lambda line: line.startswith("+details"),
    ),
]

STATUS_INTENTIONAL = [
    (
        {("POST", "/tasks", 500, 400),
         ("GET", "/tasks/search?priority=abc", 500, 400),
         ("GET", "/tasks/search?user_id=abc", 500, 400)},
        "API-03/T-15: type-unsafe input is a client error, not a server fault "
        "(and no longer answered with a Werkzeug debug page)",
    ),
]


def classify_line(line):
    for description, matcher in INTENTIONAL:
        if matcher(line):
            return description
    return None


def main():
    base, repl = load(sys.argv[1]), load(sys.argv[2])
    by_label = {r["label"]: r for r in repl["records"]}

    identical = 0
    explained = {}
    unexplained = []
    status_explained = {}

    for rec in base["records"]:
        label = rec["label"]
        other = by_label.get(label)
        if other is None:
            unexplained.append((label, ["missing from replay"]))
            continue

        if rec["status"] != other["status"]:
            key = (rec["method"], rec["path"], rec["status"], other["status"])
            matched = None
            for keys, description in STATUS_INTENTIONAL:
                if key in keys:
                    matched = description
            if matched:
                status_explained.setdefault(matched, []).append(label)
            else:
                unexplained.append(
                    (label, [f"status {rec['status']} -> {other['status']}"])
                )
            continue

        lines = diff_keys(rec.get("normalized"), other.get("normalized"))
        if not lines:
            identical += 1
            continue

        bad = []
        for line in lines:
            description = classify_line(line)
            if description:
                explained.setdefault(description, set()).add(label)
            else:
                bad.append(line)
        if bad:
            unexplained.append((label, bad))

    total = len(base["records"])
    accounted = identical + sum(len(v) for v in explained.values()) + 0
    print(f"baseline calls                    : {total}")
    print(f"byte-identical                    : {identical}")
    print(f"differ only by a declared change  : "
          f"{total - identical - len(unexplained)}")
    print(f"UNEXPLAINED                       : {len(unexplained)}")
    print()
    print("Declared intentional changes observed:")
    for description, labels in status_explained.items():
        print(f"  [status] {description}")
        print(f"           {len(labels)} endpoint(s): {', '.join(sorted(labels))}")
    for description, labels in explained.items():
        print(f"  [body]   {description}")
        print(f"           {len(labels)} endpoint(s)")
    if unexplained:
        print()
        print("UNEXPLAINED DIVERGENCES (these are regressions):")
        for label, lines in unexplained:
            print(f"  {label}")
            for line in lines[:8]:
                print(f"      {line}")
    sys.exit(1 if unexplained else 0)


if __name__ == "__main__":
    main()
