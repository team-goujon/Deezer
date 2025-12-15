from selenium import webdriver
from flask import request, redirect, url_for
import time
import logging
logger = logging.getLogger(__name__)

LOGIN_URL = "https://account.deezer.com/fr/login/"

def is_logged(request) -> bool:
    return request.cookies.get('arl') is not None and request.cookies.get('sid') is not None

def login():
    cookie_box = {}
    logger.info("Opening a browser for interactive Deezer login")
    driver = webdriver.Chrome()
    try:
        driver.get(LOGIN_URL)
        deadline = time.time() + 120
        poll_interval = 2
        while time.time() < deadline and not ("arl" in cookie_box and "sid" in cookie_box):
            time.sleep(poll_interval)
            for cookie in driver.get_cookies():
                name = cookie.get("name")
                if name in ("arl", "sid") and name not in cookie_box:
                    cookie_box[name] = cookie.get("value")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    return cookie_box

def require_login(func):
    def wrapper(*args, **kwargs):
        if not is_logged(request):
            logger.info("User not logged in, redirecting to home")
            return redirect(url_for('home'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper