from dotenv import load_dotenv
load_dotenv()

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os

email = os.getenv("DEEZER_EMAIL")
password = os.getenv("DEEZER_PWD")

driver = uc.Chrome()

driver.get("https://account.deezer.com/fr/login/")

wait = WebDriverWait(driver, 3)

try:
    accept_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Accepter')]"))
    )
    accept_btn.click()
except:
    pass

email_field = wait.until(EC.presence_of_element_located((By.ID, "email")))
password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
email_field.send_keys(email)
password_field.send_keys(password)

connect_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-testid='login-button']")))
connect_btn.click()
wait.until(EC.url_changes("https://account.deezer.com/fr/login/"))

for cookie in driver.get_cookies():
    name = cookie.get("name")
    if name in ("arl", "sid"):
        print(f'{name}: {cookie.get("value", "")}')


type(driver).__del__ = lambda self: None #Bug de uc propre à windows
driver.quit()

