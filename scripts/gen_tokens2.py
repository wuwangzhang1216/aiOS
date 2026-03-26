#!/usr/bin/env python3
"""Generate API tokens for all 10 apps (v2)."""
import re
import requests
import json
import time
import subprocess
import secrets

tokens = {}

def pg_exec(container, db, sql):
    cmd = ['docker', 'exec', container, 'psql', '-U', 'postgres', '-d', db, '-t', '-A', '-c', sql]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()

print("=" * 60)
print("Generating API tokens for all 10 apps")
print("=" * 60)

# 1. Gitea
print("\n[1] Gitea...")
pg_exec('pg-gitea', 'gitea', "UPDATE \"user\" SET must_change_password=false WHERE lower_name='experimenter';")
r = requests.post('http://localhost:3000/api/v1/users/experimenter/tokens',
    auth=('experimenter', 'Admin123!'),
    json={'name': f'exp-{int(time.time())}', 'scopes': ['all']}, timeout=5)
tokens['GITEA_API_TOKEN'] = r.json()['sha1'] if r.ok else 'FAIL'
print(f"  {'OK' if r.ok else 'FAIL'}")

# 2. Wiki.js
print("\n[2] Wiki.js...")
key = secrets.token_hex(32)
try:
    result = pg_exec('pg-wiki', 'wikijs',
        f"INSERT INTO \"apiKeys\" (key, expiration, \"isRevoked\", \"createdAt\", \"updatedAt\") "
        f"VALUES ('{key}', '2030-01-01', false, NOW(), NOW()) RETURNING key;")
    if key in result:
        tokens['WIKIJS_API_TOKEN'] = key
        print(f"  OK (DB key: {key[:12]}...)")
    else:
        tokens['WIKIJS_API_TOKEN'] = key
        print(f"  Inserted (may have worked): {result[:50]}")
except Exception as e:
    tokens['WIKIJS_API_TOKEN'] = 'FAIL'
    print(f"  FAIL: {e}")

# 3. Mattermost
print("\n[3] Mattermost...")
try:
    # Try login first
    r = requests.post('http://localhost:3006/api/v4/users/login',
        json={'login_id': 'experimenter', 'password': 'Admin123!'}, timeout=5)
    if not r.ok:
        # Create user
        r2 = requests.post('http://localhost:3006/api/v4/users',
            json={'email': 'admin@experiment.local', 'username': 'experimenter', 'password': 'Admin123!'}, timeout=5)
        print(f"  User create: {r2.status_code}")
        r = requests.post('http://localhost:3006/api/v4/users/login',
            json={'login_id': 'experimenter', 'password': 'Admin123!'}, timeout=5)

    if r.ok:
        sess = r.headers.get('Token', '')
        uid = r.json()['id']
        pg_exec('pg-mattermost', 'mattermost',
            f"UPDATE users SET roles='system_admin system_user' WHERE id='{uid}';")
        r4 = requests.post(f'http://localhost:3006/api/v4/users/{uid}/tokens',
            headers={'Authorization': f'Bearer {sess}'},
            json={'description': f'exp-{int(time.time())}'}, timeout=5)
        if r4.ok:
            tokens['MM_API_TOKEN'] = r4.json()['token']
            print(f"  OK")
        else:
            tokens['MM_API_TOKEN'] = 'FAIL'
            print(f"  Token FAIL: {r4.status_code} {r4.text[:80]}")
    else:
        tokens['MM_API_TOKEN'] = 'FAIL'
        print(f"  Login FAIL: {r.status_code}")
except Exception as e:
    tokens['MM_API_TOKEN'] = 'FAIL'
    print(f"  FAIL: {e}")

# 4. Vikunja
print("\n[4] Vikunja...")
try:
    r = requests.post('http://localhost:3002/api/v1/login',
        json={'username': 'experimenter', 'password': 'Admin123!'}, timeout=5)
    if not r.ok:
        requests.post('http://localhost:3002/api/v1/register',
            json={'username': 'experimenter', 'email': 'admin@exp.local', 'password': 'Admin123!'}, timeout=5)
        r = requests.post('http://localhost:3002/api/v1/login',
            json={'username': 'experimenter', 'password': 'Admin123!'}, timeout=5)
    tokens['VIKUNJA_API_TOKEN'] = r.json().get('token', 'FAIL') if r.ok else 'FAIL'
    print(f"  {'OK' if r.ok else 'FAIL'}")
