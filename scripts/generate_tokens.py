#!/usr/bin/env python3
"""Generate API tokens for all 10 apps. Retries on connection errors."""
import requests, json, time, subprocess, sys

tokens = {}
ADMIN_EMAIL = "admin@experiment.local"
ADMIN_PASS = "Admin123!"

def pg_exec(container, db, sql):
    cmd = ['docker', 'exec', container, 'psql', '-U', 'postgres', '-d', db, '-t', '-A', '-c', sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()

def mysql_exec(container, db, user, pw, sql):
    cmd = ['docker', 'exec', container, 'mysql', '-u', user, f'-p{pw}', db, '-N', '-B', '-e', sql]
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.stdout.strip()

def try_request(method, url, retries=3, delay=5, **kwargs):
    for i in range(retries):
        try:
            r = method(url, timeout=10, **kwargs)
            return r
        except requests.ConnectionError:
            if i < retries - 1:
                print(f"  Connection refused, retry {i+1}/{retries}...")
                time.sleep(delay)
    return None

print("=" * 60)
print("Generating API tokens for all 10 apps")
print("=" * 60)

# 1. Gitea
print("\n[1/10] Gitea...")
# Fix must-change-password flag
pg_exec('pg-gitea', 'gitea', "UPDATE \"user\" SET must_change_password=false WHERE lower_name='experimenter';")
r = try_request(requests.post, 'http://localhost:3000/api/v1/users/experimenter/tokens',
    auth=('experimenter', ADMIN_PASS),
    json={'name': f'exp-{int(time.time())}', 'scopes': ['all']})
if r and r.ok:
    tokens['GITEA_API_TOKEN'] = r.json()['sha1']
    print(f"  OK: {tokens['GITEA_API_TOKEN'][:12]}...")
else:
    print(f"  FAIL: {r.status_code if r else 'no connection'} {r.text[:80] if r else ''}")

# 2. Wiki.js - use GraphQL to create API key
print("\n[2/10] Wiki.js...")
# Wiki.js needs initial admin setup via GraphQL
gql = '{"query":"mutation { authentication { login(username: \\"admin@experiment.local\\", password: \\"Admin123!\\", strategy: \\"local\\") { responseResult { succeeded message } jwt } } }"}'
r = try_request(requests.post, 'http://localhost:3001/graphql',
    headers={'Content-Type': 'application/json'}, data=gql)
if r and r.ok:
    data = r.json()
    jwt = data.get('data', {}).get('authentication', {}).get('login', {}).get('jwt')
    if jwt:
        tokens['WIKIJS_API_TOKEN'] = jwt
        print(f"  OK (JWT): {jwt[:12]}...")
    else:
        # Try to setup admin first
        print(f"  No JWT, trying finalize setup...")
        setup_gql = '{"query":"mutation { site { setup(adminEmail: \\"admin@experiment.local\\", adminPassword: \\"Admin123!\\") { responseResult { succeeded message } } } }"}'
        r2 = try_request(requests.post, 'http://localhost:3001/graphql',
            headers={'Content-Type': 'application/json'}, data=setup_gql)
        if r2:
            print(f"  Setup response: {r2.text[:100]}")
        # Create API key via DB
        import secrets
        api_key = secrets.token_hex(32)
        pg_exec('pg-wiki', 'wikijs',
            f"INSERT INTO \"apiKeys\" (key, expiration, \"isRevoked\", \"createdAt\", \"updatedAt\") VALUES ('{api_key}', '2030-01-01', false, NOW(), NOW()) ON CONFLICT DO NOTHING;")
        tokens['WIKIJS_API_TOKEN'] = api_key
        print(f"  Created DB key: {api_key[:12]}...")
else:
    print(f"  FAIL: {r.status_code if r else 'no connection'}")
    tokens['WIKIJS_API_TOKEN'] = 'placeholder'

# 3. Mattermost
print("\n[3/10] Mattermost...")
r = try_request(requests.post, 'http://localhost:3006/api/v4/users',
    json={'email': ADMIN_EMAIL, 'username': 'experimenter', 'password': ADMIN_PASS})
if r is None:
    print("  FAIL: Mattermost not reachable")
    tokens['MM_API_TOKEN'] = 'placeholder'
else:
    if r.ok or r.status_code == 400:  # 400 = user exists
        # Login
        r2 = try_request(requests.post, 'http://localhost:3006/api/v4/users/login',
            json={'login_id': 'experimenter', 'password': ADMIN_PASS})
        if r2 and r2.ok:
            sess = r2.headers.get('Token', '')
            uid = r2.json()['id']
            # Make admin
            pg_exec('pg-mattermost', 'mattermost',
                f"UPDATE users SET roles='system_admin system_user' WHERE id='{uid}';")
            # Create PAT
            r3 = try_request(requests.post, f'http://localhost:3006/api/v4/users/{uid}/tokens',
                headers={'Authorization': f'Bearer {sess}'},
                json={'description': f'exp-{int(time.time())}'})
            if r3 and r3.ok:
                tokens['MM_API_TOKEN'] = r3.json()['token']
                print(f"  OK: {tokens['MM_API_TOKEN'][:12]}...")
            else:
                print(f"  Token FAIL: {r3.status_code if r3 else 'none'}")
                tokens['MM_API_TOKEN'] = 'placeholder'
        else:
            print(f"  Login FAIL")
            tokens['MM_API_TOKEN'] = 'placeholder'
    else:
        print(f"  User FAIL: {r.status_code}")
        tokens['MM_API_TOKEN'] = 'placeholder'

# 4. Vikunja
print("\n[4/10] Vikunja...")
r = try_request(requests.post, 'http://localhost:3002/api/v1/register',
    json={'username': 'experimenter', 'email': ADMIN_EMAIL, 'password': ADMIN_PASS})
if r is None:
    print("  FAIL: not reachable")
    tokens['VIKUNJA_API_TOKEN'] = 'placeholder'
else:
    r2 = try_request(requests.post, 'http://localhost:3002/api/v1/login',
        json={'username': 'experimenter', 'password': ADMIN_PASS})
    if r2 and r2.ok:
        tokens['VIKUNJA_API_TOKEN'] = r2.json().get('token', '')
        print(f"  OK: {tokens['VIKUNJA_API_TOKEN'][:12]}...")
    else:
        print(f"  Login FAIL: {r2.status_code if r2 else 'none'}")
        tokens['VIKUNJA_API_TOKEN'] = 'placeholder'

# 5. NocoDB
print("\n[5/10] NocoDB...")
r = try_request(requests.post, 'http://localhost:3005/api/v1/auth/user/signup',
    json={'email': ADMIN_EMAIL, 'password': ADMIN_PASS})
if r and r.ok:
    tokens['NOCODB_API_TOKEN'] = r.json().get('token', '')
    print(f"  Signup OK: {tokens['NOCODB_API_TOKEN'][:12]}...")
else:
    r2 = try_request(requests.post, 'http://localhost:3005/api/v1/auth/user/signin',
        json={'email': ADMIN_EMAIL, 'password': ADMIN_PASS})
    if r2 and r2.ok:
        tokens['NOCODB_API_TOKEN'] = r2.json().get('token', '')
        print(f"  Signin OK: {tokens['NOCODB_API_TOKEN'][:12]}...")
    else:
        print(f"  FAIL: {r2.status_code if r2 else 'none'}")
        tokens['NOCODB_API_TOKEN'] = 'placeholder'

# 6. Miniflux
print("\n[6/10] Miniflux...")
r = try_request(requests.post, 'http://localhost:3007/v1/api-keys',
    auth=('admin', ADMIN_PASS),
    json={'description': f'exp-{int(time.time())}'})
if r and r.ok:
    tokens['MINIFLUX_API_TOKEN'] = r.json().get('api_key', '')
    print(f"  OK: {tokens['MINIFLUX_API_TOKEN'][:12]}...")
elif r:
    # Try getting existing keys
    print(f"  Create FAIL ({r.status_code}), using basic auth mode")
    tokens['MINIFLUX_API_TOKEN'] = 'basic:admin:Admin123!'
else:
    print("  FAIL: not reachable")
    tokens['MINIFLUX_API_TOKEN'] = 'placeholder'

# 7. BookStack - default admin is admin@admin.com / password
print("\n[7/10] BookStack...")
# BookStack API tokens must be created via UI or DB. Create via DB.
token_id = 'exp-token-id-001'
token_secret = 'exp-secret-' + str(int(time.time()))
# BookStack stores hashed secrets, so we can't easily inject via DB
# Use the default admin creds instead
r = try_request(requests.get, 'http://localhost:3003/api/books',
    headers={'Authorization': f'Token {token_id}:{token_secret}'})
if r:
    print(f"  API responded: {r.status_code}")
tokens['BOOKSTACK_TOKEN_ID'] = token_id
tokens['BOOKSTACK_TOKEN_SECRET'] = token_secret
print("  Need manual setup: admin@admin.com / password -> Settings -> API Tokens")

# 8. n8n
print("\n[8/10] n8n...")
r = try_request(requests.get, 'http://localhost:3008/api/v1/workflows',
    headers={'X-N8N-API-KEY': 'test'})
if r:
    print(f"  API responded: {r.status_code}")
tokens['N8N_API_KEY'] = 'placeholder'
print("  Need manual setup: Settings > API > Create API Key")

# 9. Leantime
print("\n[9/10] Leantime...")
r = try_request(requests.get, 'http://localhost:3004/')
if r:
    print(f"  Web UI: {r.status_code}")
tokens['LEANTIME_API_KEY'] = 'placeholder'
print("  Need manual setup: initial install + Settings > API")

# 10. Directus
print("\n[10/10] Directus...")
r = try_request(requests.post, 'http://localhost:3009/auth/login',
    json={'email': ADMIN_EMAIL, 'password': ADMIN_PASS})
if r and r.ok:
    data = r.json().get('data', {})
    access_token = data.get('access_token', '')
    # Create a static token for the admin user
    r2 = try_request(requests.get, 'http://localhost:3009/users/me',
        headers={'Authorization': f'Bearer {access_token}'})
    if r2 and r2.ok:
        user_id = r2.json()['data']['id']
        import secrets
        static_token = secrets.token_hex(32)
        r3 = try_request(requests.patch, f'http://localhost:3009/users/{user_id}',
            headers={'Authorization': f'Bearer {access_token}'},
            json={'token': static_token})
        if r3 and r3.ok:
            tokens['DIRECTUS_API_TOKEN'] = static_token
            print(f"  OK (static token): {static_token[:12]}...")
        else:
            tokens['DIRECTUS_API_TOKEN'] = access_token
            print(f"  OK (JWT): {access_token[:12]}...")
    else:
        tokens['DIRECTUS_API_TOKEN'] = access_token
        print(f"  OK (JWT): {access_token[:12]}...")
else:
    print(f"  FAIL: {r.status_code if r else 'no connection'}")
    tokens['DIRECTUS_API_TOKEN'] = 'placeholder'

# Summary
print("\n" + "=" * 60)
auto = sum(1 for v in tokens.values() if v and not v.startswith('placeholder') and not v.startswith('will') and not v.startswith('exp-'))
manual = sum(1 for v in tokens.values() if v.startswith('placeholder') or v.startswith('will') or v.startswith('exp-'))
print(f"Auto-generated: {auto} | Need manual setup: {manual}")

# Save
with open('tokens.json', 'w') as f:
    json.dump(tokens, f, indent=2)

# Also append to .env
with open('.env', 'a') as f:
    f.write('\n# Auto-generated API tokens\n')
    for k, v in tokens.items():
        if v and not v.startswith('placeholder') and not v.startswith('will') and not v.startswith('exp-'):
            f.write(f'{k}={v}\n')

print("Tokens saved to tokens.json and appended to .env")
