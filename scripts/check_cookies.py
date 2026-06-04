import sys
import os
import requests

arl = os.environ.get("DEEZER_ARL", None)
sid = os.environ.get("DEEZER_SID", None)

if not arl or not sid:
    print("Missing arl or sid environment variables.")
    sys.exit(1)

req = requests.Session()

req.cookies.update({
    "arl": arl,
    "sid": sid
})
req.headers.update({
    'User-Agent': 'Mozilla/5.0 (compatible)',
    'Referer': 'https://www.deezer.com/',
    'Origin': 'https://www.deezer.com',
    'Content-Type': 'application/json'
})
payload = {
    "api_version": "1.0",
    "api_token": "",
    "input": "3",
    "method": "deezer.getUserData",
}

resp = req.post("https://www.deezer.com/ajax/gw-light.php", params=payload)
resp.raise_for_status()

error_api = resp.json().get('error', None)
if error_api:
    print(f"API error: {error_api}")
    print('On considère les cookies comme valides.')
    sys.exit(0)

results = resp.json()['results']
if results['USER']['USER_ID'] == 0:
    print("Invalid cookies.")
    sys.exit(1)

print("Cookies are valid.")
sys.exit(0)