except Exception as e:
    tokens['VIKUNJA_API_TOKEN'] = 'FAIL'
    print(f"  FAIL: {e}")

# 5. NocoDB
print("\n[5] NocoDB...")
try:
    r = requests.post('http://localhost:3005/api/v1/auth/user/signin',
        json={'email': 'admin@experiment.local', 'password': 'Admin123!'}, timeout=5)
    if not r.ok:
        r = requests.post('http://localhost:3005/api/v1/auth/user/signup',
            json={'email': 'admin@experiment.local', 'password': 'Admin123!'}, timeout=5)
    tokens['NOCODB_API_TOKEN'] = r.json().get('token', 'FAIL') if r.ok else 'FAIL'
    print(f"  {'OK' if r.ok else 'FAIL'}")
except Exception as e:
    tokens['NOCODB_API_TOKEN'] = 'FAIL'
    print(f"  FAIL: {e}")

# 6. Miniflux
print("\n[6] Miniflux...")
try:
    r = requests.post('http://localhost:3007/v1/api-keys', auth=('admin', 'Admin123!'),
        json={'description': f'exp-{int(time.time())}'}, timeout=5)
    if r.ok:
        tokens['MINIFLUX_API_TOKEN'] = r.json().get('api_key', 'FAIL')
        print(f"  OK")
    else:
        # Use basic auth instead
        tokens['MINIFLUX_API_TOKEN'] = 'basic:admin:Admin123!'
        print(f"  Using basic auth fallback")
except Exception as e:
    tokens['MINIFLUX_API_TOKEN'] = 'FAIL'
    print(f"  FAIL: {e}")

# 7. BookStack
print("\n[7] BookStack...")
try:
    s = requests.Session()
    login_page = s.get('http://localhost:3003/login', timeout=10)
    csrf = re.search(r'name="_token" value="([^"]+)"', login_page.text)
    if csrf:
        s.post('http://localhost:3003/login', data={
            '_token': csrf.group(1), 'email': 'admin@admin.com', 'password': 'password'
        }, timeout=10)
        # Try API endpoint to verify login
        me = s.get('http://localhost:3003/settings/users/1', timeout=10)
        if me.ok:
            print(f"  Logged in. Creating API token...")
            # Navigate to API tokens page
            api_page = s.get('http://localhost:3003/api-tokens', timeout=10)
            csrf2 = re.search(r'name="_token" value="([^"]+)"', api_page.text)
            if csrf2:
                r2 = s.post('http://localhost:3003/api-tokens', data={
                    '_token': csrf2.group(1), 'name': f'experiment', 'expires_at': '2030-01-01'
                }, timeout=10, allow_redirects=True)
                # Try to find token ID and secret in the response
                tid = re.search(r'Token ID[^<]*<[^>]*>([^<]+)', r2.text)
                tsec = re.search(r'Token Secret[^<]*<[^>]*>([^<]+)', r2.text)
                if tid and tsec:
                    tokens['BOOKSTACK_TOKEN_ID'] = tid.group(1).strip()
                    tokens['BOOKSTACK_TOKEN_SECRET'] = tsec.group(1).strip()
                    print(f"  OK (ID: {tokens['BOOKSTACK_TOKEN_ID'][:12]}...)")
                else:
                    # Fallback: get from DB
                    result = subprocess.run(['docker', 'exec', 'mysql-bookstack', 'mysql', '-u', 'bookstack',
                        '-psecret', 'bookstack', '-N', '-B', '-e',
                        "SELECT token_id, secret FROM api_tokens ORDER BY id DESC LIMIT 1;"],
                        capture_output=True, text=True)
                    parts = result.stdout.strip().split('\t')
                    if len(parts) == 2:
                        tokens['BOOKSTACK_TOKEN_ID'] = parts[0]
                        tokens['BOOKSTACK_TOKEN_SECRET'] = parts[1]
                        print(f"  OK (from DB)")
                    else:
                        tokens['BOOKSTACK_TOKEN_ID'] = 'FAIL'
                        tokens['BOOKSTACK_TOKEN_SECRET'] = 'FAIL'
                        print(f"  Could not get token from DB: {result.stdout[:80]}")
            else:
                tokens['BOOKSTACK_TOKEN_ID'] = 'FAIL'
                tokens['BOOKSTACK_TOKEN_SECRET'] = 'FAIL'
                print(f"  No CSRF on api-tokens page")
        else:
            tokens['BOOKSTACK_TOKEN_ID'] = 'FAIL'
            tokens['BOOKSTACK_TOKEN_SECRET'] = 'FAIL'
            print(f"  Login failed")
    else:
        tokens['BOOKSTACK_TOKEN_ID'] = 'FAIL'
        tokens['BOOKSTACK_TOKEN_SECRET'] = 'FAIL'
        print(f"  No CSRF on login page")
