import requests
import os

session = requests.Session()
domain = "www.dramaboxdb.com"
cookie_file = os.path.join("config", f"{domain}_cookies.txt")

print(f"Loading cookies from {cookie_file}")

if os.path.exists(cookie_file):
    with open(cookie_file, 'r') as f:
        for line in f:
            if line.startswith('#') or not line.strip():
                continue
            parts = line.strip().split('\t')
            if len(parts) >= 7:
                # domain, flag, path, secure, expiration, name, value
                # parts[0] is typically .dramaboxdb.com or www.dramaboxdb.com
                session.cookies.set(parts[5], parts[6], domain=parts[0])
                print(f"Set cookie: {parts[5]} for domain {parts[0]}")

target_url = "https://hwzthls.dramaboxdb.com/test.m3u8"

# Create a prepared request to inspect headers without sending
req = requests.Request('GET', target_url)
prepped = session.prepare_request(req)

print("\n--- Headers that WOULD be sent ---")
for k, v in prepped.headers.items():
    print(f"{k}: {v}")

print("\n--- Cookie Jar Content ---")
for cookie in session.cookies:
    print(cookie)
