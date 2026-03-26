#!/usr/bin/env python3
"""Generate API tokens for the 4 experiment apps."""
import requests
import json
import time
import subprocess

tokens = {}
ADMIN_PASS = "Admin123!"


def pg_exec(container, db, sql):
    cmd = ["docker", "exec", container, "psql", "-U", "postgres", "-d", db, "-t", "-A", "-c", sql]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def try_request(method, url, retries=3, delay=5, **kwargs):
    for i in range(retries):
        try:
            return method(url, timeout=10, **kwargs)
        except requests.ConnectionError:
            if i < retries - 1:
                print(f"  Retry {i+1}/{retries}...")
                time.sleep(delay)
    return None


print("=" * 50)
print("Generating API tokens (4 apps)")
print("=" * 50)

# 1. Gitea
print("\n[1/4] Gitea...")
pg_exec("pg-gitea", "gitea",
        "UPDATE \"user\" SET must_change_password=false WHERE lower_name='experimenter';")
r = try_request(requests.post, "http://localhost:3000/api/v1/users/experimenter/tokens",
                auth=("experimenter", ADMIN_PASS),
                json={"name": f"exp-{int(time.time())}", "scopes": ["all"]})
if r and r.ok:
    tokens["GITEA_API_TOKEN"] = r.json()["sha1"]
    print(f"  OK: {tokens['GITEA_API_TOKEN'][:12]}...")
else:
    tokens["GITEA_API_TOKEN"] = "FAIL"
    print(f"  FAIL: {r.status_code if r else 'no connection'}")

# 2. Miniflux
print("\n[2/4] Miniflux...")
r = try_request(requests.post, "http://localhost:3001/v1/api-keys",
                auth=("admin", ADMIN_PASS),
                json={"description": f"exp-{int(time.time())}"})
if r and r.ok:
    tokens["MINIFLUX_API_TOKEN"] = r.json().get("api_key", "")
    print(f"  OK: {tokens['MINIFLUX_API_TOKEN'][:12]}...")
else:
    tokens["MINIFLUX_API_TOKEN"] = "basic:admin:Admin123!"
    print("  Using basic auth fallback")

# 3. Vikunja
print("\n[3/4] Vikunja...")
try_request(requests.post, "http://localhost:3002/api/v1/register",
            json={"username": "experimenter", "email": "admin@exp.local", "password": ADMIN_PASS})
r = try_request(requests.post, "http://localhost:3002/api/v1/login",
                json={"username": "experimenter", "password": ADMIN_PASS})
if r and r.ok:
    tokens["VIKUNJA_API_TOKEN"] = r.json().get("token", "FAIL")
    print(f"  OK: {tokens['VIKUNJA_API_TOKEN'][:12]}...")
else:
    tokens["VIKUNJA_API_TOKEN"] = "FAIL"
    print(f"  FAIL: {r.status_code if r else 'no connection'}")

# 4. Mattermost
print("\n[4/4] Mattermost...")
try_request(requests.post, "http://localhost:3003/api/v4/users",
            json={"email": "admin@experiment.local", "username": "experimenter", "password": ADMIN_PASS})
r = try_request(requests.post, "http://localhost:3003/api/v4/users/login",
                json={"login_id": "experimenter", "password": ADMIN_PASS})
if r and r.ok:
    sess = r.headers.get("Token", "")
    uid = r.json()["id"]
    pg_exec("pg-mattermost", "mattermost",
            f"UPDATE users SET roles='system_admin system_user' WHERE id='{uid}';")
    r2 = try_request(requests.post, f"http://localhost:3003/api/v4/users/{uid}/tokens",
                     headers={"Authorization": f"Bearer {sess}"},
                     json={"description": f"exp-{int(time.time())}"})
    if r2 and r2.ok:
        tokens["MM_API_TOKEN"] = r2.json()["token"]
        print(f"  OK: {tokens['MM_API_TOKEN'][:12]}...")
    else:
        tokens["MM_API_TOKEN"] = "FAIL"
        print(f"  Token FAIL: {r2.status_code if r2 else 'none'}")
else:
    tokens["MM_API_TOKEN"] = "FAIL"
    print(f"  Login FAIL: {r.status_code if r else 'no connection'}")

# Summary
print("\n" + "=" * 50)
ok = sum(1 for v in tokens.values() if "FAIL" not in str(v))
print(f"Tokens OK: {ok}/{len(tokens)}")
for k, v in tokens.items():
    status = "OK" if "FAIL" not in str(v) else "FAIL"
    print(f"  {k}: [{status}] {str(v)[:20]}...")

with open(".env.tokens", "w") as f:
    for k, v in tokens.items():
        if "FAIL" not in str(v):
            f.write(f"{k}={v}\n")

print(f"\nSaved to .env.tokens")
