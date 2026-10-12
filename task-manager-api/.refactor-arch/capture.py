"""Capture the endpoint contract of the Task Manager API.

Used twice: once against the pre-refactor application to produce the baseline,
and once against the refactored application to replay it. Writes a JSON file
holding method, path, status and response body for every call.

Volatile values (generated ids, timestamps, elapsed-day counts) are masked in a
parallel `normalized` field so two runs taken minutes apart can be compared
field by field. The raw body is kept too, so a divergence can be inspected.

Usage: python .refactor-arch/capture.py <out.json> [--auth]

--auth logs in as the seeded admin and sends `Authorization: Bearer <token>` on
every call. The pre-refactor application ignores the header entirely, so the
same script produces a comparable record on both sides of the refactor.
"""
import json
import re
import sys

import requests

BASE = "http://127.0.0.1:5000"
TIMEOUT = 20

# Keys whose values differ between two runs by construction.
VOLATILE_KEYS = {
    "created_at", "updated_at", "generated_at", "timestamp",
    "due_date", "days_overdue", "token",
}
ISO_DATETIME = re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(\.\d+)?")


def normalize(value, key=None):
    """Mask values that cannot be stable across runs, keeping structure intact."""
    if key in VOLATILE_KEYS:
        return "<volatile>" if value is not None else None
    if isinstance(value, dict):
        return {k: normalize(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, str):
        if ISO_DATETIME.search(value):
            return ISO_DATETIME.sub("<datetime>", value)
        # Ids embedded in the seeded fake token, and nothing else.
        return value
    return value


class Capture:
    def __init__(self, auth):
        self.records = []
        self.session = requests.Session()
        self.auth = auth
        self.token = None
        self.ids = {}

    def login(self):
        """Obtain a token when running in --auth mode. Never recorded as a call."""
        resp = self.session.post(
            f"{BASE}/login",
            json={"email": "joao@email.com", "password": "1234"},
            timeout=TIMEOUT,
        )
        if resp.status_code == 200:
            self.token = resp.json().get("token")
        return resp.status_code, self.token is not None

    def call(self, label, method, path, body=None, expect_json=True):
        headers = {}
        if self.auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        url = f"{BASE}{path}"
        try:
            resp = self.session.request(
                method, url, json=body, headers=headers, timeout=TIMEOUT
            )
        except requests.RequestException as exc:
            record = {
                "label": label, "method": method, "path": path,
                "status": None, "error": f"{type(exc).__name__}: {exc}",
            }
            self.records.append(record)
            return record

        if expect_json:
            try:
                parsed = resp.json()
            except ValueError:
                # A debug traceback page, or any non-JSON body. Record only the
                # fact and the length; the HTML itself is machine noise.
                parsed = {"__non_json__": True, "length": len(resp.content)}
        else:
            parsed = {"__non_json__": True, "length": len(resp.content)}

        record = {
            "label": label,
            "method": method,
            "path": path,
            "request_body": body,
            "status": resp.status_code,
            "body": parsed,
            "normalized": normalize(parsed),
        }
        self.records.append(record)
        return record


def run(auth):
    cap = Capture(auth)
    if auth:
        status, ok = cap.login()
        if not ok:
            print(f"!! login failed ({status}); guarded calls will record 401", file=sys.stderr)

    # ---------- reads first: writes below change what these return ----------
    cap.call("root", "GET", "/")
    cap.call("health", "GET", "/health")

    cap.call("tasks.list", "GET", "/tasks")
    cap.call("tasks.get", "GET", "/tasks/1")
    cap.call("tasks.get.missing", "GET", "/tasks/9999")
    cap.call("tasks.search.q", "GET", "/tasks/search?q=bug")
    cap.call("tasks.search.status", "GET", "/tasks/search?status=pending")
    cap.call("tasks.search.priority", "GET", "/tasks/search?priority=1")
    cap.call("tasks.search.user", "GET", "/tasks/search?user_id=1")
    cap.call("tasks.search.empty", "GET", "/tasks/search")
    cap.call("tasks.stats", "GET", "/tasks/stats")

    cap.call("users.list", "GET", "/users")
    cap.call("users.get", "GET", "/users/1")
    cap.call("users.get.missing", "GET", "/users/9999")
    cap.call("users.tasks", "GET", "/users/1/tasks")
    cap.call("users.tasks.missing", "GET", "/users/9999/tasks")

    cap.call("categories.list", "GET", "/categories")
    cap.call("reports.summary", "GET", "/reports/summary")
    cap.call("reports.user", "GET", "/reports/user/1")
    cap.call("reports.user.missing", "GET", "/reports/user/9999")

    # ---------- error paths that are cheap to trigger ----------
    cap.call("login.ok", "POST", "/login",
             {"email": "joao@email.com", "password": "1234"})
    cap.call("login.badpass", "POST", "/login",
             {"email": "joao@email.com", "password": "wrong"})
    cap.call("login.nouser", "POST", "/login",
             {"email": "nobody@email.com", "password": "x"})
    cap.call("login.missing", "POST", "/login", {"email": "joao@email.com"})
    cap.call("login.empty", "POST", "/login", {})

    cap.call("tasks.create.notitle", "POST", "/tasks", {"description": "x"})
    cap.call("tasks.create.shorttitle", "POST", "/tasks", {"title": "ab"})
    cap.call("tasks.create.longtitle", "POST", "/tasks", {"title": "x" * 201})
    cap.call("tasks.create.badstatus", "POST", "/tasks",
             {"title": "valid title", "status": "nope"})
    cap.call("tasks.create.badpriority", "POST", "/tasks",
             {"title": "valid title", "priority": 9})
    cap.call("tasks.create.baduser", "POST", "/tasks",
             {"title": "valid title", "user_id": 9999})
    cap.call("tasks.create.badcategory", "POST", "/tasks",
             {"title": "valid title", "category_id": 9999})
    cap.call("tasks.create.baddate", "POST", "/tasks",
             {"title": "valid title", "due_date": "31/02/2026"})
    cap.call("tasks.create.empty", "POST", "/tasks", {})

    # Type-unsafe input: API-03. Pre-refactor these are 500s (or debug pages).
    cap.call("tasks.create.strpriority", "POST", "/tasks",
             {"title": "valid title", "priority": "high"})
    cap.call("tasks.search.strpriority", "GET", "/tasks/search?priority=abc")
    cap.call("tasks.search.struser", "GET", "/tasks/search?user_id=abc")

    cap.call("users.create.noname", "POST", "/users",
             {"email": "a@b.com", "password": "1234"})
    cap.call("users.create.noemail", "POST", "/users",
             {"name": "A", "password": "1234"})
    cap.call("users.create.nopass", "POST", "/users",
             {"name": "A", "email": "a@b.com"})
    cap.call("users.create.bademail", "POST", "/users",
             {"name": "A", "email": "not-an-email", "password": "1234"})
    cap.call("users.create.shortpass", "POST", "/users",
             {"name": "A", "email": "a@b.com", "password": "12"})
    cap.call("users.create.dupemail", "POST", "/users",
             {"name": "A", "email": "joao@email.com", "password": "1234"})
    cap.call("users.create.badrole", "POST", "/users",
             {"name": "A", "email": "a@b.com", "password": "1234", "role": "root"})

    cap.call("categories.create.noname", "POST", "/categories", {"description": "x"})
    cap.call("categories.update.missing", "PUT", "/categories/9999", {"name": "x"})
    cap.call("categories.delete.missing", "DELETE", "/categories/9999")
    cap.call("tasks.update.missing", "PUT", "/tasks/9999", {"title": "abc"})
    cap.call("tasks.delete.missing", "DELETE", "/tasks/9999")
    cap.call("users.update.missing", "PUT", "/users/9999", {"name": "x"})
    cap.call("users.delete.missing", "DELETE", "/users/9999")

    # ---------- writes: create, read back, update, delete ----------
    created = cap.call("tasks.create.ok", "POST", "/tasks", {
        "title": "Baseline task",
        "description": "created by the capture harness",
        "status": "pending",
        "priority": 2,
        "user_id": 1,
        "category_id": 1,
        "due_date": "2026-12-31",
        "tags": ["baseline", "harness"],
    })
    task_id = (created.get("body") or {}).get("id")
    cap.ids["task"] = task_id
    if task_id:
        cap.call("tasks.get.created", "GET", f"/tasks/{task_id}")
        cap.call("tasks.update.ok", "PUT", f"/tasks/{task_id}", {
            "title": "Baseline task updated",
            "status": "in_progress",
            "priority": 1,
            "tags": ["updated"],
        })
        cap.call("tasks.update.badstatus", "PUT", f"/tasks/{task_id}",
                 {"status": "nope"})
        cap.call("tasks.update.cleardate", "PUT", f"/tasks/{task_id}",
                 {"due_date": None})
        cap.call("tasks.delete.ok", "DELETE", f"/tasks/{task_id}")
        cap.call("tasks.get.deleted", "GET", f"/tasks/{task_id}")

    cat = cap.call("categories.create.ok", "POST", "/categories",
                   {"name": "Baseline cat", "description": "d", "color": "#abcdef"})
    cat_id = (cat.get("body") or {}).get("id")
    cap.ids["category"] = cat_id
    if cat_id:
        cap.call("categories.update.ok", "PUT", f"/categories/{cat_id}",
                 {"name": "Baseline cat renamed", "color": "#123456"})
        # DAT-03: a task pointing at the category about to be deleted.
        orphan = cap.call("tasks.create.fororphan", "POST", "/tasks",
                          {"title": "Task that will be orphaned",
                           "category_id": cat_id})
        orphan_id = (orphan.get("body") or {}).get("id")
        cap.ids["orphan_task"] = orphan_id
        cap.call("categories.delete.ok", "DELETE", f"/categories/{cat_id}")
        if orphan_id:
            # Pre-refactor: category_id still points at the deleted row.
            cap.call("tasks.get.orphaned", "GET", f"/tasks/{orphan_id}")
            cap.call("tasks.delete.orphan", "DELETE", f"/tasks/{orphan_id}")

    usr = cap.call("users.create.ok", "POST", "/users",
                   {"name": "Baseline User", "email": "baseline@email.com",
                    "password": "1234", "role": "user"})
    user_id = (usr.get("body") or {}).get("id")
    cap.ids["user"] = user_id
    if user_id:
        cap.call("users.get.created", "GET", f"/users/{user_id}")
        cap.call("users.update.ok", "PUT", f"/users/{user_id}",
                 {"name": "Baseline User renamed", "active": False})
        cap.call("users.update.bademail", "PUT", f"/users/{user_id}",
                 {"email": "bad"})
        cap.call("users.update.dupemail", "PUT", f"/users/{user_id}",
                 {"email": "joao@email.com"})
        cap.call("users.login.inactive", "POST", "/login",
                 {"email": "baseline@email.com", "password": "1234"})
        # Cascade: this user owns a task created below.
        cap.call("tasks.create.foruser", "POST", "/tasks",
                 {"title": "Task owned by baseline user", "user_id": user_id})
        cap.call("users.delete.ok", "DELETE", f"/users/{user_id}")
        cap.call("users.get.deleted", "GET", f"/users/{user_id}")

    # ---------- final state of the collections ----------
    cap.call("tasks.list.final", "GET", "/tasks")
    cap.call("users.list.final", "GET", "/users")
    cap.call("categories.list.final", "GET", "/categories")
    cap.call("tasks.stats.final", "GET", "/tasks/stats")

    return cap


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    out = sys.argv[1]
    auth = "--auth" in sys.argv[2:]
    cap = run(auth)
    payload = {
        "auth_mode": auth,
        "base": BASE,
        "generated_ids": cap.ids,
        "count": len(cap.records),
        "records": cap.records,
    }
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False, sort_keys=False)
    statuses = {}
    for rec in cap.records:
        statuses[rec["status"]] = statuses.get(rec["status"], 0) + 1
    print(f"wrote {out}: {len(cap.records)} calls")
    print("status distribution:", dict(sorted(statuses.items(), key=lambda kv: (kv[0] is None, kv[0]))))


if __name__ == "__main__":
    main()
