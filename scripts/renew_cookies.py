try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import requests
import base64
import nacl.public

def encrypt_secret(public_key_b64: str, secret_value: str) -> str:
    public_key_bytes = base64.b64decode(public_key_b64)
    public_key = nacl.public.PublicKey(public_key_bytes)
    sealed_box = nacl.public.SealedBox(public_key)
    encrypted = sealed_box.encrypt(secret_value.encode("utf-8"))
    return base64.b64encode(encrypted).decode("utf-8")

def get_public_key(repo: str, token: str) -> dict:
    url = f"https://api.github.com/repos/{repo}/actions/secrets/public-key"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()
    return data["key"], data["key_id"]

def update_github_secret(repo: str, token: str, secret_name: str, encrypted_value: str, key_id: str):
    url = f"https://api.github.com/repos/{repo}/actions/secrets/{secret_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {
        "encrypted_value": encrypted_value,
        "key_id": key_id
    }
    response = requests.put(url, headers=headers, json=data)
    response.raise_for_status()
    print(f"Secret {secret_name} updated successfully.")

repo = os.getenv("GITHUB_REPOSITORY")
token = os.getenv("GH_TOKEN")
email = os.getenv("DEEZER_EMAIL")
password = os.getenv("DEEZER_PWD")

cookie_box = {}

options = uc.ChromeOptions()
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--window-size=1920,1080")
driver = uc.Chrome(options=options)

driver.get("https://account.deezer.com/fr/login/")

wait = WebDriverWait(driver, 30)

try:
    accept_btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepter')]"))
    )
    accept_btn.click()
except:
    pass

try:
    email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
except:
    driver.save_screenshot("debug.png")
    raise
password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
email_field.send_keys(email)
password_field.send_keys(password)

connect_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='login-button']")))
connect_btn.click()
wait.until(EC.url_changes("https://account.deezer.com/fr/login/"))

for cookie in driver.get_cookies():
    name = cookie.get("name")
    if name in ("arl", "sid") and name not in cookie_box:
        cookie_box[name] = cookie.get("value")

type(driver).__del__ = lambda self: None #Bug de uc propre à windows
driver.quit()

key, key_id = get_public_key(repo, token)
update_github_secret(repo, token, "TEST_DEEZER_ARL", encrypt_secret(key, cookie_box["arl"]), key_id)
update_github_secret(repo, token, "TEST_DEEZER_SID", encrypt_secret(key, cookie_box["sid"]), key_id)

