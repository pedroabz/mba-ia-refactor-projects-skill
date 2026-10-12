"""Verify each security and data-access fix behaves as claimed.

The baseline replay proves the contract survived. This proves the findings were
actually fixed, which a replay cannot show: an endpoint that still works is not
evidence that it is now guarded.

Usage: python .refactor-arch/verify_fixes.py
"""
import sys

import requests

BASE = "http://127.0.0.1:5000"
results = []


def check(name, condition, detail=""):
    results.append((bool(condition), name, detail))


def token_for(email, password):
    resp = requests.post(f"{BASE}/login", json={"email": email, "password": password})
    if resp.status_code != 200:
        return None
    return resp.json().get("token")


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def main():
    admin = token_for("joao@email.com", "1234")          # role=admin
    plain = token_for("maria@email.com", "abcd")         # role=user

    # --- SEC-04: credentials survived the switch to a real KDF -------------
    check("SEC-04 seeded credentials still authenticate after re-seed",
          admin is not None and plain is not None)
    check("SEC-04 a wrong password is rejected",
          requests.post(f"{BASE}/login",
                        json={"email": "joao@email.com",
                              "password": "wrong"}).status_code == 401)

    # --- SEC-05: guards actually deny ------------------------------------
    guarded = [
        ("GET", "/tasks"), ("POST", "/tasks"), ("GET", "/tasks/1"),
        ("PUT", "/tasks/1"), ("DELETE", "/tasks/1"), ("GET", "/tasks/search"),
        ("GET", "/tasks/stats"), ("GET", "/users"), ("GET", "/users/1"),
        ("PUT", "/users/1"), ("DELETE", "/users/1"), ("GET", "/users/1/tasks"),
        ("GET", "/categories"), ("POST", "/categories"),
        ("PUT", "/categories/1"), ("DELETE", "/categories/1"),
        ("GET", "/reports/summary"), ("GET", "/reports/user/1"),
    ]
    denied = []
    for method, path in guarded:
        code = requests.request(method, f"{BASE}{path}", json={}).status_code
        if code != 401:
            denied.append(f"{method} {path} -> {code}")
    check(f"SEC-05 all {len(guarded)} guarded endpoints return 401 without a token",
          not denied, "; ".join(denied))

    check("SEC-05 public endpoints remain reachable without a token",
          requests.get(f"{BASE}/").status_code == 200
          and requests.get(f"{BASE}/health").status_code == 200
          and requests.post(f"{BASE}/login", json={}).status_code == 400)

    # --- SEC-05: the token is verified, not merely present ----------------
    check("SEC-05 the old fake token is rejected",
          requests.get(f"{BASE}/tasks",
                       headers=auth("fake-jwt-token-1")).status_code == 401)
    check("SEC-05 a tampered token is rejected",
          requests.get(f"{BASE}/tasks",
                       headers=auth(admin[:-4] + "AAAA")).status_code == 401)

    # --- SEC-05: role and ownership enforcement ---------------------------
    check("SEC-05 a plain user cannot list every account (403)",
          requests.get(f"{BASE}/users", headers=auth(plain)).status_code == 403)
    check("SEC-05 an admin can list accounts (200)",
          requests.get(f"{BASE}/users", headers=auth(admin)).status_code == 200)
    check("SEC-05 a plain user cannot read another account (403)",
          requests.get(f"{BASE}/users/1", headers=auth(plain)).status_code == 403)
    check("SEC-05 a plain user can read their own account (200)",
          requests.get(f"{BASE}/users/2", headers=auth(plain)).status_code == 200)
    check("SEC-05 a plain user cannot delete an account (403)",
          requests.delete(f"{BASE}/users/3", headers=auth(plain)).status_code == 403)
    check("SEC-05 a plain user cannot read the全 summary report (403)".replace("全", ""),
          requests.get(f"{BASE}/reports/summary",
                       headers=auth(plain)).status_code == 403)
    check("SEC-05 a plain user cannot create a shared category (403)",
          requests.post(f"{BASE}/categories", json={"name": "x"},
                        headers=auth(plain)).status_code == 403)

    # --- SEC-05: privilege escalation through PUT /users is blocked -------
    escalate = requests.put(f"{BASE}/users/2", json={"role": "admin"},
                            headers=auth(plain))
    check("SEC-05 a plain user cannot promote themselves to admin (403)",
          escalate.status_code == 403, f"got {escalate.status_code}")

    # --- SEC-02: no credential material in any response -------------------
    leaks = []
    for method, path, body, token in [
        ("GET", "/users/1", None, admin),
        ("GET", "/users", None, admin),
        ("POST", "/login", {"email": "joao@email.com", "password": "1234"}, None),
    ]:
        resp = requests.request(method, f"{BASE}{path}", json=body,
                                headers=auth(token) if token else {})
        text = resp.text.lower()
        for needle in ("password", "scrypt", "pbkdf2", "81dc9bdb"):
            if needle in text:
                leaks.append(f"{path}: {needle}")
    check("SEC-02 no response contains a password field or hash material",
          not leaks, "; ".join(leaks))

    # --- API-03: type-unsafe input is a 400 with JSON, not a 500 ----------
    bad = requests.post(f"{BASE}/tasks", json={"title": "valid title",
                                               "priority": "high"},
                        headers=auth(admin))
    check("API-03 a non-numeric priority is a 400 with a JSON body",
          bad.status_code == 400 and bad.headers["Content-Type"].startswith(
              "application/json"),
          f"{bad.status_code} {bad.headers.get('Content-Type')}")
    check("API-03 PUT /categories now validates (empty name rejected)",
          requests.put(f"{BASE}/categories/1", json={"name": ""},
                       headers=auth(admin)).status_code == 400)
    check("API-03 PUT /categories now validates the colour format",
          requests.put(f"{BASE}/categories/1", json={"color": "red"},
                       headers=auth(admin)).status_code == 400)

    # --- SEC-06: no debug traceback, and errors stay JSON -----------------
    missing = requests.get(f"{BASE}/no-such-route", headers=auth(admin))
    check("SEC-06 an unmatched route answers JSON, not an HTML page",
          missing.status_code == 404
          and missing.headers["Content-Type"].startswith("application/json"),
          missing.headers.get("Content-Type", ""))

    # --- DAT-05: pagination is applied and clamped ------------------------
    page = requests.get(f"{BASE}/tasks?limit=3", headers=auth(admin))
    check("DAT-05 limit is honoured on GET /tasks",
          page.status_code == 200 and len(page.json()) == 3,
          f"{len(page.json())} items")
    check("DAT-05 the collection total is reported in X-Total-Count",
          page.headers.get("X-Total-Count", "").isdigit(),
          page.headers.get("X-Total-Count", "<absent>"))
    huge = requests.get(f"{BASE}/tasks?limit=99999", headers=auth(admin))
    check("DAT-05 an oversized limit is clamped server-side",
          len(huge.json()) <= 200, f"{len(huge.json())} items")
    check("DAT-05 a malformed limit is a 400, not a 500",
          requests.get(f"{BASE}/tasks?limit=abc",
                       headers=auth(admin)).status_code == 400)

    # --- API-04: the login rate limit engages -----------------------------
    codes = [requests.post(f"{BASE}/login",
                           json={"email": "joao@email.com",
                                 "password": "wrong"}).status_code
             for _ in range(14)]
    check("API-04 brute force against /login is throttled (429 observed)",
          429 in codes, f"codes={codes}")

    # --- report ------------------------------------------------------------
    width = max(len(name) for _ok, name, _d in results)
    failed = 0
    for ok, name, detail in results:
        mark = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        suffix = f"  [{detail}]" if detail and not ok else ""
        print(f"  {mark}  {name.ljust(width)}{suffix}")
    print()
    print(f"{len(results) - failed}/{len(results)} checks passed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