except Exception as e:
    tokens['BOOKSTACK_TOKEN_ID'] = 'FAIL'
    tokens['BOOKSTACK_TOKEN_SECRET'] = 'FAIL'
    print(f"  FAIL: {e}")

# 8. n8n
print("\n[8] n8n...")
try:
    # Setup owner
    requests.post('http://localhost:3008/rest/owner/setup', json={
        'email': 'admin@experiment.local', 'password': 'Admin123!',
        'firstName': 'Admin', 'lastName': 'User'
    }, timeout=5)
    # Login
    r2 = requests.post('http://localhost:3008/rest/login', json={
        'email': 'admin@experiment.local', 'password': 'Admin123!'
    }, timeout=5)
    if r2.ok:
        cookies = r2.cookies
        r3 = requests.post('http://localhost:3008/rest/api-keys',
            cookies=cookies,
            json={'label': f'experiment-{int(time.time())}'}, timeout=5)
        if r3.ok:
            data = r3.json().get('data', {})
            tokens['N8N_API_KEY'] = data.get('rawApiKey', data.get('apiKey', 'FAIL'))
            print(f"  OK")
        else:
            tokens['N8N_API_KEY'] = 'FAIL'
            print(f"  API key FAIL: {r3.status_code} {r3.text[:80]}")
    else:
        tokens['N8N_API_KEY'] = 'FAIL'
        print(f"  Login FAIL: {r2.status_code}")
except Exception as e:
    tokens['N8N_API_KEY'] = 'FAIL'
    print(f"  FAIL: {e}")

# 9. Leantime
print("\n[9] Leantime...")
tokens['LEANTIME_API_KEY'] = 'FAIL'
print("  SKIP (empty reply from server, will use DB only)")

# 10. Directus
print("\n[10] Directus...")
try:
    r = requests.post('http://localhost:3009/auth/login',
        json={'email': 'admin@experiment.com', 'password': 'Admin123!'}, timeout=5)
    if r.ok:
        access_token = r.json().get('data', {}).get('access_token', '')
        r2 = requests.get('http://localhost:3009/users/me',
            headers={'Authorization': f'Bearer {access_token}'}, timeout=5)
        if r2.ok:
            uid = r2.json()['data']['id']
            static = secrets.token_hex(32)
            r3 = requests.patch(f'http://localhost:3009/users/{uid}',
                headers={'Authorization': f'Bearer {access_token}'},
                json={'token': static}, timeout=5)
            tokens['DIRECTUS_API_TOKEN'] = static if r3.ok else access_token
            print(f"  OK (static token)")
        else:
            tokens['DIRECTUS_API_TOKEN'] = access_token
            print(f"  OK (JWT)")
    else:
        tokens['DIRECTUS_API_TOKEN'] = 'FAIL'
        print(f"  FAIL: {r.status_code} {r.text[:80]}")
except Exception as e:
    tokens['DIRECTUS_API_TOKEN'] = 'FAIL'
    print(f"  FAIL: {e}")

# Summary
print("\n" + "=" * 60)
ok_count = sum(1 for v in tokens.values() if 'FAIL' not in str(v))
print(f"Tokens OK: {ok_count}/{len(tokens)}")
for k, v in tokens.items():
    status = "OK" if 'FAIL' not in str(v) else "FAIL"
    val_preview = str(v)[:20] + "..." if len(str(v)) > 20 else str(v)
    print(f"  {k}: [{status}] {val_preview}")

# Save
with open('tokens.json', 'w') as f:
    json.dump(tokens, f, indent=2)

# Write .env.tokens with only successful ones
with open('.env.tokens', 'w') as f:
    for k, v in tokens.items():
        if 'FAIL' not in str(v):
            f.write(f'{k}={v}\n')

print(f"\nSaved to tokens.json and .env.tokens")
